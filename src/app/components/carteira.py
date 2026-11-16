"""Blocos da página Início: situação do preço por faixa de risco.
"""
from __future__ import annotations

from src.app.components.base import compact, esc, _num, pct, SITUATIONS

__all__ = ["html_band_bars"]


def html_band_bars(table: list[dict]) -> str:
    """tabela = [{"faixa": "A", "abaixo_do_justo": 0.1, "dentro_da_margem": 0.7, "acima_do_justo": 0.2, "n": 120}]"""
    order = ["abaixo_do_justo", "dentro_da_margem", "acima_do_justo"]
    rows = []
    for row in table:
        segments = "".join(
            f'<div title="{SITUATIONS[s]["rotulo"]}: {pct(row.get(s, 0))}" '
            f'style="width:{row.get(s, 0) * 100}%;background:{SITUATIONS[s]["cor"]}"></div>'
            for s in order)
        rows.append(f"""
            <div class="ap-stack-row">
                <div class="ap-stack-label">Faixa {esc(row["faixa"])}</div>
                <div class="ap-stack">{segments}</div>
                <div class="ap-stack-n">{_num(row.get("n", 0), 0)}</div>
            </div>""")
    legend = "".join(f'<span><i style="background:{SITUATIONS[s]["cor"]}"></i>{SITUATIONS[s]["rotulo"]}</span>'
                      for s in order)
    return compact("".join(rows) + f'<div class="ap-legend">{legend}</div>')
