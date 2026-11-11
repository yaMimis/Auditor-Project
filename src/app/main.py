"""Painel do analista — Auditor de Preço Justo (Streamlit).

Telas: Revisão de contrato · Auditoria da carteira · Registro de decisões.
O estilo fica em src/app/estilo.css; os blocos de HTML do resultado, em componentes.py.
O painel só EXIBE: todos os números vêm da API (prever() do Samuel) ou dos arquivos
do lote da carteira; o parecer vem da GenAI (ou do template de reserva).
"""
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

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
                                 html_tabela_equidade, icone, kpis_revisao, pct)

FUSO = timezone(timedelta(hours=-3))
CASOS_REAIS = RAIZ / "docs" / "casos_de_teste.json"          # saídas reais do prever() (Samuel)
EXEMPLOS_PREVER = RAIZ / "docs" / "exemplos_prever.json"     # reserva: exemplos ilustrativos

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
TIMEOUT_S = 30  # cobre a busca nas normas + LLM (20 s) + queda para o template
TIMEOUT_CONSULTA_S = 5  # leituras rápidas (decisões)

# ==========================================
# 2. ESTILO (src/app/estilo.css)
# ==========================================
ESTILO = Path(__file__).with_name("estilo.css")


def carregar_estilo() -> None:
    """O CSS mora em estilo.css; aqui só é injetado na página."""
    st.markdown(f"<style>{ESTILO.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


carregar_estilo()


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
    if r.status_code in (422, 503):
        detalhe = _detalhe(r)
        if r.status_code == 422 and not isinstance(detalhe, str):
            return None, "A API recusou os dados enviados (formato inválido). Detalhe: " + r.text[:400]
        return None, detalhe or "Serviço indisponível na API."
    if not r.ok:
        return None, f"A API respondeu com erro {r.status_code}: {r.text[:300]}"
    try:
        dados = r.json()
    except json.JSONDecodeError:
        return None, "A resposta da API não pôde ser interpretada."
    if not isinstance(dados, dict):
        return None, "A API retornou uma estrutura diferente da esperada."
    return dados, None


def _detalhe(r) -> str | list | None:
    try:
        return r.json().get("detail")
    except (json.JSONDecodeError, AttributeError):
        return None


def consultar_api(rota: str, params: dict | None = None) -> tuple[list | dict | None, str | None]:
    """GET na API (leituras rápidas). Devolve (dados, erro)."""
    try:
        r = requests.get(f"{API_BASE}{rota}", params=params, timeout=TIMEOUT_CONSULTA_S)
    except requests.exceptions.RequestException:
        return None, f"Não foi possível conectar à API em {API_BASE}."
    if not r.ok:
        return None, str(_detalhe(r) or f"A API respondeu com erro {r.status_code}.")
    try:
        return r.json(), None
    except json.JSONDecodeError:
        return None, "A resposta da API não pôde ser interpretada."


def consultar_lista(rota: str, params: dict | None = None) -> tuple[list[dict], str | None]:
    """Como consultar_api, mas garante uma lista (vazia se a resposta vier em outro formato)."""
    dados, erro = consultar_api(rota, params)
    if erro is None and not isinstance(dados, list):
        return [], "A API devolveu um formato inesperado."
    return dados or [], erro


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


@st.cache_data(ttl=300, max_entries=8, show_spinner="Preparando a exportação...")
def csv_da_fila(anos, pais, faixa) -> bytes:
    """CSV da fila completa para os filtros escolhidos. Só roda quando o analista pede:
    com a carteira inteira são ~90 mil linhas (~10 MB)."""
    df, _, _ = dados_carteira()
    return cart.exportar_fila(cart.filtrar(df, anos=anos, pais=pais, faixa=faixa))


# ==========================================
# 5. BARRA DE NAVEGAÇÃO, HOME E FAIXA EXPLICATIVA
# ==========================================
analista_nav = esc(st.session_state.analista) or "não identificado"
md(f"""
    <div class="top-navbar">
        <a href="#home" class="nav-brand">{icone('balanca', 20)} AUDITOR DE PREÇO JUSTO</a>
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

md(f"""
    <div class="features-strip">
        <div class="features-grid">
            <div class="feature-item">
                <div class="feature-icon">{icone('grafico', 26)}</div>
                <div>
                    <div class="feature-title">Juro justo por fluxo de caixa</div>
                    <div class="feature-desc">Custo do dinheiro (Euribor da época), perda esperada ao longo do contrato e custos calibrados na carteira, com margem de incerteza.</div>
                </div>
            </div>
            <div class="feature-item">
                <div class="feature-icon">{icone('chip', 26)}</div>
                <div>
                    <div class="feature-title">Modelo de risco explicável</div>
                    <div class="feature-desc">XGBoost calibrado estima a probabilidade de default; os principais fatores de cada contrato aparecem com nomes legíveis.</div>
                </div>
            </div>
            <div class="feature-item">
                <div class="feature-icon">{icone('documento', 26)}</div>
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
        if status is not None and not status.get("banco_disponivel", False):
            md('<span class="ap-status"><i class="ap-dot" style="background:#e8a462"></i>'
               'Banco indisponível: as decisões ficam só nesta sessão até ele voltar.</span>')
    with col_analista:
        st.text_input("Analista responsável", key="analista", placeholder="Seu nome")

    aba_revisao, aba_carteira, aba_registro = st.tabs(
        ["REVISÃO DE CONTRATO", "AUDITORIA DA CARTEIRA", "REGISTRO DE DECISÕES"])


# ------------------------------------------
# 6.1 Formulário em etapas
# ------------------------------------------
ETAPAS = ("personal", "loan", "history")
CAMPOS_DA_ETAPA = {
    "personal": ("age", "gender", "country", "income_total"),
    "loan": ("loan_id", "amount", "interest", "loan_duration", "data_emprestimo"),
    "history": ("liabilities_total",),
}
ETAPA_DO_CAMPO = {campo: etapa for etapa, campos in CAMPOS_DA_ETAPA.items() for campo in campos}


def _desmarcar_revisao(step_name: str) -> None:
    st.session_state[f"audit_reviewed_{step_name}"] = False
    if f"_audit_review_widget_{step_name}" in st.session_state:
        st.session_state[f"_audit_review_widget_{step_name}"] = False


def _persist_audit_input(field_name: str) -> None:
    st.session_state[f"audit_{field_name}"] = st.session_state[f"_audit_widget_{field_name}"]
    # dado alterado depois de revisado → a etapa precisa ser revisada de novo
    _desmarcar_revisao(ETAPA_DO_CAMPO.get(field_name, "history"))


def etapa_revisada(step_name: str) -> bool:
    return bool(st.session_state.get(f"audit_reviewed_{step_name}"))


def etapa_liberada(step_name: str) -> bool:
    """Uma etapa só abre quando todas as anteriores estão marcadas como revisadas."""
    return all(etapa_revisada(e) for e in ETAPAS[:ETAPAS.index(step_name)])


def todas_revisadas() -> bool:
    return all(etapa_revisada(e) for e in ETAPAS)


def primeira_pendente() -> str:
    return next((e for e in ETAPAS if not etapa_revisada(e)), ETAPAS[-1])


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


def botao_proxima(step_name: str) -> None:
    """Atalho para a etapa seguinte; só funciona com a etapa atual marcada como revisada."""
    seguinte = ETAPAS[ETAPAS.index(step_name) + 1]
    rotulo = dict(STEP_CARDS)[seguinte]
    if st.button(f"Avançar para {rotulo}", key=f"audit_next_{step_name}", icon=":material/arrow_forward:",
                 disabled=not etapa_revisada(step_name)):
        st.session_state.audit_active_step = seguinte
        st.rerun()


STEP_CARDS = [("personal", "Dados pessoais"), ("loan", "Empréstimo"), ("history", "Dívidas & histórico")]
ICONES_ETAPA = {"personal": ":material/person:", "loan": ":material/payments:", "history": ":material/history:"}
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
    # Etapa aberta que deixou de estar liberada (ex.: desmarcou a revisão anterior) → volta
    # para a primeira etapa pendente. Voltar é sempre permitido; avançar, só revisando.
    if not etapa_liberada(st.session_state.audit_active_step):
        st.session_state.audit_active_step = primeira_pendente()

    with st.container(key="audit_steps"):
        for column, (step_key, step_label) in zip(st.columns(3, gap="small"), STEP_CARDS):
            with column:
                ativo = st.session_state.audit_active_step == step_key
                liberada = etapa_liberada(step_key)
                if not liberada:
                    icone_etapa = ":material/lock:"
                elif etapa_revisada(step_key):
                    icone_etapa = ":material/check_circle:"
                else:
                    icone_etapa = ICONES_ETAPA[step_key]
                if st.button(step_label, key=f"audit_select_{step_key}", disabled=not liberada, icon=icone_etapa,
                             type="primary" if ativo else "secondary",
                             help=None if liberada else "Marque “Confirmo que revisei” na etapa anterior para liberar."):
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
                botao_proxima("personal")

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
                botao_proxima("loan")

            else:
                audit_number("Total de dívidas em outras instituições (€)", "liabilities_total",
                             min_value=0.0, step=50.0, format="%.2f")
                st.markdown('<div class="audit-note">Histórico na plataforma, escolaridade, moradia e verificação '
                            'de renda seguem como “sem informação” nesta versão do formulário. O rating e a PD do '
                            'Bondora não são usados: entregariam o preço ao modelo.</div>', unsafe_allow_html=True)
                audit_review_checkbox("history")

            st.markdown("<div style='height:.35rem'></div>", unsafe_allow_html=True)
            liberado = todas_revisadas()
            if not liberado:
                faltam = [d["title"] for e, d in STEP_DETAILS.items() if not etapa_revisada(e)]
                md(f'<div class="audit-lock-note">{icone("cadeado", 14)} A auditoria libera depois das 3 confirmações. '
                   f'Falta revisar: {esc(", ".join(faltam))}.</div>')
            clicou = st.button("EXECUTAR AUDITORIA DE PREÇO", key="audit_execute", icon=":material/balance:", disabled=not liberado,
                               type="primary", use_container_width=True)
            clicou = clicou and liberado  # trava também no código, não só no botão

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
def registrar_decisao(resultado: dict, decisao: str, justificativa: str,
                      nova_taxa_pct: float | None) -> tuple[str, str]:
    """Grava a decisão no banco (POST /decisoes). Devolve (onde, mensagem):
    'banco' gravou · 'sessao' banco fora, guardada só nesta sessão · 'erro' recusada."""
    payload = {
        "requisicao_id": str(uuid4()),  # um por clique: o banco não grava o mesmo clique duas vezes
        "analista": st.session_state.analista.strip(),
        "decisao": decisao,
        "justificativa": justificativa.strip(),
        "taxa_proposta": nova_taxa_pct / 100 if (decisao == "revisar_preco" and nova_taxa_pct) else None,
        "resultado": resultado,  # a RESPOSTA do /prever: não carrega gênero nem idade
    }
    try:
        r = requests.post(f"{API_BASE}/decisoes", json=payload, timeout=TIMEOUT_CONSULTA_S)
    except requests.exceptions.RequestException:
        r = None
    if r is not None and r.status_code in (200, 201):
        return "banco", "Decisão gravada no banco."
    if r is not None and r.status_code == 422:
        return "erro", str(_detalhe(r) or "A API recusou a decisão.")
    parecer = resultado.get("parecer_ia") or {}
    st.session_state.decisoes.insert(0, {
        "registrada_em": datetime.now(FUSO).isoformat(timespec="seconds"),
        "contrato_id": resultado.get("contrato_id"),
        "origem": "só nesta sessão",
        "analista": payload["analista"],
        "decisao": decisao,
        "justificativa": payload["justificativa"],
        "taxa_proposta": payload["taxa_proposta"],
        "recomendacao_sistema": parecer.get("recomendacao"),
        "situacao_preco": resultado.get("situacao_preco"),
        "pd": resultado.get("pd"),
        "juro_cobrado": resultado.get("juro_cobrado"),
        "juro_justo": resultado.get("juro_justo"),
        "versao_modelo": resultado.get("versao_modelo"),
        "versao_parecer": parecer.get("versao_prompt"),
        "origem_parecer": parecer.get("origem"),
    })
    return "sessao", ("Banco indisponível: a decisão ficou só nesta sessão. "
                      "Exporte na aba Registro de decisões antes de fechar.")


def ultima_decisao(contrato_id: str) -> dict | None:
    dados, _ = consultar_lista("/decisoes", {"contrato_id": contrato_id, "limite": 1})
    if dados:
        return dados[0]
    da_sessao = [d for d in st.session_state.decisoes if d["contrato_id"] == contrato_id]
    return da_sessao[0] if da_sessao else None


def bloco_decisao(resultado: dict) -> None:
    cid = resultado.get("contrato_id", "?")
    parecer = resultado.get("parecer_ia") or {}
    rec = RECOMENDACOES.get(parecer.get("recomendacao"), "—")
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
                    if not (justificativa or "").strip():
                        st.warning("Escreva a justificativa antes de registrar a decisão.")
                    elif not st.session_state.analista.strip():
                        st.warning("Informe o nome do analista responsável no topo da seção.")
                    else:
                        onde, mensagem = registrar_decisao(resultado, chave, justificativa, nova)
                        {"banco": st.success, "sessao": st.warning, "erro": st.error}[onde](
                            f"{rotulo}: {mensagem}" if onde != "erro" else mensagem)
        d = ultima_decisao(cid)
        if d:
            quando = str(d.get("registrada_em", ""))[:16].replace("T", " ")
            st.caption(f"Última decisão neste contrato: {RECOMENDACOES.get(d['decisao'], d['decisao'])} "
                       f"por {d['analista']} em {quando}.")


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


def tabela_fila(linhas: list[dict], decididos: dict[str, str] | None = None) -> str:
    """decididos = {contrato_id: decisão atual} (vw_decisao_atual)."""
    decididos = decididos or {}

    def decisao(cid):
        d = decididos.get(cid)
        return badge(RECOMENDACOES.get(d, d), "#8cc7a1", "rgba(140,199,161,.10)") if d else '<span class="ap-muted">pendente</span>'
    corpo = "".join(
        f"<tr><td><b>{esc(x['contrato_id'])}</b></td><td>{esc(x.get('faixa') or '—')}</td>"
        f"<td>{pct(x.get('juro_cobrado'))}</td><td>{pct(x.get('juro_justo'))}</td>"
        f"<td>{badge_situacao(x.get('situacao_preco'))}</td>"
        f"<td>{'' if x.get('distancia_pp') is None else str(x['distancia_pp']).replace('.', ',') + ' pp'}</td>"
        f"<td>{decisao(x['contrato_id'])}</td></tr>"
        for x in linhas)
    return compactar(f"""<table class="ap-table"><thead><tr><th>Contrato</th><th>Faixa</th><th>Juro cobrado</th>
        <th>Juro justo</th><th>Situação</th><th>Além da margem</th><th>Decisão atual</th></tr></thead>
        <tbody>{corpo}</tbody></table>""")


def decisoes_atuais() -> dict[str, str]:
    dados, _ = consultar_lista("/decisoes/atuais")
    return {d["contrato_id"]: d["decisao"] for d in dados}


def abrir_da_carteira(linha: dict) -> None:
    resultado = {
        "contrato_id": str(linha["contrato_id"]),
        "versao_modelo": str(linha.get("versao_modelo") or "carteira"),
        "pd": linha.get("pd"), "faixa": linha.get("faixa"),
        "juro_cobrado": linha["juro_cobrado"], "juro_justo": linha.get("juro_justo"),
        "juro_justo_min": linha.get("juro_justo_min"), "juro_justo_max": linha.get("juro_justo_max"),
        "situacao_preco": linha["situacao_preco"], "motivos": [],
        "alerta_dados": linha["situacao_preco"] == "revisao_manual",
        "juro_pares_mediana": linha.get("juro_pares_mediana"),
        "pd_ic95": ([linha["pd_ic95_min"], linha["pd_ic95_max"]]
                    if linha.get("pd_ic95_min") is not None and linha.get("pd_ic95_max") is not None else None),
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
                chave_export = (filtros["anos"], filtros["pais"], filtros["faixa"])
                if st.button("Preparar exportação (CSV)", key="preparar_export"):
                    st.session_state.export_fila = chave_export
                if st.session_state.get("export_fila") == chave_export:  # filtros mudaram → pedir de novo
                    st.download_button("Baixar CSV", csv_da_fila(*chave_export),
                                       file_name="contratos_para_revisao.csv", mime="text/csv", key="baixar_fila")
            registros = json.loads(fila.head(50).to_json(orient="records"))  # tipos nativos, NaN → null
            md(tabela_fila(registros, decisoes_atuais()))
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
COLUNAS_REGISTRO = {
    "registrada_em": "Registrada em", "analista": "Analista", "contrato_id": "Contrato", "origem": "Origem",
    "decisao": "Decisão", "recomendacao_sistema": "Recomendação do sistema", "situacao_preco": "Situação",
    "juro_cobrado": "Juro cobrado", "juro_justo": "Juro justo", "taxa_proposta": "Nova taxa",
    "justificativa": "Justificativa", "origem_parecer": "Parecer", "versao_modelo": "Modelo",
}

with aba_registro:
    do_banco, erro_banco = consultar_lista("/decisoes", {"limite": 1000})
    decisoes = (st.session_state.decisoes or []) + do_banco
    md("""<div class="audit-eyebrow" style="margin-top:1.2rem">Registro de decisões</div>
        <div class="ap-title">Quem decidiu, o quê e por quê</div>
        <div class="ap-meta">Cada decisão fica gravada no banco com o parecer, a recomendação do sistema e a
        justificativa (direito de revisão, LGPD art. 20). O registro é só de inclusão: para corrigir, registre uma
        nova decisão; a mais recente vale.</div>""")
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    if erro_banco:
        st.warning(f"Registro do banco indisponível ({erro_banco}). Mostrando só as decisões desta sessão.")
    if st.session_state.decisoes:
        st.caption(f"{len(st.session_state.decisoes)} decisão(ões) desta sessão não foram gravadas no banco "
                   "(origem “só nesta sessão”). Exporte antes de fechar.")
    if not decisoes:
        st.caption("Nenhuma decisão registrada ainda.")
    else:
        tabela = pandas.DataFrame(decisoes)
        divergentes = int((tabela["decisao"] != tabela["recomendacao_sistema"]).sum())
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
        exibir = tabela.reindex(columns=list(COLUNAS_REGISTRO)).assign(
            registrada_em=tabela["registrada_em"].astype(str).str[:16].str.replace("T", " "),
            decisao=tabela["decisao"].map(RECOMENDACOES),
            recomendacao_sistema=tabela["recomendacao_sistema"].map(RECOMENDACOES),
            situacao_preco=tabela["situacao_preco"].map(lambda v: SITUACOES.get(v, {}).get("rotulo", v)),
            **{c: tabela[c].map(lambda v: pct(v) if v is not None and pandas.notna(v) else "—")
               for c in ("juro_cobrado", "juro_justo", "taxa_proposta") if c in tabela},
        ).rename(columns=COLUNAS_REGISTRO)
        st.dataframe(exibir, use_container_width=True, hide_index=True)
        col_csv, col_json, _ = st.columns([1, 1, 2], gap="small")
        with col_csv:
            st.download_button("Exportar CSV", tabela.to_csv(index=False).encode("utf-8"),
                               file_name="decisoes_analista.csv", mime="text/csv")
        with col_json:
            st.download_button("Exportar JSON", json.dumps(decisoes, ensure_ascii=False, indent=2, default=str).encode("utf-8"),
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
