"""Testes da conferência de números e fontes do parecer (genai/src/checagem.py).

Rodar na pasta raiz:  python -m pytest tests/genai -q
"""
from genai.src.checagem import (EntradaPrever, RespostaLLM, conferir_parecer,
                                extrair_numeros, formatar_juro, formatar_percentual)

ENTRADA = EntradaPrever.model_validate({
    "contrato_id": "TESTE-1", "versao_modelo": "teste",
    "pd": 0.184, "faixa": "C", "juro_cobrado": 0.249,
    "juro_justo": 0.162, "juro_justo_min": 0.141, "juro_justo_max": 0.183,
    "situacao_preco": "acima_do_justo",
})

ENTRADA_REVISAO = EntradaPrever.model_validate({
    "contrato_id": "TESTE-2", "versao_modelo": "teste", "pd": None, "faixa": None,
    "juro_cobrado": 0.22, "situacao_preco": "revisao_manual", "alerta_dados": True,
})

TRECHOS = ["cdc-art6-1", "cdc-art52-1", "res4881-art2-1"]

# Exemplo 5.1 do FORMATO_JSON.md
RESPOSTA = {
    "resumo": "Cliente de risco moderado (faixa C, chance de não pagar de 18,4%). Se este "
              "contrato fosse de um banco brasileiro, o juro cobrado estaria acima do juro justo.",
    "pontos_de_atencao": [
        "O juro cobrado (24,9% ao ano) está acima da margem do juro justo estimado "
        "(14,1% a 18,3% ao ano; valor central 16,2% ao ano).",
        "A diferença não é explicada pelo risco estimado pelo modelo.",
    ],
    "recomendacao_texto": "Recomenda-se revisar o preço. A decisão final é do analista.",
    "fontes": [{"norma": "CDC", "artigo": "art. 6º, III", "trecho_id": "cdc-art6-1"}],
    "numeros_citados": {"pd": 0.184, "juro_cobrado": 0.249, "juro_justo": 0.162,
                        "juro_justo_min": 0.141, "juro_justo_max": 0.183},
}


def resposta(**mudancas):
    return RespostaLLM.model_validate({**RESPOSTA, **mudancas})


# ---------- formatação ----------

def test_formata_percentual_com_virgula():
    assert formatar_percentual(0.184) == "18,4%"


def test_formata_juro_com_unidade():
    assert formatar_juro(0.249) == "24,9% ao ano (nominal)"


# ---------- extração de números ----------

def test_extrai_percentuais_com_virgula_e_ponto():
    assert extrair_numeros("chance de 18,4% e juro de 24.9 %") == [18.4, 24.9]


def test_ignora_artigos_e_numeros_de_leis():
    texto = "Conforme o art. 6º, III, da Lei nº 8.078/1990 e a Resolução CMN nº 4.881/2020."
    assert extrair_numeros(texto) == []


# ---------- conferência ----------

def test_parecer_correto_passa():
    assert conferir_parecer(resposta(), ENTRADA, TRECHOS) == []


def test_numero_com_ponto_tambem_passa():
    assert conferir_parecer(resposta(resumo="Chance de não pagar de 18.4%."), ENTRADA, TRECHOS) == []


def test_numero_inventado_no_texto_e_pego():
    problemas = conferir_parecer(resposta(resumo="O juro está 8,7 p.p. acima do justo."),
                                 ENTRADA, TRECHOS)
    assert len(problemas) == 1 and "8.7" in problemas[0]


def test_numero_errado_no_texto_e_pego():
    problemas = conferir_parecer(resposta(resumo="O juro cobrado é de 25,3% ao ano."),
                                 ENTRADA, TRECHOS)
    assert len(problemas) == 1


def test_pd_escrita_como_decimal_e_pega():
    problemas = conferir_parecer(resposta(resumo="A chance de não pagar é 0,184."),
                                 ENTRADA, TRECHOS)
    assert len(problemas) == 1


def test_numero_do_texto_ausente_em_numeros_citados_e_pego():
    # o texto cita 16,2% (juro_justo), mas o LLM não declarou juro_justo
    citados = {k: v for k, v in RESPOSTA["numeros_citados"].items() if k != "juro_justo"}
    problemas = conferir_parecer(resposta(numeros_citados=citados), ENTRADA, TRECHOS)
    assert len(problemas) == 1 and "16.2" in problemas[0]


def test_numero_citado_diferente_da_entrada_e_pego():
    citados = {**RESPOSTA["numeros_citados"], "juro_cobrado": 0.25}
    problemas = conferir_parecer(resposta(numeros_citados=citados), ENTRADA, TRECHOS)
    assert any("numeros_citados.juro_cobrado" in p for p in problemas)


def test_numero_citado_de_campo_nulo_e_pego():
    r = RespostaLLM.model_validate({
        "resumo": "Dados fora da faixa conhecida pelo modelo.",
        "pontos_de_atencao": ["O juro cobrado é de 22,0% ao ano."],
        "recomendacao_texto": "Recomenda-se análise manual. A decisão final é do analista.",
        "fontes": [],
        "numeros_citados": {"juro_cobrado": 0.22, "juro_justo": 0.16},
    })
    problemas = conferir_parecer(r, ENTRADA_REVISAO, TRECHOS)
    assert problemas == ["numeros_citados.juro_justo: o campo veio nulo do prever()"]


def test_parecer_de_revisao_manual_passa():
    r = RespostaLLM.model_validate({
        "resumo": "Dados fora da faixa conhecida pelo modelo.",
        "pontos_de_atencao": ["O juro cobrado é de 22,0% ao ano."],
        "recomendacao_texto": "Recomenda-se análise manual. A decisão final é do analista.",
        "fontes": [],
        "numeros_citados": {"juro_cobrado": 0.22},
    })
    assert conferir_parecer(r, ENTRADA_REVISAO, []) == []


def test_fonte_nao_recuperada_e_pega():
    fontes = [{"norma": "LGPD", "artigo": "art. 20", "trecho_id": "lgpd-art20-1"}]
    problemas = conferir_parecer(resposta(fontes=fontes), ENTRADA, TRECHOS)
    assert problemas == ["fonte lgpd-art20-1 não está entre os trechos recuperados"]


def test_sem_fontes_passa():
    assert conferir_parecer(resposta(fontes=[]), ENTRADA, TRECHOS) == []