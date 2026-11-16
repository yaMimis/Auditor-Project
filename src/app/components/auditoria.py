"""Blocos da página Auditoria: equidade (gráfico, leitura em português, tabela) e teste de invariância.
"""
from __future__ import annotations

from src.app.components.base import badge, compact, esc, _num, pct, pp, situation_badge
from src.app.components.laboratorio import _margin

__all__ = ["fairness_reading", "EMPTY_FAIRNESS", "fairness_sentence", "html_fairness_chart",
           "html_invariance_ring", "html_invariance", "html_invariance_summary", "html_fairness_table"]


def fairness_reading(ci_min, ci_max) -> tuple[str, str, str]:
    """IC 95% que cruza o zero = sem indício; que não cruza = indício a investigar."""
    if ci_min is None or ci_max is None:
        return "Aguardando análise", "#9aa5b5", "rgba(154,165,181,.10)"
    if ci_min <= 0 <= ci_max:
        return "Sem indício", "#8cc7a1", "rgba(140,199,161,.10)"
    return "Indício · investigar", "#e8a462", "rgba(232,164,98,.10)"


# Linhas mostradas quando o lote ainda não tem equidade.json (mesmo layout do protótipo).
EMPTY_FAIRNESS = [
    {"atributo": "Gênero", "comparacao": "feminino × masculino (dentro do país)"},
    {"atributo": "Idade", "comparacao": "18–25 × 35–44 anos"},
]


def _fairness_groups(e: dict) -> tuple[str, str]:
    """'feminino × masculino (dentro do país)' -> ('As mulheres', 'os homens'); idade -> ('Clientes de 18–25 anos', ...)."""
    parts = [p.strip() for p in str(e.get("comparacao") or "").split("(")[0].split("×")]
    if len(parts) != 2:
        return "O primeiro grupo", "o segundo"
    a, b = parts
    if (e.get("atributo") or "").lower().startswith("g"):
        names = {"feminino": ("As mulheres", "as mulheres"), "masculino": ("Os homens", "os homens")}
        return names.get(a, (a, a))[0], names.get(b, (b, b))[1]
    if (e.get("atributo") or "").lower().startswith("i"):
        a = a if a.endswith("anos") else f"{a} anos"
        b = b if b.endswith("anos") else f"{b} anos"
        return f"Clientes de {a}", f"os de {b}"
    return a, b


def fairness_sentence(e: dict) -> str:
    """Leitura da equidade em português: quanto um grupo paga a mais, com que confiança e o que isso quer dizer."""
    d, lo, hi = e.get("diferenca_pp"), e.get("ic95_min"), e.get("ic95_max")
    if d is None or lo is None or hi is None:
        return "Aguardando o cálculo da equidade no lote."
    first, second = _fairness_groups(e)
    direction = "a mais" if d > 0 else "a menos"
    text_ = (f"{first} pagam, em média, <b>{_num(abs(d), 1)} p.p. {direction}</b> de juro do que {second}, "
             "comparando contratos com o mesmo risco, país, ano, valor e prazo. ")
    if lo <= 0 <= hi:
        text_ += (f"Com 95% de confiança, a diferença real fica entre {pp(lo)} e {pp(hi)}: como essa faixa inclui o "
                  "zero, <b>não dá para afirmar que exista diferença</b>.")
    else:
        text_ += (f"Com 95% de confiança, a diferença real fica entre {pp(lo)} e {pp(hi)}: a faixa inteira fica "
                  f"{'acima' if lo > 0 else 'abaixo'} de zero, então <b>dificilmente é acaso</b>. É um indício a "
                  "investigar, não prova de discriminação: pode haver fatores que a comparação não controla.")
    if (e.get("atributo") or "").lower().startswith("g"):
        text_ += " Cautela: no Bondora, o código de gênero de 2017 a 2019 é suspeito."
    return text_


def html_fairness_chart(rows: list[dict]) -> str:
    """Equidade em gráfico: para cada comparação, a diferença de juro (ponto) e o IC 95% (barra) em torno do zero."""
    bounds = [abs(v) for e in rows for v in (e.get("ic95_min"), e.get("ic95_max"), e.get("diferenca_pp"))
              if v is not None]
    scale = max([1.0] + bounds) * 1.15  # meia largura do eixo, em pp
    pos = lambda v: 50 + 50 * v / scale  # % da largura; o zero fica no meio
    out = []
    for e in rows:
        text_, color, background = fairness_reading(e.get("ic95_min"), e.get("ic95_max"))
        n = ""
        if e.get("n_grupo_a") is not None:
            n = f' · {_num(e["n_grupo_a"], 0)} × {_num(e["n_grupo_b"], 0)} contratos'
        if e.get("diferenca_pp") is None:
            mark = '<div class="ap-fair-empty">aguardando o cálculo da equidade</div>'
            numbers = "—"
        else:
            lo, hi, d = e["ic95_min"], e["ic95_max"], e["diferenca_pp"]
            mark = (f'<div class="ap-fair-ci" style="left:{pos(lo):.1f}%;width:{pos(hi) - pos(lo):.1f}%;'
                    f'background:{color}"></div>'
                    f'<div class="ap-fair-dot" style="left:{pos(d):.1f}%;border-color:{color}"></div>')
            numbers = (f'<b style="color:{color}">{pp(d)}</b> '
                       f'<span class="ap-muted">(IC 95%: {pp(lo)} a {pp(hi)})</span>')
        out.append(f"""<div class="ap-fair-row">
            <div class="ap-fair-head"><div><b>{esc(e.get("atributo"))}</b>
                <span class="ap-muted">· {esc(e.get("comparacao"))}{n}</span></div>{badge(text_, color, background)}</div>
            <div class="ap-fair-track"><div class="ap-fair-zero"></div>{mark}</div>
            <div class="ap-fair-nums">{numbers}</div>
            <div class="ap-fair-explain">{fairness_sentence(e)}</div></div>""")
    axis = (f'<div class="ap-fair-axis"><span>{pp(-scale, 0)}</span><span>0 · sem diferença</span>'
            f'<span>{pp(scale, 0)}</span></div>')
    return compact("".join(out) + axis + """<div class="ap-foot">À direita do zero, o primeiro grupo paga mais juro
        do que o risco explica; à esquerda, paga menos. Barra = intervalo de confiança de 95%.</div>""")


def html_invariance_ring(summary: dict | None) -> str:
    """Teste em lote como um anel: quantos dos contratos sorteados deram resultado idêntico."""
    if not summary or not summary.get("n_testados"):
        return html_invariance_summary(summary)
    tested, same = summary["n_testados"], summary.get("identicos", 0)
    share = same / tested
    color = "#8cc7a1" if same == tested else "#e8a462"
    when = str(summary.get("gerado_em", ""))[:10]
    if when[:4].isdigit():
        when = f"{when[8:10]}/{when[5:7]}/{when[:4]}"
    verdict = ("Nenhuma diferença: o modelo não usa gênero nem idade." if same == tested else
               f"{_num(tested - same, 0)} contratos mudaram: o modelo está usando gênero ou idade.")
    return compact(f"""<div class="ap-ring-wrap">
        <div class="ap-ring" style="background:conic-gradient({color} {share * 360:.1f}deg, rgba(154,165,181,.18) 0)">
            <div class="ap-ring-in"><div class="ap-ring-n" style="color:{color}">{_num(same, 0)}</div>
            <div class="ap-ring-of">de {_num(tested, 0)}</div></div></div>
        <div><div class="ap-ring-title">contratos com resultado idêntico</div>
            <div class="ap-ring-verdict" style="color:{color}">{esc(verdict)}</div>
            <div class="ap-chips" style="margin:.6rem 0 0">
                <span class="ap-chip">gênero trocado</span><span class="ap-chip">idade ±25 anos</span>
                <span class="ap-chip">6 resultados comparados</span></div>
            <div class="ap-foot">Sorteio do lote · modelo {esc(summary.get("versao_modelo"))} · pacote
                {esc(summary.get("pacote_hash"))} · semente {esc(summary.get("semente"))} · {esc(when)}</div></div>
        </div>""")


def html_invariance(result: dict) -> str:
    """Teste de invariância: original × gênero e idade trocados (sem os valores reais)."""
    original, changed = result["original"], result["trocado"]
    rows = [
        ("Chance de inadimplência", pct(original.get("pd")), pct(changed.get("pd"))),
        ("Faixa de risco", original.get("faixa") or "—", changed.get("faixa") or "—"),
        ("Juro justo", pct(original.get("juro_justo")), pct(changed.get("juro_justo"))),
        ("Margem do juro justo", _margin(original), _margin(changed)),
        ("O que mais pesou", ", ".join(original.get("motivos", [])[:3]) or "—",
         ", ".join(changed.get("motivos", [])[:3]) or "—"),
    ]
    mark = lambda same: ('<span class="ap-same">✓</span>' if same else '<span class="ap-diff">✗</span>')
    body = "".join(
        f'<tr><td>{esc(name)}</td><td class="ap-mono">{esc(a)}</td>'
        f'<td class="ap-mono{" ap-changed" if a != b else ""}">{esc(b)}</td><td>{mark(a == b)}</td></tr>'
        for name, a, b in rows)
    same_situation = original.get("situacao_preco") == changed.get("situacao_preco")
    body += (f'<tr><td>Situação do preço</td><td>{situation_badge(original.get("situacao_preco"))}</td>'
             f'<td>{situation_badge(changed.get("situacao_preco"))}</td><td>{mark(same_situation)}</td></tr>')
    if result.get("identico"):
        verdict = ('<div class="ap-verdict ap-verdict-ok">Resultado idêntico: trocar gênero e idade não mudou nada '
                   'no que o modelo calcula.</div>')
    else:
        labels = {"pd": "risco", "faixa": "faixa", "juro_justo": "juro justo", "juro_justo_min": "margem",
                  "juro_justo_max": "margem", "situacao_preco": "situação", "motivos": "motivos"}
        changed_names = sorted({labels.get(d, d) for d in result.get("diferencas", [])})
        verdict = (f'<div class="ap-verdict ap-verdict-bad">Resultado diferente em: {esc(", ".join(changed_names))}. '
                   'O modelo está usando gênero ou idade: avise o responsável pelo modelo.</div>')
    return compact(f"""{verdict}
        <table class="ap-table ap-lab-table"><thead><tr><th></th><th>Original</th>
        <th>Trocados</th><th>Igual?</th></tr></thead><tbody>{body}</tbody></table>
        <div class="ap-foot">Como foi trocado: {esc(result.get("como_foi_trocado"))}. A tela não mostra o gênero nem a
        idade reais do cliente.</div>""")


def html_invariance_summary(summary: dict | None) -> str:
    """Resumo do teste em lote (scripts/invariancia_lote.py), ou como gerá-lo."""
    if not summary:
        return ('<div class="ap-card-sub">O teste em lote ainda não foi rodado. Na máquina com o banco: '
                '<code>python -m scripts.invariancia_lote</code> (500 contratos sorteados).</div>')
    tested, same = summary.get("n_testados", 0), summary.get("identicos", 0)
    when = str(summary.get("gerado_em", ""))[:10]
    if when[:4].isdigit():
        when = f"{when[8:10]}/{when[5:7]}/{when[:4]}"
    source = (f'modelo {esc(summary.get("versao_modelo"))} · pacote {esc(summary.get("pacote_hash"))} · '
              f'semente {esc(summary.get("semente"))} · gerado em {esc(when)}')
    if tested and same == tested:
        return compact(f"""<div class="ap-verdict ap-verdict-ok">Em lote: {_num(tested, 0)} contratos sorteados do lote,
            {_num(same, 0)} com resultado idêntico.</div><div class="ap-foot">{source}</div>""")
    return compact(f"""<div class="ap-verdict ap-verdict-bad">Em lote: {_num(tested - same, 0)} de {_num(tested, 0)}
        contratos deram resultado diferente. O modelo está usando gênero ou idade: avise o responsável pelo
        modelo.</div><div class="ap-foot">{source}</div>""")


def html_fairness_table(rows: list[dict]) -> str:
    body = []
    for e in rows:
        reading = badge(*fairness_reading(e.get("ic95_min"), e.get("ic95_max")))
        if e.get("ic95_min") is None:
            ci = "[a – b]"
        else:
            ci = f'{pp(e.get("ic95_min"), sign=True)} a {pp(e.get("ic95_max"), sign=True)}'
        diff = "[+0,0 pp]" if e.get("diferenca_pp") is None else pp(e.get("diferenca_pp"))
        n = ""
        if e.get("n_grupo_a") is not None:
            n = f'<div class="ap-muted ap-small">n = {_num(e["n_grupo_a"], 0)} × {_num(e["n_grupo_b"], 0)}</div>'
        body.append(f"""
            <tr><td><b>{esc(e.get("atributo"))}</b> · {esc(e.get("comparacao"))}{n}</td>
            <td>{diff}</td><td>{ci}</td><td>{reading}</td></tr>""")
    return compact(f"""
        <table class="ap-table">
            <thead><tr><th>Comparação</th><th>Diferença</th><th>IC 95%</th><th>Leitura</th></tr></thead>
            <tbody>{"".join(body)}</tbody>
        </table>
    """)
