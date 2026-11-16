"""Painel do analista — Auditoria de Crédito (Streamlit). Ponto de entrada: streamlit run src/app/main.py

Este arquivo só monta a moldura: configuração da página, estilo, memória da sessão, menu do topo e qual
página mostrar. Cada página fica no seu arquivo em src/app/paginas/; o que todas usam (chamadas à API,
navegação, md()) fica em src/app/nucleo.py; os blocos de HTML, em src/app/components/; o visual, em
src/app/styles/.

O painel só EXIBE: todos os números vêm da API, seja o prever() rodado na hora, seja o lote da
carteira (Início, lista e plano B). O parecer vem da GenAI, ou do template de reserva.
"""
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:  # "streamlit run src/app/main.py" não põe a raiz no path
    sys.path.insert(0, str(ROOT))

from src.app.components import line_icon  # noqa: E402
from src.app.nucleo import PAGES, go_to, md  # noqa: E402
from src.app.paginas.analise import render_analysis_page  # noqa: E402
from src.app.paginas.auditoria import render_audit_page  # noqa: E402
from src.app.paginas.contratos import render_contracts_page  # noqa: E402
from src.app.paginas.inicio import render_home  # noqa: E402
from src.app.paginas.laboratorio import render_lab_page  # noqa: E402
from src.app.paginas.registro import render_records_page  # noqa: E402
from src.app.paginas.sobre import render_about_page  # noqa: E402

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Auditoria de Crédito",
    page_icon=":material/balance:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ==========================================
# 2. ESTILO (src/app/styles/, um arquivo por parte, carregados em ordem: 01_base, 02_menu...)
# ==========================================
STYLES_DIR = Path(__file__).with_name("styles")


def load_style() -> None:
    """Junta os .css da pasta styles/ na ordem do número do nome e injeta na página."""
    css = "\n".join(f.read_text(encoding="utf-8") for f in sorted(STYLES_DIR.glob("*.css")))
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


load_style()

# ==========================================
# 3. MEMÓRIA DA SESSÃO (sobrevive aos cliques; cada aba do navegador tem a sua)
# ==========================================
st.session_state.setdefault("audit_last_result", None)  # contrato aberto na Análise (saída do prever())
st.session_state.setdefault("audit_last_context", {})   # origem, dados do contrato, análise completa da API
st.session_state.setdefault("history", [])   # contratos abertos nesta sessão
st.session_state.setdefault("pending_decisions", [])  # rascunhos NÃO registrados (banco fora); não são histórico
st.session_state.setdefault("analista", "")
st.session_state.setdefault("page", "home")
st.session_state.setdefault("invariance", {})  # último teste de invariância: contrato, resultado, erro
st.session_state.setdefault("outcome_open", None)  # contrato com o Resultado observado aberto
st.session_state.setdefault("lab", {})  # Laboratório: contrato, original (campos e limites), último cenário, erro

# ==========================================
# 4. MENU DO TOPO
# ==========================================
with st.container(key="top_nav"):
    col_brand, col_links, col_analyst = st.columns([1.55, 5.6, 1.15], gap="small", vertical_alignment="center")
    with col_brand:
        md(f'<div class="nav-brand">{line_icon("balanca", 20)} AUDITORIA DE CRÉDITO</div>')
    with col_links:
        for column_, (page_key, page_label) in zip(st.columns(len(PAGES), gap="small"), PAGES.items()):
            with column_:
                st.button(page_label, key=f"nav_{page_key}", on_click=go_to, args=(page_key,),
                          type="primary" if st.session_state.page == page_key else "secondary",
                          use_container_width=True)
    with col_analyst:
        st.text_input("Analista", key="analista", placeholder="Seu nome", label_visibility="collapsed")

# ==========================================
# 5. MOSTRA A PÁGINA ESCOLHIDA (cada uma em src/app/paginas/)
# ==========================================
{"home": render_home, "contratos": render_contracts_page, "analise": render_analysis_page,
 "lab": render_lab_page, "auditoria": render_audit_page, "registro": render_records_page,
 "sobre": render_about_page}[st.session_state.page]()
