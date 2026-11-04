import streamlit as st
import requests
import json
import os

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA E API
# ==========================================
st.set_page_config(
    page_title="Auditor de Preço Justo | Auditoria de Crédito",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed" # Remove a barra lateral expandida
)

# Lê a URL do Docker Compose (rede interna), ou usa localhost se rodar localmente
API_BASE = os.getenv("API_URL", "http://localhost:8000")
API_URL = f"{API_BASE}/prever"

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

    html {
        scroll-behavior: smooth;
    }

    /* Ocultar elementos nativos do Streamlit */
    #MainMenu, header, footer, [data-testid="stSidebar"] {
        display: none !important;
    }
    
    .block-container {
        padding: 0 !important;
        max-width: 100% !important;
    }

    body {
        background-color: var(--dark-bg);
        color: var(--text-light);
        font-family: 'DM Sans', sans-serif;
    }

    /* --- NAVBAR SUPERIOR FIXA --- */
    .top-navbar {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 70px;
        background-color: rgba(18, 19, 21, 0.95);
        backdrop-filter: blur(10px);
        border-bottom: 1px solid var(--card-border);
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 4rem;
        z-index: 9999;
    }

    .nav-brand {
        font-family: 'Playfair Display', serif;
        font-size: 1.4rem;
        font-weight: 700;
        color: #ffffff !important;
        letter-spacing: 1px;
        text-decoration: none;
        display: flex;
        align-items: center;
        gap: 10px;
    }

    .nav-links {
        display: flex;
        gap: 2.5rem;
        align-items: center;
    }

    .nav-link {
        color: #ffffff !important;
        text-decoration: none;
        font-weight: 500;
        font-size: 0.95rem;
        transition: color 0.3s ease;
    }

    .nav-link:hover {
        color: var(--gold);
    }

    /* --- HERO SECTION --- */
    .hero-container {
        margin-top: 0px;
        background-image: linear-gradient(to right, rgba(18, 19, 21, 0.95) 25%, rgba(18, 19, 21, 0.7) 100%), 
                          url('https://images.unsplash.com/photo-1589829085413-56de8ae18c73?q=80&w=2000&auto=format&fit=crop');
        background-size: cover;
        background-position: center;
        padding: 25rem 4rem 4rem 4rem;
        border-bottom: 5px solid var(--card-border);
    }

    .hero-title {
        font-family: 'Playfair Display', serif;
        font-size: 3.8rem;
        font-weight: 700;
        color: var(--text-light);
        line-height: 1.15;
        margin-bottom: 1rem;
    }

    .hero-title span {
        color: var(--gold);
        font-style: italic;
    }

    .hero-subtitle {
        font-size: 1.15rem;
        color: var(--text-muted);
        max-width: 650px;
        margin-bottom: 2rem;
        line-height: 1.6;
    }

    /* --- FAIXA ESCURA COM 3 BLOCOS EXPLICATIVOS --- */
    .features-strip {
        background-color: #0b0c0e;
        border-bottom: 1px solid var(--card-border);
        padding: 2.5rem 4rem;
    }

    .features-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 2rem;
        max-width: 1300px;
        margin: 0 auto;
    }

   .feature-item {
        display: flex;
        align-items: flex-start;
        gap: 1.2rem;
        background: rgba(28, 29, 33, 0.15); 
        padding: 1.5rem;
        border-radius: 12px;
    }

    .feature-icon {
        font-size: 1.8rem;
        color: var(--gold);
    }

    .feature-title {
        font-family: 'Playfair Display', serif;
        font-size: 1.15rem;
        color: var(--text-light);
        margin-bottom: 0.4rem;
    }

    .feature-desc {
        font-size: 0.88rem;
        color: var(--text-muted);
        line-height: 1.5;
    }

    /* --- SESSÃO DO AUDITOR (FORMULÁRIO E RESULTADOS) --- */
    .section-wrapper {
        padding: 4rem 4rem;
        max-width: 1400px;
        margin: 0 auto;
    }

    .section-header {
        text-align: center;
        margin-bottom: 3rem;
    }

    .section-header h2 {
        font-family: 'Playfair Display', serif;
        font-size: 2.6rem;
        color: var(--text-light);
    }

    .section-header p {
        color: var(--text-muted);
        font-size: 1.05rem;
    }

    .gold-divider {
        width: 60px;
        height: 3px;
        background-color: var(--gold);
        margin: 1rem auto;
        border-radius: 2px;
    }

    /* --- SESSÃO SOBRE (INTEGRANTES COM CARTÕES RETANGULARES) --- */
    .team-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1.8rem;
        margin-top: 2.5rem;
    }

    .team-card {
        background-color: var(--card-bg);
        border: 1px solid var(--card-border);
        border-radius: 12px;
        padding: 1.2rem;
        text-align: left;
        transition: transform 0.3s ease, border-color 0.3s ease;
    }

    .team-card:hover {
        transform: translateY(-5px);
        border-color: var(--gold);
    }

    .team-img-wrapper {
        width: 100%;
        height: 220px;
        border-radius: 8px;
        overflow: hidden;
        margin-bottom: 1rem;
        background-color: #121315;
        border: 1px solid rgba(255,255,255,0.05);
    }

    .team-img {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }

    .team-name {
        font-family: 'Playfair Display', serif;
        font-size: 1.25rem;
        color: var(--text-light);
        margin-bottom: 0.2rem;
    }

    .team-role {
        font-size: 0.82rem;
        color: var(--gold);
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
        margin-bottom: 0.6rem;
    }

    .team-bio {
        font-size: 0.85rem;
        color: var(--text-muted);
        line-height: 1.4;
    }

    /* --- COMPONENTES STREAMLIT --- */
    [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        background: var(--dark-bg);
        color: var(--text-light);
    }

    [data-testid="stMain"] .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 4rem !important;
    }

    [data-testid="stButton"] button {
        min-height: 52px;
        width: 100%;
        white-space: pre-wrap !important;
        text-align: center !important;
        line-height: 1.55 !important;
        padding: 1.1rem 1rem !important;
        border-radius: 14px !important;
        border: 1px solid rgba(200, 154, 88, 0.34) !important;
        background: linear-gradient(145deg, #202126 0%, #17181c 100%) !important;
        color: var(--text-light) !important;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.16);
        transition: transform .2s ease, border-color .2s ease, box-shadow .2s ease;
    }

    [data-testid="stButton"] button:hover {
        transform: translateY(-3px);
        border-color: var(--gold-light) !important;
        box-shadow: 0 12px 28px rgba(200, 154, 88, 0.12);
    }

    [data-testid="stButton"] button[data-testid="stBaseButton-primary"],
    [data-testid="stButton"] button[kind="primary"] {
        background: linear-gradient(135deg, #d7b9b8 0%, #c8a2a0 100%) !important;
        color: #171315 !important;
        border: 1px solid #e5c5c3 !important;
        font-weight: 700 !important;
    }

    .audit-workspace-label {
        color: var(--gold-light);
        font-size: .68rem;
        font-weight: 700;
        letter-spacing: .16em;
        text-transform: uppercase;
        margin: .15rem 0 .4rem 0;
    }

    .st-key-audit_select_personal button,
    .st-key-audit_select_loan button,
    .st-key-audit_select_history button {
        min-height: 104px !important;
        height: 104px !important;
        padding: .55rem .35rem !important;
        border-radius: 10px !important;
        font-size: .74rem !important;
        line-height: 1.35 !important;
        box-shadow: none !important;
    }

    .st-key-audit_select_personal button[kind="primary"],
    .st-key-audit_select_loan button[kind="primary"],
    .st-key-audit_select_history button[kind="primary"] {
        background: linear-gradient(135deg, #c89a58 0%, #e4bd7d 100%) !important;
        color: #171315 !important;
        border: 1px solid #e4bd7d !important;
    }

    .audit-review-progress {
        height: 7px;
        width: 100%;
        background: rgba(238, 233, 229, .12);
        border-radius: 10px;
        overflow: hidden;
        margin: .75rem 0 1.35rem 0;
    }

    .audit-review-progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #c89a58, #e4bd7d);
        border-radius: 10px;
        transition: width .25s ease;
    }

    .audit-review-status {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: .5rem;
        margin: .95rem 0 .45rem 0;
        color: #e8e5df;
        font-size: .76rem;
        font-weight: 600;
    }

    [data-testid="stVerticalBlockBorderWrapper"] {
        background: linear-gradient(145deg, rgba(31, 32, 37, .96), rgba(23, 24, 28, .96));
        border: 1px solid rgba(200, 154, 88, .24) !important;
        border-radius: 16px !important;
        padding: 1.1rem 1.2rem !important;
    }

    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stSelectbox"] [data-baseweb="select"] > div {
        background: #141519 !important;
        color: var(--text-light) !important;
        border-color: rgba(200, 154, 88, .28) !important;
        border-radius: 8px !important;
    }

    [data-testid="stMetric"] {
        background: #1c1d21;
        border: 1px solid rgba(200, 154, 88, .22);
        border-radius: 12px;
        padding: 1rem 1.1rem;
    }

    [data-testid="stMetricLabel"] p {
        color: var(--text-muted) !important;
    }

    [data-testid="stMetricValue"] {
        color: var(--gold-light) !important;
    }

    .audit-eyebrow {
        color: var(--gold-light);
        font-size: .72rem;
        font-weight: 700;
        letter-spacing: .16em;
        text-transform: uppercase;
        margin-bottom: .45rem;
    }

    .audit-panel-title {
        color: var(--text-light);
        font-family: 'Playfair Display', serif;
        font-size: 1.65rem;
        margin: 0 0 .35rem 0;
    }

    .audit-progress-title {
        color: var(--text-light);
        font-family: 'Playfair Display', serif;
        font-size: 1.25rem;
        margin: 0 0 .3rem 0;
    }

    .skill-track {
        width: 100%;
        height: 7px;
        background: #eee9e5;
        border-radius: 1px;
        overflow: hidden;
    }
    .skill-fill {
        height: 100%;
        background: #171719;
        border-radius: 1px;
        transition: width .25s ease;
    }

    .audit-note {
        background: rgba(200, 154, 88, .08);
        border-left: 3px solid var(--gold);
        border-radius: 0 8px 8px 0;
        padding: .8rem .95rem;
        color: #c6c2bb;
        font-size: .8rem;
        line-height: 1.5;
        margin-top: .8rem;
    }

    </style>
""", unsafe_allow_html=True)


# ==========================================
# 3. BARRA NAVEGAÇÃO SUPERIOR (FIXA)
# ==========================================
st.markdown("""
    <div class="top-navbar">
        <a href="#home" class="nav-brand">
            <span>⚖️</span> AUDITOR DE PREÇO JUSTO
        </a>
        <div class="nav-links">
            <a href="#home" class="nav-link">Home</a>
            <a href="#auditor" class="nav-link">Auditor de Crédito</a>
            <a href="#sobre" class="nav-link">Sobre o Projeto</a>
        </div>
    </div>
""", unsafe_allow_html=True)


# ==========================================
# 4. HOME / HERO SECTION
# ==========================================
st.markdown('<div id="home"></div>', unsafe_allow_html=True)

st.markdown("""
    <div class="hero-container">
        <div class="hero-title">
            Inteligência de Crédito &<br><span>Conformidade Jurídica.</span>
        </div>
        <div class="hero-subtitle">
            Auditoria automatizada de taxa de juros, predição de risco de inadimplência e emissão de pareceres legais fundamentados no CDC e LGPD.
        </div>
    </div>
""", unsafe_allow_html=True)


# ==========================================
# 5. FAIXA ESCURA COM 3 TEXTOS EXPLICATIVOS
# ==========================================
st.markdown("""
    <div class="features-strip">
        <div class="features-grid">
            <div class="feature-item">
                <div class="feature-icon">📊</div>
                <div>
                    <div class="feature-title">Auditoria Quantitativa</div>
                    <div class="feature-desc">Validação de taxas cobradas frente ao custo médio do dinheiro divulgado pelo Banco Central do Brasil.</div>
                </div>
            </div>
            <div class="feature-item">
                <div class="feature-icon">🤖</div>
                <div>
                    <div class="feature-title">Modelagem de Risco</div>
                    <div class="feature-desc">Algoritmo Gradient Boosting (XGBoost) para estimativa precisa de probabilidade de default por contrato.</div>
                </div>
            </div>
            <div class="feature-item">
                <div class="feature-icon">📜</div>
                <div>
                    <div class="feature-title">Pareceres em GenAI</div>
                    <div class="feature-desc">Geração de parecer técnico-jurídico com RAG estruturado sobre normas de proteção ao consumidor.</div>
                </div>
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)


# ==========================================
# 6. SESSÃO DO AUDITOR DE CRÉDITO (#AUDITOR)
# ==========================================
st.markdown('<div id="auditor" class="section-wrapper"></div>', unsafe_allow_html=True)

st.markdown("""
    <div class="section-header">
        <h2>Auditor de Contratos de Crédito</h2>
        <div class="gold-divider"></div>
        <p>Organize os dados em três etapas para calcular o risco e emitir o parecer técnico.</p>
    </div>
""", unsafe_allow_html=True)

DEFAULT_INPUTS = {
    "age": 35,
    "gender": 0,
    "country": "EE",
    "income_total": 2500.0,
    "amount": 5000.0,
    "interest": 24.5,
    "loan_duration": 36,
    "rating": "B",
    "liabilities_total": 450.0,
    "debt_to_income": 25,
}

for field_name, default_value in DEFAULT_INPUTS.items():
    st.session_state.setdefault(f"audit_{field_name}", default_value)

for step_name in ("personal", "loan", "history"):
    st.session_state.setdefault(f"audit_reviewed_{step_name}", False)

st.session_state.setdefault("audit_active_step", "personal")
st.session_state.setdefault("audit_last_result", None)
st.session_state.setdefault("audit_last_payload", None)
st.session_state.setdefault("audit_last_error", None)

def _persist_audit_input(field_name: str) -> None:
    widget_key = f"_audit_widget_{field_name}"
    st.session_state[f"audit_{field_name}"] = st.session_state[widget_key]

def _prepare_audit_widget(field_name: str) -> str:
    widget_key = f"_audit_widget_{field_name}"
    if widget_key not in st.session_state:
        st.session_state[widget_key] = st.session_state[f"audit_{field_name}"]
    return widget_key

def audit_number(label: str, field_name: str, **kwargs):
    widget_key = _prepare_audit_widget(field_name)
    return st.number_input(
        label, key=widget_key, on_change=_persist_audit_input, args=(field_name,), **kwargs,
    )

def audit_select(label: str, field_name: str, options, **kwargs):
    widget_key = _prepare_audit_widget(field_name)
    return st.selectbox(
        label, options=options, key=widget_key, on_change=_persist_audit_input, args=(field_name,), **kwargs,
    )

def audit_slider(label: str, field_name: str, **kwargs):
    widget_key = _prepare_audit_widget(field_name)
    return st.slider(
        label, key=widget_key, on_change=_persist_audit_input, args=(field_name,), **kwargs,
    )

def _persist_review(step_name: str) -> None:
    widget_key = f"_audit_review_widget_{step_name}"
    st.session_state[f"audit_reviewed_{step_name}"] = st.session_state[widget_key]

def audit_review_checkbox(step_name: str) -> None:
    widget_key = f"_audit_review_widget_{step_name}"
    if widget_key not in st.session_state:
        st.session_state[widget_key] = st.session_state[f"audit_reviewed_{step_name}"]
    st.checkbox(
        "Confirmo que revisei os dados desta etapa", key=widget_key, on_change=_persist_review, args=(step_name,),
    )

step_cards = [
    ("personal", "\n\nDADOS PESSOAIS\n\n"),
    ("loan", "\n\nEMPRÉSTIMO\n\n"),
    ("history", "\n\nSCORE & HISTÓRICO\n\n"),
]

active_step = st.session_state.audit_active_step
step_details = {
    "personal": {
        "number": "01",
        "title": "Dados pessoais",
        "copy": "Informe o perfil do tomador. Os campos ficam organizados em sequência para facilitar a leitura e o preenchimento.",
    },
    "loan": {
        "number": "02",
        "title": "Dados do empréstimo",
        "copy": "Preencha as condições financeiras do contrato que será submetido à auditoria.",
    },
    "history": {
        "number": "03",
        "title": "Score & histórico",
        "copy": "Informe a classificação interna e os indicadores de comprometimento financeiro.",
    },
}
current_step = step_details[active_step]

left_margin, workspace_column, right_margin = st.columns([1, 3.2, 1], gap="small")
with workspace_column:
    nav_left, nav_center, nav_right = st.columns([0.35, 2.3, 0.35], gap="small")
    with nav_center:
        step_columns = st.columns(3, gap="small")
        for column, (step_key, step_label) in zip(step_columns, step_cards):
            with column:
                is_active = st.session_state.audit_active_step == step_key
                if st.button(
                    step_label, key=f"audit_select_{step_key}", type="primary" if is_active else "secondary", use_container_width=True,
                ):
                    st.session_state.audit_active_step = step_key
                    st.rerun()

    active_step = st.session_state.audit_active_step
    current_step = step_details[active_step]

    input_column, progress_column = st.columns([1.7, 0.95], gap="medium")

    with input_column:
        with st.container(border=True):
            st.markdown('<div class="audit-workspace-label">ÁREA DE CONSULTA · ETAPAS DE PREENCHIMENTO</div>', unsafe_allow_html=True)
            st.markdown(
                f"""
                <div style="margin:1.25rem 0 .8rem 0; padding-bottom:.8rem; border-bottom:1px solid rgba(200,154,88,.18);">
                    <div class="audit-eyebrow">ETAPA {current_step['number']} / 03 · COLETA DE DADOS</div>
                    <div class="audit-panel-title">{current_step['title']}</div>
                    <div class="audit-panel-copy" style="margin:.35rem 0 0 0;">{current_step['copy']}</div>
                </div>
                """, unsafe_allow_html=True,
            )

            if active_step == "personal":
                with st.container(key="audit_form_stack_personal"):
                    audit_number("Idade do cliente", "age", min_value=18, max_value=100, step=1)
                    audit_select("Gênero", "gender", options=[0, 1, 2], format_func=lambda value: {0: "Feminino", 1: "Masculino", 2: "Não informado"}[value])
                    audit_select("País de origem", "country", options=["EE", "FI", "ES"])
                    audit_number("Renda total mensal (€)", "income_total", min_value=0.0, step=100.0, format="%.2f")
                    audit_review_checkbox("personal")

            elif active_step == "loan":
                with st.container(key="audit_form_stack_loan"):
                    audit_number("Valor solicitado (€)", "amount", min_value=100.0, step=250.0, format="%.2f")
                    audit_number("Taxa de juros anual (% a.a.)", "interest", min_value=0.0, step=0.5, format="%.2f")
                    audit_slider("Prazo do contrato (meses)", "loan_duration", min_value=3, max_value=60, step=1)
                    st.markdown('<div class="audit-note">Confira se a taxa e o prazo correspondem aos dados efetivamente previstos no contrato analisado.</div>', unsafe_allow_html=True)
                    audit_review_checkbox("loan")

            else:
                with st.container(key="audit_form_stack_history"):
                    audit_select("Rating interno (Bondora)", "rating", options=["AA", "A", "B", "C", "D", "E", "HR"], index=None, placeholder="Selecione a classificação")
                    audit_number("Total de passivos / dívidas (€)", "liabilities_total", min_value=0.0, step=50.0, format="%.2f")
                    audit_slider("Comprometimento da renda (%)", "debt_to_income", min_value=0, max_value=100, step=1)
                    st.markdown('<div class="audit-note">O comprometimento da renda deve refletir a proporção informada para o tomador, não uma estimativa criada pela interface.</div>', unsafe_allow_html=True)
                    audit_review_checkbox("history")

            st.markdown("<div style='height:.35rem'></div>", unsafe_allow_html=True)
            btn_submeter = st.button("⚖️ EXECUTAR AUDITORIA DE PREÇO", key="audit_execute", type="primary", use_container_width=True)

    with progress_column:
        with st.container(border=True):
            reviewed_steps = {
                "personal": st.session_state.audit_reviewed_personal,
                "loan": st.session_state.audit_reviewed_loan,
                "history": st.session_state.audit_reviewed_history,
            }
            completed_count = sum(1 for value in reviewed_steps.values() if value)
            overall_progress = round((completed_count / 3) * 100)

            st.markdown(
                f"""
                <div class="audit-eyebrow">ACOMPANHAMENTO</div>
                <div class="audit-progress-title">Revisão dos dados</div>
                <div class="audit-progress-copy" style="margin-bottom:.5rem;">{completed_count} de 3 etapas revisadas</div>
                <div style="display:flex; align-items:baseline; gap:.3rem;">
                    <span style="font-family:'Playfair Display',serif; font-size:2rem; color:#e4bd7d;">{overall_progress}%</span>
                    <span style="font-size:.72rem; color:#9aa5b5;">concluído</span>
                </div>
                <div class="audit-review-progress">
                    <div class="audit-review-progress-fill" style="width:{overall_progress}%"></div>
                </div>
                """, unsafe_allow_html=True,
            )

            progress_items = [("01", "Dados pessoais", "personal"), ("02", "Dados do empréstimo", "loan"), ("03", "Score & histórico", "history")]
            for number, label, key in progress_items:
                is_reviewed = reviewed_steps[key]
                percentage = 100 if is_reviewed else 0
                status_text = "REVISADO" if is_reviewed else "PENDENTE"
                st.markdown(
                    f"""
                    <div class="audit-review-status">
                        <span>{number} · {label}</span>
                        <span>{status_text}</span>
                    </div>
                    <div class="skill-track">
                        <div class="skill-fill" style="width:{percentage}%; background:linear-gradient(90deg,#c89a58,#e4bd7d);"></div>
                    </div>
                    """, unsafe_allow_html=True,
                )
            st.markdown('<div class="audit-note" style="margin-top:1.2rem;">Revise cada etapa e marque a confirmação no formulário à esquerda.</div>', unsafe_allow_html=True)


if btn_submeter:
    # Payload rigorosamente alinhado com SolicitacaoEmprestimo (schemas.py)
    payload = {
        "loan_id": "EMP-2026-001",
        "amount": float(st.session_state.audit_amount),
        "income_total": float(st.session_state.audit_income_total),
        "employment_status": "Employed",
        "verification_type": "Verified",
        "gender": int(st.session_state.audit_gender),
        "age": int(st.session_state.audit_age),
        "country": st.session_state.audit_country,
        "interest_cobrado": float(st.session_state.audit_interest)
    }
    
    st.session_state.audit_last_payload = payload

    try:
        with st.spinner("Conectando à API de risco e processando a auditoria..."):
            response = requests.post(API_URL, json=payload, timeout=15)
            response.raise_for_status()
            response_data = response.json()
            if not isinstance(response_data, dict):
                raise ValueError("A API retornou uma estrutura diferente da esperada.")

        st.session_state.audit_last_result = response_data
        st.session_state.audit_last_error = None

    except requests.exceptions.RequestException as exc:
        st.session_state.audit_last_result = None
        st.session_state.audit_last_error = f"Não foi possível consultar a API em {API_URL}. Detalhe técnico: {exc}"
    except (ValueError, json.JSONDecodeError) as exc:
        st.session_state.audit_last_result = None
        st.session_state.audit_last_error = f"A resposta da API não pôde ser interpretada: {exc}"

if st.session_state.audit_last_error:
    st.error(st.session_state.audit_last_error)

resultado = st.session_state.audit_last_result
if resultado:
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown('<div class="audit-eyebrow">RESULTADO DA CONSULTA</div>', unsafe_allow_html=True)
        st.markdown('<div class="audit-panel-title">Resumo da avaliação</div>', unsafe_allow_html=True)

        col_r1, col_r2, col_r3 = st.columns(3, gap="medium")
        with col_r1:
            pd = resultado.get("pd", 0)
            st.metric("Probabilidade de default", f"{pd * 100:.1f}%")
        with col_r2:
            st.metric("Classificação de risco", resultado.get("faixa", "—"))
        with col_r3:
            juro = resultado.get("juro_justo", 0)
            st.metric("Juro Justo (Mercado)", f"{juro * 100:.1f}% a.a.")

        st.markdown("#### 📜 Parecer técnico automatizado (GenAI)")
        parecer = resultado.get("parecer_ia")
        if parecer:
            st.info(parecer.get("resumo", "Resumo não disponível."))
            st.markdown(f"**Recomendação do Sistema:** `{parecer.get('recomendacao', 'N/A')}`")
            with st.expander("Ver detalhes e alertas"):
                for ponto in parecer.get("pontos_de_atencao", []):
                    st.markdown(f"- {ponto}")
        else:
            st.caption("A API não retornou um parecer textual nesta consulta.")

        with st.expander("Consultar payload enviado à API"):
            st.json(st.session_state.audit_last_payload)
        with st.expander("Consultar resposta bruta da API"):
            st.json(resultado)

# ==========================================
# 7. SESSÃO SOBRE O PROJETO & EQUIPE (#SOBRE)
# ==========================================
st.markdown('<div id="sobre" class="section-wrapper"></div>', unsafe_allow_html=True)

st.markdown("""
    <div class="section-header">
        <h2>Sobre o Projeto</h2>
        <div class="gold-divider"></div>
        <p>Projeto de Fintech & Legal Tech desenvolvido para o <b>Bootcamp IA 2026</b>.<br>Unindo engenharia de dados, inteligência artificial e análise regulatória.</p>
    </div>
    
    <div class="team-grid">
        <div class="team-card">
            <div class="team-img-wrapper">
                <img src="https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?q=80&w=400&auto=format&fit=crop" class="team-img" alt="Yasmin Garcia">
            </div>
            <div class="team-name">Yasmin Garcia</div>
            <div class="team-role">Engenharia de Software</div>
            <div class="team-bio">Desenvolvimento da infraestrutura backend, integração de APIs FastAPI e construção da interface corporativa em Streamlit.</div>
        </div>

        <div class="team-card">
            <div class="team-img-wrapper">
                <img src="https://images.unsplash.com/photo-1560250097-0b93528c311a?q=80&w=400&auto=format&fit=crop" class="team-img" alt="Marcos">
            </div>
            <div class="team-name">Marcos</div>
            <div class="team-role">Engenharia de Dados</div>
            <div class="team-bio">Estruturação de pipeline de dados, esquemas relacionais no PostgreSQL e integração de séries temporais do Banco Central.</div>
        </div>

        <div class="team-card">
            <div class="team-img-wrapper">
                <img src="https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?q=80&w=400&auto=format&fit=crop" class="team-img" alt="Samuel">
            </div>
            <div class="team-name">Samuel</div>
            <div class="team-role">Machine Learning</div>
            <div class="team-bio">Engenharia de atributos, treinamento e validação de modelos estatísticos preditivos (XGBoost) para score de inadimplência.</div>
        </div>

        <div class="team-card">
            <div class="team-img-wrapper">
                <img src="https://images.unsplash.com/photo-1580489944761-15a19d654956?q=80&w=400&auto=format&fit=crop" class="team-img" alt="Maria Vitória">
            </div>
            <div class="team-name">M. Vitória</div>
            <div class="team-role">GenAI & RAG</div>
            <div class="team-bio">Arquitetura RAG para indexação de normas legais (CDC e LGPD) e geração automatizada de pareceres de conformidade.</div>
        </div>
    </div>
""", unsafe_allow_html=True)