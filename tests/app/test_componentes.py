"""Formatação e blocos HTML do painel (src/app/componentes.py)."""
import json
from pathlib import Path

import pytest

from src.app.componentes import (valor_legivel, compactar, distancia_da_margem_pp, eur, html_barra_juros,
                                 html_motivos, html_parecer, html_tabela_equidade, kpis_revisao,
                                 leitura_equidade, pct, pp)

EXEMPLOS = json.loads((Path(__file__).resolve().parents[2] / "docs" / "exemplos_prever.json")
                      .read_text(encoding="utf-8"))
POR_SITUACAO = {e["situacao_preco"]: e for e in EXEMPLOS}


def test_formatacao_brasileira():
    assert pct(0.249) == "24,9%"
    assert pct(None) == "—"
    assert pct(float("nan")) == "—"
    assert pp(6.9) == "+6,9 pp" and pp(-1.3) == "−1,3 pp"
    assert eur(3190) == "€ 3.190"


def test_compactar_tira_indentacao_e_linhas_vazias():
    assert compactar("\n    <div>\n\n        texto\n    </div>\n") == "<div> texto </div>"


def test_distancia_da_margem():
    assert distancia_da_margem_pp(POR_SITUACAO["acima_do_justo"]) == pytest.approx(6.6, abs=0.05)
    assert distancia_da_margem_pp(POR_SITUACAO["dentro_da_margem"]) == 0.0
    assert distancia_da_margem_pp(POR_SITUACAO["abaixo_do_justo"]) < 0
    assert distancia_da_margem_pp(POR_SITUACAO["revisao_manual"]) is None


@pytest.mark.parametrize("situacao", sorted(POR_SITUACAO))
def test_kpis_nao_quebram_em_nenhuma_situacao(situacao):
    cartoes = kpis_revisao(POR_SITUACAO[situacao])
    assert len(cartoes) == 4
    if situacao == "revisao_manual":
        assert "—" in cartoes[0] and "Revisão manual" in cartoes[3]


def test_regua_some_na_revisao_manual():
    assert html_barra_juros(POR_SITUACAO["revisao_manual"]) == ""
    regua = html_barra_juros(POR_SITUACAO["acima_do_justo"])
    assert "Justo 16,2%" in regua and "Cobrado 24,9%" in regua


def test_regua_aceita_juro_extremo():
    r = dict(POR_SITUACAO["acima_do_justo"], juro_cobrado=2.64)  # 264% a.a. existe na base
    assert "Cobrado 264,0%" in html_barra_juros(r)


def test_motivos_com_rotulo_e_cor_do_efeito():
    html = html_motivos(POR_SITUACAO["acima_do_justo"]["motivos"])
    assert "dívidas em relação à renda" in html and "divida_sobre_renda" not in html
    assert "Aumenta o risco" in html
    assert "Sem motivos" in html_motivos([])


def test_parecer_escapa_html_e_mostra_origem():
    parecer = {"resumo": "<script>x</script>", "pontos_de_atencao": ["a"], "recomendacao": "revisar_preco",
               "recomendacao_texto": "t", "fontes": [], "origem": "template", "versao_prompt": "template_v1"}
    html = html_parecer(parecer)
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert "Template de reserva" in html
    assert "Não encontrei base normativa" in html
    assert "indisponível" in html_parecer(None)


def test_leitura_equidade_pelo_intervalo():
    assert leitura_equidade(-0.2, 0.5)[0] == "Sem indício"
    assert leitura_equidade(0.3, 1.1)[0] == "Indício · investigar"
    assert leitura_equidade(None, None)[0] == "Aguardando análise"
    assert "[a – b]" in html_tabela_equidade([{"atributo": "Gênero", "comparacao": "f × m"}])


def test_valores_dos_motivos_legiveis():
    assert valor_legivel("divida_sobre_renda", 0.48) == "48%"
    assert valor_legivel("tempo_emprego_atual", "MoreThan5Years") == "mais de 5 anos"
    assert valor_legivel("prazo_meses", 60) == "60 meses"
    assert valor_legivel("renda_total", 2500.0) == "€ 2.500"
    assert valor_legivel("escolaridade", "sem_info") is None