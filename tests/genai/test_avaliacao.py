"""Testes da avaliação (genai/avaliacao): os casos seguem o CRITERIOS.md e o script roda
de ponta a ponta com LLM e busca falsos. Rodar na pasta raiz: python -m pytest tests/genai -q
"""
import json
from collections import Counter
from pathlib import Path

from genai.avaliacao import avaliar
from genai.src import cadeia
from genai.src.checagem import EntradaPrever, RespostaLLM

CASOS = json.loads(Path("genai/avaliacao/casos_avaliacao.json").read_text(encoding="utf-8"))


def test_sao_20_casos_na_divisao_do_criterios():
    assert Counter(c["tipo"] for c in CASOS) == {"acima_do_justo": 5, "abaixo_do_justo": 4,
                                                 "dentro_da_margem": 4, "revisao_manual": 2, "difícil": 5}


def test_todas_as_entradas_seguem_o_contrato_e_tem_esperado():
    for caso in CASOS:
        EntradaPrever.model_validate(caso["entrada"])
        assert caso["esperado"]["recomendacao"] in ("revisar_preco", "manter_preco", "revisao_manual")


def test_avaliacao_roda_de_ponta_a_ponta(monkeypatch, tmp_path):
    resposta = RespostaLLM.model_validate({
        "resumo": "O juro cobrado está acima do juro justo.", "pontos_de_atencao": [],
        "recomendacao_texto": "Recomenda-se revisar o preço. A decisão final é do analista.",
        "fontes": [], "numeros_citados": {}})
    monkeypatch.setattr(cadeia, "chamar_llm", lambda s, u: resposta)
    monkeypatch.setattr(cadeia, "buscar_trechos", lambda e: [])
    monkeypatch.setattr(avaliar, "PASTA", tmp_path)
    monkeypatch.setattr(avaliar, "PAUSA", 0)
    avaliar.main()
    markdown = next(tmp_path.glob("resultados_*.md")).read_text(encoding="utf-8")
    assert "Recomendação certa" in markdown and "| C01 |" in markdown and "| D05 |" in markdown


def test_escolaridade_nao_conta_como_idade():
    assert avaliar.proibidos("Fatores: escolaridade e capacidade de pagamento.") == []
    assert avaliar.proibidos("A idade do cliente pesa. O preço parece abusivo.") != []


# ---------- repetição por falha do Google ----------

RESPOSTA_BOA = RespostaLLM.model_validate({
    "resumo": "O juro cobrado está acima do juro justo.", "pontos_de_atencao": [],
    "recomendacao_texto": "Recomenda-se revisar o preço. A decisão final é do analista.",
    "fontes": [], "numeros_citados": {}})


def _llm_que_falha(vezes, erro):
    chamadas = {"n": 0}

    def llm(sistema, usuario):
        chamadas["n"] += 1
        if chamadas["n"] <= vezes:
            raise RuntimeError(erro)
        return RESPOSTA_BOA
    return llm, chamadas


def _avaliar_c01(monkeypatch, llm):
    import logging
    monkeypatch.setattr(cadeia, "chamar_llm", llm)
    monkeypatch.setattr(cadeia, "buscar_trechos", lambda e: [])
    monkeypatch.setattr(avaliar, "PAUSA", 0)
    monkeypatch.setattr(avaliar, "ESPERA_ENTRE_TENTATIVAS", 0)
    guarda = avaliar._GuardaAvisos()
    logging.getLogger("genai.cadeia").addHandler(guarda)
    try:
        return avaliar.avaliar_caso(CASOS[0], guarda)["rodadas"][0]  # a 1ª das 2 rodadas
    finally:
        logging.getLogger("genai.cadeia").removeHandler(guarda)


def test_503_e_repetido_e_a_rodada_sai_pela_ia(monkeypatch):
    llm, chamadas = _llm_que_falha(1, "503 UNAVAILABLE. high demand")
    rodada = _avaliar_c01(monkeypatch, llm)
    assert rodada["origem"] == "llm" and rodada["tentativas"] == 2
    assert chamadas["n"] == 3  # 1ª rodada: falha + repetição; 2ª rodada: de primeira
    assert any("503" in aviso for aviso in rodada["falhas_anteriores"])


def test_falha_do_google_em_todas_as_tentativas_fica_no_template(monkeypatch):
    llm, chamadas = _llm_que_falha(99, "504 DEADLINE_EXCEEDED")
    rodada = _avaliar_c01(monkeypatch, llm)
    assert rodada["origem"] == "template" and rodada["tentativas"] == avaliar.TENTATIVAS_POR_RODADA
    assert avaliar.falha_do_google(rodada)


def test_resposta_invalida_nao_e_repetida(monkeypatch):
    """Repetir erro do modelo seria escolher a resposta que passa: só a indisponibilidade é repetida."""
    llm, chamadas = _llm_que_falha(99, "1 validation error for _RespostaGemini")
    rodada = _avaliar_c01(monkeypatch, llm)
    assert rodada["origem"] == "template" and rodada["tentativas"] == 1
    assert chamadas["n"] == 2  # uma chamada por rodada, sem repetição
    assert not avaliar.falha_do_google(rodada)


def test_recusa_da_conferencia_nao_e_repetida(monkeypatch):
    numero_inventado = RespostaLLM.model_validate({**RESPOSTA_BOA.model_dump(),
                                                   "resumo": "O juro cobrado está 26,5% acima do juro justo."})
    chamadas = {"n": 0}

    def llm(sistema, usuario):
        chamadas["n"] += 1
        return numero_inventado
    rodada = _avaliar_c01(monkeypatch, llm)
    assert rodada["origem"] == "template" and rodada["tentativas"] == 1
    assert chamadas["n"] == 2  # uma chamada por rodada, sem repetição
    assert any("recusou" in aviso for aviso in rodada["avisos"])
