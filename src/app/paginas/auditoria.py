"""Página Auditoria: equidade agregada (lote) e teste de invariância
(POST /contracts/{id}/invariance).
"""

import streamlit as st

from src.app.components import (
    EMPTY_FAIRNESS, esc, html_fairness_chart, html_invariance, html_invariance_ring, info_tip)
from src.app.nucleo import md, portfolio_overview, post_api


def render_audit_page() -> None:
    _, area, _ = st.columns([0.35, 5, 0.35])
    with area:
        data, _ = portfolio_overview()
        fairness = (data or {}).get("equidade")
        md(f"""<div class="audit-eyebrow">Auditoria</div>
            <div class="ap-title">O preço trata grupos iguais de forma igual?</div>
            <div class="ap-meta">Duas perguntas diferentes, com dois testes. <b>O preço cobrado trata grupos de forma
            diferente a risco igual?</b> A equidade agregada mede isso nos preços do Bondora (é onde aparece
            discriminação, inclusive indireta). <b>O nosso modelo usa gênero ou idade?</b> O teste de invariância
            mostra que não, em um contrato e em lote, e passa a acusar se alguém um dia colocar esses dados no
            modelo.</div>""")
        col_fair, col_test = st.columns(2, gap="medium")  # equidade à esquerda, teste à direita
        with col_fair, st.container(border=True, key="audit_fairness"):
            md(f"""{info_tip("equidade")}<div class="ap-card-title">Equidade agregada</div>
                <div class="ap-card-sub">O preço cobrado pelo Bondora trata grupos diferentes de forma diferente, a
                risco igual? Cada linha compara dois grupos de clientes parecidos (mesmo risco, país, ano, valor e
                prazo) e mede quantos pontos percentuais de juro um paga a mais ou a menos do que o outro, além do
                que o risco justifica. O ponto é a diferença; a barra, a faixa de confiança de 95%.</div>
                {html_fairness_chart(fairness or EMPTY_FAIRNESS)}
                <div class="ap-foot">Números do lote (src/modelos/equidade.py). Gênero e idade servem só para esta
                auditoria: não aparecem na análise de um contrato.</div>""")
        with col_test:
            render_invariance((data or {}).get("invariancia_lote"))


def run_invariance() -> None:
    cid = (st.session_state.get("invariance_id") or "").strip()
    if not cid:
        st.session_state.invariance = {"erro": "Digite o ID de um contrato."}
        return
    result, error_msg = post_api(f"/contracts/{cid}/invariance", {})
    st.session_state.invariance = {"contrato_id": cid, "resultado": result, "erro": error_msg}


def render_invariance(summary: dict | None = None) -> None:
    """Teste de invariância: o modelo dá o mesmo resultado com gênero e idade trocados?"""
    if "invariance_id" not in st.session_state:  # começa com o contrato aberto na Análise, se houver
        st.session_state.invariance_id = (st.session_state.audit_last_result or {}).get("contrato_id", "")
    with st.container(border=True, key="audit_invariance"):
        md(f"""{info_tip("invariancia")}<div class="ap-card-title">Teste de invariância</div>
            <div class="ap-card-sub">O nosso modelo usa gênero ou idade? Roda o modelo com os dados reais e com os
            dois trocados: o resultado tem de ser igual. <b>Não prova que o preço é justo</b>; isso é a equidade,
            ao lado.</div>""")
        md(html_invariance_ring(summary))
        md('<div class="ap-sec">Teste agora, em um contrato</div>')
        col_id, col_run = st.columns([3, 1], vertical_alignment="bottom")
        with col_id:
            st.text_input("ID do contrato", key="invariance_id", placeholder="cole o ID de um contrato da base")
        with col_run:
            st.button("Rodar o teste", key="run_invariance", type="primary", icon=":material/balance:",
                      on_click=run_invariance, use_container_width=True)
        state = st.session_state.invariance
        if state.get("erro"):
            st.error(f"O teste não rodou: {state['erro']}")
        elif state.get("resultado"):
            result = state["resultado"]
            md(f'<div class="ap-card-sub" style="margin:.4rem 0">Contrato {esc(result["contrato_id"])} · modelo '
               f'{esc(result["procedencia"].get("versao_modelo"))} · as 21 variáveis do modelo '
               f'{"não incluem gênero nem idade" if result.get("modelo_sem_atributos_protegidos") else "INCLUEM gênero ou idade"}</div>')
            md(html_invariance(result))
