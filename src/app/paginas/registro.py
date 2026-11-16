"""Página Registro: histórico de decisões gravadas no banco (GET /decisions), rascunhos
pendentes e exportação CSV/JSON.
"""
import json

import pandas
import streamlit as st

from src.app.components import pct, RECOMMENDATIONS, SITUATIONS
from src.app.nucleo import get_list, md
from src.app.paginas.analise import retry_pending


RECORD_COLUMNS = {
    "registrada_em": "Registrada em", "analista": "Analista", "contrato_id": "Contrato", "origem": "Origem",
    "decisao": "Decisão", "recomendacao_sistema": "Recomendação do sistema", "situacao_preco": "Situação",
    "juro_cobrado": "Juro cobrado", "juro_justo": "Juro justo", "taxa_proposta": "Nova taxa",
    "justificativa": "Justificativa", "origem_parecer": "Parecer", "versao_modelo": "Modelo",
}


def render_records() -> None:
    decisions, database_error = get_list("/decisions", {"limit": 1000})  # só o que está no banco
    col_title, col_export = st.columns([3, 1.1], vertical_alignment="bottom")
    with col_title:
        md("""<div class="audit-eyebrow">Registro de decisões</div>
            <div class="ap-title">Quem decidiu, o quê e por quê</div>""")
    with col_export, st.container(key="records_export", horizontal=True):  # no canto direito, ao lado do título
        if decisions:
            st.download_button("CSV", pandas.DataFrame(decisions).to_csv(index=False).encode("utf-8"),
                               file_name="decisoes_analista.csv", mime="text/csv", icon=":material/download:")
            st.download_button("JSON", json.dumps(decisions, ensure_ascii=False, indent=2, default=str).encode("utf-8"),
                               file_name="decisoes_analista.json", mime="application/json", icon=":material/download:")
    md("""<div class="ap-meta">Cada decisão fica gravada no banco com o parecer, a recomendação do sistema e a
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


def render_records_page() -> None:
    _, area, _ = st.columns([0.35, 5, 0.35])
    with area:
        render_records()
