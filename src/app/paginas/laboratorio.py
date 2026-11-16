"""Página Laboratório: o mesmo contrato com outros valores, recalculado pelo modelo
(POST /contracts/{id}/scenario). Nada é gravado.
"""
from datetime import datetime

import streamlit as st

from src.app.components import (
    esc, html_scenario_effects, html_scenario_table, readable_value, uncertainty_text)
from src.app.nucleo import api_status_line, BR_TIMEZONE, go_to, md, post_api


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
    note = {"treino": "Limite: faixa vista no treino do modelo (0,5% a 99,5%).",
            "provisorio": "Limite provisório (ainda sem a faixa vista no treino)."}.get(field["limite"])
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
            st.button("Ir para Contratos", key="lab_go_contracts", icon=":material/arrow_back:",
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
