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
    
    # NOVAS MÉTRICAS SIMULADAS PARA O FRONTEND
    juro_risco_mock = pd_mock + 0.05 # Lógica simples simulada: risco + margem
    juro_mercado_mock = 0.162 # Antigo 'juro_justo' (mediana)
    
    juro_min = 0.141
    juro_max = 0.183
    
    # Regra da situação do preço (agora avaliada contra o Juro de Risco, e não mais contra a mediana)
    situacao = "acima_do_justo" if juro_cobrado_frac > juro_risco_mock else "dentro_da_margem"

    # Formato de mock corrigido conforme o schemas.py e o Guia v2
    return {
        "contrato_id": dados.loan_id,
        "versao_modelo": "v1.0",
        "pd": pd_mock, # Usando a variável gerada no mock em vez do 0.15 fixo
        "faixa": faixa_mock,
        "juro_cobrado": juro_cobrado_frac,
        "juro_risco": juro_risco_mock, # <- NOVO CAMPO: Vai preencher o cartão "Juro por Risco" no Streamlit
        "juro_justo": juro_mercado_mock, # Vai preencher o cartão "Mediana dos Pares" no Streamlit
        "juro_justo_min": juro_min,
        "juro_justo_max": juro_max,
        "situacao_preco": situacao,
        "alerta_dados": False,
        "motivos": [
            {"variavel": "divida_renda", "efeito": "aumenta_risco"},
            {"variavel": "historico", "efeito": "reduz_risco"}
        ],
        "parecer_ia": {
            "contrato_id": dados.loan_id,
            "resumo": "Análise preliminar indica juro desfasado do risco.",
            "pontos_de_atencao": ["Risco de fuga do cliente", "Diferença em relação à PD"],
            "recomendacao_texto": "Sugerida a revisão imediata do preço.",
            "fontes": [],
            "numeros_citados": {"pd": pd_mock, "juro_cobrado": juro_cobrado_frac, "juro_risco": juro_risco_mock},
            "recomendacao": "revisar_preco",
            "origem": "template",
            "versao_prompt": "v1",
            "gerado_em": "2026-11-04T10:00:00Z"
        }
    }