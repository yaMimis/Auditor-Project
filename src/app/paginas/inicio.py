"""Página Início: capa, faixa explicativa e panorama da carteira (GET /portfolio/overview).
"""

import pandas
import streamlit as st

from src.app.components import (
    COUNTRIES, esc, eur, eur_short, html_band_bars, html_logo, image_data_uri, info_tip, line_icon, pct, SITUATIONS)
from src.app.nucleo import go_to, IMAGES_DIR, md, portfolio_overview


def portfolio_kpis(summary: dict | None) -> None:
    empty_ = summary is None
    cards = [
        ("Contratos auditados", "[N]" if empty_ else f"{summary['auditados']:,}".replace(",", "."),
         "no período e filtros escolhidos" if empty_ else
         f"+ {summary['revisao_manual']:,} em revisão manual".replace(",", "."), None, "auditados"),
        ("Acima do justo", "[X%]" if empty_ else pct(summary["acima"]), "juro acima do que o risco justifica",
         SITUATIONS["acima_do_justo"], "acima"),
        ("Abaixo do justo", "[Y%]" if empty_ else pct(summary["abaixo"]), "juro pode não cobrir o risco",
         SITUATIONS["abaixo_do_justo"], "abaixo"),
        ("Cobrado a mais", "€ [VALOR]" if empty_ else eur_short(summary["pago_a_mais_eur"]),
         "estimativa acima do teto da margem", None, "cobrado_mais",
         None if empty_ else eur(summary["pago_a_mais_eur"])),
        ("Prejuízo real", "€ [VALOR]" if empty_ else eur_short(summary["perda_nao_coberta_eur"]),
         "abaixo do justo, já encerrados", None, "prejuizo",
         None if empty_ else eur(summary["perda_nao_coberta_eur"])),
    ]
    # cartões do mesmo tamanho, uma linha de título e uma de número (styles/04_cartoes.css: .ap-kpi-home)
    for column_, card in zip(st.columns(5, gap="medium"), cards):
        label_, valor, sub, color, info = card[:5]
        exact = card[5] if len(card) > 5 else None  # valor exato em euro: aparece ao passar o mouse
        with column_:
            style = f'style="color:{color["cor"]}"' if color else ""
            title = f' title="{esc(exact)}"' if exact else ""
            md(f"""<div class="ap-kpi ap-kpi-home">{info_tip(info)}<div class="ap-kpi-label">{esc(label_)}</div>
                <div class="ap-kpi-value" {style}{title}>{esc(valor)}</div><div class="ap-kpi-sub">{esc(sub)}</div></div>""")


def render_home() -> None:
    cover = image_data_uri(IMAGES_DIR, "capa")
    if cover:  # foto de capa local no lugar da imagem padrão do styles/03_inicio.css (a mesma película escura por cima)
        md(f"""<style>.hero-container {{ background-image: linear-gradient(to right, rgba(18,19,21,.95) 25%,
            rgba(18,19,21,.7) 100%), url('{cover}') !important; }}</style>""")
    md("""
        <div class="hero-container">
            <div class="hero-logo">""" + html_logo("hero", animated=True) + """</div>
            <div class="hero-title">O preço acompanha<br><span>o risco?</span></div>
            <div class="hero-subtitle">
                Para cada contrato, o sistema estima a chance de inadimplência, calcula o juro justo para esse risco
                e o compara com o juro cobrado. Um parecer de apoio, em análise hipotética pela lei brasileira,
                explica o resultado. A decisão é sempre do analista.
            </div>
        </div>
    """)
    with st.container(key="hero_cta"):
        st.button("Ver os contratos", key="hero_to_contracts", type="primary", icon=":material/arrow_forward:",
                  on_click=go_to, args=("contratos",))
    md(f"""
        <div class="features-strip">
            <div class="features-grid">
                <div class="feature-item">
                    <div class="feature-icon">{line_icon('grafico', 26)}</div>
                    <div>
                        <div class="feature-title">Juro justo por fluxo de caixa</div>
                        <div class="feature-desc">Custo do dinheiro (Euribor da época), perda esperada ao longo do contrato e custos calibrados na carteira, com margem de incerteza.</div>
                    </div>
                </div>
                <div class="feature-item">
                    <div class="feature-icon">{line_icon('chip', 26)}</div>
                    <div>
                        <div class="feature-title">Modelo de risco explicável</div>
                        <div class="feature-desc">Um modelo XGBoost calibrado estima a chance de inadimplência; o que mais pesou em cada contrato aparece com nomes legíveis.</div>
                    </div>
                </div>
                <div class="feature-item">
                    <div class="feature-icon">{line_icon('documento', 26)}</div>
                    <div>
                        <div class="feature-title">Parecer com normas e checagem</div>
                        <div class="feature-desc">IA generativa com busca em CDC, LGPD e normas do CMN. Os números do texto são conferidos por código; se algo falhar, entra o template.</div>
                    </div>
                </div>
            </div>
        </div>
    """)
    _, home_area, _ = st.columns([0.35, 5, 0.35])
    with home_area:
        meta, portfolio_error = portfolio_overview()
        col_title, col_f1, col_f2, col_f3 = st.columns([2.2, 1.3, 0.8, 0.8], gap="small")
        with col_title:
            md("""<div class="audit-eyebrow">Panorama da carteira</div>
                <div class="ap-title">O preço acompanha o risco?</div>
                <div class="ap-meta">Contratos pontuados pelo modelo · reestruturados fora da comparação de preço</div>""")
            st.button("Ver os contratos", key="home_to_contracts", icon=":material/arrow_forward:",
                      on_click=go_to, args=("contratos",))
        data = None
        if meta:
            year_min, year_max = meta["anos"]
            years = (year_min, year_max)
            with col_f1:
                if year_min < year_max:
                    years = st.slider("Período", year_min, year_max, (year_min, year_max), key="f_years")
                else:
                    st.caption(f"Período: {year_min}")
            with col_f2:
                p = st.selectbox("País", ["Todos"] + meta["paises"], key="f_country",
                                 format_func=lambda s: COUNTRIES.get(s, s))
            with col_f3:
                f = st.selectbox("Faixa de risco", ["Todas"] + meta["faixas"], key="f_band")
            data, portfolio_error = portfolio_overview(years[0], years[1], None if p == "Todos" else p,
                                                       None if f == "Todas" else f)

        if portfolio_error:
            md(f"""<div class="ap-alert"><b>Panorama indisponível.</b> {esc(portfolio_error)} Os campos aparecem entre
                colchetes até a API servir o lote da carteira.</div>""")

        portfolio_kpis(data["resumo"] if data else None)

        # Situação por faixa e backtest lado a lado (a equidade fica só na página Auditoria).
        col_band, col_backtest = st.columns(2, gap="medium")
        if data and data["por_faixa"]:
            body = html_band_bars(data["por_faixa"])
            note = "Proporções na carteira filtrada; à direita, número de contratos por faixa."
        else:
            body = '<div class="ap-empty">Distribuição disponível quando o lote da carteira for gerado.</div>'
            note = "Mostra, em cada faixa, a parte abaixo, dentro e acima do juro justo."
        with col_band:
            md(f"""<div class="ap-card">{info_tip("faixas")}<div class="ap-card-title">Situação do preço por faixa de risco</div>
                {body}<div class="ap-foot">{note}</div></div>""")

        if data and data.get("backtest"):
            columns_ = ["abaixo_do_justo", "dentro_da_margem", "acima_do_justo"]
            table = pandas.DataFrame(
                [[pct(row.get(c)) if row.get(c) is not None else "—" for c in columns_] for row in data["backtest"]],
                index=[f'Faixa {row["faixa"]}' for row in data["backtest"]],
                columns=[SITUATIONS[c]["rotulo"] for c in columns_])
            with col_backtest, st.container(border=True, key="home_backtest"):  # alinhado ao cartão ao lado (styles/)
                md(f"""{info_tip("backtest")}<div class="ap-card-title">Backtest (2016): retorno real por faixa e situação</div>
                    <div class="ap-card-sub">Contratos encerrados. Se a auditoria funciona, em cada faixa “abaixo do justo”
                    rende menos e “acima do justo” rende mais.</div>""")
                st.dataframe(table, use_container_width=True)
