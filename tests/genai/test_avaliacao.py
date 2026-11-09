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
