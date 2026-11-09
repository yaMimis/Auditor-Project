"""API do Auditor de Preço Justo.

POST /prever: converte o formulário para os nomes do banco, chama o prever() real
(Samuel) e anexa o parecer. Enquanto o gerar_parecer() da Maria não existe, o parecer
vem do template de reserva (origem "template"), que segue as mesmas regras.
"""
from fastapi import FastAPI, HTTPException

from genai.src.checagem import EntradaPrever, Parecer
from genai.src.template import montar_template
from src.api.schemas import RespostaPrever, SolicitacaoEmprestimo
from src.modelos.prever import PACOTE_PADRAO, prever
from src.api import banco

app = FastAPI(
    title="Auditor de Juros - API",
    version="1.0.0",
    description="API para cálculo de risco, juro justo e auditoria com GenAI",
)


@app.get("/")
def read_root():
    return {
        "status": "API - AUDITOR OPERACIONAL",
        "modelo_carregavel": PACOTE_PADRAO.exists(),  # False = falta o .joblib em modelos_salvos/
        "banco_disponivel": banco.banco_disponivel(),
    }


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


@app.post("/prever", response_model=RespostaPrever)
def prever_juro_justo(dados: SolicitacaoEmprestimo):
    try:
        resultado = prever(montar_contrato(dados))
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail=f"Modelo não encontrado em {PACOTE_PADRAO.name}. "
                   "Coloque o arquivo em modelos_salvos/ (ele não vai para o GitHub).",
        )

    return {**resultado, "parecer_ia": _parecer(resultado)}


@app.post("/parecer", response_model=Parecer)
def parecer_de_saida_prever(saida: RespostaPrever):
    """Gera o parecer para uma saída do prever() já calculada (exemplos e carteira)."""
    return _parecer(saida.model_dump(exclude={"parecer_ia"}))


def _parecer(resultado: dict) -> dict:
    # TODO (Maria, até 08/11): trocar o template por gerar_parecer(resultado).
    return montar_template(EntradaPrever.model_validate(resultado)).model_dump()

@app.post("/decisoes", status_code=201)
def registrar_decisao(payload: dict):
    resultado = payload.get("resultado") or {}
    parecer = resultado.get("parecer_ia") or {}
    
    if resultado.get("situacao_preco") == "revisao_manual":
        raise HTTPException(status_code=422, detail="Contratos em revisão manual não podem ter decisões gravadas.")
        
    justificativa = payload.get("justificativa", "")
    if not justificativa.strip():
        raise HTTPException(status_code=422, detail="A justificativa não pode estar em branco.")

    # Remove o parecer_ia de dentro do dicionário guardado como prever_json
    prever_limpo = {k: v for k, v in resultado.items() if k != "parecer_ia"}

    registro_banco = {
        "requisicao_id": payload.get("requisicao_id"),
        "contrato_id": resultado.get("contrato_id"),
        "analista": payload.get("analista"),
        "decisao": payload.get("decisao"),
        "justificativa": justificativa,
        "taxa_proposta": payload.get("taxa_proposta") if payload.get("decisao") == "revisar_preco" else None,
        "recomendacao_sistema": parecer.get("recomendacao"),
        "situacao_preco": resultado.get("situacao_preco"),
        "pd": resultado.get("pd"),
        "faixa": resultado.get("faixa"),
        "juro_cobrado": resultado.get("juro_cobrado"),
        "juro_justo": resultado.get("juro_justo"),
        "juro_justo_min": resultado.get("juro_justo_min"),
        "juro_justo_max": resultado.get("juro_justo_max"),
        "versao_modelo": resultado.get("versao_modelo"),
        "versao_parecer": parecer.get("versao_prompt"),
        "origem_parecer": parecer.get("origem"),
        "prever_json": prever_limpo,
        "parecer_json": parecer,
    }

    try:
        return banco.registrar_decisao(registro_banco)
    except banco.BancoIndisponivel as e:
        raise HTTPException(status_code=503, detail=str(e))
    except banco.DecisaoRecusada as e:
        raise HTTPException(status_code=422, detail=str(e))

@app.get("/decisoes")
def listar_decisoes(contrato_id: str = None, limite: int = 200):
    try:
        return banco.listar_decisoes(contrato_id, limite)
    except banco.BancoIndisponivel as e:
        raise HTTPException(status_code=503, detail=str(e))

@app.get("/decisoes/atuais")
def decisoes_atuais():
    try:
        return banco.decisoes_atuais()
    except banco.BancoIndisponivel as e:
        raise HTTPException(status_code=503, detail=str(e))