"""Painel do analista — Auditor de Preço Justo (Streamlit).

Páginas: Home (panorama da carteira) · Contratos da base · Análise do contrato · Laboratório ·
Auditoria · Registro · Sobre. O estilo fica em src/app/styles.css; os blocos de HTML, em components.py.
O painel só EXIBE: todos os números vêm da API (prever() do Samuel, ao vivo) ou dos arquivos do
lote da carteira (plano B); o parecer vem da GenAI (ou do template de reserva).
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pandas
import requests
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:  # "streamlit run src/app/main.py" não põe a raiz no path
    sys.path.insert(0, str(ROOT))

from src.app.components import (COUNTRIES, EMPTY_FAIRNESS, RECOMMENDATIONS, SITUATIONS, badge, compact,  # noqa: E402
                                 esc, eur,
                                 html_band_bars, html_considered_data, html_fairness_table,
                                 html_opinion, html_outcome, html_pricing, html_provenance, html_rate_bar,
                                 html_reasons, html_scenario_effects, html_scenario_table, line_icon, pct,
                                 readable_value, review_kpis, situation_badge)

BR_TIMEZONE = timezone(timedelta(hours=-3))

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA E API
# ==========================================
st.set_page_config(
    page_title="Auditor de Preço Justo | Auditoria de Crédito",
    page_icon=":material/balance:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

API_BASE = os.getenv("API_URL", "http://localhost:8000")
TIMEOUT_S = 30  # cobre o modelo + a busca nas normas + LLM (20 s) + queda para o template
QUERY_TIMEOUT_S = 5  # leituras rápidas (decisões)

# ==========================================
# 2. ESTILO (src/app/styles.css)
# ==========================================
STYLE_FILE = Path(__file__).with_name("styles.css")


def load_style() -> None:
    """O CSS mora em styles.css; aqui só é injetado na página."""
    st.markdown(f"<style>{STYLE_FILE.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


load_style()


def md(block: str) -> None:
    st.markdown(compact(block), unsafe_allow_html=True)


# ==========================================
# 3. ESTADO DA SESSÃO E NAVEGAÇÃO
# ==========================================
st.session_state.setdefault("audit_last_result", None)  # contrato aberto na Análise (saída do prever())
st.session_state.setdefault("audit_last_context", {})   # origem, dados do contrato, análise completa da API
st.session_state.setdefault("history", [])   # contratos abertos nesta sessão
st.session_state.setdefault("pending_decisions", [])  # rascunhos NÃO registrados (banco fora); não são histórico
st.session_state.setdefault("analista", "")
st.session_state.setdefault("page", "home")
st.session_state.setdefault("lab", {})  # Laboratório: contrato, original (campos e limites), último cenário, erro

# Páginas do menu do topo. Botões (e não st.tabs) porque o painel troca de página sozinho:
# abrir um contrato vai direto para a Análise.
PAGES = {"home": "Home", "contratos": "Contratos da base", "analise": "Análise do contrato",
         "lab": "Laboratório", "auditoria": "Auditoria", "registro": "Registro", "sobre": "Sobre"}


def go_to(page: str) -> None:
    st.session_state.page = page


# ==========================================
# 4. COMUNICAÇÃO COM A API E DADOS DO LOTE
# ==========================================
@st.cache_data(ttl=20, show_spinner=False)
def api_status() -> dict | None:
    try:
        r = requests.get(f"{API_BASE}/", timeout=3)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException:
        return None


def post_api(route: str, payload: dict) -> tuple[dict | None, str | None]:
    """POST na API. Devolve (resposta, erro) com mensagem amigável para a tela."""
    url = f"{API_BASE}{route}"
    try:
        r = requests.post(url, json=payload, timeout=TIMEOUT_S)
    except requests.exceptions.Timeout:
        return None, f"A API não respondeu em {TIMEOUT_S} s ({url})."
    except requests.exceptions.ConnectionError:
        return None, f"Não foi possível conectar à API em {API_BASE}. Confira se o serviço 'api' está no ar."
    if r.status_code in (404, 422, 503):
        detail = _detail(r)
        if r.status_code == 422 and not isinstance(detail, str):
            return None, "A API recusou os dados enviados (formato inválido). Detalhe: " + r.text[:400]
        return None, detail or "Serviço indisponível na API."
    if not r.ok:
        return None, f"A API respondeu com erro {r.status_code}: {r.text[:300]}"
    try:
        data = r.json()
    except json.JSONDecodeError:
        return None, "A resposta da API não pôde ser interpretada."
    if not isinstance(data, dict):
        return None, "A API retornou uma estrutura diferente da esperada."
    return data, None


def _detail(r) -> str | list | None:
    try:
        return r.json().get("detail")
    except (json.JSONDecodeError, AttributeError):
        return None


def get_api(route: str, params: dict | None = None,
            timeout: float = QUERY_TIMEOUT_S) -> tuple[list | dict | None, str | None]:
    """GET na API (leituras rápidas por padrão). Devolve (dados, erro)."""
    try:
        r = requests.get(f"{API_BASE}{route}", params=params, timeout=timeout)
    except requests.exceptions.RequestException:
        return None, f"Não foi possível conectar à API em {API_BASE}."
    if not r.ok:
        return None, str(_detail(r) or f"A API respondeu com erro {r.status_code}.")
    try:
        return r.json(), None
    except json.JSONDecodeError:
        return None, "A resposta da API não pôde ser interpretada."


def get_list(route: str, params: dict | None = None) -> tuple[list[dict], str | None]:
    """Como get_api, mas garante uma lista (vazia se a resposta vier em outro formato)."""
    data, error_msg = get_api(route, params)
    if error_msg is None and not isinstance(data, list):
        return [], "A API devolveu um formato inesperado."
    return data or [], error_msg


def store_result(resultado: dict, context: dict) -> None:
    st.session_state.audit_last_result = resultado
    st.session_state.audit_last_context = context
    item = {k: resultado.get(k) for k in ("contrato_id", "pd", "faixa", "juro_cobrado", "juro_justo",
                                         "juro_justo_min", "juro_justo_max", "situacao_preco")}
    history = [h for h in st.session_state.history if h["contrato_id"] != item["contrato_id"]]
    st.session_state.history = [item] + history


BATCH_FILE = "carteira_auditoria.csv"  # o lote fica com a API (docs/resultados/); o painel só pede


@st.cache_data(ttl=60, show_spinner=False)
def portfolio_overview(year_min: int | None = None, year_max: int | None = None,
                       country: str | None = None, band: str | None = None) -> tuple[dict | None, str | None]:
    """Panorama da carteira (GET /portfolio/overview). Devolve (dados, erro)."""
    params = {k: v for k, v in {"year_min": year_min, "year_max": year_max, "country": country,
                                "band": band}.items() if v is not None}
    data, error_msg = get_api("/portfolio/overview", params, timeout=TIMEOUT_S)
    return (data, None) if isinstance(data, dict) else (None, error_msg or "resposta inesperada da API")


@st.cache_data(ttl=60, show_spinner=False)
def contract_listing(situation: str | None, limit: int) -> tuple[dict | None, str | None]:
    """Contratos do lote (GET /contracts), do mais distante para o mais próximo da margem."""
    params = {"limit": limit, **({"situation": situation} if situation else {})}
    data, error_msg = get_api("/contracts", params, timeout=TIMEOUT_S)
    return (data, None) if isinstance(data, dict) else (None, error_msg or "resposta inesperada da API")


@st.cache_data(ttl=300, max_entries=8, show_spinner="Preparando a exportação...")
def listing_csv(situation: str | None) -> bytes | None:
    """CSV da lista completa (GET /contracts/export). Só roda quando o analista pede."""
    try:
        r = requests.get(f"{API_BASE}/contracts/export", params={"situation": situation} if situation else None,
                         timeout=TIMEOUT_S)
    except requests.exceptions.RequestException:
        return None
    return r.content if r.ok else None


def api_status_line() -> None:
    """Uma linha com o estado da API, do modelo e do banco (topo de Contratos e Análise)."""
    status = api_status()
    if status is None:
        md(f'<span class="ap-status"><i class="ap-dot" style="background:#d9825b"></i>'
           f'API fora do ar ({esc(API_BASE)}): a Análise abre com os valores do lote.</span>')
        return
    if not status.get("modelo_carregavel", True):
        md('<span class="ap-status"><i class="ap-dot" style="background:#e8a462"></i>'
           'API no ar, mas o arquivo do modelo não está em modelos_salvos/: a Análise usa o lote.</span>')
    else:
        md(f'<span class="ap-status"><i class="ap-dot" style="background:#8cc7a1"></i>API no ar · modelo carregado'
           f' ({esc(status.get("versao_modelo") or "versão não informada")})</span>')
    if not status.get("genai_configurada", True):
        md('<span class="ap-status"><i class="ap-dot" style="background:#e8a462"></i>'
           'GenAI sem chave configurada: o parecer sai pelo template de reserva.</span>')
    if not status.get("banco_disponivel", False):
        md('<span class="ap-status"><i class="ap-dot" style="background:#e8a462"></i>'
           'Banco indisponível: a Análise usa o lote e nenhuma decisão é registrada até ele voltar.</span>')


# ==========================================
# 5. BARRA DE NAVEGAÇÃO
# ==========================================
with st.container(key="top_nav"):
    col_brand, col_links, col_analyst = st.columns([1.5, 5.2, 1.3], gap="small", vertical_alignment="center")
    with col_brand:
        md(f'<div class="nav-brand">{line_icon("balanca", 20)} AUDITOR DE PREÇO JUSTO</div>')
    with col_links:
        for column_, (page_key, page_label) in zip(st.columns(len(PAGES), gap="small"), PAGES.items()):
            with column_:
                st.button(page_label, key=f"nav_{page_key}", on_click=go_to, args=(page_key,),
                          type="primary" if st.session_state.page == page_key else "secondary",
                          use_container_width=True)
    with col_analyst:
        st.text_input("Analista", key="analista", placeholder="Seu nome", label_visibility="collapsed")


# ==========================================
# 6. HOME: PANORAMA DA CARTEIRA
# ==========================================
def portfolio_kpis(summary: dict | None) -> None:
    empty_ = summary is None
    cards = [
        ("Contratos auditados", "[N]" if empty_ else f"{summary['auditados']:,}".replace(",", "."),
         "no período e filtros escolhidos" if empty_ else
         f"+ {summary['revisao_manual']:,} em revisão manual".replace(",", "."), None),
        ("Acima do justo", "[X%]" if empty_ else pct(summary["acima"]), "risco de perder bons clientes",
         SITUATIONS["acima_do_justo"]),
        ("Abaixo do justo", "[Y%]" if empty_ else pct(summary["abaixo"]), "juro não cobre a perda esperada",
         SITUATIONS["abaixo_do_justo"]),
        ("Pago a mais pelos clientes", "€ [VALOR]" if empty_ else eur(summary["pago_a_mais_eur"]),
         "soma acima da margem de incerteza", None),
        ("Perda líquida realizada", "€ [VALOR]" if empty_ else eur(summary["perda_nao_coberta_eur"]),
         "abaixo do justo · só contratos encerrados", None),
    ]
    for column_, (label_, valor, sub, color) in zip(st.columns(5, gap="small"), cards):
        with column_:
            style = f'style="color:{color["cor"]}"' if color else ""
            md(f"""<div class="ap-kpi"><div class="ap-kpi-label">{esc(label_)}</div>
                <div class="ap-kpi-value" {style}>{esc(valor)}</div><div class="ap-kpi-sub">{esc(sub)}</div></div>""")


def render_home() -> None:
    md("""
        <div class="hero-container">
            <div class="hero-title">O preço acompanha<br><span>o risco?</span></div>
            <div class="hero-subtitle">
                Para cada contrato, o Auditor estima a chance de inadimplência, calcula o juro justo para esse risco
                e o compara com o juro cobrado. Um parecer de apoio, em análise hipotética pela lei brasileira,
                explica o resultado. A decisão é sempre do analista.
            </div>
        </div>
    """)
    with st.container(key="hero_cta"):
        st.button("Ir para a auditoria", key="hero_to_contracts", type="primary", icon=":material/arrow_forward:",
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
                        <div class="feature-desc">XGBoost calibrado estima a probabilidade de default; os principais fatores de cada contrato aparecem com nomes legíveis.</div>
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
            st.button("Abrir contratos da base", key="home_to_contracts", icon=":material/arrow_forward:",
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

        st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)
        portfolio_kpis(data["resumo"] if data else None)

        col_faixa, col_fair = st.columns([1, 1.5], gap="medium")
        with col_faixa:
            if data and data["por_faixa"]:
                body = html_band_bars(data["por_faixa"])
                note = "Proporções na carteira filtrada; à direita, número de contratos por faixa."
            else:
                body = '<div class="ap-empty">Distribuição disponível quando o lote da carteira for gerado.</div>'
                note = "Mostra, em cada faixa, a parte abaixo, dentro e acima do juro justo."
            md(f"""<div class="ap-card"><div class="ap-card-title">Situação do preço por faixa de risco</div>
                {body}<div class="ap-foot">{note}</div></div>""")
        with col_fair:
            fairness_rows = (data or {}).get("equidade") or EMPTY_FAIRNESS
            md(f"""<div class="ap-card"><div class="ap-card-title">Equidade no preço: diferença residual entre grupos de mesmo risco</div>
                <div class="ap-card-sub">Diferença de juros (cobrado − justo) que sobra depois de controlar por risco, país, ano, valor e prazo.
                País é controle, não grupo comparado.</div>
                {html_fairness_table(fairness_rows)}
                <div class="ap-foot">“Indício” pede investigação; não é conclusão. Gênero: comparação só entre 0 e 1, dentro do país;
                a codificação de 2017–2019 é suspeita. Controlar por renda pode esconder efeito de gênero.</div></div>""")

        if data and data.get("backtest"):
            columns_ = ["abaixo_do_justo", "dentro_da_margem", "acima_do_justo"]
            table = pandas.DataFrame(
                [[pct(row.get(c)) if row.get(c) is not None else "—" for c in columns_] for row in data["backtest"]],
                index=[f'Faixa {row["faixa"]}' for row in data["backtest"]],
                columns=[SITUATIONS[c]["rotulo"] for c in columns_])
            with st.container(border=True):
                md("""<div class="ap-card-title">Backtest: rentabilidade realizada dentro de cada faixa</div>
                    <div class="ap-card-sub">Contratos encerrados. Se a auditoria funciona, em cada faixa “abaixo do justo”
                    rende menos e “acima do justo” rende mais.</div>""")
                st.dataframe(table, use_container_width=True)


# ==========================================
# 7. CONTRATOS DA BASE
# ==========================================
def current_decisions() -> dict[str, str]:
    data, _ = get_list("/decisions/current")
    return {d["contrato_id"]: d["decisao"] for d in data}


def open_contract(row: dict) -> None:
    """Abre um contrato da base na Análise (callback: roda antes da página redesenhar).

    Uma chamada só: a API devolve o cálculo ao vivo ou, se o banco ou o modelo falharem, os
    números do lote marcados como "lote" (o plano B é decidido na API, não aqui)."""
    cid = str(row["contrato_id"])
    analysis, error_msg = get_api(f"/contracts/{cid}/analysis", timeout=TIMEOUT_S)
    if not (isinstance(analysis, dict) and analysis.get("resultado")):
        st.session_state.contract_open_error = f"Não foi possível abrir o contrato {cid}: {error_msg}"
        return  # fica na página atual, com o erro em português
    st.session_state.contract_open_error = None
    contract = analysis.get("contrato") or {}
    prov = analysis.get("procedencia") or {}
    live = prov.get("modo", "ao_vivo") == "ao_vivo"
    context = {"origem": "carteira", "fonte": "ao_vivo" if live else "lote", "analise": analysis,
               "lote": row, "data": contract.get("data_emprestimo"),
               "pais": contract.get("pais") or row.get("pais"),
               "ano": contract.get("ano") or row.get("ano"),
               "valor": contract.get("valor_concedido") or row.get("valor_concedido"),
               "prazo": contract.get("prazo_meses") or row.get("prazo_meses")}
    store_result(analysis["resultado"], context)
    st.session_state.audit_open_message = None if live else (
        f"A API não calculou este contrato agora ({prov.get('motivo_lote') or 'motivo não informado'}). "
        "A Análise mostra os números do lote, calculados antes, sem os motivos.")
    go_to("analise")


SEARCH_LIMIT = 5000  # IDs na lista da busca (os mais distantes da margem); um ID completo fora dela também abre


@st.cache_data(ttl=300, show_spinner=False)
def search_options() -> list[str]:
    """IDs para a caixa de busca (GET /contracts/ids), do mais distante para o mais próximo da margem."""
    data, _ = get_list("/contracts/ids", {"limit": SEARCH_LIMIT})
    return [str(x) for x in data]


def open_from_search() -> None:
    """Escolher (ou digitar) um ID na busca abre o contrato direto na Análise."""
    chosen = st.session_state.get("contract_search")
    st.session_state.contract_search = None  # a busca volta vazia para a próxima consulta
    row, _ = get_api(f"/contracts/{chosen.strip()}") if chosen else (None, None)
    if not isinstance(row, dict):
        st.session_state.contract_not_found = chosen
        return
    st.session_state.contract_not_found = None
    open_contract(row)


SITUATION_CHIPS = {"Todas": None, "Acima do justo": "acima_do_justo", "Abaixo do justo": "abaixo_do_justo",
                   "Dentro da margem": "dentro_da_margem", "Revisão manual": "revisao_manual"}
ROWS_SHOWN = 25


def render_contracts_page() -> None:
    _, area, _ = st.columns([0.35, 5, 0.35])
    with area:
        md("""<div class="audit-eyebrow">Contratos da base</div>
            <div class="ap-title">Abra qualquer contrato pelo ID</div>
            <div class="ap-meta">Busca única, filtro de situação e lista. Escolher um ID abre a Análise do contrato,
            com o modelo calculando na hora.</div>""")
        api_status_line()
        probe, portfolio_error = contract_listing(None, 1)
        if probe is None:
            md(f"""<div class="ap-alert"><b>Lista de contratos indisponível.</b> {esc(portfolio_error)}</div>""")
            return

        with st.container(key="contract_search_bar"):
            st.selectbox("Buscar pelo ID (loan_id)", search_options(), index=None, key="contract_search",
                         on_change=open_from_search, accept_new_options=True,
                         placeholder="Clique e digite o ID: a lista filtra a cada letra ou número")
            st.caption("Escolher um ID abre a Análise. A lista traz os "
                       f"{SEARCH_LIMIT:,} contratos mais distantes da margem; um ID completo de fora dela também abre."
                       .replace(",", "."))
        if st.session_state.get("contract_not_found"):
            st.warning(f"Nenhum contrato com o ID {st.session_state.contract_not_found} na base.")
        if st.session_state.get("contract_open_error"):
            st.error(st.session_state.contract_open_error)

        st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)
        with st.container(border=True):
            col_filter, col_export = st.columns([4, 1], gap="small", vertical_alignment="bottom")
            with col_filter:
                chosen = st.pills("Situação do preço", list(SITUATION_CHIPS), default="Todas",
                                  key="contract_situation") or "Todas"
            listing, listing_error = contract_listing(SITUATION_CHIPS[chosen], ROWS_SHOWN)
            total = listing["total"] if listing else 0
            with col_export:
                if st.button("Exportar CSV", key="prepare_export", icon=":material/download:",
                             disabled=not total, use_container_width=True):
                    st.session_state.export_queue_csv = chosen
                if st.session_state.get("export_queue_csv") == chosen:  # filtro mudou → pedir de novo
                    content = listing_csv(SITUATION_CHIPS[chosen])
                    if content is None:
                        st.caption("Exportação indisponível: a API não respondeu.")
                    else:
                        st.download_button("Baixar CSV", content, file_name="contratos_da_base.csv",
                                           mime="text/csv", key="download_queue", use_container_width=True)
            md(f'<div class="ap-card-title">{esc(chosen)} · {total:,} contrato(s)</div>'.replace(",", ".")
               + '<div class="ap-card-sub">Do mais distante para o mais próximo da margem de incerteza.</div>')
            if listing_error:
                st.error(f"Não foi possível carregar a lista: {listing_error}")
                return
            if not total:
                st.caption("Nenhum contrato nessa situação.")
                return
            contract_rows(listing["itens"], current_decisions())
            if total > ROWS_SHOWN:
                st.caption(f"Mostrando os {ROWS_SHOWN} primeiros; use a busca para os outros. "
                           "A exportação traz a lista completa.")


CONTRACT_COLUMNS = [1.9, 0.9, 0.6, 0.9, 0.8, 0.9, 1.3, 1.1, 0.8]


def contract_rows(rows: list[dict], decided: dict[str, str]) -> None:
    """Lista com um botão "Abrir" por contrato."""
    headers = ["Contrato", "País", "Ano", "Valor", "Prazo", "Juro cobrado", "Situação", "Decisão atual", ""]
    with st.container(key="contract_list"):
        for column_, title in zip(st.columns(CONTRACT_COLUMNS, gap="small"), headers):
            with column_:
                md(f'<div class="ap-list-head">{esc(title)}</div>')
        for x in rows:
            cid = str(x["contrato_id"])
            d = decided.get(cid)
            cells = [f'<span class="ap-mono">{esc(cid[:13])}…</span>',
                     esc(COUNTRIES.get(x.get("pais"), x.get("pais") or "—")), esc(x.get("ano") or "—"),
                     eur(x.get("valor_concedido")), f'{x["prazo_meses"]} meses' if x.get("prazo_meses") else "—",
                     pct(x.get("juro_cobrado"), 2), situation_badge(x.get("situacao_preco")),
                     badge(RECOMMENDATIONS.get(d, d), "#8cc7a1", "rgba(140,199,161,.10)") if d
                     else '<span class="ap-muted">pendente</span>']
            columns_ = st.columns(CONTRACT_COLUMNS, gap="small", vertical_alignment="center")
            for column_, cell in zip(columns_, cells):
                with column_:
                    md(f'<div class="ap-list-cell">{cell}</div>')
            with columns_[-1]:
                st.button("Abrir", key=f"open_{cid}", on_click=open_contract, args=(x,),
                          use_container_width=True)


# ==========================================
# 8. ANÁLISE DO CONTRATO
# ==========================================
def post_decision(payload: dict) -> tuple[str, str]:
    """POST /decisions. Devolve (situação, mensagem): 'gravada' · 'pendente' (banco fora) · 'recusada'."""
    try:
        r = requests.post(f"{API_BASE}/decisions", json=payload, timeout=QUERY_TIMEOUT_S)
    except requests.exceptions.RequestException:
        return "pendente", "a API não respondeu"
    if r.status_code in (200, 201):
        return "gravada", "Decisão registrada no histórico."
    if r.status_code == 422:
        return "recusada", str(_detail(r) or "A API recusou a decisão.")
    return "pendente", str(_detail(r) or f"erro {r.status_code}")


def record_decision(resultado: dict, decisao: str, justificativa: str,
                    new_rate_pct: float | None) -> tuple[str, str]:
    """Grava a decisão no banco. Se o banco estiver fora, a decisão NÃO é registrada: fica como
    rascunho pendente nesta sessão (para tentar de novo) e a tela diz isso com todas as letras."""
    payload = {
        "requisicao_id": str(uuid4()),  # um por clique: o banco não grava o mesmo clique duas vezes
        "analista": st.session_state.analista.strip(),
        "decisao": decisao,
        "justificativa": justificativa.strip(),
        "taxa_proposta": new_rate_pct / 100 if (decisao == "revisar_preco" and new_rate_pct) else None,
        "resultado": resultado,  # a RESPOSTA do prever(): não carrega gênero nem idade
    }
    status_, message = post_decision(payload)
    if status_ == "pendente":
        st.session_state.pending_decisions.insert(0, {
            "payload": payload, "motivo": message,
            "criada_em": datetime.now(BR_TIMEZONE).isoformat(timespec="seconds")})
        message = ("Decisão NÃO registrada: o banco está indisponível. A justificativa ficou guardada como "
                   "rascunho nesta sessão, mas ainda não existe registro oficial. Tente gravar de novo na "
                   "página Registro quando o banco voltar.")
    return status_, message


def retry_pending() -> None:
    """Tenta gravar de novo os rascunhos pendentes (callback do Registro)."""
    still_pending = []
    for item in st.session_state.pending_decisions:
        status_, message = post_decision(item["payload"])  # mesmo requisicao_id: o banco não duplica
        if status_ == "pendente":
            still_pending.append({**item, "motivo": message})
    st.session_state.pending_decisions = still_pending


def last_decision(contrato_id: str) -> dict | None:
    data, _ = get_list("/decisions", {"contrato_id": contrato_id, "limit": 1})
    return data[0] if data else None


def decision_block(resultado: dict) -> None:
    cid = resultado.get("contrato_id", "?")
    opinion = resultado.get("parecer_ia") or {}
    rec = RECOMMENDATIONS.get(opinion.get("recomendacao"), "—")
    revisao_manual = resultado.get("situacao_preco") == "revisao_manual"
    with st.container(border=True):
        md(f"""
            <div class="ap-card-title">Decisão do analista</div>
            <div class="ap-card-sub">Recomendação do sistema: <b style="color:#e4bd7d">{esc(rec)}</b>.
            O sistema não decide: a decisão final é sempre do analista e fica registrada com o parecer e a justificativa.</div>
        """)
        if revisao_manual:
            md("""<div class="ap-alert">Revisão manual: o sistema não calculou PD nem juro justo. Confira os dados
                de origem e registre na justificativa o que foi verificado; a decisão é gravada sem esses números.</div>""")
        if st.session_state.lab.get("proposta") and st.session_state.lab.get("contrato_id") == cid:
            md(f"""<div class="ap-alert"><b>Taxa do Laboratório.</b> {esc(st.session_state.lab["proposta"])}
                Nada foi registrado: a decisão continua com você.</div>""")
        col_justification, col_rate = st.columns([3, 1], gap="medium")
        with col_justification:
            justificativa = st.text_area("Justificativa (obrigatória)", key=f"justification_{cid}",
                                         placeholder="Explique sua decisão", height=110)
        with col_rate:
            # sem value= quando o Laboratório já preencheu a chave (evita o aviso do Streamlit)
            initial = {} if f"new_rate_{cid}" in st.session_state else {"value": None}
            new = st.number_input("Nova taxa proposta (% a.a.)", key=f"new_rate_{cid}", min_value=0.0,
                                   max_value=500.0, step=0.5, format="%.2f", **initial,
                                   help="Opcional; registrada só quando a decisão for revisar o preço. "
                                        "O Laboratório pode preenchê-la (\"usar como proposta\").")
        buttons = st.columns(3, gap="small")
        choices = [("manter_preco", "Manter preço", "secondary"),
                    ("revisar_preco", "Revisar preço", "primary"),
                    ("encaminhar_compliance", "Encaminhar ao compliance", "secondary")]
        for column_, (decision_key, label_, kind) in zip(buttons, choices):
            with column_:
                if st.button(label_, key=f"decision_{decision_key}_{cid}", type=kind, use_container_width=True):
                    if not (justificativa or "").strip():
                        st.warning("Escreva a justificativa antes de registrar a decisão.")
                    elif not st.session_state.analista.strip():
                        st.warning("Informe o nome do analista responsável no topo da página.")
                    else:
                        where_, message = record_decision(resultado, decision_key, justificativa, new)
                        {"gravada": st.success, "pendente": st.error, "recusada": st.error}[where_](
                            f"{label_}: {message}" if where_ == "gravada" else message)
        d = last_decision(cid)
        if d:
            when = str(d.get("registrada_em", ""))[:16].replace("T", " ")
            st.caption(f"Última decisão neste contrato: {RECOMMENDATIONS.get(d['decisao'], d['decisao'])} "
                       f"por {d['analista']} em {when}.")


UNCERTAINTY = {
    "bootstrap": "intervalo de incerteza estimado por bootstrap (reamostragem por cliente)",
    "margem_padrao": "PD sem intervalo: o pacote do modelo não tem o bootstrap (a margem do juro justo é a "
                     "padrão de ±2 p.p., que não é um intervalo da PD)",
    "nao_calculada": "não se aplica: revisão manual",
}


def uncertainty_text(kind: str | None, n_resamples: int | None) -> str:
    text = UNCERTAINTY.get(kind, "—")
    if kind == "bootstrap" and n_resamples:
        text += (f" · {n_resamples} reamostragens; com poucas reamostragens os extremos do intervalo são "
                 "instáveis, então leia como estimativa, não como 95% calibrado")
    return text


def provenance_rows(r: dict, ctx: dict) -> list[tuple[str, str]]:
    analysis = ctx.get("analise") or {}
    prov = analysis.get("procedencia") or {}
    manual = r.get("situacao_preco") == "revisao_manual"
    if ctx.get("fonte") == "ao_vivo":
        when = str(prov.get("calculado_em", ""))
        try:
            when = datetime.fromisoformat(when).astimezone(BR_TIMEZONE).strftime("agora (%d/%m/%Y %H:%M)")
        except ValueError:
            pass
        seconds = str(round(prov.get("tempo_ms", 0) / 1000, 1)).replace(".", ",")
        return [("Versão do modelo", prov.get("versao_modelo") or r.get("versao_modelo") or "—"),
                ("Data do cálculo", f"{when} · {seconds} s"),
                ("Origem dos dados", "banco: empréstimo, cliente, histórico de crédito"),
                ("Dentro do que o modelo conhece?", "não: revisão manual" if prov.get("fora_do_dominio") else "sim"),
                ("Incerteza da PD", uncertainty_text(prov.get("incerteza"), prov.get("n_reamostras_bootstrap"))),
                ("Arquivo do modelo", " · ".join(x for x in (prov.get("pacote_arquivo"),
                                                             f'hash {prov["pacote_hash"]}' if prov.get("pacote_hash") else None,
                                                             f'de {prov["pacote_data"]}' if prov.get("pacote_data") else None) if x))]
    return [("Versão do modelo", r.get("versao_modelo") or "—"),
            ("Por que o lote", prov.get("motivo_lote") or "a API não calculou este contrato agora"),
            ("Data do cálculo", "lote da carteira (calculado antes)"),
            ("Origem dos dados", f"lote ({BATCH_FILE}), servido pela API"),
            ("Dentro do que o modelo conhece?", "não: revisão manual" if manual else "sim"),
            ("Incerteza da PD", UNCERTAINTY["nao_calculada"] if manual
             else UNCERTAINTY["bootstrap"] if r.get("pd_ic95") else UNCERTAINTY["margem_padrao"]),
            ("Arquivo do modelo", "o do momento em que o lote foi gerado")]


def render_analysis(r: dict, ctx: dict) -> None:
    situation = r.get("situacao_preco", "revisao_manual")
    analysis = ctx.get("analise") or {}
    country = COUNTRIES.get(ctx.get("pais"), ctx.get("pais"))
    year = str(ctx["data"])[:4] if ctx.get("data") else ctx.get("ano")
    meta = [p for p in (country, str(year) if year else None,
                        eur(ctx["valor"]) if ctx.get("valor") else None,
                        f"{ctx['prazo']} meses" if ctx.get("prazo") else None) if p]
    live = ctx.get("fonte") == "ao_vivo"
    chips = [('<span class="ap-chip ap-chip-solid">Calculado agora pelo modelo</span>' if live
              else '<span class="ap-chip ap-chip-batch">Valores do lote</span>'),
             '<span class="ap-chip">Custo do dinheiro: Euribor da época</span>']
    batch_pd = (ctx.get("lote") or {}).get("pd")
    if live and batch_pd is not None and r.get("pd") is not None:
        chips.append('<span class="ap-chip ap-chip-live">Confere com o lote da carteira</span>'
                     if abs(batch_pd - r["pd"]) <= 0.0005 else
                     f'<span class="ap-chip">O lote tinha PD {pct(batch_pd, 1)}: modelo ou dados mudaram</span>')
    md(f"""
        <div class="ap-head">
            <div>
                <div class="audit-eyebrow">Análise do contrato</div>
                <div class="ap-title">Contrato {esc(r.get("contrato_id"))}</div>
                <div class="ap-meta">{esc(" · ".join(meta)) if meta else "&nbsp;"}</div>
            </div>
            <div>{situation_badge(situation)}</div>
        </div>
        <div class="ap-chips">{"".join(chips)}</div>
    """)
    if st.session_state.get("audit_open_message"):
        md(f'<div class="ap-alert"><b>Valores do lote.</b> {esc(st.session_state.audit_open_message)}</div>')

    md(f"""<div class="ap-card"><div class="ap-card-title">Procedência</div>
        {html_provenance(provenance_rows(r, ctx))}</div>""")

    if situation == "revisao_manual":
        md("""<div class="ap-alert"><b>Revisão manual: o contrato está fora do que o modelo conhece.</b> O prever()
            não calcula risco nem juro justo para dados fora da faixa vista no treino (país não visto, ou valor, prazo
            ou renda vazios ou extremos). O analista decide sem a comparação de preço.</div>""")
    for column_, card in zip(st.columns(4, gap="small"), review_kpis(r)):
        with column_:
            md(card)

    if situation != "revisao_manual":
        md(f"""<div class="ap-card"><div class="ap-card-title">Juro cobrado × juro justo</div>
            {html_rate_bar(r)}</div>""")
        source = "parâmetros devolvidos pelo prever()" if analysis.get("precificacao") else "valores do lote"
        md(f"""<div class="ap-card"><div class="ap-card-title">Precificação: como o juro justo foi calculado</div>
            <div class="ap-card-sub">{source}</div>
            {html_pricing(analysis.get("precificacao"), r, country)}</div>""")

    col_reasons, col_opinion = st.columns([1, 1.55], gap="medium")
    with col_reasons:
        empty = ("Os motivos vêm do modelo calculado na hora; o lote não os guarda." if not live
                 else "Sem motivos para este contrato.")
        md(f"""<div class="ap-card"><div class="ap-card-title">O que mais pesou no risco</div>
            <div class="ap-card-sub">Contribuição para a previsão (SHAP), com o valor deste contrato: o que pesou na
            previsão, não causa e efeito. Gênero e idade não entram no modelo. O modelo também considera o mercado do
            contrato (país): ele não aparece nesta lista, por regra do projeto, e os pesos foram calculados sem ele.</div>
            {html_reasons(r.get("motivos") or [], empty)}</div>""")
    with col_opinion:
        md(f"""<div class="ap-card"><div class="ap-seal">Simulação normativa pela lei brasileira ·
            os dados são europeus; a leitura jurídica é hipotética.</div>{html_opinion(r.get("parecer_ia"))}</div>""")

    variables = analysis.get("dados_considerados") or []
    if variables:
        given = sum(v.get("origem") == "fornecida" for v in variables)
        with st.expander(f"Dados considerados · {len(variables)} variáveis "
                         f"({given} fornecidas × {len(variables) - given} derivadas)"):
            md(html_considered_data(variables))

    md(f"""<div class="ap-card"><div class="ap-card-title">Resultado observado</div>
        <div class="ap-card-sub">Só para contratos encerrados: o que aconteceu de verdade depois da concessão.</div>
        {html_outcome(analysis.get("resultado_observado"), ctx.get("lote") if not live else None)}</div>""")

    st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)
    decision_block(r)


def render_analysis_page() -> None:
    _, area, _ = st.columns([0.35, 5, 0.35])
    with area:
        api_status_line()
        result, context = st.session_state.audit_last_result, st.session_state.audit_last_context
        if not result:
            md("""<div class="ap-card"><div class="ap-card-title">Nenhum contrato aberto</div>
                <div class="ap-card-sub">Escolha um contrato em Contratos da base para abri-lo aqui.</div></div>""")
            st.button("Ir para Contratos da base", key="go_contracts", icon=":material/arrow_back:",
                      on_click=go_to, args=("contratos",))
            return
        col_back, col_lab = st.columns([1, 1])
        with col_back:
            st.button("Voltar para a lista", key="back_to_contracts", icon=":material/arrow_back:",
                      on_click=go_to, args=("contratos",))
        with col_lab:
            live = context.get("fonte") == "ao_vivo"
            st.button("Abrir no Laboratório", key="open_lab", icon=":material/science:", on_click=open_lab,
                      args=(result.get("contrato_id"),), disabled=not live,
                      help=None if live else "O Laboratório recalcula com o modelo ao vivo: precisa do banco.")
        render_analysis(result, context)


# ==========================================
# 9. LABORATÓRIO (etapa 2)
# ==========================================
def open_lab(contrato_id: str) -> None:
    """Abre o contrato no Laboratório: pede à API o original e os campos editáveis (sem trocas)."""
    for key in [k for k in st.session_state if str(k).startswith("lab_in_")]:
        del st.session_state[key]  # o formulário começa com os valores do contrato
    base, error_msg = post_api(f"/contracts/{contrato_id}/scenario", {})
    st.session_state.lab = {"contrato_id": contrato_id, "base": base, "resultado": base, "erro": error_msg}
    go_to("lab")


def reset_lab() -> None:
    lab = st.session_state.lab
    for key in [k for k in st.session_state if str(k).startswith("lab_in_")]:
        del st.session_state[key]
    lab.update({"resultado": lab.get("base"), "erro": None})


def _differs(new, old) -> bool:
    if new is None:
        return False
    if isinstance(new, (int, float)) and isinstance(old, (int, float)):
        return abs(float(new) - float(old)) > 1e-9
    return str(new) != str(old)


def lab_changes(base: dict) -> dict:
    """Só o que o analista trocou em relação ao contrato (o resto fica como no banco)."""
    cid = base["contrato_id"]
    changes = {}
    for f in base["campos"]:
        value = st.session_state.get(f"lab_in_{f['campo']}_{cid}")
        if _differs(value, f.get("valor_atual")):
            changes[f["campo"]] = int(value) if f["tipo"] == "inteiro" else value
    rate = st.session_state.get(f"lab_in_juro_{cid}")
    original_rate = round(base["original"]["juro_cobrado"] * 100, 4)
    if rate is not None and abs(rate - original_rate) > 1e-6:
        changes["juro_aa"] = rate
    return changes


def run_lab() -> None:
    lab = st.session_state.lab
    result, error_msg = post_api(f"/contracts/{lab['contrato_id']}/scenario", lab_changes(lab["base"]))
    # com erro, nenhum cenário fica na tela (para não parecer que o anterior é o resultado novo)
    lab.update({"resultado": result or lab.get("base"), "erro": error_msg, "proposta": None})


def use_as_proposal() -> None:
    """Leva o juro do cenário para a decisão na Análise, sem registrar nada."""
    lab = st.session_state.lab
    rate = round(lab["resultado"]["cenario"]["juro_cobrado"] * 100, 2)
    st.session_state[f"new_rate_{lab['contrato_id']}"] = rate
    lab["proposta"] = (f"{_num_br(rate)}% a.a. veio do Laboratório e está em \"Nova taxa proposta\". "
                       "Ela só é gravada se você escolher \"Revisar preço\".")
    go_to("analise")


def _num_br(value: float) -> str:
    return f"{value:.2f}".replace(".", ",")


def lab_input(field: dict, cid: str):
    key = f"lab_in_{field['campo']}_{cid}"
    current = field.get("valor_atual")
    note = {"treino": "Limite: faixa vista no treino do modelo.",
            "provisorio": "Limite provisório, até o Samuel passar a faixa vista no treino."}.get(field["limite"])
    if field["tipo"] == "categoria":
        options = field.get("opcoes") or []
        index = options.index(current) if current in options else None
        return st.selectbox(field["rotulo"].capitalize(), options, index=index, key=key,
                            format_func=lambda v, c=field["campo"]: readable_value(c, v) or str(v),
                            placeholder="sem informação")
    integer = field["tipo"] == "inteiro"
    cast = int if integer else float
    lo, hi = field.get("minimo"), field.get("maximo")
    if current is not None:  # o contrato pode estar fora da faixa: o campo precisa aceitar o valor dele
        lo = min(lo, current) if lo is not None else None
        hi = max(hi, current) if hi is not None else None
    kwargs = {"min_value": cast(lo) if lo is not None else None, "max_value": cast(hi) if hi is not None else None,
              "step": 1 if integer else (1.0 if field["campo"] == "prazo_meses" else 50.0),
              "format": "%d" if integer else "%.2f", "help": note}
    if key not in st.session_state:
        kwargs["value"] = cast(current) if current is not None else None
    return st.number_input(field["rotulo"].capitalize(), key=key, **kwargs)


def render_lab_page() -> None:
    _, area, _ = st.columns([0.35, 5, 0.35])
    with area:
        api_status_line()
        lab = st.session_state.lab
        md("""<div class="audit-eyebrow">Laboratório do contrato</div>
            <div class="ap-title">E se este contrato fosse diferente?</div>""")
        if not lab.get("contrato_id"):
            md("""<div class="ap-card"><div class="ap-card-title">Nenhum contrato no Laboratório</div>
                <div class="ap-card-sub">Abra um contrato e clique em "Abrir no Laboratório". O contrato original não
                muda: o Laboratório só mostra o que o modelo diria com outros valores.</div></div>""")
            st.button("Ir para Contratos da base", key="lab_go_contracts", icon=":material/arrow_back:",
                      on_click=go_to, args=("contratos",))
            return
        cid, base = lab["contrato_id"], lab.get("base")
        st.button("Voltar para a Análise", key="lab_back", icon=":material/arrow_back:",
                  on_click=go_to, args=("analise",))
        if not base:
            st.error(f"Não foi possível abrir o contrato {cid} no Laboratório: {lab.get('erro')}")
            return
        md(f"""<div class="ap-card"><div class="ap-card-title">Contrato {esc(cid)}</div>
            <div class="ap-card-sub">Troque os campos e recalcule: a API aplica só o que mudou sobre o contrato do banco
            e roda o modelo de novo. Nada é gravado e o contrato original continua igual. Gênero e idade não estão aqui:
            não entram no modelo.</div></div>""")

        with st.form(f"lab_form_{cid}", border=True):
            fields = base["campos"]
            columns_ = st.columns(2, gap="medium")
            for n, field in enumerate(fields):
                with columns_[n % 2]:
                    lab_input(field, cid)
            md('<div class="ap-card-sub" style="margin-top:.4rem"><b>Juro cobrado</b> · não é variável do modelo: '
               'muda a situação do preço e a parcela, nunca o risco.</div>')
            rate_key = f"lab_in_juro_{cid}"
            rate_kwargs = {} if rate_key in st.session_state else {
                "value": round(base["original"]["juro_cobrado"] * 100, 2)}
            st.number_input("Juro cobrado (% a.a. nominal)", key=rate_key, min_value=0.01, max_value=500.0,
                            step=0.5, format="%.2f", **rate_kwargs)
            st.form_submit_button("Recalcular com o modelo", type="primary", icon=":material/calculate:",
                                  on_click=run_lab)
        st.button("Voltar aos valores do contrato", key="lab_reset", icon=":material/restart_alt:",
                  on_click=reset_lab)

        if lab.get("erro"):
            st.error(f"O modelo não recalculou: {lab['erro']}")
        result = lab.get("resultado")
        if not result or not result.get("alteracoes"):
            st.caption("Troque algum campo e clique em \"Recalcular com o modelo\".")
            return
        prov = result.get("procedencia") or {}
        when = str(prov.get("calculado_em", ""))
        try:
            when = datetime.fromisoformat(when).astimezone(BR_TIMEZONE).strftime("%d/%m/%Y %H:%M")
        except ValueError:
            pass
        md(f"""<div class="ap-card"><div class="ap-card-title">Original × recalculado</div>
            <div class="ap-card-sub">Modelo {esc(prov.get("versao_modelo"))} · calculado agora ({esc(when)}) ·
            {esc(uncertainty_text(prov.get("incerteza"), prov.get("n_reamostras_bootstrap")))}</div>
            {html_scenario_table(result["original"], result["cenario"], result.get("parcela_original"),
                                 result.get("parcela_cenario"))}</div>""")
        if result["cenario"].get("situacao_preco") == "revisao_manual":
            md("""<div class="ap-alert"><b>Revisão manual.</b> Com esses valores o contrato sai do que o modelo
                conhece: o prever() não calcula risco nem juro justo.</div>""")
        md(f"""<div class="ap-card"><div class="ap-card-title">O que mudou o risco</div>
            <div class="ap-card-sub">Cada campo trocado foi testado sozinho, com o modelo rodado de novo. Os efeitos
            não somam exatamente a mudança total: o modelo combina as variáveis.</div>
            {html_scenario_effects(result.get("efeitos") or [])}</div>""")
        rate_changed = result["cenario"].get("juro_cobrado") != result["original"].get("juro_cobrado")
        st.button("Usar como proposta", key="lab_use", type="primary", icon=":material/arrow_forward:",
                  on_click=use_as_proposal, disabled=not rate_changed,
                  help="Leva o juro cobrado do cenário para \"Nova taxa proposta\" na Análise, sem registrar nada."
                  if rate_changed else "Mude o juro cobrado para usar o cenário como proposta.")


# ==========================================
# 10. AUDITORIA (equidade agregada; teste de invariância na etapa 3)
# ==========================================
def render_audit_page() -> None:
    _, area, _ = st.columns([0.35, 5, 0.35])
    with area:
        data, _ = portfolio_overview()
        fairness = (data or {}).get("equidade")
        md(f"""<div class="audit-eyebrow">Auditoria</div>
            <div class="ap-title">O preço trata grupos iguais de forma igual?</div>
            <div class="ap-card"><div class="ap-card-title">Equidade agregada</div>
            <div class="ap-card-sub">Diferença de juros (cobrado − justo) que sobra depois de controlar por risco, país,
            ano, valor e prazo.</div>
            {html_fairness_table(fairness or EMPTY_FAIRNESS)}
            <div class="ap-foot">Filtros por grupo ficam para depois da demo (a metodologia já existe em equidade.py).
            Gênero e idade servem só para esta auditoria: não aparecem na análise de um contrato.</div></div>""")


# ==========================================
# 11. REGISTRO DE DECISÕES
# ==========================================
RECORD_COLUMNS = {
    "registrada_em": "Registrada em", "analista": "Analista", "contrato_id": "Contrato", "origem": "Origem",
    "decisao": "Decisão", "recomendacao_sistema": "Recomendação do sistema", "situacao_preco": "Situação",
    "juro_cobrado": "Juro cobrado", "juro_justo": "Juro justo", "taxa_proposta": "Nova taxa",
    "justificativa": "Justificativa", "origem_parecer": "Parecer", "versao_modelo": "Modelo",
}

def render_records() -> None:
    decisions, database_error = get_list("/decisions", {"limit": 1000})  # só o que está no banco
    md("""<div class="audit-eyebrow">Registro de decisões</div>
        <div class="ap-title">Quem decidiu, o quê e por quê</div>
        <div class="ap-meta">Cada decisão fica gravada no banco com o parecer, a recomendação do sistema e a
        justificativa (direito de revisão, LGPD art. 20). O registro é só de inclusão: para corrigir, registre uma
        nova decisão; a mais recente vale.</div>""")
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    if database_error:
        st.error(f"Histórico indisponível ({database_error}): o banco não respondeu.")
    pending = st.session_state.pending_decisions
    if pending:
        with st.container(border=True):
            md(f"""<div class="ap-card-title" style="color:#f2b48a">Decisões não registradas · {len(pending)}</div>
                <div class="ap-card-sub">Rascunhos guardados só nesta sessão porque o banco estava indisponível.
                <b>Não fazem parte do histórico</b> e se perdem se a página for fechada. Tente gravar de novo.</div>""")
            for item in pending:
                pl = item["payload"]
                st.caption(f'{item["criada_em"][:16].replace("T", " ")} · {pl["resultado"].get("contrato_id")} · '
                           f'{RECOMMENDATIONS.get(pl["decisao"], pl["decisao"])} · pendente ({item["motivo"]})')
            st.button("Tentar gravar de novo", key="retry_pending", type="primary", icon=":material/refresh:",
                      on_click=retry_pending)
    if not decisions:
        st.caption("Nenhuma decisão registrada no histórico ainda.")
    else:
        table = pandas.DataFrame(decisions)
        divergent = int((table["decisao"] != table["recomendacao_sistema"]).sum())
        c1, c2, c3 = st.columns(3, gap="small")
        with c1:
            md(f'<div class="ap-kpi"><div class="ap-kpi-label">Decisões registradas</div><div class="ap-kpi-value">{len(table)}</div></div>')
        with c2:
            md(f'<div class="ap-kpi"><div class="ap-kpi-label">Diferentes da recomendação</div><div class="ap-kpi-value">{divergent}</div>'
               '<div class="ap-kpi-sub">o analista discordou do sistema</div></div>')
        with c3:
            n_compliance = int((table["decisao"] == "encaminhar_compliance").sum())
            md(f'<div class="ap-kpi"><div class="ap-kpi-label">Encaminhadas ao compliance</div><div class="ap-kpi-value">{n_compliance}</div></div>')
        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        shown = table.reindex(columns=list(RECORD_COLUMNS)).assign(
            registrada_em=table["registrada_em"].astype(str).str[:16].str.replace("T", " "),
            decisao=table["decisao"].map(RECOMMENDATIONS),
            recomendacao_sistema=table["recomendacao_sistema"].map(RECOMMENDATIONS),
            situacao_preco=table["situacao_preco"].map(lambda v: SITUATIONS.get(v, {}).get("rotulo", v)),
            **{c: table[c].map(lambda v: pct(v) if v is not None and pandas.notna(v) else "—")
               for c in ("juro_cobrado", "juro_justo", "taxa_proposta") if c in table},
        ).rename(columns=RECORD_COLUMNS)
        st.dataframe(shown, use_container_width=True, hide_index=True)
        col_csv, col_json, _ = st.columns([1, 1, 2], gap="small")
        with col_csv:
            st.download_button("Exportar CSV", table.to_csv(index=False).encode("utf-8"),
                               file_name="decisoes_analista.csv", mime="text/csv")
        with col_json:
            st.download_button("Exportar JSON", json.dumps(decisions, ensure_ascii=False, indent=2, default=str).encode("utf-8"),
                               file_name="decisoes_analista.json", mime="application/json")


def render_records_page() -> None:
    _, area, _ = st.columns([0.35, 5, 0.35])
    with area:
        render_records()


# ==========================================
# 12. SOBRE O PROJETO
# ==========================================
TEAM = [
    ("YG", "Yasmin Garcia", "App & Infraestrutura",
     "Docker, API FastAPI, painel Streamlit, integração contínua e vídeo da demo."),
    ("MA", "Marcos", "Dados & Processo",
     "Carga do Bondora e das séries de juros no PostgreSQL, qualidade dos dados, EDA e BPMN."),
    ("SL", "Samuel", "Modelo & Juro Justo",
     "Modelo de risco calibrado, motivos (SHAP), juro justo com margem de incerteza, equidade e backtest."),
    ("MV", "M. Vitória", "GenAI & RAG",
     "Normas e busca (RAG), prompts, parecer com checagem por código e template de reserva."),
]

STUDY_MAP = [
    ("Base Bondora no PostgreSQL", "Marcos", "Dados buscados pelo ID; resultado observado"),
    ("XGBoost calibrado + bootstrap", "Samuel", "Risco e intervalo calculados na hora; Laboratório"),
    ("SHAP", "Samuel", "“O que mais pesou”, com o valor do contrato"),
    ("Juro justo por fluxo de caixa", "Samuel", "Precificação; Laboratório"),
    ("Equidade", "Samuel", "Auditoria; Home"),
    ("RAG com normas + checagem", "M. Vitória", "Parecer da Análise"),
    ("API, painel, decisões no banco", "Yasmin", "Todo o fluxo e o Registro"),
]


def render_about_page() -> None:
    md("""
        <div class="section-header">
            <h2>Sobre o Projeto</h2>
            <div class="gold-divider"></div>
            <p>Projeto integrador do <b>Bootcamp IA 2026</b> (segmento BFSI).<br>
            Dados reais do Bondora (2009–2021) como substitutos do comportamento de crédito; análise jurídica hipotética pela lei brasileira.</p>
        </div>
    """)
    md('<div class="team-grid">' + "".join(f"""
        <div class="team-card">
            <div class="team-avatar">{code}</div>
            <div class="team-name">{esc(name_)}</div>
            <div class="team-role">{esc(role)}</div>
            <div class="team-bio">{esc(bio)}</div>
        </div>""" for code, name_, role, bio in TEAM) + "</div>")
    _, area, _ = st.columns([0.35, 5, 0.35])
    with area:
        body = "".join(f"<tr><td>{esc(a)}</td><td>{esc(b)}</td><td>{esc(c)}</td></tr>" for a, b, c in STUDY_MAP)
        md(f"""<div class="ap-card"><div class="ap-card-title">Onde cada parte do estudo aparece funcionando</div>
            <table class="ap-table"><thead><tr><th>Parte do estudo</th><th>Quem fez</th><th>Onde aparece</th></tr></thead>
            <tbody>{body}</tbody></table></div>""")


# ==========================================
# 13. MOSTRA A PÁGINA ESCOLHIDA
# ==========================================
{"home": render_home, "contratos": render_contracts_page, "analise": render_analysis_page,
 "lab": render_lab_page, "auditoria": render_audit_page, "registro": render_records_page,
 "sobre": render_about_page}[st.session_state.page]()
