"""Página Análise: o contrato aberto (cartões, régua, dados, precificação, resultado observado,
parecer, motivos) e a decisão do analista (POST /decisions).
"""
from datetime import datetime
from uuid import uuid4

import requests
import streamlit as st

from src.app.components import (
    COUNTRIES, esc, eur, html_considered_data, html_opinion, html_outcome, html_pricing, html_provenance,
    html_rate_bar, html_reasons, info_tip, pct, RECOMMENDATIONS, review_kpis, situation_badge,
    UNCERTAINTY, uncertainty_text)
from src.app.nucleo import (
    API_BASE, api_status_line, BATCH_FILE, BR_TIMEZONE, api_error_detail, get_list, go_to, md, QUERY_TIMEOUT_S)
from src.app.paginas.laboratorio import open_lab


def post_decision(payload: dict) -> tuple[str, str]:
    """POST /decisions. Devolve (situação, mensagem): 'gravada' · 'pendente' (banco fora) · 'recusada'."""
    try:
        r = requests.post(f"{API_BASE}/decisions", json=payload, timeout=QUERY_TIMEOUT_S)
    except requests.exceptions.RequestException:
        return "pendente", "a API não respondeu"
    if r.status_code in (200, 201):
        return "gravada", "Decisão registrada no histórico."
    if r.status_code == 422:
        return "recusada", str(api_error_detail(r) or "A API recusou a decisão.")
    return "pendente", str(api_error_detail(r) or f"erro {r.status_code}")


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
            md("""<div class="ap-alert">Revisão manual: o sistema não calculou o risco nem o juro justo. Confira os dados
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
        buttons = st.columns(3, gap="medium")
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
                ("Incerteza do risco", uncertainty_text(prov.get("incerteza"), prov.get("n_reamostras_bootstrap"))),
                ("Arquivo do modelo", " · ".join(x for x in (prov.get("pacote_arquivo"),
                                                             f'hash {prov["pacote_hash"]}' if prov.get("pacote_hash") else None,
                                                             f'de {prov["pacote_data"]}' if prov.get("pacote_data") else None) if x))]
    return [("Versão do modelo", r.get("versao_modelo") or "—"),
            ("Por que o lote", prov.get("motivo_lote") or "a API não calculou este contrato agora"),
            ("Data do cálculo", "lote da carteira (calculado antes)"),
            ("Origem dos dados", f"lote ({BATCH_FILE}), servido pela API"),
            ("Dentro do que o modelo conhece?", "não: revisão manual" if manual else "sim"),
            ("Incerteza do risco", UNCERTAINTY["nao_calculada"] if manual
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
                     f'<span class="ap-chip">No lote o risco era {pct(batch_pd, 1)}: o modelo ou os dados mudaram</span>')
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

    with st.expander("Procedência: de onde vêm estes números (modelo, data do cálculo, origem dos dados)"):
        md(html_provenance(provenance_rows(r, ctx)))

    if situation == "revisao_manual":
        md("""<div class="ap-alert"><b>Revisão manual: o contrato está fora do que o modelo conhece.</b> O prever()
            não calcula risco nem juro justo para dados fora da faixa vista no treino (país não visto, ou valor, prazo
            ou renda vazios ou extremos). O analista decide sem a comparação de preço.</div>""")
    for column_, card in zip(st.columns(4, gap="medium"), review_kpis(r)):
        with column_:
            md(card)

    if situation != "revisao_manual":
        md(f"""<div class="ap-card">{info_tip("regua")}<div class="ap-card-title">Juro cobrado × juro justo</div>
            <div class="ap-card-sub">O juro justo é o juro que paga o risco deste cliente: o custo do dinheiro na época,
            a perda esperada com inadimplência e os custos da operação. A faixa dourada é a margem de incerteza.</div>
            {html_rate_bar(r)}</div>""")
    # Dados do contrato (esquerda) e Precificação (direita); o botão do Resultado observado fica embaixo da Precificação.
    if situation != "revisao_manual":
        col_data, col_pricing = st.columns(2, gap="medium")
        with col_data:
            contract_data_block(analysis)
        with col_pricing, st.container(key="pricing_area"):  # tabelas empilhadas na meia largura (styles/)
            source = "parâmetros devolvidos pelo prever()" if analysis.get("precificacao") else "valores do lote"
            md(f"""<div class="ap-card ap-card-tight">{info_tip("precificacao")}
                <div class="ap-card-title">Precificação: como o juro justo foi calculado</div>
                <div class="ap-card-sub">{source}</div>
                {html_pricing(analysis.get("precificacao"), r, country)}</div>""")
            outcome_block(analysis, ctx, live)
    else:
        contract_data_block(analysis)
        outcome_block(analysis, ctx, live)

    col_opinion, col_reasons = st.columns([1.55, 1], gap="medium")  # parecer à esquerda, motivos à direita
    with col_opinion:
        md(f"""<div class="ap-card">{info_tip("parecer")}<div class="ap-seal">Simulação normativa pela lei brasileira ·
            os dados são europeus; a leitura jurídica é hipotética.</div>{html_opinion(r.get("parecer_ia"))}</div>""")

    with col_reasons:
        empty = ("Os motivos vêm do modelo calculado na hora; o lote não os guarda." if not live
                 else "Sem motivos para este contrato.")
        md(f"""<div class="ap-card">{info_tip("motivos")}<div class="ap-card-title">O que mais pesou no risco</div>
            <div class="ap-card-sub">Quanto cada dado empurrou o risco para cima ou para baixo (método SHAP), com o
            valor deste contrato. Mostra o que pesou na previsão, não causa e efeito. Gênero e idade não entram no modelo. O modelo também considera o mercado do
            contrato (país): ele não aparece nesta lista, por regra do projeto, e os pesos foram calculados sem ele.</div>
            {html_reasons(r.get("motivos") or [], empty)}</div>""")

    lab_invite(r, ctx)
    st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)
    decision_block(r)


def contract_data_block(analysis: dict) -> None:
    """As variáveis que o modelo usou, sempre abertas, à esquerda da Precificação."""
    variables = analysis.get("dados_considerados") or []
    if variables:
        given = sum(v.get("origem") == "fornecida" for v in variables)
        with st.container(key="data_area"):  # tabelas empilhadas na meia largura (styles/)
            md(f"""<div class="ap-card">{info_tip("dados")}<div class="ap-card-title">Dados direto do contrato</div>
                <div class="ap-card-sub">{len(variables)} variáveis usadas pelo modelo: {given} fornecidas e
                {len(variables) - given} calculadas a partir delas.</div>{html_considered_data(variables)}</div>""")


def toggle_outcome(contract_id) -> None:
    shown = st.session_state.outcome_open
    st.session_state.outcome_open = None if shown == contract_id else contract_id


def outcome_block(analysis: dict, ctx: dict, live: bool) -> None:
    """Botão logo abaixo de Dados e Precificação: abre o Resultado observado ali embaixo (fecha ao trocar de contrato)."""
    contract_id = (analysis.get("resultado") or {}).get("contrato_id")
    is_open = st.session_state.get("outcome_open") == contract_id
    st.button("Ocultar resultado observado" if is_open else "Ver resultado observado: o que aconteceu com o contrato",
              key="toggle_outcome", type="primary", icon=":material/visibility_off:" if is_open else ":material/history:",
              on_click=toggle_outcome, args=(contract_id,))
    if is_open:
        md(f"""<div class="ap-card ap-card-tight">{info_tip("resultado")}<div class="ap-card-title">Resultado observado</div>
            <div class="ap-card-sub">Só para contratos encerrados: o que aconteceu de verdade depois da concessão.</div>
            {html_outcome(analysis.get("resultado_observado"), ctx.get("lote") if not live else None,
                          analysis.get("motivo_sem_desfecho"))}</div>""")


def lab_invite(r: dict, ctx: dict) -> None:
    """Fim da Análise, antes da decisão: convite para testar outros valores no Laboratório."""
    live = ctx.get("fonte") == "ao_vivo"
    with st.container(border=True):
        col_text, col_button = st.columns([3, 1], vertical_alignment="center")
        with col_text:
            md("""<div class="ap-card-title">E se o contrato fosse diferente?</div>
                <div class="ap-card-sub">Teste outro prazo, valor, renda ou juro cobrado: o modelo recalcula e mostra o
                que mudou o risco. Nada é gravado; uma taxa testada pode virar a proposta da decisão abaixo.</div>""")
        with col_button, st.container(key="lab_button_area"):  # alinhado à direita pelo styles/
            st.button("Abrir no Laboratório", key="open_lab", type="primary", icon=":material/science:", on_click=open_lab,
                      args=(r.get("contrato_id"),), disabled=not live,
                      help=None if live else "O Laboratório recalcula com o modelo ao vivo: precisa do banco.")


def render_analysis_page() -> None:
    _, area, _ = st.columns([0.35, 5, 0.35])
    with area:
        api_status_line()
        result, context = st.session_state.audit_last_result, st.session_state.audit_last_context
        if not result:
            md("""<div class="ap-card"><div class="ap-card-title">Nenhum contrato aberto</div>
                <div class="ap-card-sub">Escolha um contrato na página Contratos para abri-lo aqui.</div></div>""")
            st.button("Ir para Contratos", key="go_contracts", icon=":material/arrow_back:",
                      on_click=go_to, args=("contratos",))
            return
        st.button("Voltar para a lista", key="back_to_contracts", icon=":material/arrow_back:",
                  on_click=go_to, args=("contratos",))
        render_analysis(result, context)
