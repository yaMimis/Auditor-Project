"""Testes da v5 (16/11).

1. Citação: no caso "acima do justo", ponto de atenção sobre a informação do preço ao consumidor. A busca trazia
   os trechos do CDC sobre isso em todos os casos "acima", e o modelo quase não os citava (avaliação v4 e
   contar_fontes.py de 16/11).
2. Clareza: quatro regras vindas da primeira rodada da v5 (D05, C10, C07 e C04).
3. Gabarito: o CDC art. 54-D passa a ser aceito no "acima" (CRITERIOS.md, "Mudanças no gabarito").

Rodar na pasta raiz:  python -m pytest tests/genai -q
"""
import json
from pathlib import Path

import pytest

from genai.avaliacao.avaliar import _aceita, fala_dos_bastidores
from genai.avaliacao.montar_casos import NORMAS_ESPERADAS
from genai.src.checagem import PALAVRAS_PROIBIDAS, EntradaPrever, artigos_no_texto
from genai.src.prompt import VERSAO_PROMPT, carregar_prompt, montar_mensagens

ENTRADA = EntradaPrever.model_validate({
    "contrato_id": "BO-1", "versao_modelo": "teste",
    "pd": 0.184, "faixa": "C", "juro_cobrado": 0.249,
    "juro_justo": 0.162, "juro_justo_min": 0.141, "juro_justo_max": 0.183,
    "situacao_preco": "acima_do_justo", "motivos": [],
})


def test_versao_atual_e_a_v5():
    assert VERSAO_PROMPT == "parecer_v5"


def test_v5_pede_ponto_sobre_a_informacao_do_preco_no_acima():
    sistema, _ = montar_mensagens(ENTRADA, "revisar_preco", [])
    assert "No caso \"acima do justo\", se os TRECHOS DE NORMAS trouxerem um trecho do Código de Defesa" in sistema
    assert "vale verificar se isso aconteceu" in sistema
    assert "Esse ponto conta dentro do limite de 3 pontos de atenção" in sistema


def test_v5_continua_sem_artigo_nomeado_nas_regras():
    """Lição da v3: artigo nomeado numa regra virou alucinação. A regra descreve o conteúdo do trecho."""
    sistema, _ = montar_mensagens(ENTRADA, "revisar_preco", [])
    assert artigos_no_texto(sistema) == set()


# Linhas da v4 que a v5 muda de propósito (o resto da v4 continua igual).
MUDADAS_NA_V5 = {
    "Você só escreve.": "abertura sem a palavra \"código\" (mudança 3)",
    "- Acima do justo:": "a v5 acrescenta uma frase no fim (mudança 1)",
}


def test_v5_mantem_as_regras_da_v4():
    sistema_v4, usuario_v4 = carregar_prompt("parecer_v4")
    sistema_v5, usuario_v5 = carregar_prompt("parecer_v5")
    assert usuario_v5 == usuario_v4.replace("RECOMENDAÇÃO ESCOLHIDA PELO CÓDIGO:", "RECOMENDAÇÃO:")
    for linha in sistema_v4.splitlines():
        if linha.startswith("- Acima do justo:"):
            assert linha.rstrip() in sistema_v5
        elif not any(linha.startswith(inicio) for inicio in MUDADAS_NA_V5):
            assert linha in sistema_v5


def test_notas_da_v5_nao_vao_para_o_llm():
    sistema, usuario = carregar_prompt()
    assert "Por que existe a v5" not in sistema + usuario


# ---------- clareza (primeira rodada da v5) ----------

REGRAS_DE_CLAREZA = {
    "D05 (indício de aderência)": "Use \"indício\" só para apontar um possível problema no preço.",
    "C10 (recomendação calculada pelo código)":
        "Em \"recomendacao_texto\", comece com \"Recomenda-se\" seguido da recomendação recebida",
    "C07 (relatório chamado de norma)":
        "O Relatório de Estabilidade Financeira é um relatório do Banco Central, não uma norma",
    "C04 (faixa com dois sentidos)": "Use a palavra \"faixa\" só para a faixa de risco (A a E).",
}


@pytest.mark.parametrize("origem", REGRAS_DE_CLAREZA)
def test_v5_tem_as_regras_de_clareza(origem):
    sistema, _ = carregar_prompt("parecer_v5")
    assert REGRAS_DE_CLAREZA[origem] in sistema


def test_regras_de_clareza_nao_ensinam_palavra_proibida():
    """Uma regra do prompt não pode ser a origem de uma palavra que a conferência recusa (lição da v3)."""
    novas = "\n".join(REGRAS_DE_CLAREZA.values())
    assert PALAVRAS_PROIBIDAS.search(novas) is None
    assert artigos_no_texto(novas) == set()


# ---------- gabarito da avaliação ----------

CASOS = json.loads(Path("genai/avaliacao/casos_avaliacao.json").read_text(encoding="utf-8"))


def _situacao_do_gabarito(caso):
    """Revisão manual prevalece sobre a situação do preço (D04), como em montar_casos.py."""
    if caso["esperado"]["recomendacao"] == "revisao_manual":
        return "revisao_manual"
    return caso["entrada"]["situacao_preco"]


def test_cdc_54d_aceito_no_acima_do_justo():
    assert "cdc-art54d" in NORMAS_ESPERADAS["acima_do_justo"]
    acima = [c for c in CASOS if _situacao_do_gabarito(c) == "acima_do_justo"]
    assert [c["id"] for c in acima] == ["C01", "C02", "C03", "C04", "C05", "D01", "D02", "D03"]
    assert all(_aceita("cdc-art54d-1", c["esperado"]["normas_aceitas"]) for c in acima)


def test_cdc_54d_nao_entrou_nas_outras_situacoes():
    for situacao in ("abaixo_do_justo", "dentro_da_margem", "revisao_manual"):
        assert "cdc-art54d" not in NORMAS_ESPERADAS[situacao]


def test_casos_e_montar_casos_tem_o_mesmo_gabarito():
    """O JSON foi editado à mão (rodar montar_casos.py sortearia outros contratos): os dois não podem divergir."""
    for caso in CASOS:
        assert caso["esperado"]["normas_aceitas"] == NORMAS_ESPERADAS[_situacao_do_gabarito(caso)], caso["id"]


# ---------- mudança 3: nada de "código" nas mensagens ----------

def test_mensagens_da_v5_nao_falam_do_codigo():
    """A regra negativa sobre o código piorou o problema (6/20): a palavra não aparece mais para o modelo."""
    sistema, usuario = montar_mensagens(ENTRADA, "revisar_preco", [])
    sem_cdc = (sistema + usuario).lower().replace("código de defesa do consumidor", "")
    assert "código" not in sem_cdc
    assert usuario.startswith("SITUAÇÃO DO PREÇO:") and "\nRECOMENDAÇÃO: revisar o preço\n" in usuario


@pytest.mark.parametrize("texto, fala", [
    ("O código calculou a recomendação de manter o preço. A decisão final é do analista.", True),
    ("A recomendação calculada pelo código é revisar o preço. A decisão final é do analista.", True),
    ("O sistema recomendou revisar o preço. A decisão final é do analista.", True),
    ("A recomendação escolhida é manter o preço. A decisão final é do analista.", True),
    ("Recomenda-se revisar o preço, porque o juro passa da margem. A decisão final é do analista.", False),
])
def test_metrica_de_bastidores(texto, fala):
    assert fala_dos_bastidores({"recomendacao_texto": texto}) is fala
