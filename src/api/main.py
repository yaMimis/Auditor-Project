from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

#API REST PARA MOTOR DE REGRAS DE NEGOCIO DO SISTEMA

app = FastAPI(
    title="Auditor de Juros - API",
    version= "1.0.0",
    descriptions="API para cálculo de risco e juros justo"
)

class SolicitacaoEmprestimo(BaseModel):
    loan_id: int
    amount: float
    income_total: float
    employment_status: Optional[str] = "Unemployed"
    verification_type: Optional[str] = "Not Verified"
    gender: str
    age: int
    country: str
    interest_cobrado: float

class RespostaPrever(BaseModel):
    loan_id: int
    pd: float
    faixa_risco: str    
    juro_cobrado_am: float  #taxa real cobrada usando %a.m
    juro_justo_am: float   #taxa calculada pelo motor %a.m
    delta_injustica: float  #taxa calculada entre cobrado e o justo
    fora_margem: bool
    motivos_shap: List[str] #principais fatores de risco RAG
    alerta_vies: bool

@app.get("/")
def read_root():
    return {"status": "API - AUDITOR OPERACIONAL"}

@app.post("/prever", response_model=RespostaPrever)
def prever_juro_justo(dados: SolicitacaoEmprestimo):
    #necessita endpoint samuel
    #mock temporaria pra testar a integração
    #DADOS SIMULADOS ATE ENDPOINT PRONTO
    pd_mock = 0.12 if dados.income_total > 2000 else 0.35
    faixa_mock = "B" if pd_mock < 0.20 else "D"
    juro_justo_mock = round(1.5 + (pd_mock * 3.0), 2)
    delta_mock = round(dados.interest_cobrado - juro_justo_mock, 2)

    return {
        "loan_id": dados.loan_id,
        "pd": pd_mock,
        "faixa_risco": faixa_mock,
        "juro_cobrado_am": dados.interest_cobrado,
        "juro_justo_am": juro_justo_mock,
        "delta_injustica": delta_mock,
        "fora_margem": True if delta_mock > 1.0 else False,
        "motivos_shap": [
            "TESTE"
        ],
        "alerta_vies": True if dados.country == "ES" and delta_mock > 1.5 else False
    }