"""Painel do analista — Auditor de Preço Justo (Streamlit).

Telas: Revisão de contrato · Auditoria da carteira · Registro de decisões.
O painel só EXIBE: todos os números vêm da API (prever() do Samuel) ou dos arquivos
do lote da carteira; o parecer vem da GenAI (ou do template de reserva).
"""
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas
import requests
import streamlit as st

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:  # "streamlit run src/app/main.py" não põe a raiz no path
    sys.path.insert(0, str(RAIZ))

from src.app import carteira as cart  # noqa: E402
from src.app.componentes import (PAISES, RECOMENDACOES, SITUACOES, badge, badge_situacao,  # noqa: E402
                                 compactar, data_br, esc, eur, html_barra_juros,
                                 html_barras_faixa, html_motivos, html_parecer,
                                 html_tabela_equidade, kpis_revisao, pct)

FUSO = timezone(timedelta(hours=-3))
CASOS_REAIS = RAIZ / "docs" / "casos_de_teste.json"          # saídas reais do prever() (Samuel)
EXEMPLOS_PREVER = RAIZ / "docs" / "exemplos_prever.json"     # reserva: exemplos ilustrativos

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA E API
# ==========================================
st.set_page_config(
    page_title="Auditor de Preço Justo | Auditoria de Crédito",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

API_BASE = os.getenv("API_URL", "http://localhost:8000")
TIMEOUT_S = 30  # cobre a busca nas normas + LLM (20 s) + queda para o template

# ==========================================
# 2. ESTILIZAÇÃO CSS CUSTOMIZADA (FINTECH / LEGAL-TECH)
# ==========================================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;0,700;1,400&family=DM+Sans:wght@300;400;500;600&display=swap');

    :root {
        --gold: #c89a58;
        --gold-light: #e4bd7d;
        --dark-bg: #121315;
        --card-bg: #1c1d21;
        --card-border: rgba(200, 154, 88, 0.2);
        --text-light: #f0f2f4;
        --text-muted: #9aa5b5;
    }
    html { scroll-behavior: smooth; }
    #MainMenu, header, footer, [data-testid="stSidebar"] { display: none !important; }
    .block-container { padding: 0 !important; max-width: 100% !important; }
    body { background-color: var(--dark-bg); color: var(--text-light); font-family: 'DM Sans', sans-serif; }

    /* --- NAVBAR SUPERIOR FIXA --- */
    .top-navbar {
        position: fixed; top: 0; left: 0; width: 100%; height: 70px;
        background-color: rgba(18, 19, 21, 0.95); backdrop-filter: blur(10px);
        border-bottom: 1px solid var(--card-border);
        display: flex; align-items: center; justify-content: space-between;
        padding: 0 4rem; z-index: 9999;
    }
    .nav-brand {
        font-family: 'Playfair Display', serif; font-size: 1.4rem; font-weight: 700;
        color: #ffffff !important; letter-spacing: 1px; text-decoration: none;
        display: flex; align-items: center; gap: 10px;
    }
    .nav-links { display: flex; gap: 2.5rem; align-items: center; }
    .nav-link { color: #ffffff !important; text-decoration: none; font-weight: 500; font-size: 0.95rem; transition: color 0.3s ease; }
    .nav-link:hover { color: var(--gold); }
    .nav-analyst { color: var(--text-muted); font-size: .82rem; }
    .nav-analyst b { color: var(--gold-light); font-weight: 600; }

    /* --- HERO SECTION --- */
    .hero-container {
        margin-top: 0px;
        background-image: linear-gradient(to right, rgba(18, 19, 21, 0.95) 25%, rgba(18, 19, 21, 0.7) 100%),
                          url('https://images.unsplash.com/photo-1589829085413-56de8ae18c73?q=80&w=2000&auto=format&fit=crop');
        background-color: #16171a;
        background-size: cover; background-position: center;
        padding: 25rem 4rem 4rem 4rem;
        border-bottom: 5px solid var(--card-border);
    }
    .hero-title { font-family: 'Playfair Display', serif; font-size: 3.8rem; font-weight: 700; color: var(--text-light); line-height: 1.15; margin-bottom: 1rem; }
    .hero-title span { color: var(--gold); font-style: italic; }
    .hero-subtitle { font-size: 1.15rem; color: var(--text-muted); max-width: 680px; margin-bottom: 2rem; line-height: 1.6; }

    /* --- FAIXA ESCURA COM 3 BLOCOS EXPLICATIVOS --- */
    .features-strip { background-color: #0b0c0e; border-bottom: 1px solid var(--card-border); padding: 2.5rem 4rem; }
    .features-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 2rem; max-width: 1300px; margin: 0 auto; }
    .feature-item { display: flex; align-items: flex-start; gap: 1.2rem; background: rgba(28, 29, 33, 0.15); padding: 1.5rem; border-radius: 12px; }
    .feature-icon { font-size: 1.8rem; color: var(--gold); }
    .feature-title { font-family: 'Playfair Display', serif; font-size: 1.15rem; color: var(--text-light); margin-bottom: 0.4rem; }
    .feature-desc { font-size: 0.88rem; color: var(--text-muted); line-height: 1.5; }

    /* --- SEÇÕES --- */
    .section-wrapper { padding: 4rem 4rem; max-width: 1400px; margin: 0 auto; }
    .section-header { text-align: center; margin-bottom: 2rem; }
    .section-header h2 { font-family: 'Playfair Display', serif; font-size: 2.6rem; color: var(--text-light); }
    .section-header p { color: var(--text-muted); font-size: 1.05rem; }
    .gold-divider { width: 60px; height: 3px; background-color: var(--gold); margin: 1rem auto; border-radius: 2px; }

    /* --- SOBRE (EQUIPE) --- */
    .team-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.8rem; margin-top: 2.5rem; padding: 0 4rem 4rem 4rem; max-width: 1400px; margin-left: auto; margin-right: auto; }
    .team-card { background-color: var(--card-bg); border: 1px solid var(--card-border); border-radius: 12px; padding: 1.2rem; text-align: left; transition: transform 0.3s ease, border-color 0.3s ease; }
    .team-card:hover { transform: translateY(-5px); border-color: var(--gold); }
    .team-avatar {
        width: 100%; height: 150px; border-radius: 8px; margin-bottom: 1rem;
        display: flex; align-items: center; justify-content: center;
        background: radial-gradient(circle at 30% 20%, rgba(228,189,125,.22), rgba(18,19,21,1) 70%);
        border: 1px solid rgba(255,255,255,0.05);
        font-family: 'Playfair Display', serif; font-size: 3rem; color: var(--gold-light); letter-spacing: 2px;
    }
    .team-name { font-family: 'Playfair Display', serif; font-size: 1.25rem; color: var(--text-light); margin-bottom: 0.2rem; }
    .team-role { font-size: 0.82rem; color: var(--gold); text-transform: uppercase; letter-spacing: 1px; font-weight: 600; margin-bottom: 0.6rem; }
    .team-bio { font-size: 0.85rem; color: var(--text-muted); line-height: 1.4; }

    /* --- COMPONENTES STREAMLIT --- */
    [data-testid="stAppViewContainer"], [data-testid="stMain"] { background: var(--dark-bg); color: var(--text-light); }
    [data-testid="stMain"] .block-container { padding-top: 1.5rem !important; padding-bottom: 4rem !important; }

    [data-testid="stButton"] button, [data-testid="stDownloadButton"] button {
        min-height: 52px; width: 100%; white-space: pre-wrap !important; text-align: center !important;
        line-height: 1.55 !important; padding: 1.1rem 1rem !important; border-radius: 14px !important;
        border: 1px solid rgba(200, 154, 88, 0.34) !important;
        background: linear-gradient(145deg, #202126 0%, #17181c 100%) !important;
        color: var(--text-light) !important; box-shadow: 0 8px 24px rgba(0, 0, 0, 0.16);
        transition: transform .2s ease, border-color .2s ease, box-shadow .2s ease;
    }
    [data-testid="stButton"] button:hover, [data-testid="stDownloadButton"] button:hover {
        transform: translateY(-3px); border-color: var(--gold-light) !important; box-shadow: 0 12px 28px rgba(200, 154, 88, 0.12);
    }
    [data-testid="stButton"] button[data-testid="stBaseButton-primary"],
    [data-testid="stButton"] button[kind="primary"] {
        background: linear-gradient(135deg, #d7b9b8 0%, #c8a2a0 100%) !important;
        color: #171315 !important; border: 1px solid #e5c5c3 !important; font-weight: 700 !important;
    }

    .audit-workspace-label { color: var(--gold-light); font-size: .68rem; font-weight: 700; letter-spacing: .16em; text-transform: uppercase; margin: .15rem 0 .4rem 0; }
    .st-key-audit_select_personal button, .st-key-audit_select_loan button, .st-key-audit_select_history button {
        min-height: 104px !important; height: 104px !important; padding: .55rem .35rem !important;
        border-radius: 10px !important; font-size: .74rem !important; line-height: 1.35 !important; box-shadow: none !important;
    }
    .st-key-audit_select_personal button[kind="primary"], .st-key-audit_select_loan button[kind="primary"], .st-key-audit_select_history button[kind="primary"] {
        background: linear-gradient(135deg, #c89a58 0%, #e4bd7d 100%) !important; color: #171315 !important; border: 1px solid #e4bd7d !important;
    }
    .audit-review-progress { height: 7px; width: 100%; background: rgba(238, 233, 229, .12); border-radius: 10px; overflow: hidden; margin: .75rem 0 1.35rem 0; }
    .audit-review-progress-fill { height: 100%; background: linear-gradient(90deg, #c89a58, #e4bd7d); border-radius: 10px; transition: width .25s ease; }
    .audit-review-status { display: flex; align-items: center; justify-content: space-between; gap: .5rem; margin: .95rem 0 .45rem 0; color: #e8e5df; font-size: .76rem; font-weight: 600; }
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: linear-gradient(145deg, rgba(31, 32, 37, .96), rgba(23, 24, 28, .96));
        border: 1px solid rgba(200, 154, 88, .24) !important; border-radius: 16px !important; padding: 1.1rem 1.2rem !important;
    }
    [data-testid="stTextInput"] input, [data-testid="stNumberInput"] input, [data-testid="stDateInput"] input,
    [data-testid="stTextArea"] textarea, [data-testid="stSelectbox"] [data-baseweb="select"] > div {
        background: #141519 !important; color: var(--text-light) !important;
        border-color: rgba(200, 154, 88, .28) !important; border-radius: 8px !important;
    }
    .audit-eyebrow { color: var(--gold-light); font-size: .72rem; font-weight: 700; letter-spacing: .16em; text-transform: uppercase; margin-bottom: .45rem; }
    .audit-panel-title { color: var(--text-light); font-family: 'Playfair Display', serif; font-size: 1.65rem; margin: 0 0 .35rem 0; }
    .audit-progress-title { color: var(--text-light); font-family: 'Playfair Display', serif; font-size: 1.25rem; margin: 0 0 .3rem 0; }
    .skill-track { width: 100%; height: 7px; background: #eee9e5; border-radius: 1px; overflow: hidden; }
    .skill-fill { height: 100%; background: #171719; border-radius: 1px; transition: width .25s ease; }
    .audit-note {
        background: rgba(200, 154, 88, .08); border-left: 3px solid var(--gold); border-radius: 0 8px 8px 0;
        padding: .8rem .95rem; color: #c6c2bb; font-size: .8rem; line-height: 1.5; margin-top: .8rem;
    }

    /* --- ABAS --- */
    [data-testid="stTabs"] [data-baseweb="tab-list"] { gap: .4rem; border-bottom: 1px solid var(--card-border); }
    [data-testid="stTabs"] [data-baseweb="tab"] {
        background: transparent; color: var(--text-muted); font-weight: 600; letter-spacing: .04em;
        padding: .7rem 1.2rem; border-radius: 10px 10px 0 0;
    }
    [data-testid="stTabs"] [aria-selected="true"] { color: var(--gold-light) !important; background: rgba(200,154,88,.08); }
    [data-testid="stTabs"] [data-baseweb="tab-highlight"] { background-color: var(--gold) !important; }

    /* --- BLOCOS DO RESULTADO (ap-*) --- */
    .ap-head { display: flex; justify-content: space-between; align-items: flex-end; gap: 1rem; margin: 1.6rem 0 .6rem 0; }
    .ap-title { font-family: 'Playfair Display', serif; font-size: 2.1rem; color: var(--text-light); line-height: 1.1; }
    .ap-meta { color: var(--text-muted); font-size: .9rem; margin-top: .35rem; }
    .ap-chips { display: flex; flex-wrap: wrap; gap: .45rem; margin: .6rem 0 1.1rem 0; }
    .ap-chip { font-size: .74rem; color: #d9d4cb; background: rgba(255,255,255,.04); border: 1px solid rgba(200,154,88,.22); border-radius: 999px; padding: .28rem .7rem; }
    .ap-chip-gold { color: #171315; background: var(--gold-light); border-color: var(--gold-light); font-weight: 700; }
    .ap-badge { display: inline-block; font-size: .72rem; font-weight: 700; border: 1px solid; border-radius: 999px; padding: .2rem .65rem; white-space: nowrap; }

    .ap-kpi { background: linear-gradient(145deg, rgba(31,32,37,.96), rgba(23,24,28,.96)); border: 1px solid rgba(200,154,88,.24); border-radius: 16px; padding: 1.1rem 1.2rem; min-height: 152px; }
    .ap-kpi-label { color: var(--text-muted); font-size: .78rem; font-weight: 600; letter-spacing: .04em; }
    .ap-kpi-value { font-family: 'Playfair Display', serif; font-size: 2.25rem; color: var(--gold-light); margin: .35rem 0 .2rem 0; line-height: 1.1; }
    .ap-kpi-unit { font-family: 'DM Sans', sans-serif; font-size: .85rem; color: var(--text-muted); margin-left: .3rem; }
    .ap-kpi-sub { color: #b9b4ab; font-size: .78rem; line-height: 1.4; }
    .ap-kpi-foot { margin-top: .55rem; }
    .ap-faixa { display: inline-block; background: #0b0c0e; color: var(--gold-light); border: 1px solid var(--gold); border-radius: 6px; padding: .15rem .55rem; font-size: .75rem; font-weight: 700; }
    .ap-faixa-off { color: var(--text-muted); border-color: rgba(154,165,181,.4); }

    .ap-card { background: linear-gradient(145deg, rgba(31,32,37,.96), rgba(23,24,28,.96)); border: 1px solid rgba(200,154,88,.24); border-radius: 16px; padding: 1.25rem 1.35rem; margin-top: 1rem; }
    .ap-card-title { font-family: 'Playfair Display', serif; font-size: 1.3rem; color: var(--text-light); margin-bottom: .2rem; }
    .ap-card-sub { color: var(--text-muted); font-size: .8rem; margin-bottom: 1rem; }
    .ap-alert { border-left: 3px solid #9aa5b5; background: rgba(154,165,181,.08); border-radius: 0 10px 10px 0; padding: .9rem 1rem; color: #d7dbe2; font-size: .86rem; line-height: 1.5; margin-top: 1rem; }

    .ap-ruler { padding: 2.1rem .4rem .2rem .4rem; }
    .ap-ruler-track { position: relative; height: 14px; background: #0f1013; border-radius: 8px; border: 1px solid rgba(255,255,255,.04); }
    .ap-ruler-band { position: absolute; top: 0; bottom: 0; background: rgba(228,189,125,.28); border-radius: 8px; }
    .ap-ruler-mark { position: absolute; top: -9px; width: 3px; height: 32px; border-radius: 2px; transform: translateX(-50%); }
    .ap-ruler-label { position: absolute; transform: translateX(-50%); font-size: .76rem; font-weight: 700; white-space: nowrap; }
    .ap-up { top: -32px; }
    .ap-down { top: 28px; }
    .ap-ruler-ticks { position: relative; height: 22px; margin-top: 2.2rem; }
    .ap-tick { position: absolute; transform: translateX(-50%); font-size: .7rem; color: var(--text-muted); }

    .ap-legend { display: flex; flex-wrap: wrap; gap: 1.1rem; color: var(--text-muted); font-size: .74rem; margin-top: .9rem; align-items: center; }
    .ap-legend i { display: inline-block; width: 11px; height: 11px; border-radius: 3px; margin-right: .4rem; vertical-align: -1px; }

    .ap-factor { display: grid; grid-template-columns: 1.25fr 1fr 2.6rem; gap: .8rem; align-items: center; margin: .55rem 0; }
    .ap-factor-name { font-size: .85rem; color: #e8e5df; line-height: 1.3; }
    .ap-factor-bar { height: 9px; background: #0f1013; border-radius: 6px; overflow: hidden; }
    .ap-factor-bar div { height: 100%; border-radius: 6px; }
    .ap-factor-w { font-size: .72rem; color: var(--text-muted); text-align: right; }

    .ap-parecer-head { display: flex; justify-content: space-between; align-items: center; gap: .8rem; margin-bottom: .6rem; }
    .ap-sec { color: var(--gold-light); font-size: .68rem; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; margin: 1rem 0 .35rem 0; }
    .ap-text { color: #e8e5df; font-size: .9rem; line-height: 1.6; margin: 0; }
    .ap-list { margin: 0; padding-left: 1.1rem; color: #e8e5df; font-size: .88rem; line-height: 1.6; }
    .ap-foot { color: var(--text-muted); font-size: .7rem; margin-top: .9rem; }
    .ap-muted { color: var(--text-muted); }
    .ap-small { font-size: .72rem; }
    .ap-empty { color: var(--text-muted); font-size: .85rem; padding: .6rem 0; }

    .ap-stack-row { display: grid; grid-template-columns: 4.2rem 1fr 3.2rem; gap: .8rem; align-items: center; margin: .5rem 0; }
    .ap-stack-label { font-size: .84rem; font-weight: 700; color: #e8e5df; }
    .ap-stack { display: flex; height: 16px; border-radius: 6px; overflow: hidden; background: #0f1013; }
    .ap-stack div { height: 100%; }
    .ap-stack-n { font-size: .72rem; color: var(--text-muted); text-align: right; }

    .ap-table { width: 100%; border-collapse: collapse; font-size: .84rem; color: #e8e5df; }
    .ap-table th { text-align: left; color: var(--text-muted); font-size: .68rem; letter-spacing: .12em; text-transform: uppercase; font-weight: 700; padding: .55rem .5rem; border-bottom: 1px solid rgba(200,154,88,.3); }
    .ap-table td { padding: .65rem .5rem; border-bottom: 1px solid rgba(255,255,255,.06); vertical-align: middle; }
    .ap-table tr:hover td { background: rgba(200,154,88,.04); }

    .ap-status { display: inline-flex; align-items: center; gap: .45rem; font-size: .76rem; color: var(--text-muted); }
    .ap-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
    </style>
""", unsafe_allow_html=True)


def md(bloco: str) -> None:
    st.markdown(compactar(bloco), unsafe_allow_html=True)


# ==========================================
# 3. ESTADO DA SESSÃO
# ==========================================
DEFAULT_INPUTS = {
    "loan_id": "EMP-2026-001",
    "age": 35,
    "gender": 0,
    "country": "EE",
    "income_total": 2500.0,
    "amount": 5000.0,
    "interest": 24.5,
    "loan_duration": 36,
    "data_emprestimo": date.today(),
    "liabilities_total": 450.0,
}
for field_name, default_value in DEFAULT_INPUTS.items():
    st.session_state.setdefault(f"audit_{field_name}", default_value)
if st.session_state.get("audit_country") not in PAISES:  # sessão antiga com "EE(Estônia)"
    st.session_state["audit_country"] = "EE"
for step_name in ("personal", "loan", "history"):
    st.session_state.setdefault(f"audit_reviewed_{step_name}", False)

st.session_state.setdefault("audit_active_step", "personal")
st.session_state.setdefault("audit_last_result", None)
st.session_state.setdefault("audit_last_contexto", {})
st.session_state.setdefault("audit_last_payload", None)
st.session_state.setdefault("audit_last_error", None)
st.session_state.setdefault("historico", [])   # contratos auditados nesta sessão
st.session_state.setdefault("decisoes", [])    # decisões registradas pelo analista
st.session_state.setdefault("analista", "")


# ==========================================
# 4. COMUNICAÇÃO COM A API
# ==========================================
@st.cache_data(ttl=20, show_spinner=False)
def status_api() -> dict | None:
    try:
        r = requests.get(f"{API_BASE}/", timeout=3)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException:
        return None


def chamar_api(rota: str, payload: dict) -> tuple[dict | None, str | None]:
    """POST na API. Devolve (resposta, erro) com mensagem amigável para a tela."""
    url = f"{API_BASE}{rota}"
    try:
        r = requests.post(url, json=payload, timeout=TIMEOUT_S)
    except requests.exceptions.Timeout:
        return None, f"A API não respondeu em {TIMEOUT_S} s ({url})."
    except requests.exceptions.ConnectionError:
        return None, f"Não foi possível conectar à API em {API_BASE}. Confira se o serviço 'api' está no ar."
    if r.status_code == 422:
        return None, "A API recusou os dados enviados (formato inválido). Detalhe: " + r.text[:400]
    if r.status_code == 503:
        return None, r.json().get("detail", "Modelo indisponível na API.")
    if not r.ok:
        return None, f"A API respondeu com erro {r.status_code}: {r.text[:300]}"
    try:
        dados = r.json()
    except json.JSONDecodeError:
        return None, "A resposta da API não pôde ser interpretada."
    if not isinstance(dados, dict):
        return None, "A API retornou uma estrutura diferente da esperada."
    return dados, None


def guardar_resultado(resultado: dict, contexto: dict) -> None:
    st.session_state.audit_last_result = resultado
    st.session_state.audit_last_contexto = contexto
    st.session_state.audit_last_error = None
    item = {k: resultado.get(k) for k in ("contrato_id", "pd", "faixa", "juro_cobrado", "juro_justo",
                                         "juro_justo_min", "juro_justo_max", "situacao_preco")}
    historico = [h for h in st.session_state.historico if h["contrato_id"] != item["contrato_id"]]
    st.session_state.historico = [item] + historico


@st.cache_data(show_spinner=False)
def carregar_exemplos() -> tuple[list[dict], bool]:
    """(casos, reais). Usa os casos reais do prever(); se não houver, os ilustrativos."""
    if CASOS_REAIS.exists():
        por_situacao = json.loads(CASOS_REAIS.read_text(encoding="utf-8"))
        return [caso for lista in por_situacao.values() for caso in lista], True
    if EXEMPLOS_PREVER.exists():
        return json.loads(EXEMPLOS_PREVER.read_text(encoding="utf-8")), False
    return [], False


@st.cache_data(ttl=300, show_spinner=False)
def dados_carteira():
    """(carteira, equidade, erro). Lê os arquivos do lote do Samuel, se existirem."""
    try:
        return cart.carregar_carteira(), cart.carregar_equidade(), None
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        return None, None, str(exc)


# ==========================================
# 5. BARRA DE NAVEGAÇÃO, HOME E FAIXA EXPLICATIVA
# ==========================================
analista_nav = esc(st.session_state.analista) or "não identificado"
md(f"""
    <div class="top-navbar">
        <a href="#home" class="nav-brand"><span>⚖️</span> AUDITOR DE PREÇO JUSTO</a>
        <div class="nav-links">
            <a href="#home" class="nav-link">Home</a>
            <a href="#auditor" class="nav-link">Auditoria</a>
            <a href="#sobre" class="nav-link">Sobre o Projeto</a>
            <span class="nav-analyst">Analista: <b>{analista_nav}</b></span>
        </div>
    </div>
""")

st.markdown('<div id="home"></div>', unsafe_allow_html=True)
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

md("""
    <div class="features-strip">
        <div class="features-grid">
            <div class="feature-item">
                <div class="feature-icon">📊</div>
                <div>
                    <div class="feature-title">Juro justo por fluxo de caixa</div>
                    <div class="feature-desc">Custo do dinheiro (Euribor da época), perda esperada ao longo do contrato e custos calibrados na carteira, com margem de incerteza.</div>
                </div>
            </div>
            <div class="feature-item">
                <div class="feature-icon">🤖</div>
                <div>
                    <div class="feature-title">Modelo de risco explicável</div>
                    <div class="feature-desc">XGBoost calibrado estima a probabilidade de default; os principais fatores de cada contrato aparecem com nomes legíveis.</div>
                </div>
            </div>
            <div class="feature-item">
                <div class="feature-icon">📜</div>
                <div>
                    <div class="feature-title">Parecer com normas e checagem</div>
                    <div class="feature-desc">IA generativa com busca em CDC, LGPD e normas do CMN. Os números do texto são conferidos por código; se algo falhar, entra o template.</div>
                </div>
            </div>
        </div>
    </div>
""")


# ==========================================
# 6. SEÇÃO DE AUDITORIA (#AUDITOR)
# ==========================================
st.markdown('<div id="auditor" class="section-wrapper"></div>', unsafe_allow_html=True)
md("""
    <div class="section-header">
        <h2>Auditoria de Preço</h2>
        <div class="gold-divider"></div>
        <p>Revise um contrato, acompanhe a carteira e registre as decisões.</p>
    </div>
""")

_, area, _ = st.columns([0.35, 5, 0.35])
with area:
    col_status, col_analista = st.columns([3, 1.2], gap="medium")
    with col_status:
        status = status_api()
        if status is None:
            md(f'<span class="ap-status"><i class="ap-dot" style="background:#d9825b"></i>'
               f'API fora do ar ({esc(API_BASE)}). Os casos de exemplo continuam disponíveis.</span>')
        elif not status.get("modelo_carregavel", True):
            md('<span class="ap-status"><i class="ap-dot" style="background:#e8a462"></i>'
               'API no ar, mas o arquivo do modelo não está em modelos_salvos/.</span>')
        else:
            md('<span class="ap-status"><i class="ap-dot" style="background:#8cc7a1"></i>'
               'API no ar · modelo carregado</span>')
    with col_analista:
        st.text_input("Analista responsável", key="analista", placeholder="Seu nome")

    aba_revisao, aba_carteira, aba_registro = st.tabs(
        ["REVISÃO DE CONTRATO", "AUDITORIA DA CARTEIRA", "REGISTRO DE DECISÕES"])


# ------------------------------------------
# 6.1 Formulário em etapas
# ------------------------------------------
def _persist_audit_input(field_name: str) -> None:
    st.session_state[f"audit_{field_name}"] = st.session_state[f"_audit_widget_{field_name}"]


def _prepare_audit_widget(field_name: str) -> str:
    widget_key = f"_audit_widget_{field_name}"
    if widget_key not in st.session_state:
        st.session_state[widget_key] = st.session_state[f"audit_{field_name}"]
    return widget_key


def audit_number(label, field_name, **kwargs):
    return st.number_input(label, key=_prepare_audit_widget(field_name),
                           on_change=_persist_audit_input, args=(field_name,), **kwargs)


def audit_select(label, field_name, options, **kwargs):
    return st.selectbox(label, options=options, key=_prepare_audit_widget(field_name),
                        on_change=_persist_audit_input, args=(field_name,), **kwargs)


def audit_slider(label, field_name, **kwargs):
    return st.slider(label, key=_prepare_audit_widget(field_name),
                     on_change=_persist_audit_input, args=(field_name,), **kwargs)


def audit_text(label, field_name, **kwargs):
    return st.text_input(label, key=_prepare_audit_widget(field_name),
                         on_change=_persist_audit_input, args=(field_name,), **kwargs)


def audit_date(label, field_name, **kwargs):
    return st.date_input(label, key=_prepare_audit_widget(field_name),
                         on_change=_persist_audit_input, args=(field_name,), **kwargs)


def _persist_review(step_name: str) -> None:
    st.session_state[f"audit_reviewed_{step_name}"] = st.session_state[f"_audit_review_widget_{step_name}"]


def audit_review_checkbox(step_name: str) -> None:
    widget_key = f"_audit_review_widget_{step_name}"
    if widget_key not in st.session_state:
        st.session_state[widget_key] = st.session_state[f"audit_reviewed_{step_name}"]
    st.checkbox("Confirmo que revisei os dados desta etapa", key=widget_key,
                on_change=_persist_review, args=(step_name,))


STEP_CARDS = [("personal", "\n\nDADOS PESSOAIS\n\n"), ("loan", "\n\nEMPRÉSTIMO\n\n"),
              ("history", "\n\nDÍVIDAS & HISTÓRICO\n\n")]
STEP_DETAILS = {
    "personal": {"number": "01", "title": "Dados pessoais",
                 "copy": "Perfil do tomador no momento do pedido. Gênero e idade ficam registrados só para a auditoria de equidade e nunca entram no modelo."},
    "loan": {"number": "02", "title": "Dados do empréstimo",
             "copy": "Condições do contrato. A data de concessão define a Euribor (custo do dinheiro) usada no juro justo."},
    "history": {"number": "03", "title": "Dívidas & histórico",
                "copy": "Dívidas existentes do tomador. Campos sem informação seguem vazios para o modelo (nunca zero)."},
}


def formulario() -> bool:
    """Desenha o formulário em 3 etapas. Devolve True quando o botão de auditoria é clicado."""
    _, nav_center, _ = st.columns([0.35, 2.3, 0.35], gap="small")
    with nav_center:
        for column, (step_key, step_label) in zip(st.columns(3, gap="small"), STEP_CARDS):
            with column:
                ativo = st.session_state.audit_active_step == step_key
                if st.button(step_label, key=f"audit_select_{step_key}",
                             type="primary" if ativo else "secondary", use_container_width=True):
                    st.session_state.audit_active_step = step_key
                    st.rerun()

    active_step = st.session_state.audit_active_step
    current_step = STEP_DETAILS[active_step]
    input_column, progress_column = st.columns([1.7, 0.95], gap="medium")

    with input_column:
        with st.container(border=True):
            st.markdown('<div class="audit-workspace-label">ÁREA DE CONSULTA · ETAPAS DE PREENCHIMENTO</div>',
                        unsafe_allow_html=True)
            md(f"""
                <div style="margin:1.25rem 0 .8rem 0; padding-bottom:.8rem; border-bottom:1px solid rgba(200,154,88,.18);">
                    <div class="audit-eyebrow">ETAPA {current_step['number']} / 03 · COLETA DE DADOS</div>
                    <div class="audit-panel-title">{current_step['title']}</div>
                    <div class="audit-panel-copy" style="margin:.35rem 0 0 0; color:#9aa5b5; font-size:.88rem;">{current_step['copy']}</div>
                </div>
            """)

            if active_step == "personal":
                audit_number("Idade do cliente", "age", min_value=18, max_value=100, step=1)
                audit_select("Gênero", "gender", options=[0, 1, 2],
                             format_func=lambda v: {0: "Masculino", 1: "Feminino", 2: "Não informado"}[v])
                audit_select("País do contrato", "country", options=list(PAISES),
                             format_func=lambda s: f"{s} · {PAISES[s]}")
                audit_number("Renda total mensal (€)", "income_total", min_value=0.0, step=100.0, format="%.2f")
                st.markdown('<div class="audit-note">Valores em euro (€). Renda e passivos da Estônia até 2010 '
                            'foram convertidos de coroas estonianas na carga.</div>', unsafe_allow_html=True)
                audit_review_checkbox("personal")

            elif active_step == "loan":
                audit_text("ID do contrato", "loan_id", max_chars=40)
                audit_number("Valor concedido (€)", "amount", min_value=100.0, step=250.0, format="%.2f")
                audit_number("Juro cobrado (% a.a.)", "interest", min_value=0.0, max_value=500.0, step=0.5, format="%.2f")
                audit_slider("Prazo do contrato (meses)", "loan_duration", min_value=3, max_value=60, step=1)
                audit_date("Data de concessão", "data_emprestimo", min_value=date(2009, 1, 1),
                           max_value=date.today(), format="DD/MM/YYYY")
                st.markdown('<div class="audit-note">O custo do dinheiro é a Euribor 12 meses do mês da concessão. '
                            'Para meses após o fim da série, o modelo usa o último valor disponível. '
                            'Juros acima de 100% a.a. existem na base e são legítimos.</div>', unsafe_allow_html=True)
                audit_review_checkbox("loan")

            else:
                audit_number("Total de dívidas em outras instituições (€)", "liabilities_total",
                             min_value=0.0, step=50.0, format="%.2f")
                st.markdown('<div class="audit-note">Histórico na plataforma, escolaridade, moradia e verificação '
                            'de renda seguem como “sem informação” nesta versão do formulário. O rating e a PD do '
                            'Bondora não são usados: entregariam o preço ao modelo.</div>', unsafe_allow_html=True)
                audit_review_checkbox("history")

            st.markdown("<div style='height:.35rem'></div>", unsafe_allow_html=True)
            clicou = st.button("⚖️ EXECUTAR AUDITORIA DE PREÇO", key="audit_execute",
                               type="primary", use_container_width=True)

    with progress_column:
        with st.container(border=True):
            revisadas = {k: st.session_state[f"audit_reviewed_{k}"] for k in ("personal", "loan", "history")}
            feitas = sum(revisadas.values())
            progresso = round(feitas / 3 * 100)
            md(f"""
                <div class="audit-eyebrow">ACOMPANHAMENTO</div>
                <div class="audit-progress-title">Revisão dos dados</div>
                <div style="margin-bottom:.5rem; color:#9aa5b5; font-size:.85rem;">{feitas} de 3 etapas revisadas</div>
                <div style="display:flex; align-items:baseline; gap:.3rem;">
                    <span style="font-family:'Playfair Display',serif; font-size:2rem; color:#e4bd7d;">{progresso}%</span>
                    <span style="font-size:.72rem; color:#9aa5b5;">concluído</span>
                </div>
                <div class="audit-review-progress"><div class="audit-review-progress-fill" style="width:{progresso}%"></div></div>
            """)
            for numero, rotulo, chave in [("01", "Dados pessoais", "personal"), ("02", "Dados do empréstimo", "loan"),
                                          ("03", "Dívidas & histórico", "history")]:
                ok = revisadas[chave]
                md(f"""
                    <div class="audit-review-status"><span>{numero} · {rotulo}</span><span>{"REVISADO" if ok else "PENDENTE"}</span></div>
                    <div class="skill-track"><div class="skill-fill" style="width:{100 if ok else 0}%; background:linear-gradient(90deg,#c89a58,#e4bd7d);"></div></div>
                """)
            ss = st.session_state
            md(f"""
                <div class="audit-note" style="margin-top:1.2rem;">
                    <b>Resumo do pedido</b><br>
                    {esc(ss.audit_loan_id)} · {PAISES.get(ss.audit_country, ss.audit_country)}<br>
                    {eur(ss.audit_amount)} · {ss.audit_loan_duration} meses · {pct(ss.audit_interest / 100)} a.a.<br>
                    Concessão em {ss.audit_data_emprestimo.strftime("%d/%m/%Y")}
                </div>
            """)
    return clicou


def montar_payload() -> dict:
    """Mesmo formato do SolicitacaoEmprestimo (src/api/schemas.py)."""
    ss = st.session_state
    return {
        "loan_id": (ss.audit_loan_id or "EMP-SEM-ID").strip(),
        "amount": float(ss.audit_amount),
        "income_total": float(ss.audit_income_total),
        "loan_duration": int(ss.audit_loan_duration),
        "country": ss.audit_country,
        "interest_cobrado": float(ss.audit_interest),
        "liabilities_total": float(ss.audit_liabilities_total),
        "data_emprestimo": ss.audit_data_emprestimo.isoformat(),
        "gender": int(ss.audit_gender),  # só auditoria: a API não repassa ao modelo
        "age": int(ss.audit_age),
    }


# ------------------------------------------
# 6.2 Resultado da revisão
# ------------------------------------------
def registrar_decisao(resultado: dict, decisao: str, justificativa: str, nova_taxa: float | None) -> None:
    parecer = resultado.get("parecer_ia") or {}
    st.session_state.decisoes.insert(0, {
        "registrado_em": datetime.now(FUSO).strftime("%Y-%m-%d %H:%M:%S"),
        "analista": st.session_state.analista.strip(),
        "contrato_id": resultado.get("contrato_id"),
        "situacao_preco": resultado.get("situacao_preco"),
        "pd": resultado.get("pd"),
        "juro_cobrado": resultado.get("juro_cobrado"),
        "juro_justo": resultado.get("juro_justo"),
        "recomendacao_sistema": parecer.get("recomendacao"),
        "decisao": decisao,
        "nova_taxa_proposta": nova_taxa,
        "justificativa": justificativa.strip(),
        "origem_parecer": parecer.get("origem"),
        "versao_modelo": resultado.get("versao_modelo"),
        "versao_prompt": parecer.get("versao_prompt"),
    })


def bloco_decisao(resultado: dict) -> None:
    cid = resultado.get("contrato_id", "?")
    parecer = resultado.get("parecer_ia") or {}
    rec = RECOMENDACOES.get(parecer.get("recomendacao"), "—")
    with st.container(border=True):
        md(f"""
            <div class="ap-card-title">Decisão do analista</div>
            <div class="ap-card-sub">Recomendação do sistema: <b style="color:#e4bd7d">{esc(rec)}</b>.
            O sistema não decide: a decisão final é sempre do analista e fica registrada com o parecer e a justificativa.</div>
        """)
        col_just, col_taxa = st.columns([3, 1], gap="medium")
        with col_just:
            justificativa = st.text_area("Justificativa (obrigatória)", key=f"just_{cid}",
                                         placeholder="Explique sua decisão", height=110)
        with col_taxa:
            nova = st.number_input("Nova taxa proposta (% a.a.)", key=f"nova_{cid}", min_value=0.0,
                                   max_value=500.0, value=None, step=0.5, format="%.2f",
                                   help="Opcional; registrada só quando a decisão for revisar o preço.")
        botoes = st.columns(3, gap="small")
        escolhas = [("manter_preco", "Manter preço", "secondary"),
                    ("revisar_preco", "Revisar preço", "primary"),
                    ("encaminhar_compliance", "Encaminhar ao compliance", "secondary")]
        for coluna, (chave, rotulo, tipo) in zip(botoes, escolhas):
            with coluna:
                if st.button(rotulo, key=f"dec_{chave}_{cid}", type=tipo, use_container_width=True):
                    if not justificativa.strip():
                        st.warning("Escreva a justificativa antes de registrar a decisão.")
                    elif not st.session_state.analista.strip():
                        st.warning("Informe o nome do analista responsável no topo da seção.")
                    else:
                        registrar_decisao(resultado, chave, justificativa,
                                          nova if chave == "revisar_preco" else None)
                        st.success(f"Decisão registrada: {rotulo}. Veja a aba Registro de decisões.")
        anteriores = [d for d in st.session_state.decisoes if d["contrato_id"] == cid]
        if anteriores:
            d = anteriores[0]
            st.caption(f"Última decisão neste contrato: {RECOMENDACOES.get(d['decisao'], d['decisao'])} "
                       f"por {d['analista']} em {d['registrado_em']}.")


def render_revisao(r: dict, ctx: dict) -> None:
    situacao = r.get("situacao_preco", "revisao_manual")
    pais = PAISES.get(ctx.get("pais"), ctx.get("pais"))
    meta = [p for p in (pais,
                        f"concedido em {data_br(ctx.get('data'))}" if ctx.get("data") else None,
                        eur(ctx["valor"]) if ctx.get("valor") else None,
                        f"{ctx['prazo']} meses" if ctx.get("prazo") else None) if p]
    chips = []
    if ctx.get("caso_real"):
        chips.append('<span class="ap-chip ap-chip-gold">Caso real da base</span>')
    elif ctx.get("ilustrativo"):
        chips.append('<span class="ap-chip ap-chip-gold">Exemplo ilustrativo</span>')
    if ctx.get("origem") == "carteira":
        chips.append('<span class="ap-chip ap-chip-gold">Aberto da carteira</span>')
    chips += ['<span class="ap-chip">Custo do dinheiro: Euribor da época</span>',
              '<span class="ap-chip">Parecer: análise hipotética pela lei brasileira</span>',
              f'<span class="ap-chip">Modelo: {esc(r.get("versao_modelo"))}</span>']

    md(f"""
        <div class="ap-head">
            <div>
                <div class="audit-eyebrow">Revisão de contrato</div>
                <div class="ap-title">Contrato {esc(r.get("contrato_id"))}</div>
                <div class="ap-meta">{esc(" · ".join(meta)) if meta else "&nbsp;"}</div>
            </div>
            <div>{badge_situacao(situacao)}</div>
        </div>
        <div class="ap-chips">{"".join(chips)}</div>
    """)

    for coluna, cartao in zip(st.columns(4, gap="small"), kpis_revisao(r)):
        with coluna:
            md(cartao)

    if situacao == "revisao_manual":
        md("""<div class="ap-alert"><b>Revisão manual.</b> Os dados deste contrato estão fora da faixa vista no
            treino do modelo (país não visto, ou valor, prazo ou renda vazios ou extremos). Por isso a chance de não pagar
            e o juro justo não foram calculados. Confira os dados de origem antes de qualquer decisão.</div>""")
    else:
        md(f"""<div class="ap-card"><div class="ap-card-title">Juro cobrado × juro justo</div>
            {html_barra_juros(r)}</div>""")

    col_motivos, col_parecer = st.columns([1, 1.55], gap="medium")
    with col_motivos:
        md(f"""<div class="ap-card"><div class="ap-card-title">O que mais pesou no risco</div>
            <div class="ap-card-sub">Contribuição de cada fator (SHAP). Gênero, idade e país não aparecem como motivo.</div>
            {html_motivos(r.get("motivos") or [])}</div>""")
    with col_parecer:
        md(f'<div class="ap-card">{html_parecer(r.get("parecer_ia"))}</div>')

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    bloco_decisao(r)

    with st.expander("Dados técnicos da consulta"):
        if st.session_state.audit_last_payload and not ctx.get("ilustrativo"):
            st.markdown("**Enviado à API**")
            st.json(st.session_state.audit_last_payload)
        st.markdown("**Resposta da API**")
        st.json(r)


# ------------------------------------------
# 6.3 Aba: revisão de contrato
# ------------------------------------------
with aba_revisao:
    modo = st.radio("Origem do contrato", ["Novo contrato (formulário)", "Caso de exemplo"],
                    horizontal=True, key="modo_revisao", label_visibility="collapsed")

    if modo == "Novo contrato (formulário)":
        if formulario():
            payload = montar_payload()
            st.session_state.audit_last_payload = payload
            with st.spinner("Calculando risco, juro justo e parecer..."):
                resposta, erro = chamar_api("/prever", payload)
            if erro:
                st.session_state.audit_last_error = erro
            else:
                guardar_resultado(resposta, {"pais": payload["country"], "data": payload["data_emprestimo"],
                                             "valor": payload["amount"], "prazo": payload["loan_duration"]})
    else:
        exemplos, reais = carregar_exemplos()
        if not exemplos:
            st.info("Nenhum caso encontrado em docs/casos_de_teste.json nem em docs/exemplos_prever.json.")
        else:
            origem = ("Contratos reais da base, já pontuados pelo prever() (docs/casos_de_teste.json), dois por situação."
                      if reais else "Saídas ilustrativas do prever() (docs/exemplos_prever.json), uma por situação.")
            with st.container(border=True):
                md(f"""<div class="audit-eyebrow">MODO DEMONSTRAÇÃO</div>
                    <div class="ap-card-sub">{origem} Útil para a demo e para conferir a tela sem o modelo carregado.</div>""")
                opcoes = {f'{SITUACOES[e["situacao_preco"]]["rotulo"]} · {e["contrato_id"][:13]}': e for e in exemplos}
                escolha = st.selectbox("Caso", list(opcoes), key="exemplo_escolhido")
                if st.button("Abrir caso", key="abrir_exemplo", type="primary"):
                    exemplo = dict(opcoes[escolha])
                    parecer, erro = chamar_api("/parecer", exemplo)
                    exemplo["parecer_ia"] = parecer  # sem API: abre só com os números
                    if erro:
                        st.caption(f"Parecer indisponível: {erro}")
                    guardar_resultado(exemplo, {"ilustrativo": True, "caso_real": reais})

    if st.session_state.audit_last_error:
        st.error(st.session_state.audit_last_error)
    if st.session_state.audit_last_result:
        render_revisao(st.session_state.audit_last_result, st.session_state.audit_last_contexto)


# ------------------------------------------
# 6.4 Aba: auditoria da carteira
# ------------------------------------------
def kpis_carteira(res: dict | None) -> None:
    vazio = res is None
    cartoes = [
        ("Contratos auditados", "[N]" if vazio else f"{res['auditados']:,}".replace(",", "."),
         "no período e filtros escolhidos" if vazio else
         f"+ {res['revisao_manual']:,} em revisão manual".replace(",", "."), None),
        ("Acima do justo", "[X%]" if vazio else pct(res["acima"]), "risco de perder bons clientes",
         SITUACOES["acima_do_justo"]),
        ("Abaixo do justo", "[Y%]" if vazio else pct(res["abaixo"]), "juro não cobre a perda esperada",
         SITUACOES["abaixo_do_justo"]),
        ("Pago a mais pelos clientes", "€ [VALOR]" if vazio else eur(res["pago_a_mais_eur"]),
         "soma acima da margem de incerteza", None),
        ("Perda não coberta", "€ [VALOR]" if vazio else eur(res["perda_nao_coberta_eur"]),
         "abaixo do justo · só contratos encerrados", None),
    ]
    for coluna, (rotulo, valor, sub, cor) in zip(st.columns(5, gap="small"), cartoes):
        with coluna:
            estilo = f'style="color:{cor["cor"]}"' if cor else ""
            md(f"""<div class="ap-kpi"><div class="ap-kpi-label">{esc(rotulo)}</div>
                <div class="ap-kpi-value" {estilo}>{esc(valor)}</div><div class="ap-kpi-sub">{esc(sub)}</div></div>""")


def tabela_fila(linhas: list[dict]) -> str:
    corpo = "".join(
        f"<tr><td><b>{esc(x['contrato_id'])}</b></td><td>{esc(x.get('faixa') or '—')}</td>"
        f"<td>{pct(x.get('juro_cobrado'))}</td><td>{pct(x.get('juro_justo'))}</td>"
        f"<td>{badge_situacao(x.get('situacao_preco'))}</td>"
        f"<td>{'' if x.get('distancia_pp') is None else str(x['distancia_pp']).replace('.', ',') + ' pp'}</td></tr>"
        for x in linhas)
    return compactar(f"""<table class="ap-table"><thead><tr><th>Contrato</th><th>Faixa</th><th>Juro cobrado</th>
        <th>Juro justo</th><th>Situação</th><th>Além da margem</th></tr></thead><tbody>{corpo}</tbody></table>""")


def abrir_da_carteira(linha: dict) -> None:
    resultado = {
        "contrato_id": str(linha["contrato_id"]),
        "versao_modelo": str(linha.get("versao_modelo") or "carteira"),
        "pd": linha.get("pd"), "faixa": linha.get("faixa"),
        "juro_cobrado": linha["juro_cobrado"], "juro_justo": linha.get("juro_justo"),
        "juro_justo_min": linha.get("juro_justo_min"), "juro_justo_max": linha.get("juro_justo_max"),
        "situacao_preco": linha["situacao_preco"], "motivos": [],
        "alerta_dados": linha["situacao_preco"] == "revisao_manual",
    }
    parecer, erro = chamar_api("/parecer", resultado)
    resultado["parecer_ia"] = parecer
    guardar_resultado(resultado, {"pais": linha.get("pais"), "valor": linha.get("valor_concedido"),
                                  "prazo": linha.get("prazo_meses"), "origem": "carteira"})
    st.success(f"Contrato {resultado['contrato_id']} aberto na aba Revisão de contrato."
               + (f" Parecer indisponível: {erro}" if erro else ""))


with aba_carteira:
    df, equidade, erro_carteira = dados_carteira()

    col_tit, col_f1, col_f2, col_f3 = st.columns([2.2, 1.3, 0.8, 0.8], gap="small")
    with col_tit:
        md("""<div class="audit-eyebrow">Auditoria da carteira</div>
            <div class="ap-title">O preço acompanha o risco?</div>
            <div class="ap-meta">Contratos pontuados pelo modelo · reestruturados fora da comparação de preço</div>""")
    filtros = {"anos": None, "pais": None, "faixa": None}
    if df is not None and not df.empty:
        ano_min, ano_max = int(df["ano"].min()), int(df["ano"].max())
        with col_f1:
            if ano_min < ano_max:
                filtros["anos"] = st.slider("Período", ano_min, ano_max, (ano_min, ano_max), key="f_anos")
            else:
                st.caption(f"Período: {ano_min}")
        with col_f2:
            p = st.selectbox("País", ["Todos"] + sorted(df["pais"].dropna().unique()), key="f_pais",
                             format_func=lambda s: PAISES.get(s, s))
            filtros["pais"] = None if p == "Todos" else p
        with col_f3:
            f = st.selectbox("Faixa de risco", ["Todas"] + cart.FAIXAS, key="f_faixa")
            filtros["faixa"] = None if f == "Todas" else f

    if erro_carteira:
        st.error(f"Não foi possível ler os arquivos da carteira: {erro_carteira}")
    if df is None:
        md(f"""<div class="ap-alert"><b>Aguardando o lote da carteira.</b> Este painel lê
            <code>{esc(cart.ARQ_CARTEIRA)}</code> e <code>{esc(cart.ARQ_EQUIDADE)}</code> em
            <code>docs/resultados/</code>, gerados pelo processo em lote do modelo. Enquanto eles não existem, os campos
            aparecem entre colchetes e a lista abaixo mostra os contratos auditados nesta sessão.</div>""")

    filtrado = cart.filtrar(df, **filtros) if df is not None else None
    st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)
    kpis_carteira(cart.resumo(filtrado) if filtrado is not None else None)

    col_faixa, col_eq = st.columns([1, 1.5], gap="medium")
    with col_faixa:
        if filtrado is not None and not filtrado.empty:
            corpo = html_barras_faixa(cart.por_faixa(filtrado))
            nota = "Proporções na carteira filtrada; à direita, número de contratos por faixa."
        else:
            corpo = '<div class="ap-empty">Distribuição disponível quando o lote da carteira for gerado.</div>'
            nota = "Mostra, em cada faixa, a parte abaixo, dentro e acima do juro justo."
        md(f"""<div class="ap-card"><div class="ap-card-title">Situação do preço por faixa de risco</div>
            {corpo}<div class="ap-foot">{nota}</div></div>""")
    with col_eq:
        linhas_eq = equidade if equidade else cart.EQUIDADE_VAZIA
        md(f"""<div class="ap-card"><div class="ap-card-title">Equidade no preço: diferença residual entre grupos de mesmo risco</div>
            <div class="ap-card-sub">Diferença de juros (cobrado − justo) que sobra depois de controlar por risco, país, ano, valor e prazo.
            País é controle, não grupo comparado.</div>
            {html_tabela_equidade(linhas_eq)}
            <div class="ap-foot">“Indício” pede investigação; não é conclusão. Gênero: comparação só entre 0 e 1, dentro do país;
            a codificação de 2017–2019 é suspeita. Controlar por renda pode esconder efeito de gênero.</div></div>""")

    if filtrado is not None:
        bt = cart.backtest(filtrado)
        if bt is not None:
            formatar = getattr(bt, "map", None) or bt.applymap  # pandas < 2.1 não tem DataFrame.map
            tabela = formatar(lambda v: pct(v) if pandas.notna(v) else "—")
            tabela.columns = [SITUACOES[c]["rotulo"] for c in tabela.columns]
            tabela.index = [f"Faixa {i}" for i in tabela.index]
            with st.container(border=True):
                md("""<div class="ap-card-title">Backtest: rentabilidade realizada dentro de cada faixa</div>
                    <div class="ap-card-sub">Contratos encerrados. Se a auditoria funciona, em cada faixa “abaixo do justo”
                    rende menos e “acima do justo” rende mais.</div>""")
                st.dataframe(tabela, use_container_width=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    with st.container(border=True):
        if filtrado is not None:
            fila = cart.fila_revisao(filtrado, limite=None)
            titulo = f"Contratos para revisão · {len(fila):,}".replace(",", ".")
        else:
            fila = None
            titulo = "Contratos auditados nesta sessão"
        col_t, col_exp = st.columns([3, 1])
        with col_t:
            md(f'<div class="ap-card-title">{esc(titulo)}</div>'
               '<div class="ap-card-sub">Do mais distante para o mais próximo da margem de incerteza.</div>')
        if fila is not None and not fila.empty:
            with col_exp:
                st.download_button("Exportar lista (CSV)", fila.to_csv(index=False).encode("utf-8"),
                                   file_name="contratos_para_revisao.csv", mime="text/csv")
            registros = json.loads(fila.head(50).to_json(orient="records"))  # tipos nativos, NaN → null
            md(tabela_fila(registros))
            if len(fila) > 50:
                st.caption("Mostrando os 50 primeiros; a exportação traz a lista completa.")
            col_sel, col_btn = st.columns([3, 1], gap="small")
            with col_sel:
                escolhido = st.selectbox("Abrir na revisão", [x["contrato_id"] for x in registros], key="fila_sel")
            with col_btn:
                st.markdown("<div style='height:1.7rem'></div>", unsafe_allow_html=True)
                if st.button("Revisar", key="fila_revisar", type="primary", use_container_width=True):
                    abrir_da_carteira(next(x for x in registros if x["contrato_id"] == escolhido))
        elif fila is not None:
            st.caption("Nenhum contrato fora da margem com os filtros escolhidos.")
        elif st.session_state.historico:
            md(tabela_fila(st.session_state.historico))
        else:
            st.caption("Nenhum contrato auditado ainda nesta sessão.")


# ------------------------------------------
# 6.5 Aba: registro de decisões
# ------------------------------------------
with aba_registro:
    decisoes = st.session_state.decisoes
    md("""<div class="audit-eyebrow" style="margin-top:1.2rem">Registro de decisões</div>
        <div class="ap-title">Quem decidiu, o quê e por quê</div>
        <div class="ap-meta">Cada decisão fica com o parecer, a recomendação do sistema e a justificativa
        (direito de revisão, LGPD art. 20). Nesta versão o registro vale para a sessão; exporte antes de fechar.</div>""")
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    if not decisoes:
        st.caption("Nenhuma decisão registrada nesta sessão.")
    else:
        tabela = pandas.DataFrame(decisoes)
        divergentes = (tabela["decisao"] != tabela["recomendacao_sistema"]).sum()
        c1, c2, c3 = st.columns(3, gap="small")
        with c1:
            md(f'<div class="ap-kpi"><div class="ap-kpi-label">Decisões registradas</div><div class="ap-kpi-value">{len(tabela)}</div></div>')
        with c2:
            md(f'<div class="ap-kpi"><div class="ap-kpi-label">Diferentes da recomendação</div><div class="ap-kpi-value">{divergentes}</div>'
               '<div class="ap-kpi-sub">o analista discordou do sistema</div></div>')
        with c3:
            n_comp = int((tabela["decisao"] == "encaminhar_compliance").sum())
            md(f'<div class="ap-kpi"><div class="ap-kpi-label">Encaminhadas ao compliance</div><div class="ap-kpi-value">{n_comp}</div></div>')
        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        exibir = tabela.assign(decisao=tabela["decisao"].map(RECOMENDACOES),
                               recomendacao_sistema=tabela["recomendacao_sistema"].map(RECOMENDACOES))
        st.dataframe(exibir, use_container_width=True, hide_index=True)
        col_csv, col_json, _ = st.columns([1, 1, 2], gap="small")
        with col_csv:
            st.download_button("Exportar CSV", tabela.to_csv(index=False).encode("utf-8"),
                               file_name="decisoes_analista.csv", mime="text/csv")
        with col_json:
            st.download_button("Exportar JSON", json.dumps(decisoes, ensure_ascii=False, indent=2).encode("utf-8"),
                               file_name="decisoes_analista.json", mime="application/json")


# ==========================================
# 7. SESSÃO SOBRE O PROJETO & EQUIPE (#SOBRE)
# ==========================================
st.markdown('<div id="sobre" class="section-wrapper"></div>', unsafe_allow_html=True)
md("""
    <div class="section-header">
        <h2>Sobre o Projeto</h2>
        <div class="gold-divider"></div>
        <p>Projeto integrador do <b>Bootcamp IA 2026</b> (segmento BFSI).<br>
        Dados reais do Bondora (2009–2021) como substitutos do comportamento de crédito; análise jurídica hipotética pela lei brasileira.</p>
    </div>
""")
EQUIPE = [
    ("YG", "Yasmin Garcia", "App & Infraestrutura",
     "Docker, API FastAPI, painel Streamlit, integração contínua e vídeo da demo."),
    ("MA", "Marcos", "Dados & Processo",
     "Carga do Bondora e das séries de juros no PostgreSQL, qualidade dos dados, EDA e BPMN."),
    ("SL", "Samuel", "Modelo & Juro Justo",
     "Modelo de risco calibrado, motivos (SHAP), juro justo com margem de incerteza, equidade e backtest."),
    ("MV", "M. Vitória", "GenAI & RAG",
     "Normas e busca (RAG), prompts, parecer com checagem por código e template de reserva."),
]
md('<div class="team-grid">' + "".join(f"""
    <div class="team-card">
        <div class="team-avatar">{sigla}</div>
        <div class="team-name">{esc(nome)}</div>
        <div class="team-role">{esc(papel)}</div>
        <div class="team-bio">{esc(bio)}</div>
    </div>""" for sigla, nome, papel, bio in EQUIPE) + "</div>")
