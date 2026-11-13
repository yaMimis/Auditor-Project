"""API do Auditor de Preço Justo.

GET  /portfolio/overview · GET /contracts · /contracts/ids · /contracts/export · /contracts/{id}:
     o lote da carteira (prever() rodado em toda a base), para a Home e a lista de contratos.
GET  /contracts/{id}/analysis: contrato da base buscado no banco → prever() ao vivo → parecer,
     com as variáveis usadas, os parâmetros do preço e o desfecho real (quando existe).
POST /predict:  dados de um contrato → prever() real (Samuel) → parecer (gerar_parecer, Maria).
POST /opinion:  parecer para uma saída do prever() já calculada (casos de exemplo, carteira).
POST/GET /decisions: trilha das decisões do analista no banco (tabela do Marcos).

O parecer recebe a média do BC do mês da concessão (bc_credito_pessoal_aa), buscada no
banco; com ela o código da Maria escreve o contexto_mercado. gerar_parecer() nunca falha:
sem Gemini, sem chave ou sem banco, devolve o template de reserva.
"""
import logging
import os
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query, Response

from genai.src import cadeia
from src.api import contract_analysis, database, portfolio
from src.api.schemas import (ContractAnalysis, ContractList, CurrentDecision, LoanRequest, NewDecision, Parecer,
                             PortfolioOverview, PredictionResponse, RecordedDecision)
from src.modelos import prever as modelo
from src.modelos.prever import PACOTE_PADRAO, prever

log = logging.getLogger("api")


EMBEDDINGS_STATE = {"situacao": "carregando"}  # carregando · pronto · indisponivel


def _load_embeddings() -> None:
    """Carrega o modelo de busca nas normas (a 1ª vez baixa ~0,5 GB). Roda em segundo plano."""
    try:
        cadeia.carregar_modelo_embeddings()
        EMBEDDINGS_STATE["situacao"] = "pronto"
    except Exception as error_msg:  # sem sentence-transformers: o parecer segue sem fontes
        EMBEDDINGS_STATE["situacao"] = "indisponivel"
        log.warning("modelo de busca nas normas indisponível (%s)", error_msg)


@asynccontextmanager
async def lifespan_handler(_app: FastAPI):
    # Em segundo plano: a API responde (e o healthcheck passa) mesmo durante o download do
    # modelo de busca. Antes, a subida esperava o download e, em rede lenta, o Docker dava
    # o container como "unhealthy" antes de ele terminar.
    threading.Thread(target=_load_embeddings, name="carregar-embeddings", daemon=True).start()
    yield


app = FastAPI(
    title="Auditor de Juros - API",
    version="1.0.0",
    description="API para cálculo de risco, juro justo e auditoria com GenAI",
    lifespan=lifespan_handler,
)


@app.get("/")
def read_root():
    """Estado de cada parte, separado: uma parte fora não derruba as outras."""
    return {
        "status": "API - AUDITOR OPERACIONAL",
        "modelo_carregavel": PACOTE_PADRAO.exists(),   # False = falta o .joblib em modelos_salvos/
        "banco_disponivel": database.database_available(),  # False = banco fora ou sem a tabela de decisões
        "versao_modelo": modelo.VERSAO,
        "pacote_modelo": PACOTE_PADRAO.name,
        "pacote_hash": contract_analysis.package_identity(PACOTE_PADRAO)["pacote_hash"],
        "genai_configurada": bool(os.getenv("GOOGLE_API_KEY")),  # False = parecer sai pelo template
        "busca_normas": EMBEDDINGS_STATE["situacao"],  # "carregando" na 1ª subida (download do modelo de busca)
    }


# ---------- Risco, juro justo e parecer ----------

def build_contract(loan_request: LoanRequest) -> dict:
    """Formulário → dict com os nomes do banco, como o prever() espera.

    Todas as chaves abaixo precisam existir (com None quando não houver dado).
    Gênero e idade NÃO entram: servem só para a auditoria de equidade.
    """
    return {
        "loan_id": loan_request.loan_id,
        "valor_concedido": loan_request.amount,
        "renda_total": loan_request.income_total,
        "prazo_meses": loan_request.loan_duration,
        "data_emprestimo": loan_request.data_emprestimo.isoformat(),
        "pais": loan_request.country,
        "juro_aa": loan_request.interest_cobrado,  # em %; o prever() divide por 100
        "passivos_total": loan_request.liabilities_total,
        "passivos_existentes": None,
        "n_emprestimos_anteriores": None,
        "valor_emprestimos_anteriores": None,
        "novo_cliente": None,
        "tempo_emprego_atual": None,
        "escolaridade": None,
        "tipo_moradia": None,
        "tipo_verificacao": None,
    }


def _opinion(resultado: dict, data_emprestimo: str | None = None) -> dict:
    """Acrescenta a média do BC do mês e chama o gerar_parecer() da Maria."""
    input_data = {k: v for k, v in resultado.items() if k != "parecer_ia"}
    if input_data.get("bc_credito_pessoal_aa") is None:
        input_data["bc_credito_pessoal_aa"] = database.bc_rate(input_data.get("contrato_id"), data_emprestimo)
    return cadeia.gerar_parecer(input_data)


@app.post("/predict", response_model=PredictionResponse)
def predict_fair_rate(loan_request: LoanRequest):
    loan_date = loan_request.data_emprestimo.isoformat()
    try:
        resultado = prever(build_contract(loan_request))
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail=f"Modelo não encontrado em {PACOTE_PADRAO.name}. "
                   "Coloque o arquivo em modelos_salvos/ (ele não vai para o GitHub).",
        )
    resultado["bc_credito_pessoal_aa"] = database.bc_rate(data_emprestimo=loan_date)
    return {**resultado, "parecer_ia": _opinion(resultado, loan_date)}


@app.post("/opinion", response_model=Parecer)
def opinion_from_prediction(output: PredictionResponse):
    """Parecer para uma saída do prever() já calculada (casos de exemplo e carteira)."""
    return _opinion(output.model_dump(mode="json", exclude={"parecer_ia"}))


# ---------- Lote da carteira (Home e lista de contratos) ----------
SituationFilter = Literal["acima_do_justo", "abaixo_do_justo", "dentro_da_margem", "revisao_manual"]


def _portfolio():
    """O lote como DataFrame, ou 503 com a explicação (arquivo ausente ou inválido)."""
    try:
        df = portfolio.cached_portfolio()
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=503, detail=f"Lote da carteira inválido: {exc}")
    if df is None:
        raise HTTPException(status_code=503, detail=(
            f"Lote da carteira ausente: falta {portfolio.PORTFOLIO_FILE} em docs/resultados/ "
            "(gerado pelo processo em lote do modelo)."))
    return df


@app.get("/portfolio/overview", response_model=PortfolioOverview)
def portfolio_overview(year_min: int | None = None, year_max: int | None = None,
                       country: str | None = None, band: str | None = None):
    df = _portfolio()
    years = (year_min, year_max) if year_min is not None and year_max is not None else None
    try:
        fairness = portfolio.load_fairness()
    except (ValueError, OSError):
        fairness = None
    return portfolio.overview(df, fairness, years=years, pais=country, faixa=band)


@app.get("/contracts", response_model=ContractList)
def list_contracts(situation: SituationFilter | None = None, offset: int = Query(0, ge=0),
                   limit: int = Query(25, ge=1, le=200)):
    """Contratos do lote, do mais distante para o mais próximo da margem."""
    df = _portfolio()
    listing = df if situation is None else df[df["situacao_preco"] == situation]
    return {"total": len(listing), "itens": portfolio.records(listing.iloc[offset:offset + limit])}


@app.get("/contracts/ids", response_model=list[str])
def contract_ids(limit: int = Query(5000, ge=1, le=20000)):
    """IDs para a caixa de busca, dos mais distantes da margem para os mais próximos."""
    return _portfolio()["contrato_id"].astype(str).head(limit).tolist()


@app.get("/contracts/export")
def export_contracts(situation: SituationFilter | None = None):
    """CSV da lista completa (UTF-8 com BOM, abre certo no Excel)."""
    df = _portfolio()
    listing = df if situation is None else df[df["situacao_preco"] == situation]
    return Response(portfolio.export_contracts(listing), media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=contratos_da_base.csv"})


@app.get("/contracts/{contrato_id}", response_model=dict[str, Any])
def contract_from_batch(contrato_id: str):
    """Uma linha do lote (números calculados antes). A tela usa no plano B."""
    row = portfolio.find_contract(_portfolio(), contrato_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Contrato {contrato_id} não está no lote da carteira.")
    return row


# ---------- Contrato da base, calculado na hora ----------
MODEL_MISSING = ("Modelo não encontrado em {}. Coloque o arquivo em modelos_salvos/ "
                 "(ele não vai para o GitHub).")


def _uncertainty(resultado: dict) -> str:
    return ("nao_calculada" if resultado.get("pd") is None
            else "bootstrap" if resultado.get("pd_ic95") else "margem_padrao")


def _analysis_from_batch(contrato_id: str, reason: str, not_found: bool = False,
                         database_down: bool = False) -> dict:
    """Plano B: os números do lote para este contrato, marcados como "lote" (nunca como ao vivo).

    Sem linha no lote: 404 se o contrato não existe no banco; 503 se o banco ou o modelo caiu."""
    try:
        batch = portfolio.cached_portfolio()
    except (ValueError, OSError):
        batch = None
    row = portfolio.find_contract(batch, contrato_id) if batch is not None else None
    if row is None:
        if not_found:
            raise HTTPException(status_code=404, detail=f"Contrato {contrato_id} não encontrado no banco nem no lote.")
        raise HTTPException(status_code=503, detail=f"{reason[0].upper()}{reason[1:]}; o contrato também não está no lote.")
    resultado = contract_analysis.batch_result(row)
    if database_down:  # sem banco: nem tenta a referência do BC (evita esperar o timeout de novo)
        resultado["bc_credito_pessoal_aa"] = None
        resultado["parecer_ia"] = cadeia.gerar_parecer(dict(resultado))
    else:
        resultado["bc_credito_pessoal_aa"] = database.bc_rate(resultado["contrato_id"])
        resultado["parecer_ia"] = _opinion(resultado)
    log.warning("análise de %s pelo lote: %s", contrato_id, reason)
    return {
        "resultado": resultado,
        "contrato": contract_analysis.batch_summary(row),
        "dados_considerados": [],
        "precificacao": None,
        "resultado_observado": None,
        "procedencia": {
            "modo": "lote", "motivo_lote": reason,
            "versao_modelo": resultado["versao_modelo"], "calculado_em": None, "tempo_ms": 0,
            "origem_dados": f"lote ({portfolio.PORTFOLIO_FILE}), calculado antes pelo prever()",
            "fora_do_dominio": bool(resultado.get("alerta_dados")),
            "incerteza": _uncertainty(resultado),
            "pacote_arquivo": portfolio.PORTFOLIO_FILE,
        },
    }


@app.get("/contracts/{contrato_id}/analysis", response_model=ContractAnalysis)
def analyze_contract(contrato_id: str):
    """Busca o contrato no banco, roda o prever() agora e devolve tudo o que a tela de análise mostra.

    Plano B (aqui, não no painel): se o banco ou o modelo falharem, ou o contrato não estiver no
    banco, devolve os números do lote com procedencia.modo = "lote" e o motivo. 404: não está no
    banco nem no lote. 503: banco ou modelo fora e o contrato também não está no lote."""
    started = time.perf_counter()
    try:
        row = database.load_contract(contrato_id)
    except database.DatabaseUnavailable as exc:
        return _analysis_from_batch(contrato_id, f"banco indisponível ({exc})", database_down=True)
    if row is None:
        return _analysis_from_batch(contrato_id, "contrato não encontrado no banco", not_found=True)
    try:
        package = modelo._pacote()
        resultado = prever(row, package)
    except FileNotFoundError:
        return _analysis_from_batch(contrato_id, MODEL_MISSING.format(PACOTE_PADRAO.name))
    loan_date = contract_analysis.contract_summary(row)["data_emprestimo"]
    resultado["bc_credito_pessoal_aa"] = database.bc_rate(resultado["contrato_id"], loan_date)
    resultado["parecer_ia"] = _opinion(resultado, loan_date)
    try:
        outcome = database.observed_outcome(contrato_id)
    except database.DatabaseUnavailable:
        outcome = None
    return {
        "resultado": resultado,
        "contrato": contract_analysis.contract_summary(row),
        "dados_considerados": contract_analysis.considered_data(row, package),
        "precificacao": contract_analysis.pricing_parameters(row, resultado, package),
        "resultado_observado": outcome,
        "procedencia": {
            "versao_modelo": resultado.get("versao_modelo") or modelo.VERSAO,
            "calculado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "tempo_ms": int((time.perf_counter() - started) * 1000),
            "origem_dados": "banco (emprestimo, cliente, historico_credito) + prever() ao vivo",
            "fora_do_dominio": bool(resultado.get("alerta_dados")),
            "modo": "ao_vivo",
            "incerteza": _uncertainty(resultado),
            **contract_analysis.package_identity(PACOTE_PADRAO, package),
        },
    }


# ---------- Decisões do analista ----------

def build_record(new: NewDecision) -> dict:
    """NewDecision → colunas da tabela decisao_analista (sem gênero nem idade).

    Em revisão manual, PD, faixa e juros justos vão nulos (nunca zero).
    """
    r = new.resultado
    opinion = r.parecer_ia
    return {
        "requisicao_id": new.requisicao_id,
        "contrato_id": r.contrato_id,
        "analista": new.analista,
        "decisao": new.decisao,
        "justificativa": new.justificativa,
        "taxa_proposta": new.taxa_proposta if new.decisao == "revisar_preco" else None,
        "recomendacao_sistema": opinion.recomendacao if opinion else None,
        "situacao_preco": r.situacao_preco,
        "pd": r.pd, "faixa": r.faixa, "juro_cobrado": r.juro_cobrado, "juro_justo": r.juro_justo,
        "juro_justo_min": r.juro_justo_min, "juro_justo_max": r.juro_justo_max,
        "versao_modelo": r.versao_modelo,
        "versao_parecer": opinion.versao_prompt if opinion else None,
        "origem_parecer": opinion.origem if opinion else None,
        "prever_json": r.model_dump(mode="json", exclude={"parecer_ia"}),
        "parecer_json": opinion.model_dump(mode="json") if opinion else None,
    }


def _database_down(exc: Exception) -> HTTPException:
    return HTTPException(status_code=503, detail=f"Banco indisponível: {exc}")


@app.post("/decisions", response_model=RecordedDecision, status_code=201)
def record_decision(new: NewDecision):
    try:
        return database.record_decision(build_record(new))
    except database.DecisionRejected as exc:
        raise HTTPException(status_code=422, detail=f"O banco recusou a decisão: {exc}")
    except database.DatabaseUnavailable as exc:
        raise _database_down(exc)


@app.get("/decisions", response_model=list[RecordedDecision])
def list_decisions(contrato_id: str | None = None, limit: int = Query(200, ge=1, le=5000)):
    try:
        return database.list_decisions(contrato_id, limit)
    except database.DatabaseUnavailable as exc:
        raise _database_down(exc)


@app.get("/decisions/current", response_model=list[CurrentDecision])
def current_decisions():
    """Decisão mais recente de cada contrato da carteira (para marcar "já decidido" na fila)."""
    try:
        return database.current_decisions()
    except database.DatabaseUnavailable as exc:
        raise _database_down(exc)
