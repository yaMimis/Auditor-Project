"""
Cadeia do parecer: gerar_parecer(saida_prever) -> dict no formato Parecer.

Passo a passo (REGRAS_PARECER.md, seções 7 a 9):
1. valida a saída do prever() (EntradaPrever); inválida -> template de revisão manual;
2. o código escolhe a recomendação; revisão manual -> template (o LLM não é chamado);
3. roda a cadeia RAG em LangChain (LCEL), com 4 passos fixos:
   busca nas normas (pgvector) | prompt (prompt.py) | Gemini (saída estruturada) | conferência;
4. qualquer problema ou erro -> template.
Sem memória: cada parecer é independente (nada é guardado entre contratos; LGPD, art. 6º, III).
Os imports do LangChain ficam dentro das funções: onde ele não estiver instalado (CI mínimo,
imagem sem GenAI), o módulo continua importável e o parecer cai no template.
A função nunca levanta erro para a API: no pior caso, devolve o template.

Teste rápido (na pasta raiz; precisa da GOOGLE_API_KEY no .env):
    python -m genai.src.cadeia
"""
import logging
import os
import warnings
from datetime import datetime

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError

from genai.src.checagem import (EntradaPrever, Fonte, Parecer, RespostaLLM, ajustar_resposta,
                                conferir_parecer, montar_contexto_mercado)
from genai.src.prompt import VERSAO_PROMPT, montar_mensagens
from genai.src.template import FUSO, escolher_recomendacao, montar_template

load_dotenv()
log = logging.getLogger("genai.cadeia")

MODELO_LLM = os.getenv("MODELO_LLM", "gemini-3.5-flash-lite")
SEGUNDOS_POR_TENTATIVA = 10  # mínimo aceito pelo Gemini; 2 tentativas = cerca de 20 s
TENTATIVAS_LLM = 2          # a segunda só acontece em erro temporário (ex.: 503)

MODELO_EMBEDDINGS = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
TABELA = "trechos_normas"
QUANTOS_TRECHOS = 4
# Pergunta extra, igual para todas as situações: o parecer apoia uma decisão de crédito feita
# com um modelo, então o direito de revisão de decisões automatizadas (LGPD, art. 20) é sempre
# pertinente. Entra no máximo 1 trecho dela, depois dos trechos da situação.
PERGUNTA_GOVERNANCA = ("revisão de decisões de crédito tomadas unicamente com base em "
                       "tratamento automatizado de dados pessoais")

# O que procurar nas normas para cada situação do preço (v3: o "acima" focado em transparência
# do preço; a v2 trazia também o CDC art. 42, de cobrança de dívidas, sem relação com o caso).
PERGUNTAS_BUSCA = {
    "acima_do_justo": "informação adequada e clara ao consumidor sobre a taxa efetiva de juros, "
                      "o custo efetivo total e o preço do crédito",
    "abaixo_do_justo": "composição do custo do crédito: inadimplência, custo de captação, "
                       "despesas administrativas e margem; preço que não cobre a perda esperada",
    "dentro_da_margem": "informação clara ao consumidor sobre a taxa de juros efetiva "
                        "e o custo efetivo total do contrato de crédito",
}


# ---------- Busca nas normas (pgvector) ----------

_modelo_embeddings = None


def carregar_modelo_embeddings():
    """Carrega o modelo de embeddings uma vez só. A API chama isto quando sobe."""
    global _modelo_embeddings
    if _modelo_embeddings is None:
        from sentence_transformers import SentenceTransformer
        _modelo_embeddings = SentenceTransformer(MODELO_EMBEDDINGS)
    return _modelo_embeddings


def _consultar_banco(pergunta: str, quantos: int) -> list[dict]:
    import psycopg2
    from pgvector.psycopg2 import register_vector

    vetor = carregar_modelo_embeddings().encode(pergunta, normalize_embeddings=True)
    conexao = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=3)
    try:
        register_vector(conexao)
        with conexao.cursor() as cursor:
            cursor.execute(
                f"SELECT trecho_id, norma, artigo, texto FROM {TABELA} "
                "ORDER BY embedding <=> %s LIMIT %s",
                (vetor, quantos),
            )
            linhas = cursor.fetchall()
    finally:
        conexao.close()
    return [{"trecho_id": t, "norma": n, "artigo": a, "texto": x} for t, n, a, x in linhas]


def buscar_trechos(entrada: EntradaPrever, quantos: int = QUANTOS_TRECHOS) -> list[dict]:
    """Trechos de normas para o contrato. Se o banco não responder, segue sem trechos."""
    try:
        trechos = _consultar_banco(PERGUNTAS_BUSCA[entrada.situacao_preco], quantos)
        ids = {t["trecho_id"] for t in trechos}
        extras = [t for t in _consultar_banco(PERGUNTA_GOVERNANCA, 2) if t["trecho_id"] not in ids]
        return trechos + extras[:1]
    except Exception as erro:  # sem Docker, sem biblioteca ou sem DATABASE_URL
        log.warning("busca nas normas indisponível (%s): parecer segue sem fontes", erro)
        return []


# ---------- Chamada ao Gemini ----------

class _NumerosGemini(BaseModel):
    """O Gemini não aceita dicionário livre no esquema: cada número vira um campo."""
    pd: float | None = None
    juro_cobrado: float | None = None
    juro_justo: float | None = None
    juro_justo_min: float | None = None
    juro_justo_max: float | None = None


class _RespostaGemini(BaseModel):
    resumo: str
    pontos_de_atencao: list[str] = Field(max_length=3)
    recomendacao_texto: str
    fontes: list[Fonte]
    numeros_citados: _NumerosGemini


def _para_resposta_llm(bruta: _RespostaGemini) -> RespostaLLM:
    dados = bruta.model_dump()
    dados["numeros_citados"] = {k: v for k, v in dados["numeros_citados"].items() if v is not None}
    return RespostaLLM.model_validate(dados)


def chamar_llm(sistema: str, usuario: str) -> RespostaLLM:
    """Gemini via LangChain, com saída estruturada. Erros sobem para gerar_parecer() tratar."""
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_google_genai import ChatGoogleGenerativeAI

    modelo = ChatGoogleGenerativeAI(
        model=MODELO_LLM,
        temperature=0,
        timeout=SEGUNDOS_POR_TENTATIVA,
        max_retries=TENTATIVAS_LLM - 1,  # a 1ª chamada + 1 nova tentativa em erro temporário
    )
    estruturado = modelo.with_structured_output(_RespostaGemini)
    with warnings.catch_warnings():
        # Os modelos Gemini mais novos ignoram a temperatura (amostragem fixa) e o LangChain avisa
        # a cada chamada. Mantemos temperature=0 para os modelos que a aceitam e calamos o aviso.
        warnings.filterwarnings("ignore", message=".*fixed sampling defaults.*")
        bruta = estruturado.invoke([SystemMessage(content=sistema), HumanMessage(content=usuario)])
    return _para_resposta_llm(bruta)


# ---------- Cadeia RAG (LangChain LCEL) ----------
# Cada passo recebe e devolve um dicionário de estado. As funções de fora (buscar_trechos,
# montar_mensagens, chamar_llm, conferir_parecer) são chamadas na hora: os testes podem trocá-las.

DECISAO = "A decisão final é do analista."


def _passo_busca(estado: dict) -> dict:
    return {**estado, "trechos": buscar_trechos(estado["entrada"])}


def _passo_prompt(estado: dict) -> dict:
    sistema, usuario = montar_mensagens(estado["entrada"], estado["recomendacao"], estado["trechos"])
    return {**estado, "sistema": sistema, "usuario": usuario}


def _passo_llm(estado: dict) -> dict:
    return {**estado, "resposta": chamar_llm(estado["sistema"], estado["usuario"])}


def _passo_conferencia(estado: dict) -> dict:
    resposta = estado["resposta"]
    if not resposta.recomendacao_texto.rstrip().endswith(DECISAO):
        resposta.recomendacao_texto = f"{resposta.recomendacao_texto.rstrip()} {DECISAO}"
    problemas = conferir_parecer(resposta, estado["entrada"], [t["trecho_id"] for t in estado["trechos"]])
    # Os ajustes vêm DEPOIS da conferência, que vê a resposta original do LLM. Eles só tiram texto ou
    # fontes; nunca acrescentam. Assim não escondem um erro que a conferência recusaria.
    if not problemas:
        ajustes = ajustar_resposta(resposta)
        if ajustes:
            log.info("ajustes de estilo no parecer do LLM: %s", "; ".join(ajustes))
    return {**estado, "resposta": resposta, "problemas": problemas}


PASSOS = (
    ("busca_normas", _passo_busca),
    ("monta_prompt", _passo_prompt),
    ("gemini", _passo_llm),
    ("conferencia", _passo_conferencia),
)


class _CadeiaSemLangChain:
    """Os mesmos 4 passos, em sequência, para quando o LangChain não está instalado."""

    def invoke(self, estado: dict) -> dict:
        for _, passo in PASSOS:
            estado = passo(estado)
        return estado


def _montar_cadeia_rag():
    """busca_normas | monta_prompt | gemini | conferencia, como uma chain LCEL."""
    try:
        from langchain_core.runnables import RunnableLambda
    except ImportError:
        log.info("LangChain não instalado: os mesmos passos rodam em sequência")
        return _CadeiaSemLangChain()
    nome, passo = PASSOS[0]
    cadeia = RunnableLambda(passo, name=nome)
    for nome, passo in PASSOS[1:]:
        cadeia = cadeia | RunnableLambda(passo, name=nome)
    return cadeia


# ---------- A função que a API chama ----------


def _entrada_de_revisao(saida: dict) -> EntradaPrever:
    """Saída do prever() fora do contrato: tratada como revisão manual."""
    return EntradaPrever.model_validate({
        "contrato_id": saida.get("contrato_id", "desconhecido"),
        "versao_modelo": saida.get("versao_modelo", "desconhecida"),
        "juro_cobrado": saida["juro_cobrado"],
        "situacao_preco": "revisao_manual",
        "alerta_dados": True,
    })


def gerar_parecer(saida_prever: dict) -> dict:
    """Parecer para uma saída do prever(). Nunca falha: no pior caso, devolve o template."""
    try:
        entrada = EntradaPrever.model_validate(saida_prever)
    except ValidationError as erro:
        log.warning("saída do prever() fora do contrato (%s erro(s)): revisão manual",
                    erro.error_count())
        entrada = _entrada_de_revisao(saida_prever)

    recomendacao = escolher_recomendacao(entrada)
    if entrada.vai_para_revisao_manual:
        return montar_template(entrada).model_dump()

    try:
        estado = _montar_cadeia_rag().invoke({"entrada": entrada, "recomendacao": recomendacao})
    except Exception as erro:
        log.warning("LLM indisponível ou resposta inválida (%s): template", erro)
        return montar_template(entrada).model_dump()

    if estado["problemas"]:
        log.warning("conferência recusou o parecer do LLM: %s", "; ".join(estado["problemas"]))
        return montar_template(entrada).model_dump()

    resposta = estado["resposta"]
    return Parecer(
        **resposta.model_dump(),
        contrato_id=entrada.contrato_id,
        recomendacao=recomendacao,
        origem="llm",
        versao_prompt=VERSAO_PROMPT,
        gerado_em=datetime.now(FUSO),
        contexto_mercado=montar_contexto_mercado(entrada),
    ).model_dump()


if __name__ == "__main__":
    import json
    import time
    from pathlib import Path

    logging.basicConfig(level=logging.WARNING, format="  [aviso] %(message)s")
    casos = json.loads(Path("docs/casos_de_teste.json").read_text(encoding="utf-8"))
    for situacao, lista in casos.items():
        caso = lista[0]
        inicio = time.time()
        parecer = gerar_parecer(caso)
        print(f"\n=== {situacao} | origem: {parecer['origem']} | {time.time() - inicio:.1f} s")
        print("resumo:", parecer["resumo"])
        for ponto in parecer["pontos_de_atencao"]:
            print(" -", ponto)
        print("recomendação:", parecer["recomendacao_texto"])
        print("fontes:", [f["trecho_id"] for f in parecer["fontes"]] or "nenhuma")