"""Formatação e blocos HTML do painel (src/app/components.py)."""
import json
from pathlib import Path

import pytest

from src.app.components import (readable_value, compact, margin_distance_pp, eur, html_rate_bar,
                                 html_reasons, html_opinion, html_fairness_table, review_kpis,
                                 fairness_reading, pct, pp)

EXAMPLES = json.loads((Path(__file__).resolve().parents[2] / "docs" / "exemplos_prever.json")
                      .read_text(encoding="utf-8"))
BY_SITUATION = {e["situacao_preco"]: e for e in EXAMPLES}


def test_brazilian_formatting():
    assert pct(0.249) == "24,9%"
    assert pct(None) == "—"
    assert pct(float("nan")) == "—"
    assert pp(6.9) == "+6,9 pp" and pp(-1.3) == "−1,3 pp"
    assert eur(3190) == "€ 3.190"


def test_compact_strips_indentation_and_blank_lines():
    assert compact("\n    <div>\n\n        texto\n    </div>\n") == "<div> texto </div>"


def test_margin_distance():
    assert margin_distance_pp(BY_SITUATION["acima_do_justo"]) == pytest.approx(6.6, abs=0.05)
    assert margin_distance_pp(BY_SITUATION["dentro_da_margem"]) == 0.0
    assert margin_distance_pp(BY_SITUATION["abaixo_do_justo"]) < 0
    assert margin_distance_pp(BY_SITUATION["revisao_manual"]) is None


@pytest.mark.parametrize("situation", sorted(BY_SITUATION))
def test_kpis_never_break_in_any_situation(situation):
    cards = review_kpis(BY_SITUATION[situation])
    assert len(cards) == 4
    if situation == "revisao_manual":
        assert "—" in cards[0] and "Revisão manual" in cards[3]


def test_rate_bar_hidden_on_manual_review():
    assert html_rate_bar(BY_SITUATION["revisao_manual"]) == ""
    ruler = html_rate_bar(BY_SITUATION["acima_do_justo"])
    assert "Justo 16,2%" in ruler and "Cobrado 24,9%" in ruler


def test_rate_bar_accepts_extreme_rate():
    r = dict(BY_SITUATION["acima_do_justo"], juro_cobrado=2.64)  # 264% a.a. existe na base
    assert "Cobrado 264,0%" in html_rate_bar(r)


def test_reasons_with_label_and_effect_color():
    html = html_reasons(BY_SITUATION["acima_do_justo"]["motivos"])
    assert "dívidas em relação à renda" in html and "divida_sobre_renda" not in html
    assert "Aumenta o risco" in html
    assert "Sem motivos" in html_reasons([])


def test_opinion_escapes_html_and_shows_source():
    opinion = {"resumo": "<script>x</script>", "pontos_de_atencao": ["a"], "recomendacao": "revisar_preco",
               "recomendacao_texto": "t", "fontes": [], "origem": "template", "versao_prompt": "template_v1"}
    html = html_opinion(opinion)
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert "Template de reserva" in html
    assert "Não encontrei base normativa" in html
    assert "indisponível" in html_opinion(None)


def test_fairness_reading_by_interval():
    assert fairness_reading(-0.2, 0.5)[0] == "Sem indício"
    assert fairness_reading(0.3, 1.1)[0] == "Indício · investigar"
    assert fairness_reading(None, None)[0] == "Aguardando análise"
    assert "[a – b]" in html_fairness_table([{"atributo": "Gênero", "comparacao": "f × m"}])


def test_reason_values_readable():
    assert readable_value("valor_sobre_renda", 6.098) == "6,1× a renda mensal"
    assert readable_value("divida_sobre_renda", 0.48) == "0,5× a renda mensal"
    assert readable_value("parcela_neutra_sobre_renda", 0.12) == "12% da renda"
    assert readable_value("tempo_emprego_atual", "MoreThan5Years") == "mais de 5 anos"
    assert readable_value("prazo_meses", 60.0) == "60 meses"
    assert readable_value("renda_total", 2500.0) == "€ 2.500"
    assert readable_value("escolaridade", "5") == "superior"
    assert readable_value("tipo_verificacao", 1) == "renda não verificada"
    assert readable_value("tipo_moradia", "8") == "financiada"
    assert readable_value("passivos_existentes", "4.0") == "4"
    assert readable_value("score_ee_mini", 1000.0) == "1.000"
    assert readable_value("escolaridade", "sem_info") is None


def test_real_cases_show_reasons_without_raw_codes():
    cases = json.loads((Path(__file__).resolve().parents[2] / "docs" / "casos_de_teste.json")
                       .read_text(encoding="utf-8"))
    for items_list in cases.values():
        for case in items_list:
            html = html_reasons(case["motivos"])
            assert "escolaridade</span>" not in html  # rótulo sem valor cru
            assert ".0<" not in html                   # nada de "4.0"

def test_nominal_rates_and_peer_median_on_card():
    r = dict(BY_SITUATION["acima_do_justo"], juro_pares_mediana=0.2233)
    cards = review_kpis(r)
    assert "a.a. nominal" in cards[1] and "a.a. nominal" in cards[2]
    assert "Mediana dos pares: 22,3%" in cards[2]
    assert "Mediana dos pares" not in review_kpis(dict(r, juro_pares_mediana=None))[2]
    assert "Juros nominais ao ano" in html_rate_bar(r)


def test_opinion_shows_bc_reference_only_when_present():
    base = {"resumo": "r", "pontos_de_atencao": [], "recomendacao": "manter_preco", "recomendacao_texto": "t",
            "fontes": [], "origem": "llm", "versao_prompt": "parecer_v2"}
    sentence = "Referência de mercado: no mês da concessão, a taxa média <b>era</b> de 84,5% ao ano (nominal)."
    html = html_opinion({**base, "contexto_mercado": sentence})
    assert "Referência de mercado (Brasil)" in html and "&lt;b&gt;" in html  # texto escapado
    assert "Referência de mercado (Brasil)" not in html_opinion({**base, "contexto_mercado": None})


def test_two_decimals_when_rates_would_look_equal():
    """Caso C07 da avaliação do parecer: cobrado 30,56% e limite 30,58% não podem virar 30,6% e 30,6%."""
    r = dict(BY_SITUATION["abaixo_do_justo"], juro_cobrado=0.3056, juro_justo=0.33, juro_justo_min=0.3058,
             juro_justo_max=0.36)
    cards = review_kpis(r)
    assert "30,56%" in cards[1] and "30,58%" in cards[2]
    assert "Cobrado 30,56%" in html_rate_bar(r)
    assert "24,9%" in review_kpis(BY_SITUATION["acima_do_justo"])[1]  # caso normal: 1 casa


def test_line_icons_without_emoji():
    from src.app.components import line_icon
    svg = line_icon("cadeado", 14)
    assert svg.startswith("<svg") and 'width="14"' in svg and 'stroke="currentColor"' in svg
    assert line_icon("nao-existe") == ""
    for name_ in ("balanca", "grafico", "chip", "documento"):
        assert "<path" in line_icon(name_) or "<rect" in line_icon(name_)


def test_margin_label_says_when_there_is_no_bootstrap():
    """Sem bootstrap o prever() usa ±2 p.p. fixos: a tela não pode chamar isso de intervalo de 95%."""
    with_ci = " ".join(review_kpis(BY_SITUATION["acima_do_justo"]))
    without_ci = " ".join(review_kpis({**BY_SITUATION["acima_do_justo"], "pd_ic95": None}))
    assert "Incerteza (bootstrap)" in with_ci and "Margem de incerteza" in with_ci
    assert "Incerteza (bootstrap)" not in without_ci and "Margem padrão de ±2 p.p. (sem bootstrap)" in without_ci
    assert "Sem intervalo da PD" in without_ci
