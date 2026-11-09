"""Testes da v3 (09/11): busca com a pergunta de governança (LGPD art. 20) e regras novas do prompt.
Origem: avaliação dos 20 casos com a v2 (genai/avaliacao/).

Rodar na pasta raiz:  python -m pytest tests/genai -q
"""
import json
from pathlib import Path

from genai.src import cadeia
from genai.src.checagem import EntradaPrever
from genai.src.prompt import carregar_prompt, montar_mensagens

ENTRADA = EntradaPrever.model_validate({
    "contrato_id": "BO-1", "versao_modelo": "teste",
    "pd": 0.184, "faixa": "C", "juro_cobrado": 0.249,
    "juro_justo": 0.162, "juro_justo_min": 0.141, "juro_justo_max": 0.183,
    "situacao_preco": "acima_do_justo", "motivos": [],
})


def _trecho(tid):
    return {"trecho_id": tid, "norma": "X", "artigo": "Art. 1", "texto": "..."}


def _banco_falso(respostas):
    def consultar(pergunta, quantos):
        return respostas["governanca"] if pergunta == cadeia.PERGUNTA_GOVERNANCA else respostas["situacao"]
    return consultar


# ---------- busca ----------

def test_busca_acrescenta_um_trecho_de_governanca(monkeypatch):
    monkeypatch.setattr(cadeia, "_consultar_banco", _banco_falso({
        "situacao": [_trecho("cdc-art52-1"), _trecho("cdc-art54b-1")],
        "governanca": [_trecho("lgpd-art20-1"), _trecho("lgpd-art20-2")]}))
    ids = [t["trecho_id"] for t in cadeia.buscar_trechos(ENTRADA)]
    assert ids == ["cdc-art52-1", "cdc-art54b-1", "lgpd-art20-1"]


def test_busca_nao_repete_trecho(monkeypatch):
    monkeypatch.setattr(cadeia, "_consultar_banco", _banco_falso({
        "situacao": [_trecho("lgpd-art20-1"), _trecho("cdc-art52-1")],
        "governanca": [_trecho("lgpd-art20-1"), _trecho("cdc-art54d-1")]}))
    ids = [t["trecho_id"] for t in cadeia.buscar_trechos(ENTRADA)]
    assert ids == ["lgpd-art20-1", "cdc-art52-1", "cdc-art54d-1"]


def test_busca_sem_banco_continua_vazia(monkeypatch):
    def fora(pergunta, quantos):
        raise ConnectionError("sem Docker")
    monkeypatch.setattr(cadeia, "_consultar_banco", fora)
    assert cadeia.buscar_trechos(ENTRADA) == []


def test_pergunta_do_acima_nao_fala_mais_em_cobranca():
    assert "acima do justo" not in cadeia.PERGUNTAS_BUSCA["acima_do_justo"]
    assert "taxa efetiva" in cadeia.PERGUNTAS_BUSCA["acima_do_justo"]


# ---------- prompt v3 ----------

def test_versoes_anteriores_continuam():
    for versao in ("parecer_v1", "parecer_v2", "parecer_v3"):
        sistema, usuario = carregar_prompt(versao)
        assert sistema and "{numeros}" in usuario


def test_prompt_v3_tem_as_regras_novas():
    sistema, _ = montar_mensagens(ENTRADA, "revisar_preco", [], versao="parecer_v3")
    assert "Não a repita nos pontos de atenção" in sistema
    assert "Não chame o valor central de \"margem\"" in sistema
    assert "\"fontes\" não deve ficar vazia" in sistema
    assert "LGPD, art. 20" in sistema
    assert "perda esperada e que isso é um ponto de atenção para o banco" in sistema


def test_prompt_v3_mantem_as_regras_da_v2():
    sistema, _ = montar_mensagens(ENTRADA, "revisar_preco", [])
    assert "verbo no condicional" in sistema
    assert "Não acrescente nem troque palavras no nome de um fator" in sistema


def test_notas_do_prompt_nao_vao_para_o_llm():
    sistema, usuario = carregar_prompt()
    assert "Por que existe a v3" not in sistema + usuario


# ---------- avaliação ----------

def test_lgpd_20_aceita_nas_situacoes_com_llm():
    casos = json.loads(Path("genai/avaliacao/casos_avaliacao.json").read_text(encoding="utf-8"))
    for caso in casos:
        if caso["esperado"]["recomendacao"] != "revisao_manual":
            assert "lgpd-art20" in caso["esperado"]["normas_aceitas"]


# ---------- revisão antes de rodar (09/11) ----------

def test_prompt_v3_pede_para_nao_copiar_palavras_proibidas_dos_trechos():
    sistema, _ = montar_mensagens(ENTRADA, "revisar_preco", [], versao="parecer_v3")
    assert "nunca copie essas palavras para o parecer" in sistema
    assert "cumpre, atende, respeita ou descumpre" in sistema
    assert "art. 6º, III" in sistema


def test_metrica_de_fonte_especifica_ignora_a_lgpd_20():
    from genai.avaliacao.avaliar import fontes_especificas
    assert fontes_especificas(["lgpd-art20-1"]) == []
    assert fontes_especificas(["lgpd-art20-1", "cdc-art52-1"]) == ["cdc-art52-1"]


def test_conta_recusa_por_palavra_proibida():
    from genai.avaliacao.avaliar import _recusa_por_palavra
    assert _recusa_por_palavra({"avisos": ['conferência recusou o parecer do LLM: palavra proibida "abusiva" no texto']})
    assert not _recusa_por_palavra({"avisos": ["conferência recusou o parecer do LLM: resumo com 3 frases (máximo 2)"]})
    assert not _recusa_por_palavra({"avisos": []})
