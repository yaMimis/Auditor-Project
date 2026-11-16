"""Blocos da página Laboratório: original × cenário e o efeito de cada campo trocado.
"""
from __future__ import annotations

from src.app.components.base import compact, esc, eur, pct, situation_badge
from src.app.components.analise import readable_value

__all__ = ["html_scenario_table", "EFFECT_TEXT", "html_scenario_effects"]


def _margin(r: dict) -> str:
    if r.get("juro_justo_min") is None:
        return "—"
    return f'{pct(r["juro_justo_min"])} a {pct(r["juro_justo_max"])}'


def html_scenario_table(original: dict, scenario: dict, installment_before=None, installment_after=None) -> str:
    """Original × recalculado, linha a linha; o que mudou fica destacado."""
    rows = [
        ("Chance de inadimplência", pct(original.get("pd")), pct(scenario.get("pd"))),
        ("Faixa de risco", original.get("faixa") or "—", scenario.get("faixa") or "—"),
        ("Juro justo", pct(original.get("juro_justo")), pct(scenario.get("juro_justo"))),
        ("Margem do juro justo", _margin(original), _margin(scenario)),
        ("Juro cobrado (a.a. nominal)", pct(original.get("juro_cobrado"), 2), pct(scenario.get("juro_cobrado"), 2)),
        ("Parcela mensal", eur(installment_before, 2), eur(installment_after, 2)),
    ]
    body = "".join(
        f'<tr><td>{esc(name)}</td><td class="ap-mono">{esc(before)}</td>'
        f'<td class="ap-mono{" ap-changed" if before != after else ""}">{esc(after)}</td></tr>'
        for name, before, after in rows)
    situation_changed = original.get("situacao_preco") != scenario.get("situacao_preco")
    body += (f'<tr><td>Situação do preço</td><td>{situation_badge(original.get("situacao_preco"))}</td>'
             f'<td class="{"ap-changed" if situation_changed else ""}">{situation_badge(scenario.get("situacao_preco"))}'
             f'</td></tr>')
    return compact(f"""<table class="ap-table ap-lab-table"><thead><tr><th></th><th>Original</th>
        <th>Recalculado</th></tr></thead><tbody>{body}</tbody></table>""")


EFFECT_TEXT = {"aumenta": ("aumenta o risco", "#d9825b"), "reduz": ("reduz o risco", "#7fa7d9"),
               "neutro": ("quase não muda o risco", "#9aa5b5"),
               "revisao_manual": ("leva o contrato para fora do que o modelo conhece", "#9aa5b5"),
               "sem_pd": ("sem risco calculado para comparar (revisão manual)", "#9aa5b5")}


def _field_value(field: str, value) -> str:
    if value is None:
        return "sem informação"
    if field in ("renda_total", "passivos_total"):
        return f"{eur(float(value))}/mês"
    if field == "valor_concedido":
        return eur(float(value))
    if field == "prazo_meses":
        return f"{int(value)} meses"
    try:
        return readable_value(field, value) or "sem informação"
    except (TypeError, ValueError):
        return str(value)


def html_scenario_effects(effects: list[dict]) -> str:
    """'O que mudou o risco': cada campo trocado sozinho, com o modelo rodado de novo."""
    if not effects:
        return '<div class="ap-card-sub">Nenhuma variável do modelo foi trocada (o juro cobrado não é variável do modelo).</div>'
    items = []
    for e in effects:
        text_, color = EFFECT_TEXT.get(e.get("efeito"), EFFECT_TEXT["neutro"])
        change = f'{_field_value(e["campo"], e.get("valor_original"))} → {_field_value(e["campo"], e.get("valor_novo"))}'
        detail = (f' · risco {pct(e.get("pd_original"))} → {pct(e.get("pd_so_este_campo"))}'
                  if e.get("pd_so_este_campo") is not None and e.get("pd_original") is not None else "")
        items.append(f'<li><b>{esc(e.get("rotulo"))}</b>: {esc(change)} '
                     f'<span style="color:{color}">{esc(text_)}</span>{esc(detail)}</li>')
    return compact(f'<ul class="ap-lab-effects">{"".join(items)}</ul>')
