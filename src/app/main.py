from __future__ import annotations

import html
import json
import os
from datetime import datetime
from typing import Any

import requests
import streamlit as st


# -----------------------------------------------------------------------------
# Configuração
# -----------------------------------------------------------------------------
APP_NAME = "VERITAS | Auditoria de Crédito"
API_BASE_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")
API_ENDPOINT = f"{API_BASE_URL}/prever"
REQUEST_TIMEOUT = float(os.getenv("API_TIMEOUT", "15"))

st.set_page_config(
    page_title=APP_NAME,
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# -----------------------------------------------------------------------------
# Design system — fintech / legal-tech
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');

    :root {
        --canvas: #080d16;
        --canvas-2: #0b1220;
        --panel: #101a2a;
        --panel-2: #142033;
        --panel-soft: rgba(19, 31, 49, .76);
        --line: rgba(192, 169, 124, .16);
        --line-cool: rgba(148, 163, 184, .14);
        --gold: #d4ad70;
        --gold-2: #f0d4a0;
        --gold-deep: #9e7540;
        --text: #f1f0eb;
        --muted: #9aa7b8;
        --muted-2: #718096;
        --green: #54c6a3;
        --red: #ef7e7e;
        --amber: #e7b866;
    }

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
    }
    [data-testid="stAppViewContainer"] {
        color: var(--text);
        background:
            radial-gradient(ellipse at 82% 2%, rgba(151, 111, 57, .13), transparent 27%),
            radial-gradient(ellipse at 8% 35%, rgba(39, 75, 112, .14), transparent 34%),
            linear-gradient(145deg, #080d16 0%, #0b1220 50%, #080e18 100%);
    }
    [data-testid="stHeader"] { background: rgba(8, 13, 22, .72); }
    [data-testid="stToolbar"] { right: 1rem; }
    .block-container {
        max-width: 1600px;
        padding: 1.55rem 2.25rem 3.25rem;
    }
    footer { visibility: hidden; }
    #MainMenu { visibility: hidden; }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0c1422 0%, #0a111d 100%);
        border-right: 1px solid var(--line-cool);
    }
    [data-testid="stSidebar"] > div:first-child { padding-top: 1.1rem; }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stSidebar"] label { color: #c5cfdb; }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 { color: var(--text); font-family: 'Manrope', sans-serif; }
    [data-testid="stSidebar"] hr { border-color: var(--line-cool); }
    [data-testid="stSidebar"] input,
    [data-testid="stSidebar"] textarea,
    [data-testid="stSidebar"] [data-baseweb="select"] > div {
        background: #111d2d !important;
        border-color: rgba(160, 176, 196, .18) !important;
        color: var(--text) !important;
        border-radius: 9px !important;
    }
    [data-testid="stSidebar"] [data-testid="stNumberInput"] button {
        background: #19283a !important;
        color: #d9e1eb !important;
        border-color: rgba(160, 176, 196, .16) !important;
    }

    /* Inputs and buttons */
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stSelectbox"] [data-baseweb="select"] > div {
        background: rgba(17, 29, 45, .88) !important;
        color: var(--text) !important;
        border: 1px solid rgba(160, 176, 196, .17) !important;
        border-radius: 9px !important;
    }
    [data-testid="stTextInput"] input:focus,
    [data-testid="stNumberInput"] input:focus {
        border-color: rgba(212, 173, 112, .75) !important;
        box-shadow: 0 0 0 1px rgba(212, 173, 112, .18) !important;
    }
    .stButton > button, [data-testid="stFormSubmitButton"] > button {
        min-height: 2.75rem;
        border-radius: 9px;
        border: 1px solid rgba(240, 212, 160, .32);
        background: linear-gradient(135deg, #c89a58 0%, #e4bd7d 100%);
        color: #17130d;
        font-weight: 800;
        letter-spacing: .01em;
        box-shadow: 0 8px 24px rgba(174, 128, 63, .15);
        transition: transform .18s ease, box-shadow .18s ease, filter .18s ease;
    }
    .stButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover {
        transform: translateY(-1px);
        filter: brightness(1.06);
        box-shadow: 0 12px 28px rgba(174, 128, 63, .22);
        color: #17130d;
        border-color: var(--gold-2);
    }
    .stButton > button:focus, [data-testid="stFormSubmitButton"] > button:focus {
        box-shadow: 0 0 0 2px #0b1220, 0 0 0 4px rgba(212,173,112,.45);
    }

    /* Main header */
    .brand-row { display:flex; align-items:center; gap:12px; margin:0 0 1.1rem; }
    .brand-mark {
        width:42px; height:42px; display:flex; align-items:center; justify-content:center;
        border-radius:12px; color:#17130d; font-family:'Manrope',sans-serif; font-weight:800;
        background:linear-gradient(145deg,#f0d4a0,#b88548);
        box-shadow:0 8px 25px rgba(185,133,72,.2); font-size:20px;
    }
    .brand-name { font-family:'Manrope',sans-serif; font-weight:800; letter-spacing:.16em; font-size:13px; color:#f0e8d9; }
    .brand-sub { color:#7f8da0; font-size:10px; letter-spacing:.16em; text-transform:uppercase; margin-top:2px; }
    .top-meta { display:flex; justify-content:flex-end; align-items:center; gap:9px; padding-top:5px; }
    .top-pill {
        display:inline-flex; align-items:center; gap:7px; padding:7px 11px;
        border:1px solid var(--line-cool); border-radius:99px; color:#aeb9c7;
        font-size:10px; letter-spacing:.09em; text-transform:uppercase; background:rgba(15,25,40,.6);
    }
    .live-dot { width:6px; height:6px; border-radius:50%; background:#54c6a3; box-shadow:0 0 10px rgba(84,198,163,.6); }
    .hero {
        position:relative; overflow:hidden; display:flex; justify-content:space-between; align-items:center;
        gap:24px; min-height:184px; padding:28px 32px; margin: .25rem 0 1.35rem;
        border:1px solid rgba(212,173,112,.22); border-radius:18px;
        background:linear-gradient(110deg,rgba(20,31,48,.97) 0%,rgba(15,25,40,.95) 55%,rgba(35,31,27,.78) 100%);
        box-shadow:0 18px 50px rgba(0,0,0,.18), inset 0 1px rgba(255,255,255,.025);
    }
    .hero:after {
        content:''; position:absolute; width:360px; height:360px; right:-80px; top:-180px; border-radius:50%;
        border:1px solid rgba(212,173,112,.12); box-shadow:0 0 0 28px rgba(212,173,112,.025),0 0 0 58px rgba(212,173,112,.02);
        pointer-events:none;
    }
    .eyebrow { color:var(--gold); text-transform:uppercase; letter-spacing:.2em; font-size:10px; font-weight:700; margin-bottom:10px; }
    .hero h1 { color:#f5f1e9; font-family:'Manrope',sans-serif; font-size:clamp(27px,3vw,39px); line-height:1.14; letter-spacing:-.04em; margin:0; font-weight:700; }
    .hero h1 span { color:var(--gold-2); }
    .hero-copy { color:#a8b3c2; margin:11px 0 0; font-size:13px; max-width:620px; line-height:1.65; }
    .hero-side { min-width:190px; position:relative; z-index:1; border-left:1px solid rgba(212,173,112,.2); padding-left:25px; }
    .hero-side-label { color:#7f8b9a; font-size:9px; letter-spacing:.16em; text-transform:uppercase; }
    .hero-side-value { font-family:'Manrope',sans-serif; color:#f0d4a0; font-size:19px; font-weight:700; margin:6px 0 4px; }
    .hero-side-note { color:#95a1b1; font-size:11px; line-height:1.5; }

    /* Section headings and cards */
    .section-kicker { color:var(--gold); font-size:10px; font-weight:700; letter-spacing:.17em; text-transform:uppercase; margin:0 0 5px; }
    .section-title { color:#f0f2f4; font:700 20px 'Manrope',sans-serif; letter-spacing:-.025em; margin:0; }
    .section-subtitle { color:#8f9bad; font-size:12px; margin-top:5px; }
    .metric-card {
        height:100%; min-height:128px; padding:17px 18px 15px; border-radius:14px;
        border:1px solid rgba(153,171,194,.13); background:linear-gradient(145deg,rgba(20,32,50,.94),rgba(14,23,37,.94));
        box-shadow:0 10px 28px rgba(0,0,0,.12); position:relative; overflow:hidden;
    }
    .metric-card:before { content:''; position:absolute; top:0; left:18px; right:18px; height:1px; background:linear-gradient(90deg,transparent,rgba(212,173,112,.42),transparent); }
    .metric-top { display:flex; justify-content:space-between; align-items:center; gap:10px; }
    .metric-label { color:#9ba8b8; font-size:10px; letter-spacing:.11em; text-transform:uppercase; line-height:1.4; }
    .metric-icon { width:27px; height:27px; display:flex; align-items:center; justify-content:center; border-radius:8px; color:#e6c58d; background:rgba(212,173,112,.1); font-size:14px; }
    .metric-value { color:#f3f0e9; font:700 clamp(21px,2vw,27px) 'Manrope',sans-serif; margin-top:13px; letter-spacing:-.035em; white-space:nowrap; }
    .metric-foot { color:#718096; font-size:10px; margin-top:3px; }
    .panel {
        border:1px solid rgba(153,171,194,.13); border-radius:15px;
        background:linear-gradient(145deg,rgba(18,29,46,.93),rgba(13,22,36,.94));
        padding:19px 20px; box-shadow:0 12px 34px rgba(0,0,0,.12); height:100%;
    }
    [data-testid="stVerticalBlockBorderWrapper"] {
        border:1px solid rgba(153,171,194,.13) !important;
        border-radius:15px !important;
        background:linear-gradient(145deg,rgba(18,29,46,.93),rgba(13,22,36,.94)) !important;
        box-shadow:0 12px 34px rgba(0,0,0,.12);
    }
    [data-testid="stVerticalBlockBorderWrapper"] > div { border:0 !important; }
    .panel-heading { color:#e9edf2; font:700 13px 'Manrope',sans-serif; margin-bottom:3px; }
    .panel-caption { color:#8592a4; font-size:10px; line-height:1.5; margin-bottom:10px; }
    .status-banner { display:flex; align-items:center; gap:14px; padding:15px 18px; border-radius:13px; margin:14px 0 19px; border:1px solid; }
    .status-banner .status-icon { width:34px; height:34px; flex:0 0 34px; display:flex; align-items:center; justify-content:center; border-radius:10px; font-size:17px; }
    .status-banner .status-title { font:700 12px 'Manrope',sans-serif; letter-spacing:.07em; text-transform:uppercase; margin-bottom:3px; }
    .status-banner .status-copy { font-size:11px; line-height:1.5; opacity:.86; }
    .status-ok { color:#c3f0df; background:rgba(46,150,116,.10); border-color:rgba(84,198,163,.27); }
    .status-ok .status-icon { background:rgba(84,198,163,.15); color:#69d7b4; }
    .status-warn { color:#f5dfb4; background:rgba(194,143,61,.10); border-color:rgba(231,184,102,.28); }
    .status-warn .status-icon { background:rgba(231,184,102,.15); color:#e7b866; }
    .status-bad { color:#f4c7c7; background:rgba(190,79,79,.10); border-color:rgba(239,126,126,.28); }
    .status-bad .status-icon { background:rgba(239,126,126,.14); color:#ef9292; }
    .factor-card { border:1px solid rgba(153,171,194,.12); border-radius:11px; background:rgba(17,29,45,.72); padding:12px 13px; margin:8px 0; }
    .factor-name { color:#dfe6ed; font-size:12px; font-weight:600; }
    .factor-tag { display:inline-block; font-size:9px; text-transform:uppercase; letter-spacing:.09em; border-radius:20px; padding:4px 7px; margin-right:7px; }
    .tag-up { color:#f2b0b0; background:rgba(239,126,126,.12); border:1px solid rgba(239,126,126,.18); }
    .tag-down { color:#9fe4cb; background:rgba(84,198,163,.11); border:1px solid rgba(84,198,163,.18); }
    .recommendation {
        display:inline-block; border:1px solid rgba(212,173,112,.25); color:#efd5a7;
        border-radius:8px; background:rgba(212,173,112,.09); padding:8px 11px; font-size:11px; font-weight:700;
        letter-spacing:.08em; text-transform:uppercase;
    }
    .empty-state { border:1px dashed rgba(153,171,194,.2); border-radius:15px; padding:26px; text-align:center; background:rgba(15,25,40,.42); }
    .empty-icon { color:#d4ad70; font-size:25px; margin-bottom:9px; }
    .empty-title { color:#e7eaf0; font:700 15px 'Manrope',sans-serif; }
    .empty-copy { color:#8592a4; font-size:11px; line-height:1.6; max-width:460px; margin:7px auto 0; }
    .footer-note { border-top:1px solid rgba(153,171,194,.12); padding-top:13px; margin-top:28px; color:#69788b; font-size:10px; line-height:1.6; }

    /* Tabs */
    [data-testid="stTabs"] [data-baseweb="tab-list"] {
        gap:7px; border-bottom:1px solid rgba(153,171,194,.13); background:transparent;
    }
    [data-testid="stTabs"] button[role="tab"] {
        color:#8391a4; border-radius:9px 9px 0 0; padding:10px 15px;
        font-size:11px; font-weight:700; letter-spacing:.015em;
    }
    [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
        color:#f0d4a0; background:rgba(212,173,112,.08); border-bottom:2px solid #d4ad70;
    }
    [data-testid="stTabs"] [data-baseweb="tab-highlight"] { background-color:#d4ad70; }
    [data-testid="stExpander"] { border:1px solid rgba(153,171,194,.13); border-radius:11px; background:rgba(15,25,40,.45); }
    [data-testid="stJson"] { background:rgba(7,12,20,.7); border:1px solid rgba(153,171,194,.1); border-radius:10px; }
    [data-testid="stAlert"] { border-radius:10px; }
    .stCaption, [data-testid="stCaptionContainer"] { color:#7f8da0; }

    @media (max-width: 900px) {
        .block-container { padding:1.1rem 1rem 2.5rem; }
        .hero { padding:22px; }
        .hero-side { display:none; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def to_number(value: Any) -> float | None:
    """Converte valores numéricos vindos da API sem interromper a renderização."""
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def format_percent(value: Any, *, multiplier: float = 100.0, decimals: int = 1) -> str:
    number = to_number(value)
    return "—" if number is None else f"{number * multiplier:.{decimals}f}%"


def format_rate(value: Any) -> str:
    number = to_number(value)
    return "—" if number is None else f"{number * 100:.2f}% a.a.".replace(".", ",", 1)


def format_money_eur(value: Any) -> str:
    number = to_number(value)
    if number is None:
        return "—"
    return f"€ {number:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def safe_text(value: Any, fallback: str = "—") -> str:
    if value is None or str(value).strip() == "":
        return fallback
    return html.escape(str(value))


def render_metric(label: str, value: str, foot: str, icon: str) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-top">
                <div class="metric-label">{html.escape(label)}</div>
                <div class="metric-icon">{html.escape(icon)}</div>
            </div>
            <div class="metric-value">{html.escape(value)}</div>
            <div class="metric-foot">{html.escape(foot)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_header(kicker: str, title: str, subtitle: str = "") -> None:
    st.markdown(
        f"""
        <div style="margin: 4px 0 16px;">
            <div class="section-kicker">{html.escape(kicker)}</div>
            <div class="section-title">{html.escape(title)}</div>
            <div class="section-subtitle">{html.escape(subtitle)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_content(situation: Any) -> tuple[str, str, str, str]:
    mapping = {
        "acima_do_justo": (
            "status-bad", "!", "Preço acima do referencial justo",
            "A taxa cobrada está acima da estimativa do modelo para o perfil de risco analisado.",
        ),
        "abaixo_do_justo": (
            "status-warn", "!", "Preço abaixo do referencial justo",
            "A taxa cobrada está abaixo da estimativa de custo e risco calculada pelo modelo.",
        ),
        "conforme": (
            "status-ok", "✓", "Enquadramento conforme",
            "A taxa aplicada foi classificada como compatível pelos critérios retornados pela API.",
        ),
    }
    return mapping.get(
        situation,
        ("status-warn", "i", "Situação não mapeada", "A API retornou um status que não possui uma classificação visual configurada."),
    )


def make_risk_gauge(pd_value: float) -> dict[str, Any]:
    value = min(100.0, max(0.0, pd_value * 100.0))
    return {
        "animation": True,
        "series": [{
            "type": "gauge",
            "startAngle": 210,
            "endAngle": -30,
            "min": 0,
            "max": 100,
            "radius": "92%",
            "center": ["50%", "58%"],
            "progress": {"show": True, "width": 13, "roundCap": True, "itemStyle": {"color": "#d4ad70"}},
            "axisLine": {"lineStyle": {"width": 13, "color": [[1, "#263346"]]}},
            "pointer": {"show": False},
            "axisTick": {"show": False},
            "splitLine": {"show": False},
            "axisLabel": {"show": False},
            "anchor": {"show": False},
            "title": {"show": True, "offsetCenter": [0, "31%"], "color": "#8997a9", "fontSize": 11},
            "detail": {"valueAnimation": True, "formatter": "{value}%", "offsetCenter": [0, "4%"], "color": "#f2eee6", "fontSize": 27, "fontWeight": 700},
            "data": [{"value": round(value, 1), "name": "Probabilidade estimada"}],
        }],
    }


def make_rate_comparison(charged: float | None, fair: float | None) -> dict[str, Any]:
    labels = ["Juro cobrado", "Juro justo estimado"]
    values = [
        round(charged * 100, 2) if charged is not None else 0,
        round(fair * 100, 2) if fair is not None else 0,
    ]
    return {
        "grid": {"left": 12, "right": 34, "top": 18, "bottom": 14, "containLabel": True},
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "xAxis": {
            "type": "value", "name": "% a.a.", "nameTextStyle": {"color": "#8997a9", "fontSize": 10},
            "axisLabel": {"color": "#8997a9", "fontSize": 10, "formatter": "{value}%"},
            "splitLine": {"lineStyle": {"color": "rgba(148,163,184,.10)", "type": "dashed"}},
            "axisLine": {"show": False}, "axisTick": {"show": False},
        },
        "yAxis": {
            "type": "category", "data": labels, "axisLabel": {"color": "#c5ced9", "fontSize": 11},
            "axisLine": {"show": False}, "axisTick": {"show": False},
        },
        "series": [{
            "type": "bar", "barWidth": 18, "data": [
                {"value": values[0], "itemStyle": {"color": "#d4ad70", "borderRadius": [0, 5, 5, 0]}},
                {"value": values[1], "itemStyle": {"color": "#6d9dba", "borderRadius": [0, 5, 5, 0]}},
            ],
            "label": {"show": True, "position": "right", "color": "#e8edf2", "fontSize": 10, "formatter": "{c}%"},
        }],
    }


# -----------------------------------------------------------------------------
# Estado da sessão — mantém a última auditoria depois de cada rerun.
# -----------------------------------------------------------------------------
if "audit_result" not in st.session_state:
    st.session_state.audit_result = None
if "audit_payload" not in st.session_state:
    st.session_state.audit_payload = None
if "audit_error" not in st.session_state:
    st.session_state.audit_error = None
if "audit_timestamp" not in st.session_state:
    st.session_state.audit_timestamp = None


# -----------------------------------------------------------------------------
# Sidebar: parâmetros de entrada
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        """
        <div class="brand-row" style="margin-bottom:22px;">
            <div class="brand-mark">V</div>
            <div><div class="brand-name">VERITAS</div><div class="brand-sub">Risk & Compliance</div></div>
        </div>
        <div class="section-kicker">Workspace / 01</div>
        <div style="font:700 17px 'Manrope',sans-serif;color:#f0f2f4;margin-bottom:5px;">Parâmetros da operação</div>
        <div style="font-size:11px;color:#8290a2;line-height:1.5;margin-bottom:16px;">Configure os dados do contrato para iniciar uma nova avaliação de preço e risco.</div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("form_contrato", border=False):
        st.markdown("<div class='section-kicker'>01 — Identificação</div>", unsafe_allow_html=True)
        loan_id = st.text_input("ID do contrato", value="BO-483449", placeholder="Ex.: BO-483449")

        st.markdown("<div class='section-kicker' style='margin-top:14px;'>02 — Perfil financeiro</div>", unsafe_allow_html=True)
        amount = st.number_input("Valor solicitado (€)", min_value=100.0, value=5000.0, step=250.0, format="%.2f")
        income_total = st.number_input("Renda mensal declarada (€)", min_value=0.0, value=2500.0, step=100.0, format="%.2f")
        interest_cobrado = st.number_input("Taxa de juro cobrada (% a.a.)", min_value=0.0, value=24.9, step=0.1, format="%.2f")

        st.markdown("<div class='section-kicker' style='margin-top:14px;'>03 — Perfil demográfico</div>", unsafe_allow_html=True)
        age = st.number_input("Idade", min_value=18, max_value=100, value=35, step=1)
        country = st.selectbox("País de origem", options=["EE", "FI", "ES"], index=0, format_func=lambda code: {
            "EE": "Estônia (EE)", "FI": "Finlândia (FI)", "ES": "Espanha (ES)"
        }[code])
        gender = st.selectbox(
            "Gênero (auditoria)",
            options=[0, 1, 2],
            format_func=lambda value: {0: "Masculino", 1: "Feminino", 2: "Não especificado"}[value],
        )

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        btn_submeter = st.form_submit_button("Executar auditoria  →", type="primary", width="stretch")

    st.markdown(
        f"""
        <div style="border:1px solid rgba(153,171,194,.13);border-radius:11px;padding:12px 13px;margin-top:17px;background:rgba(16,26,42,.58);">
            <div style="color:#7f8da0;font-size:9px;letter-spacing:.14em;text-transform:uppercase;margin-bottom:6px;">Conexão da API</div>
            <div style="display:flex;align-items:center;gap:7px;color:#c2ccd8;font-size:10px;">
                <span style="width:6px;height:6px;border-radius:50%;background:#d4ad70;display:inline-block;"></span>
                Endpoint configurado
            </div>
            <div style="color:#78879a;font-size:9px;margin-top:5px;word-break:break-all;">{html.escape(API_ENDPOINT)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------------
# Executa a auditoria somente no submit; mantém o resultado salvo na sessão.
# -----------------------------------------------------------------------------
if btn_submeter:
    if not loan_id.strip():
        st.session_state.audit_error = "Informe um ID de contrato antes de executar a auditoria."
        st.session_state.audit_result = None
        st.session_state.audit_payload = None
    else:
        payload = {
            "loan_id": loan_id.strip(),
            "amount": amount,
            "income_total": income_total,
            # Mantidos conforme o contrato de integração fornecido no código original.
            "employment_status": "Unemployed",
            "verification_type": "Not Verified",
            "gender": gender,
            "age": age,
            "country": country,
            "interest_cobrado": interest_cobrado,
        }
        st.session_state.audit_payload = payload
        st.session_state.audit_error = None

        try:
            with st.spinner("Analisando o contrato e consultando o motor de risco…"):
                response = requests.post(API_ENDPOINT, json=payload, timeout=REQUEST_TIMEOUT)

            if response.status_code == 200:
                try:
                    result = response.json()
                except ValueError as exc:
                    raise ValueError("A API respondeu com sucesso, mas não retornou um JSON válido.") from exc

                if not isinstance(result, dict):
                    raise ValueError("Formato de resposta inesperado: era esperado um objeto JSON.")

                st.session_state.audit_result = result
                st.session_state.audit_timestamp = datetime.now().astimezone().strftime("%d/%m/%Y às %H:%M:%S")
                st.session_state.audit_error = None
            else:
                detail = response.text.strip()
                detail = detail[:600] if detail else "A API não enviou detalhes adicionais."
                st.session_state.audit_error = f"A API retornou HTTP {response.status_code}. {detail}"
                st.session_state.audit_result = None

        except requests.exceptions.Timeout:
            st.session_state.audit_error = f"Tempo limite excedido ao consultar a API ({REQUEST_TIMEOUT:g}s). Verifique se o serviço está ativo."
            st.session_state.audit_result = None
        except requests.exceptions.ConnectionError:
            st.session_state.audit_error = f"Não foi possível conectar a {API_BASE_URL}. Confirme se a API FastAPI está em execução."
            st.session_state.audit_result = None
        except requests.exceptions.RequestException as exc:
            st.session_state.audit_error = f"Falha na comunicação com a API: {exc}"
            st.session_state.audit_result = None
        except ValueError as exc:
            st.session_state.audit_error = str(exc)
            st.session_state.audit_result = None


# -----------------------------------------------------------------------------
# Cabeçalho principal
# -----------------------------------------------------------------------------
col_brand, col_meta = st.columns([1.35, 1], vertical_alignment="center")
with col_brand:
    st.markdown(
        """
        <div class="brand-row" style="margin:0;">
            <div class="brand-mark">V</div>
            <div><div class="brand-name">VERITAS</div><div class="brand-sub">Credit intelligence platform</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col_meta:
    run_label = "AUDITORIA REALIZADA" if st.session_state.audit_result else "AMBIENTE DE ANÁLISE"
    st.markdown(
        f"""
        <div class="top-meta">
            <span class="top-pill"><span class="live-dot" style="background:#d4ad70;box-shadow:0 0 10px rgba(212,173,112,.5);"></span> API configurada</span>
            <span class="top-pill">{run_label}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown(
    """
    <div class="hero">
        <div style="position:relative;z-index:1;">
            <div class="eyebrow">Governança financeira · Análise explicável</div>
            <h1>Auditoria de <span>Preço Justo</span></h1>
            <p class="hero-copy">Uma visão integrada de risco de crédito, adequação de taxa e suporte à decisão de compliance. Transforme dados operacionais em evidências claras e acionáveis.</p>
        </div>
        <div class="hero-side">
            <div class="hero-side-label">Módulo operacional</div>
            <div class="hero-side-value">Risk & Pricing</div>
            <div class="hero-side-note">Avaliação quantitativa<br/>e parecer técnico assistido</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if st.session_state.audit_error:
    st.error(st.session_state.audit_error, icon="🚨")

# -----------------------------------------------------------------------------
# Conteúdo — abas persistentes
# -----------------------------------------------------------------------------
tab_analise, tab_parecer, tab_detalhes = st.tabs(
    ["◈  Visão executiva", "▤  Parecer técnico", "⌘  Trilha de auditoria"]
)

dados = st.session_state.audit_result

with tab_analise:
    if not dados:
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-icon">◈</div>
                <div class="empty-title">Workspace pronto para análise</div>
                <div class="empty-copy">Preencha os parâmetros da operação no painel lateral e execute a auditoria. Os indicadores de risco, o comparativo de preço e a decomposição explicável serão exibidos aqui após o retorno da API.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        for col, icon, title, desc in [
            (c1, "◉", "Risco de crédito", "Probabilidade estimada e classificação operacional."),
            (c2, "◇", "Justiça tarifária", "Comparação entre a taxa aplicada e o preço justo calculado."),
            (c3, "⌁", "Explicabilidade", "Fatores de risco e mitigação retornados pelo modelo."),
        ]:
            with col:
                st.markdown(
                    f"<div class='panel'><div style='color:#d4ad70;font-size:20px;margin-bottom:10px'>{icon}</div><div class='panel-heading'>{title}</div><div class='panel-caption' style='margin-top:7px'>{desc}</div></div>",
                    unsafe_allow_html=True,
                )
    else:
        render_section_header(
            "01 / Executive overview",
            "Resumo da avaliação financeira",
            f"Contrato {dados.get('loan_id') or (st.session_state.audit_payload or {}).get('loan_id') or '—'} · Última execução: {st.session_state.audit_timestamp or '—'}",
        )

        pd_value = to_number(dados.get("pd"))
        faixa = dados.get("faixa", "—")
        juro_cobrado = to_number(dados.get("juro_cobrado"))
        juro_justo = to_number(dados.get("juro_justo"))

        metric_cols = st.columns(4, gap="medium")
        with metric_cols[0]:
            render_metric("Probabilidade de inadimplência", format_percent(pd_value), "PD · saída do modelo", "◉")
        with metric_cols[1]:
            render_metric("Faixa de risco operacional", f"Classe {faixa}", "Classificação retornada pela API", "▦")
        with metric_cols[2]:
            render_metric("Juro efetivo cobrado", format_rate(juro_cobrado), "Taxa contratual · anual", "↗")
        with metric_cols[3]:
            render_metric("Juro justo estimado", format_rate(juro_justo), "Referencial calculado · anual", "◇")

        status_class, status_icon, status_title, status_copy = status_content(dados.get("situacao_preco"))
        st.markdown(
            f"""
            <div class="status-banner {status_class}">
                <div class="status-icon">{status_icon}</div>
                <div><div class="status-title">{status_title}</div><div class="status-copy">{status_copy}</div></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        left_chart, right_chart = st.columns([0.85, 1.35], gap="medium")
        with left_chart:
            with st.container(border=True):
                st.markdown(
                    "<div class='panel-heading'>Probabilidade de inadimplência</div><div class='panel-caption'>Indicador de PD retornado pelo motor de risco</div>",
                    unsafe_allow_html=True,
                )
                if pd_value is not None:
                    st.echarts_chart(
                        make_risk_gauge(pd_value),
                        height=245,
                        theme=None,
                        key="risk_gauge",
                        alt="Medidor da probabilidade estimada de inadimplência",
                    )
                else:
                    st.caption("A API não retornou um valor numérico para PD.")

        with right_chart:
            with st.container(border=True):
                st.markdown(
                    "<div class='panel-heading'>Comparativo de precificação</div><div class='panel-caption'>Taxa cobrada versus taxa justa estimada pelo modelo · % ao ano</div>",
                    unsafe_allow_html=True,
                )
                if juro_cobrado is not None or juro_justo is not None:
                    st.echarts_chart(
                        make_rate_comparison(juro_cobrado, juro_justo),
                        height=245,
                        theme=None,
                        key="rate_comparison",
                        alt="Comparação entre a taxa de juro cobrada e a taxa justa estimada",
                    )
                else:
                    st.caption("A API não retornou taxas numéricas para comparação.")

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        render_section_header(
            "02 / Explainable risk",
            "Decomposição do risco",
            "Fatores de agravação e mitigação identificados na resposta do modelo.",
        )
        motivos = dados.get("motivos") or []
        aggravating = [item for item in motivos if isinstance(item, dict) and item.get("efeito") == "aumenta_risco"]
        mitigating = [item for item in motivos if isinstance(item, dict) and item.get("efeito") == "reduz_risco"]
        factor_col1, factor_col2 = st.columns(2, gap="medium")

        with factor_col1:
            with st.container(border=True):
                st.markdown(
                    f"<div class='panel-heading'>↑ Fatores de agravação</div><div class='panel-caption'>{len(aggravating)} variável(is) retornada(s) com efeito de aumento de risco</div>",
                    unsafe_allow_html=True,
                )
                if aggravating:
                    for item in aggravating:
                        variable = str(item.get("variavel", "Variável não identificada")).replace("_", " ").title()
                        st.markdown(
                            f"<div class='factor-card'><span class='factor-tag tag-up'>Aumenta risco</span><span class='factor-name'>{html.escape(variable)}</span></div>",
                            unsafe_allow_html=True,
                        )
                else:
                    st.caption("Nenhum fator de agravação foi retornado pela API.")

        with factor_col2:
            with st.container(border=True):
                st.markdown(
                    f"<div class='panel-heading'>↓ Fatores de mitigação</div><div class='panel-caption'>{len(mitigating)} variável(is) retornada(s) com efeito de redução de risco</div>",
                    unsafe_allow_html=True,
                )
                if mitigating:
                    for item in mitigating:
                        variable = str(item.get("variavel", "Variável não identificada")).replace("_", " ").title()
                        st.markdown(
                            f"<div class='factor-card'><span class='factor-tag tag-down'>Reduz risco</span><span class='factor-name'>{html.escape(variable)}</span></div>",
                            unsafe_allow_html=True,
                        )
                else:
                    st.caption("Nenhum fator de mitigação foi retornado pela API.")

with tab_parecer:
    if not dados:
        st.markdown(
            "<div class='empty-state'><div class='empty-icon'>▤</div><div class='empty-title'>Parecer ainda não disponível</div><div class='empty-copy'>O parecer técnico será apresentado após a execução de uma auditoria e o retorno da API.</div></div>",
            unsafe_allow_html=True,
        )
    else:
        render_section_header(
            "03 / Intelligence & governance",
            "Parecer técnico assistido por IA",
            "Síntese operacional e pontos de atenção recebidos do módulo GenAI.",
        )
        parecer = dados.get("parecer_ia")
        if isinstance(parecer, dict) and parecer:
            resumo = parecer.get("resumo")
            pontos = parecer.get("pontos_de_atencao") or []
            recomendacao = parecer.get("recomendacao")

            if resumo:
                with st.container(border=True):
                    st.markdown("<div class='section-kicker'>Síntese operacional</div>", unsafe_allow_html=True)
                    st.markdown(
                        f"<div style='color:#e8edf2;font:500 14px/1.8 Manrope,sans-serif;'>{html.escape(str(resumo))}</div>",
                        unsafe_allow_html=True,
                    )

            point_col, rec_col = st.columns([1.5, 1], gap="medium")
            with point_col:
                with st.container(border=True):
                    st.markdown(
                        "<div class='panel-heading'>Pontos de atenção</div><div class='panel-caption'>Itens destacados pelo parecer automatizado</div>",
                        unsafe_allow_html=True,
                    )
                    if pontos:
                        for index, point in enumerate(pontos, start=1):
                            st.markdown(
                                f"<div class='factor-card'><span style='color:#d4ad70;font-size:10px;font-weight:700;margin-right:9px;'>0{index}</span><span class='factor-name'>{html.escape(str(point))}</span></div>",
                                unsafe_allow_html=True,
                            )
                    else:
                        st.caption("Nenhum ponto de atenção foi informado pela API.")

            with rec_col:
                with st.container(border=True):
                    st.markdown("<div class='panel-heading'>Recomendação de compliance</div><div class='panel-caption'>Encaminhamento informado pelo módulo GenAI</div>", unsafe_allow_html=True)
                    if recomendacao:
                        st.markdown(f"<div class='recommendation'>{html.escape(str(recomendacao))}</div>", unsafe_allow_html=True)
                    else:
                        st.caption("A API não retornou uma recomendação.")
                    st.markdown("<div style='height:16px'></div><div style='font-size:10px;color:#7f8da0;line-height:1.6;'>A recomendação automatizada deve ser interpretada como suporte à análise, não como decisão jurídica ou aprovação de crédito.</div>", unsafe_allow_html=True)

        else:
            st.markdown(
                "<div class='empty-state'><div class='empty-icon'>⌁</div><div class='empty-title'>Módulo GenAI não retornou parecer</div><div class='empty-copy'>Os dados quantitativos foram recebidos, mas o campo parecer_ia está ausente ou vazio nesta resposta. O espaço será preenchido automaticamente quando o módulo estiver integrado.</div></div>",
                unsafe_allow_html=True,
            )

with tab_detalhes:
    if not dados:
        st.markdown(
            "<div class='empty-state'><div class='empty-icon'>⌘</div><div class='empty-title'>Trilha de auditoria vazia</div><div class='empty-copy'>O payload enviado e a resposta integral da API serão registrados nesta seção após a primeira execução.</div></div>",
            unsafe_allow_html=True,
        )
    else:
        render_section_header(
            "04 / Traceability",
            "Trilha de auditoria",
            "Registro técnico da operação para conferência, depuração e rastreabilidade.",
        )
        if st.session_state.audit_payload:
            with st.expander("Payload enviado à API", expanded=False):
                st.json(st.session_state.audit_payload, expanded=True)
        st.markdown("<div class='panel-heading' style='margin:8px 0 9px;'>Resposta integral · POST /prever</div>", unsafe_allow_html=True)
        st.json(dados, expanded=True)
        st.download_button(
            "Exportar resposta JSON",
            data=json.dumps(dados, ensure_ascii=False, indent=2),
            file_name=f"auditoria_{(st.session_state.audit_payload or {}).get('loan_id', 'contrato')}.json",
            mime="application/json",
            width="content",
        )


# -----------------------------------------------------------------------------
# Rodapé de governança
# -----------------------------------------------------------------------------
st.markdown(
    """
    <div class="footer-note">
        <strong style="color:#aab5c3;letter-spacing:.08em;">VERITAS · RISK & COMPLIANCE</strong><br/>
        Ferramenta de apoio à auditoria de preço e risco de crédito. Os indicadores e pareceres dependem dos dados e modelos fornecidos pela API; a validação final deve permanecer sob responsabilidade da equipe competente.
    </div>
    """,
    unsafe_allow_html=True,
)
