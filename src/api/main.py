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

    # Formato de mock corrigido conforme o schemas.py e o Guia v2
    return {
        "contrato_id": dados.loan_id,
        "versao_modelo": "v1.0",
        "pd": 0.15,
        "faixa": "C",
        "juro_cobrado": dados.interest_cobrado / 100, # Convertido para fração
        "juro_justo": 0.19,
        "juro_justo_min": 0.16,
        "juro_justo_max": 0.22,
        "situacao_preco": "abaixo_do_justo",
        "alerta_dados": False,
        "motivos": [
            {"variavel": "divida_renda", "efeito": "aumenta_risco"},
            {"variavel": "historico", "efeito": "reduz_risco"}
        ],
        "parecer_ia": {
            "contrato_id": dados.loan_id,
            "resumo": "Análise preliminar indica juro desfasado do risco.",
            "pontos_de_atencao": ["Risco de fuga do cliente", "Diferença de 4 p.p."],
            "recomendacao_texto": "Sugerida a revisão imediata do preço.",
            "fontes": [],
            "numeros_citados": {"pd": 0.15, "juro_cobrado": 0.249},
            "recomendacao": "revisar_preco",
            "origem": "template",
            "versao_prompt": "v1",
            "gerado_em": "2026-11-04T10:00:00Z"
        }
    }