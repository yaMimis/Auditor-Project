"""Testes do contrato de dados da GenAI (genai/src/checagem.py).

Rodar na pasta raiz:  python -m pytest tests/genai -q
"""
from datetime import datetime

import pytest
from pydantic import ValidationError

from genai.src.checagem import EntradaPrever, Parecer, RespostaLLM

ENTRADA_NORMAL = {
    "contrato_id": "TESTE-1",
    "versao_modelo": "teste",
    "pd": 0.184,
    "faixa": "C",
    "juro_cobrado": 0.249,
    "juro_justo": 0.162,
    "juro_justo_min": 0.141,
    "juro_justo_max": 0.183,
    "situacao_preco": "acima_do_justo",
    "motivos": [{"variavel": "prazo_meses", "rotulo": "prazo do empréstimo",
                 "efeito": "aumenta_risco", "valor": 60, "peso": 0.18}],
    "alerta_dados": False,
    "pd_ic95": [0.159, 0.210],
    "diferenca_pp": 8.7,
}

ENTRADA_REVISAO_MANUAL = {
    "contrato_id": "TESTE-2",
    "versao_modelo": "teste",
    "pd": None,
    "faixa": None,
    "juro_cobrado": 0.30,
    "juro_justo": None,
    "juro_justo_min": None,
    "juro_justo_max": None,
    "situacao_preco": "revisao_manual",
    "motivos": [],
    "alerta_dados": True,
}

RESPOSTA_LLM = {
    "resumo": "Cliente de risco moderado (faixa C, chance de não pagar de 18,4%).",
    "pontos_de_atencao": ["O juro cobrado (24,9% ao ano) está acima da margem do juro justo."],
    "recomendacao_texto": "Recomenda-se revisar o preço. A decisão final é do analista.",
    "fontes": [{"norma": "CDC", "artigo": "art. 6º, III", "trecho_id": "cdc-art6-1"}],
    "numeros_citados": {"pd": 0.184, "juro_cobrado": 0.249},
}


def test_entrada_normal_e_valida_e_descarta_extras():
    entrada = EntradaPrever.model_validate(ENTRADA_NORMAL)
    assert entrada.situacao_preco == "acima_do_justo"
    assert not entrada.vai_para_revisao_manual
    assert not hasattr(entrada, "diferenca_pp")
    assert entrada.motivos[0].rotulo == "prazo do empréstimo"


def test_revisao_manual_aceita_campos_nulos():
    entrada = EntradaPrever.model_validate(ENTRADA_REVISAO_MANUAL)
    assert entrada.vai_para_revisao_manual


def test_alerta_dados_manda_para_revisao_manual():
    entrada = EntradaPrever.model_validate({**ENTRADA_NORMAL, "alerta_dados": True})
    assert entrada.vai_para_revisao_manual


def test_campo_nulo_fora_da_revisao_manual_e_recusado():
    with pytest.raises(ValidationError):
        EntradaPrever.model_validate({**ENTRADA_NORMAL, "juro_justo": None})


def test_pd_fora_de_0_a_1_e_recusada():
    with pytest.raises(ValidationError):
        EntradaPrever.model_validate({**ENTRADA_NORMAL, "pd": 18.4})


def test_efeito_desconhecido_e_recusado():
    motivo_errado = [{"variavel": "prazo_meses", "rotulo": "prazo", "efeito": "aumenta"}]
    with pytest.raises(ValidationError):
        EntradaPrever.model_validate({**ENTRADA_NORMAL, "motivos": motivo_errado})


def test_resposta_llm_valida():
    resposta = RespostaLLM.model_validate(RESPOSTA_LLM)
    assert resposta.fontes[0].trecho_id == "cdc-art6-1"


def test_mais_de_3_pontos_de_atencao_e_recusado():
    with pytest.raises(ValidationError):
        RespostaLLM.model_validate({**RESPOSTA_LLM, "pontos_de_atencao": ["a", "b", "c", "d"]})


def test_numero_citado_fora_da_lista_e_recusado():
    with pytest.raises(ValidationError):
        RespostaLLM.model_validate({**RESPOSTA_LLM, "numeros_citados": {"diferenca_pp": 8.7}})


def test_parecer_completo_valido():
    parecer = Parecer.model_validate({
        **RESPOSTA_LLM,
        "contrato_id": "TESTE-1",
        "recomendacao": "revisar_preco",
        "origem": "llm",
        "versao_prompt": "parecer_v1",
        "gerado_em": datetime.now().isoformat(),
    })
    assert parecer.origem == "llm"


def test_recomendacao_desconhecida_e_recusada():
    with pytest.raises(ValidationError):
        Parecer.model_validate({
            **RESPOSTA_LLM,
            "contrato_id": "TESTE-1",
            "recomendacao": "cancelar_contrato",
            "origem": "llm",
            "versao_prompt": "parecer_v1",
            "gerado_em": datetime.now().isoformat(),
        })