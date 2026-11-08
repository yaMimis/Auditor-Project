"""
Cadeia do parecer: gerar_parecer(saida_prever) -> dict no formato Parecer.

Passo a passo (REGRAS_PARECER.md, seções 7 a 9):
1. valida a saída do prever() (EntradaPrever); inválida -> template de revisão manual;
2. o código escolhe a recomendação; revisão manual -> template (o LLM não é chamado);
3. busca os trechos de normas no pgvector (sem banco -> segue sem trechos);
4. monta o prompt (prompt.py) e chama o Gemini com saída estruturada;
5. confere o resultado (conferir_parecer); qualquer problema ou erro -> template.
A função nunca levanta erro para a API: no pior caso, devolve o template.

Teste rápido (na pasta raiz; precisa da GOOGLE_API_KEY no .env):
    python -m genai.src.cadeia
"""
import logging
import os
from datetime import datetime

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError

from genai.src.checagem import (EntradaPrever, Fonte, Parecer, RespostaLLM, conferir_parecer,
                                montar_contexto_mercado)
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

# O que procurar nas normas para cada situação do preço.
PERGUNTAS_BUSCA = {
    "acima_do_justo": "juro cobrado acima do justo para o risco; informação clara ao consumidor "
                      "sobre a taxa de juros e o custo efetivo total do crédito",
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
        return _consultar_banco(PERGUNTAS_BUSCA[entrada.situacao_preco], quantos)
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
    """Chama o Gemini com saída estruturada. Erros sobem para gerar_parecer() tratar."""
    from google import genai
    from google.genai import types

    cliente = genai.Client(http_options=types.HttpOptions(
        timeout=SEGUNDOS_POR_TENTATIVA * 1000,
            retry_options=types.HttpRetryOptions(attempts=TENTATIVAS_LLM, initial_delay=0.5, max_delay=1.0),
    ))
    resposta = cliente.models.generate_content(
        model=MODELO_LLM,
        contents=usuario,
        config=types.GenerateContentConfig(
            system_instruction=sistema,
            temperature=0,
            response_mime_type="application/json",
            response_schema=_RespostaGemini,
        ),
    )
    return _para_resposta_llm(_RespostaGemini.model_validate_json(resposta.text))


# ---------- A função que a API chama ----------

DECISAO = "A decisão final é do analista."


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

    trechos = buscar_trechos(entrada)
    try:
        sistema, usuario = montar_mensagens(entrada, recomendacao, trechos)
        resposta = chamar_llm(sistema, usuario)
    except Exception as erro:
        log.warning("LLM indisponível ou resposta inválida (%s): template", erro)
        return montar_template(entrada).model_dump()

    if not resposta.recomendacao_texto.rstrip().endswith(DECISAO):
        resposta.recomendacao_texto = f"{resposta.recomendacao_texto.rstrip()} {DECISAO}"

    problemas = conferir_parecer(resposta, entrada, [t["trecho_id"] for t in trechos])
    if problemas:
        log.warning("conferência recusou o parecer do LLM: %s", "; ".join(problemas))
        return montar_template(entrada).model_dump()

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