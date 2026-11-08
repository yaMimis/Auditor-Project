"""Testes da montagem das mensagens do LLM (genai/src/prompt.py e genai/prompts/parecer_v1.md).

Rodar na pasta raiz:  python -m pytest tests/genai -q
"""
import pytest

from genai.src.checagem import EntradaPrever
from genai.src.prompt import carregar_prompt, montar_mensagens

ENTRADA = EntradaPrever.model_validate({
    "contrato_id": "BO-SEGREDO-123", "versao_modelo": "xgboost_v2",
    "pd": 0.184, "faixa": "C", "juro_cobrado": 0.249,
    "juro_justo": 0.162, "juro_justo_min": 0.141, "juro_justo_max": 0.183,
    "situacao_preco": "acima_do_justo",
    "motivos": [
        {"variavel": "DebtToIncome", "rotulo": "dívidas em relação à renda", "efeito": "aumenta_risco"},
        {"variavel": "Age", "rotulo": "idade do cliente", "efeito": "reduz_risco"},
    ],
    "pd_ic95": [0.159, 0.210], "diferenca_pp": 8.7,
})

TRECHOS = [{"trecho_id": "cdc-art6-1", "norma": "CDC", "artigo": "Art. 6º",
            "texto": "Art. 6º São direitos básicos do consumidor: III - a informação adequada e clara."}]


def test_prompt_tem_as_duas_mensagens_e_nao_envia_as_notas():
    sistema, usuario = carregar_prompt()
    assert "Você escreve pareceres" in sistema
    assert "{numeros}" in usuario and "{trechos}" in usuario
    assert "Notas" not in sistema and "Notas" not in usuario


def test_mensagem_tem_numeros_formatados_e_valores_para_numeros_citados():
    _, usuario = montar_mensagens(ENTRADA, "revisar_preco", TRECHOS)
    assert "24,9% ao ano (nominal) [juro_cobrado: 0.249]" in usuario
    assert "18,4% [pd: 0.184]" in usuario
    assert "14,1% ao ano" in usuario and "18,3% ao ano" in usuario


def test_mensagem_nao_envia_identificadores_nem_campos_extras():
    sistema, usuario = montar_mensagens(ENTRADA, "revisar_preco", TRECHOS)
    texto = sistema + usuario
    for proibido in ("BO-SEGREDO-123", "xgboost_v2", "8,7", "8.7", "0.159", "DebtToIncome"):
        assert proibido not in texto


def test_mensagem_nao_envia_motivo_sensivel():
    _, usuario = montar_mensagens(ENTRADA, "revisar_preco", TRECHOS)
    assert "dívidas em relação à renda (aumenta o risco)" in usuario
    assert "idade" not in usuario


def test_mensagem_traz_os_trechos_com_ids():
    _, usuario = montar_mensagens(ENTRADA, "revisar_preco", TRECHOS)
    assert "[trecho_id: cdc-art6-1 | norma: CDC | artigo: Art. 6º]" in usuario


def test_sem_trechos_avisa_o_llm():
    _, usuario = montar_mensagens(ENTRADA, "revisar_preco", [])
    assert "(nenhum trecho encontrado)" in usuario


def test_revisao_manual_nao_monta_mensagem():
    revisao = EntradaPrever.model_validate({
        "contrato_id": "X", "versao_modelo": "t", "juro_cobrado": 0.22,
        "situacao_preco": "revisao_manual"})
    with pytest.raises(ValueError):
        montar_mensagens(revisao, "revisao_manual", TRECHOS)


def test_nenhuma_chave_sobrando_na_mensagem():
    _, usuario = montar_mensagens(ENTRADA, "revisar_preco", TRECHOS)
    assert "{" not in usuario and "}" not in usuario