"""Testes do template de reserva (genai/src/template.py).

Rodar na pasta raiz:  python -m pytest tests/genai -q
"""
from datetime import datetime, timedelta

import pytest

from genai.src.checagem import EntradaPrever, conferir_parecer
from genai.src.template import FUSO, escolher_recomendacao, montar_template

BASE = {
    "contrato_id": "TESTE-1", "versao_modelo": "teste",
    "pd": 0.184, "faixa": "C", "juro_cobrado": 0.249,
    "juro_justo": 0.162, "juro_justo_min": 0.141, "juro_justo_max": 0.183,
    "situacao_preco": "acima_do_justo",
    "motivos": [{"variavel": "prazo_meses", "rotulo": "prazo do empréstimo",
                 "efeito": "aumenta_risco"}],
}

REVISAO = {
    "contrato_id": "TESTE-2", "versao_modelo": "teste", "pd": None, "faixa": None,
    "juro_cobrado": 0.22, "situacao_preco": "revisao_manual",
}


def entrada(**mudancas):
    return EntradaPrever.model_validate({**BASE, **mudancas})


@pytest.mark.parametrize("situacao, esperada", [
    ("acima_do_justo", "revisar_preco"),
    ("abaixo_do_justo", "revisar_preco"),
    ("dentro_da_margem", "manter_preco"),
])
def test_recomendacao_segue_a_tabela(situacao, esperada):
    assert escolher_recomendacao(entrada(situacao_preco=situacao)) == esperada


def test_revisao_manual_tem_recomendacao_revisao_manual():
    assert escolher_recomendacao(EntradaPrever.model_validate(REVISAO)) == "revisao_manual"


def test_alerta_dados_vence_a_situacao_do_preco():
    assert escolher_recomendacao(entrada(alerta_dados=True)) == "revisao_manual"


def test_template_acima_tem_numeros_formatados_e_fatores():
    parecer = montar_template(entrada())
    assert parecer.origem == "template" and parecer.versao_prompt == "template_v1"
    assert parecer.fontes == []
    assert "24,9% ao ano" in parecer.pontos_de_atencao[0]
    assert "18,4%" in parecer.resumo
    assert any("prazo do empréstimo (aumenta o risco)" in p for p in parecer.pontos_de_atencao)
    assert "compliance" in parecer.recomendacao_texto


def test_template_revisao_manual_cita_so_o_juro_cobrado():
    parecer = montar_template(EntradaPrever.model_validate(REVISAO))
    assert parecer.recomendacao == "revisao_manual"
    assert parecer.numeros_citados == {"juro_cobrado": 0.22}
    assert "22,0% ao ano" in parecer.pontos_de_atencao[0]


def test_template_com_alerta_dados_nao_opina_sobre_preco():
    parecer = montar_template(entrada(alerta_dados=True))
    assert parecer.recomendacao == "revisao_manual"
    assert parecer.numeros_citados == {"juro_cobrado": 0.249}


def test_template_sem_motivos_nao_quebra():
    parecer = montar_template(entrada(situacao_preco="dentro_da_margem", motivos=[]))
    assert parecer.recomendacao == "manter_preco"
    assert len(parecer.pontos_de_atencao) == 1


@pytest.mark.parametrize("dados", [
    {**BASE},
    {**BASE, "situacao_preco": "abaixo_do_justo"},
    {**BASE, "situacao_preco": "dentro_da_margem"},
    REVISAO,
])
def test_template_passa_na_propria_conferencia(dados):
    entrada_prever = EntradaPrever.model_validate(dados)
    parecer = montar_template(entrada_prever)
    assert conferir_parecer(parecer, entrada_prever, []) == []
    assert parecer.recomendacao_texto.endswith("A decisão final é do analista.")


# ---------- correções da revisão (sensíveis, caso "abaixo" e fuso) ----------

def test_template_nao_cita_motivo_sensivel():
    motivos = [{"variavel": "Age", "rotulo": "idade", "efeito": "reduz_risco"},
               {"variavel": "prazo_meses", "rotulo": "prazo do empréstimo", "efeito": "aumenta_risco"}]
    parecer = montar_template(entrada(motivos=motivos))
    texto = " ".join([parecer.resumo, *parecer.pontos_de_atencao])
    assert "idade" not in texto
    assert "prazo do empréstimo" in texto


def test_template_so_com_motivos_sensiveis_nao_lista_fatores():
    motivos = [{"variavel": "Gender", "rotulo": "gênero", "efeito": "aumenta_risco"}]
    parecer = montar_template(entrada(motivos=motivos))
    assert not any("Principais fatores" in p for p in parecer.pontos_de_atencao)


def test_template_abaixo_fala_do_risco_para_o_banco():
    parecer = montar_template(entrada(situacao_preco="abaixo_do_justo"))
    assert "abaixo da margem" in parecer.pontos_de_atencao[0]
    assert any("não uma falha do cliente" in p for p in parecer.pontos_de_atencao)
    assert "compliance" not in parecer.recomendacao_texto


def test_gerado_em_usa_horario_de_brasilia():
    parecer = montar_template(entrada())
    assert parecer.gerado_em.utcoffset() == timedelta(hours=-3)


def test_gerado_em_aceita_hora_fixa():
    hora = datetime(2026, 11, 5, 14, 30, tzinfo=FUSO)
    assert montar_template(entrada(), agora=hora).gerado_em == hora