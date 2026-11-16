"""Página Contratos: busca por ID, filtro de situação e lista do lote (GET /contracts...).
Abrir um contrato chama a Análise ao vivo (GET /contracts/{id}/analysis).
"""

import streamlit as st

from src.app.components import badge, COUNTRIES, esc, eur, pct, RECOMMENDATIONS, situation_badge
from src.app.nucleo import (
    api_status_line, contract_listing, get_api, get_list, go_to, listing_csv, md, store_result, TIMEOUT_S)


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
