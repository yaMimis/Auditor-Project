"""API do Auditor de Preço Justo.

POST /prever:   formulário → prever() real (Samuel) → parecer (gerar_parecer, Maria).
POST /parecer:  parecer para uma saída do prever() já calculada (casos de exemplo, carteira).
POST/GET /decisoes: trilha das decisões do analista no banco (tabela do Marcos).

O parecer recebe a média do BC do mês da concessão (bc_credito_pessoal_aa), buscada no
banco; com ela o código da Maria escreve o contexto_mercado. gerar_parecer() nunca falha:
sem Gemini, sem chave ou sem banco, devolve o template de reserva.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query

from genai.src import cadeia
from src.api import banco
from src.api.schemas import (DecisaoAtual, DecisaoRegistrada, NovaDecisao, Parecer, RespostaPrever,
                             SolicitacaoEmprestimo)
from src.modelos.prever import PACOTE_PADRAO, prever

log = logging.getLogger("api")


@asynccontextmanager
async def ciclo_de_vida(_app: FastAPI):
    # Carrega o modelo de busca nas normas uma vez, na subida (a 1ª carga baixa o modelo).
    try:
        cadeia.carregar_modelo_embeddings()
    except Exception as erro:  # sem sentence-transformers: o parecer segue sem fontes
        log.warning("modelo de busca nas normas indisponível (%s)", erro)
    yield


app = FastAPI(
    title="Auditor de Juros - API",
    version="1.0.0",
    description="API para cálculo de risco, juro justo e auditoria com GenAI",
    lifespan=ciclo_de_vida,
)


@app.get("/")
def read_root():
    return {
        "status": "API - AUDITOR OPERACIONAL",
        "modelo_carregavel": PACOTE_PADRAO.exists(),   # False = falta o .joblib em modelos_salvos/
        "banco_disponivel": banco.banco_disponivel(),  # False = banco fora ou sem a tabela de decisões
    }


# ---------- Risco, juro justo e parecer ----------

def montar_contrato(dados: SolicitacaoEmprestimo) -> dict:
    """Formulário → dict com os nomes do banco, como o prever() espera.

    Todas as chaves abaixo precisam existir (com None quando não houver dado).
    Gênero e idade NÃO entram: servem só para a auditoria de equidade.
    """
    return {
        "loan_id": dados.loan_id,
        "valor_concedido": dados.amount,
        "renda_total": dados.income_total,
        "prazo_meses": dados.loan_duration,
        "data_emprestimo": dados.data_emprestimo.isoformat(),
        "pais": dados.country,
        "juro_aa": dados.interest_cobrado,  # em %; o prever() divide por 100
        "passivos_total": dados.liabilities_total,
        "passivos_existentes": None,
        "n_emprestimos_anteriores": None,
        "valor_emprestimos_anteriores": None,
        "novo_cliente": None,
        "tempo_emprego_atual": None,
        "escolaridade": None,
        "tipo_moradia": None,
        "tipo_verificacao": None,
    }


def _parecer(resultado: dict, data_emprestimo: str | None = None) -> dict:
    """Acrescenta a média do BC do mês e chama o gerar_parecer() da Maria."""
    entrada = {k: v for k, v in resultado.items() if k != "parecer_ia"}
    if entrada.get("bc_credito_pessoal_aa") is None:
        entrada["bc_credito_pessoal_aa"] = banco.taxa_bc(entrada.get("contrato_id"), data_emprestimo)
    return cadeia.gerar_parecer(entrada)


@app.post("/prever", response_model=RespostaPrever)
def prever_juro_justo(dados: SolicitacaoEmprestimo):
    data = dados.data_emprestimo.isoformat()
    try:
        resultado = prever(montar_contrato(dados))
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail=f"Modelo não encontrado em {PACOTE_PADRAO.name}. "
                   "Coloque o arquivo em modelos_salvos/ (ele não vai para o GitHub).",
        )
    resultado["bc_credito_pessoal_aa"] = banco.taxa_bc(data_emprestimo=data)
    return {**resultado, "parecer_ia": _parecer(resultado, data)}


@app.post("/parecer", response_model=Parecer)
def parecer_de_saida_prever(saida: RespostaPrever):
    """Parecer para uma saída do prever() já calculada (casos de exemplo e carteira)."""
    return _parecer(saida.model_dump(mode="json", exclude={"parecer_ia"}))


# ---------- Decisões do analista ----------

def montar_registro(nova: NovaDecisao) -> dict:
    """NovaDecisao → colunas da tabela decisao_analista (sem gênero nem idade).

    Em revisão manual, PD, faixa e juros justos vão nulos (nunca zero).
    """
    r = nova.resultado
    parecer = r.parecer_ia
    return {
        "requisicao_id": nova.requisicao_id,
        "contrato_id": r.contrato_id,
        "analista": nova.analista,
        "decisao": nova.decisao,
        "justificativa": nova.justificativa,
        "taxa_proposta": nova.taxa_proposta if nova.decisao == "revisar_preco" else None,
        "recomendacao_sistema": parecer.recomendacao if parecer else None,
        "situacao_preco": r.situacao_preco,
        "pd": r.pd, "faixa": r.faixa, "juro_cobrado": r.juro_cobrado, "juro_justo": r.juro_justo,
        "juro_justo_min": r.juro_justo_min, "juro_justo_max": r.juro_justo_max,
        "versao_modelo": r.versao_modelo,
        "versao_parecer": parecer.versao_prompt if parecer else None,
        "origem_parecer": parecer.origem if parecer else None,
        "prever_json": r.model_dump(mode="json", exclude={"parecer_ia"}),
        "parecer_json": parecer.model_dump(mode="json") if parecer else None,
    }


def _banco_fora(exc: Exception) -> HTTPException:
    return HTTPException(status_code=503, detail=f"Banco indisponível: {exc}")


@app.post("/decisoes", response_model=DecisaoRegistrada, status_code=201)
def registrar_decisao(nova: NovaDecisao):
    try:
        return banco.registrar_decisao(montar_registro(nova))
    except banco.DecisaoRecusada as exc:
        raise HTTPException(status_code=422, detail=f"O banco recusou a decisão: {exc}")
    except banco.BancoIndisponivel as exc:
        raise _banco_fora(exc)


@app.get("/decisoes", response_model=list[DecisaoRegistrada])
def listar_decisoes(contrato_id: str | None = None, limite: int = Query(200, ge=1, le=5000)):
    try:
        return banco.listar_decisoes(contrato_id, limite)
    except banco.BancoIndisponivel as exc:
        raise _banco_fora(exc)


@app.get("/decisoes/atuais", response_model=list[DecisaoAtual])
def decisoes_atuais():
    """Decisão mais recente de cada contrato da carteira (para marcar "já decidido" na fila)."""
    try:
        return banco.decisoes_atuais()
    except banco.BancoIndisponivel as exc:
        raise _banco_fora(exc)
