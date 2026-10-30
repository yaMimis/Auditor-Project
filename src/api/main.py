from fastapi import FastAPI
from datetime import datetime, timezone
from src.api.schemas import SolicitacaoEmprestimo, RespostaPrever

#API REST PARA MOTOR DE REGRAS DE NEGOCIO DO SISTEMA

app = FastAPI(
    title="Auditor de Juros - API",
    version= "1.0.0",
    description="API para cálculo de risco, juros justo e auditoria com GenAI"
)

@app.get("/")
def read_root():
    return {"status": "API - AUDITOR OPERACIONAL"}

@app.post("/prever", response_model=RespostaPrever)
def prever_juro_justo(dados: SolicitacaoEmprestimo):
    #necessita endpoint samuel
    #mock temporaria pra testar a integração
    #DADOS SIMULADOS ATE ENDPOINT PRONTO
    pd_mock = 0.184 if dados.income_total > 2000 else 0.350
    faixa_mock = "C" if pd_mock < 0.20 else "D"

    # CONVERSÃO (24.9) P/ (0.249) -> exigida pelo contrato
    juro_cobrado_frac = round(dados.interest_cobrado / 100, 3) 
    
    juro_justo_frac = 0.162
    juro_min = 0.141
    juro_max = 0.183
    
    # Regra da situação do preço
    situacao = "acima_do_justo" if juro_cobrado_frac > juro_max else "dentro_da_margem"

    # Retorno Formatado. O parecer_ia fica como None até entao
    return {
        "contrato_id": dados.loan_id,
        "versao_modelo": "v1-mock",
        "pd": pd_mock,
        "faixa": faixa_mock,
        "juro_cobrado": juro_cobrado_frac,
        "juro_justo": juro_justo_frac,
        "juro_justo_min": juro_min,
        "juro_justo_max": juro_max,
        "situacao_preco": situacao,
        "motivos": [
            {"variavel": "divida_sobre_renda", "efeito": "aumenta_risco"},
            {"variavel": "tempo_no_emprego", "efeito": "reduz_risco"}
        ],
        "alerta_dados": False,
        "parecer_ia": None
    }