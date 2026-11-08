"""Testes da cadeia do parecer (genai/src/cadeia.py), sem internet e sem banco:
o LLM e a busca são substituídos por versões falsas (monkeypatch).

Rodar na pasta raiz:  python -m pytest tests/genai -q
"""
import json
from datetime import timedelta
from pathlib import Path

import pytest

from genai.src import cadeia
from genai.src.checagem import RespostaLLM

ACIMA = {
    "contrato_id": "BO-1", "versao_modelo": "teste",
    "pd": 0.184, "faixa": "C", "juro_cobrado": 0.249,
    "juro_justo": 0.162, "juro_justo_min": 0.141, "juro_justo_max": 0.183,
    "situacao_preco": "acima_do_justo",
    "motivos": [{"variavel": "prazo_meses", "rotulo": "prazo do empréstimo", "efeito": "aumenta_risco"}],
}
REVISAO = {"contrato_id": "BO-2", "versao_modelo": "teste", "juro_cobrado": 0.22,
           "situacao_preco": "revisao_manual"}
TRECHOS = [{"trecho_id": "cdc-art6-1", "norma": "CDC", "artigo": "Art. 6º",
            "texto": "Art. 6º São direitos básicos do consumidor: III - a informação adequada e clara."}]

BOA = {
    "resumo": "Risco faixa C (chance de não pagar de 18,4%). O juro cobrado está acima do juro justo.",
    "pontos_de_atencao": ["O juro cobrado (24,9% ao ano) passa da margem do juro justo."],
    "recomendacao_texto": "Recomenda-se revisar o preço. A decisão final é do analista.",
    "fontes": [{"norma": "CDC", "artigo": "art. 6º, III", "trecho_id": "cdc-art6-1"}],
    "numeros_citados": {"pd": 0.184, "juro_cobrado": 0.249},
}


@pytest.fixture
def falsos(monkeypatch):
    """Troca a busca e o LLM por versões falsas e registra o que o LLM recebeu."""
    chamadas = {"llm": [], "resposta": BOA, "erro": None, "trechos": TRECHOS}

    def llm_falso(sistema, usuario):
        chamadas["llm"].append(sistema + usuario)
        if chamadas["erro"]:
            raise chamadas["erro"]
        return RespostaLLM.model_validate(chamadas["resposta"])

    monkeypatch.setattr(cadeia, "chamar_llm", llm_falso)
    monkeypatch.setattr(cadeia, "buscar_trechos", lambda entrada: chamadas["trechos"])
    return chamadas


def test_parecer_do_llm_aprovado(falsos):
    parecer = cadeia.gerar_parecer(ACIMA)
    assert parecer["origem"] == "llm"
    assert parecer["contrato_id"] == "BO-1"
    assert parecer["recomendacao"] == "revisar_preco"
    assert parecer["versao_prompt"] == "parecer_v1"
    assert parecer["gerado_em"].utcoffset() == timedelta(hours=-3)
    assert parecer["fontes"][0]["trecho_id"] == "cdc-art6-1"


def test_revisao_manual_nao_chama_o_llm(falsos):
    parecer = cadeia.gerar_parecer(REVISAO)
    assert parecer["origem"] == "template" and parecer["recomendacao"] == "revisao_manual"
    assert falsos["llm"] == []


def test_entrada_fora_do_contrato_vira_revisao_manual(falsos):
    quebrada = {**ACIMA, "juro_justo": None}  # nulo fora da revisão manual
    parecer = cadeia.gerar_parecer(quebrada)
    assert parecer["recomendacao"] == "revisao_manual"
    assert falsos["llm"] == []


def test_llm_fora_do_ar_usa_template(falsos):
    falsos["erro"] = RuntimeError("503 UNAVAILABLE")
    parecer = cadeia.gerar_parecer(ACIMA)
    assert parecer["origem"] == "template" and parecer["recomendacao"] == "revisar_preco"


def test_numero_inventado_usa_template(falsos):
    falsos["resposta"] = {**BOA, "resumo": "O juro está 8,7 p.p. acima do justo."}
    assert cadeia.gerar_parecer(ACIMA)["origem"] == "template"


def test_fonte_nao_recuperada_usa_template(falsos):
    falsos["resposta"] = {**BOA, "fontes": [{"norma": "LGPD", "artigo": "art. 20", "trecho_id": "lgpd-art20-1"}]}
    assert cadeia.gerar_parecer(ACIMA)["origem"] == "template"


def test_palavra_proibida_usa_template(falsos):
    falsos["resposta"] = {**BOA, "pontos_de_atencao": ["O preço parece abusivo."]}
    assert cadeia.gerar_parecer(ACIMA)["origem"] == "template"


def test_sem_trechos_o_parecer_sai_sem_fontes(falsos):
    falsos["trechos"] = []
    falsos["resposta"] = {**BOA, "fontes": []}
    parecer = cadeia.gerar_parecer(ACIMA)
    assert parecer["origem"] == "llm" and parecer["fontes"] == []


def test_frase_da_decisao_final_e_garantida(falsos):
    falsos["resposta"] = {**BOA, "recomendacao_texto": "Recomenda-se revisar o preço."}
    parecer = cadeia.gerar_parecer(ACIMA)
    assert parecer["recomendacao_texto"].endswith("A decisão final é do analista.")


def test_llm_nao_recebe_o_contrato_id(falsos):
    cadeia.gerar_parecer(ACIMA)
    assert "BO-1" not in falsos["llm"][0]


def test_busca_sem_banco_devolve_lista_vazia(monkeypatch):
    def banco_fora(pergunta, quantos):
        raise ConnectionError("sem Docker")
    monkeypatch.setattr(cadeia, "_consultar_banco", banco_fora)
    entrada = cadeia.EntradaPrever.model_validate(ACIMA)
    assert cadeia.buscar_trechos(entrada) == []


def test_resposta_do_gemini_vira_resposta_llm():
    bruta = cadeia._RespostaGemini.model_validate(
        {**BOA, "numeros_citados": {"pd": 0.184, "juro_cobrado": 0.249, "juro_justo": None}})
    assert cadeia._para_resposta_llm(bruta).numeros_citados == {"pd": 0.184, "juro_cobrado": 0.249}


def test_casos_de_teste_do_samuel_sempre_geram_parecer(falsos):
    falsos["erro"] = RuntimeError("sem LLM")  # pior caso: tudo cai no template
    casos = json.loads(Path("docs/casos_de_teste.json").read_text(encoding="utf-8"))
    for lista in casos.values():
        for caso in lista:
            parecer = cadeia.gerar_parecer(caso)
            assert parecer["contrato_id"] == caso["contrato_id"]
            assert parecer["recomendacao_texto"].endswith("A decisão final é do analista.")