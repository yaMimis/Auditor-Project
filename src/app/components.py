"""Formatação e blocos HTML do painel (sem Streamlit: tudo aqui é testável com pytest).

Regras de exibição (genai/REGRAS_PARECER.md e FORMATO_JSON.md):
- PD e juros chegam em FRAÇÃO (0.249) e são mostrados com vírgula e 1 casa ("24,9%");
- juros são NOMINAIS ao ano (convenção do Bondora; FORMATO_JSON v1.5): rótulo "a.a. nominal";
- campo nulo vira "—" (nunca 0%);
- todo texto vindo da API passa por html.escape antes de entrar no HTML.
"""
from __future__ import annotations

import base64
import html
import math
from pathlib import Path

# ---------------------------------------------------------------- formatação

COUNTRIES = {"EE": "Estônia", "FI": "Finlândia", "ES": "Espanha"}


def esc(text_) -> str:
    return html.escape("" if text_ is None else str(text_))


def _num(valor: float, decimals: int) -> str:
    """1234.5 -> '1.234,5' (padrão brasileiro)."""
    return f"{valor:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(fraction, decimals: int = 1) -> str:
    """0.249 -> '24,9%'; None -> '—'."""
    if fraction is None or (isinstance(fraction, float) and math.isnan(fraction)):
        return "—"
    return f"{_num(fraction * 100, decimals)}%"


def pp(valor, decimals: int = 1, sign: bool = True) -> str:
    """6.9 -> '+6,9 pp'."""
    if valor is None:
        return "—"
    text_ = _num(abs(valor), decimals)
    prefix = ("+" if valor > 0 else "−" if valor < 0 else "") if sign else ""
    return f"{prefix}{text_} pp"


def eur(valor, decimals: int = 0) -> str:
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return "—"
    return f"€ {_num(valor, decimals)}"


def compact(block: str) -> str:
    """Tira indentação e linhas vazias: o Markdown do Streamlit transforma linha
    indentada em bloco de código e linha vazia encerra o bloco HTML."""
    return " ".join(row.strip() for row in block.splitlines() if row.strip())


# ---------------------------------------------------------------- situações

SITUATIONS = {
    "acima_do_justo": {"rotulo": "Acima do justo", "icone": "↑", "cor": "#e8a462",
                       "fundo": "rgba(232,164,98,.10)", "leitura": "juro acima do que o risco justifica"},
    "abaixo_do_justo": {"rotulo": "Abaixo do justo", "icone": "↓", "cor": "#c3a6f0",
                        "fundo": "rgba(195,166,240,.10)", "leitura": "juro pode não cobrir a perda esperada"},
    "dentro_da_margem": {"rotulo": "Dentro da margem", "icone": "=", "cor": "#8cc7a1",
                         "fundo": "rgba(140,199,161,.10)", "leitura": "preço compatível com o risco"},
    "revisao_manual": {"rotulo": "Revisão manual", "icone": "!", "cor": "#9aa5b5",
                       "fundo": "rgba(154,165,181,.10)", "leitura": "dados fora do que o modelo conhece"},
}

RECOMMENDATIONS = {
    "manter_preco": "Manter preço",
    "revisar_preco": "Revisar preço",
    "encaminhar_compliance": "Encaminhar ao compliance",
    "revisao_manual": "Revisão manual",
}

RATE_UNIT = " a.a. nominal"
COLOR_INCREASES = "#d9825b"
COLOR_DECREASES = "#7fa7d9"


def margin_distance_pp(r: dict) -> float | None:
    """Quanto o juro cobrado passa da margem de incerteza, em pontos percentuais."""
    charged, rate_min, rate_max = r.get("juro_cobrado"), r.get("juro_justo_min"), r.get("juro_justo_max")
    if None in (charged, rate_min, rate_max):
        return None
    if charged > rate_max:
        return round((charged - rate_max) * 100, 1)
    if charged < rate_min:
        return round((charged - rate_min) * 100, 1)
    return 0.0


def badge(text_: str, color: str, background: str | None = None) -> str:
    background = background or "rgba(255,255,255,.05)"
    return (f'<span class="ap-badge" style="color:{color};background:{background};'
            f'border-color:{color}55">{esc(text_)}</span>')


def situation_badge(situation: str) -> str:
    s = SITUATIONS.get(situation, SITUATIONS["revisao_manual"])
    return badge(s["rotulo"], s["cor"], s["fundo"])


# ---------------------------------------------------------------- revisão de contrato

def html_kpi(label_: str, valor: str, unit: str = "", sub: str = "", extra: str = "",
             highlight: dict | None = None, info: str = "") -> str:
    style = ""
    value_color = ""
    if highlight:  # cartão da situação: cor da situação e fonte menor (texto, não número)
        style = f'style="border-color:{highlight["cor"]}66;background:{highlight["fundo"]}"'
        value_color = f'style="color:{highlight["cor"]};font-size:1.75rem;white-space:nowrap"'
    return compact(f"""
        <div class="ap-kpi" {style}>{info_tip(info) if info else ""}
            <div class="ap-kpi-label">{esc(label_)}</div>
            <div class="ap-kpi-value" {value_color}>{valor}<span class="ap-kpi-unit">{esc(unit)}</span></div>
            <div class="ap-kpi-sub">{sub}</div>
            {extra}
        </div>
    """)


def rate_decimals(r: dict) -> int:
    """Casas decimais dos juros: 1; ou 2 quando dois juros diferentes ficariam iguais com 1 casa
    (mesma regra do parecer, genai/src/checagem.py: evita "30,6% abaixo de 30,6%")."""
    rates = [v for v in (r.get("juro_cobrado"), r.get("juro_justo"), r.get("juro_justo_min"),
                         r.get("juro_justo_max")) if v is not None]
    for i, a in enumerate(rates):
        for b in rates[i + 1:]:
            if abs(a - b) > 1e-9 and pct(a) == pct(b):
                return 2
    return 1


def review_kpis(r: dict) -> list[str]:
    """Os 4 cartões do topo: risco, juro cobrado, juro justo e situação."""
    situation = r.get("situacao_preco", "revisao_manual")
    s = SITUATIONS.get(situation, SITUATIONS["revisao_manual"])
    decimals = rate_decimals(r)
    ci = r.get("pd_ic95")
    ci_text = (f"Pode variar de {pct(ci[0])} a {pct(ci[1])} (incerteza do modelo)" if ci
               else "Sem faixa de incerteza do risco neste modelo")
    faixa = r.get("faixa")
    band_html = (f'<span class="ap-faixa">Faixa {esc(faixa)}</span>' if faixa
                  else '<span class="ap-faixa ap-faixa-off">Sem faixa</span>')

    if r.get("juro_justo") is None:
        fair_sub = "Não calculado: dados fora do que o modelo conhece"
    else:
        label = "Margem" if ci else "Margem padrão de ±2 p.p."
        fair_sub = f"{label}: de {pct(r.get('juro_justo_min'), decimals)} a {pct(r.get('juro_justo_max'), decimals)}"
    if r.get("juro_pares_mediana") is not None:  # segunda opinião: não muda a situação
        fair_sub += f"<br>Contratos parecidos (mediana): {pct(r['juro_pares_mediana'])}"

    dist = margin_distance_pp(r)
    if situation == "revisao_manual":
        situation_sub = "risco e juro justo não calculados; o analista confere os dados"
    elif situation == "dentro_da_margem":
        situation_sub = "o juro cobrado está entre o mínimo e o máximo da margem"
    elif situation == "acima_do_justo":
        situation_sub = f"{pp(dist)} acima do teto da margem"
    else:
        situation_sub = f"{pp(dist)} abaixo do piso da margem"

    pd_value = pct(r.get("pd")) if r.get("pd") is not None else "—"
    return [
        html_kpi("Risco de inadimplência", pd_value, "", esc(ci_text),
                 extra=f'<div class="ap-kpi-foot">{band_html}</div>', info="risco"),
        html_kpi("Juro cobrado", pct(r.get("juro_cobrado"), decimals), RATE_UNIT, "Taxa do contrato", info="cobrado"),
        html_kpi("Juro justo calculado", pct(r.get("juro_justo"), decimals), RATE_UNIT if r.get("juro_justo") else "",
                 fair_sub, info="justo"),  # fair_sub só tem números formatados por pct() e texto fixo
        html_kpi("Situação do preço", f'{s["icone"]} {esc(s["rotulo"])}', "", esc(situation_sub), highlight=s, info="situacao"),
    ]


def _scale(*values_: float) -> float:
    """Fim do eixo: no mínimo 40%, arredondado para cima de 10 em 10 pontos."""
    largest = max([v for v in values_ if v is not None] + [0.0])
    return max(0.40, math.ceil(largest * 1.15 * 10) / 10)


def html_rate_bar(r: dict) -> str:
    """Régua horizontal: margem de incerteza (faixa), juro justo e juro cobrado."""
    charged, fair = r.get("juro_cobrado"), r.get("juro_justo")
    rate_min, rate_max = r.get("juro_justo_min"), r.get("juro_justo_max")
    if None in (charged, fair, rate_min, rate_max):
        return ""
    scale = _scale(charged, rate_max)
    position = lambda v: min(max(v / scale * 100, 0), 100)  # noqa: E731
    charged_color = SITUATIONS.get(r.get("situacao_preco"), SITUATIONS["dentro_da_margem"])["cor"]
    step_ = 0.1 if scale <= 0.6 else 0.2 if scale <= 1.2 else 0.5
    n_marks = int(round(scale / step_))
    marks = "".join(
        f'<span class="ap-tick" style="left:{position(i * step_)}%">{pct(i * step_, 0)}</span>'
        for i in range(n_marks + 1))
    # rótulos acima (justo) e abaixo (cobrado) para não se sobreporem
    return compact(f"""
        <div class="ap-ruler">
            <div class="ap-ruler-track">
                <div class="ap-ruler-band" style="left:{position(rate_min)}%;width:{position(rate_max) - position(rate_min)}%"></div>
                <div class="ap-ruler-mark" style="left:{position(fair)}%;background:#e4bd7d"></div>
                <div class="ap-ruler-label ap-up" style="left:{position(fair)}%;color:#e4bd7d">Justo {pct(fair, rate_decimals(r))}</div>
                <div class="ap-ruler-mark" style="left:{position(charged)}%;background:{charged_color}"></div>
                <div class="ap-ruler-label ap-down" style="left:{position(charged)}%;color:{charged_color}">Cobrado {pct(charged, rate_decimals(r))}</div>
            </div>
            <div class="ap-ruler-ticks">{marks}</div>
        </div>
        <div class="ap-legend">
            <span><i style="background:rgba(228,189,125,.28)"></i>Margem de incerteza do modelo</span>
            <span>Juros nominais ao ano</span>
        </div>
    """)


EMPLOYMENT_TIME = {
    "TrialPeriod": "em período de experiência", "UpTo1Year": "até 1 ano", "UpTo2Years": "até 2 anos",
    "UpTo3Years": "até 3 anos", "UpTo4Years": "até 4 anos", "UpTo5Years": "até 5 anos",
    "MoreThan5Years": "mais de 5 anos", "Retiree": "aposentado", "Other": "outro",
}
# Códigos do dicionário do Bondora (conferir com o glossário do Marcos).
CODE_LABELS = {
    "escolaridade": {"1": "fundamental", "2": "básico", "3": "técnico", "4": "médio", "5": "superior"},
    "tipo_verificacao": {"1": "renda não verificada", "2": "renda conferida por telefone",
                         "3": "renda verificada", "4": "renda e despesas verificadas"},
    "tipo_moradia": {"0": "sem moradia", "1": "própria", "2": "com os pais", "3": "aluguel mobiliado",
                     "4": "aluguel sem mobília", "5": "moradia social", "6": "aluguel compartilhado",
                     "7": "propriedade conjunta", "8": "financiada", "9": "própria com ônus", "10": "outra"},
}
IN_EUROS = {"valor_concedido", "renda_total", "valor_emprestimos_anteriores"}
TIMES_INCOME = {"valor_sobre_renda", "divida_sobre_renda"}  # podem passar de 1: "6,1× a renda"
QUANTITIES = {"passivos_existentes", "n_emprestimos_anteriores", "quitacoes_antecipadas_qtd"}


def _code(valor) -> str:
    """'5', 5, 5.0 e '5.0' viram '5'."""
    try:
        return str(int(float(valor)))
    except (TypeError, ValueError):
        return str(valor)


def readable_value(variable: str, valor) -> str | None:
    """Valor do motivo como o analista lê (None = não mostrar)."""
    if valor is None or str(valor) in ("", "sem_info", "outros", "nan", "None", "<NA>"):
        return None
    if variable in TIMES_INCOME:
        return f"{_num(float(valor), 1)}× a renda mensal"
    if variable == "parcela_neutra_sobre_renda":
        return f"{pct(float(valor), 0)} da renda"
    if variable == "renda_relativa":
        return f"{_num(float(valor), 1)}× a mediana do país"
    if variable in IN_EUROS:
        return eur(float(valor))
    if variable == "prazo_meses":
        return f"{_code(valor)} meses"
    if variable in QUANTITIES:
        return _code(valor)
    if variable == "tempo_emprego_atual":
        return EMPLOYMENT_TIME.get(str(valor), str(valor))
    if variable in CODE_LABELS:
        return CODE_LABELS[variable].get(_code(valor), _code(valor))
    if variable == "novo_cliente":
        return "sim" if str(valor).lower() in ("true", "1", "sim") else "não"
    if isinstance(valor, float) or variable == "score_ee_mini":
        number = float(valor)
        return _num(number, 0 if number.is_integer() or abs(number) >= 10 else 2)
    return str(valor)


def _reason_description(m: dict) -> str:
    label_ = esc(m.get("rotulo") or m.get("variavel"))
    try:
        valor = readable_value(m.get("variavel", ""), m.get("valor"))
    except (TypeError, ValueError):
        valor = str(m.get("valor"))
    if not valor:
        return label_
    return f'{label_}: <span class="ap-muted">{esc(valor)}</span>'


def html_reasons(motivos: list[dict], empty_text: str = "Sem motivos para este contrato.") -> str:
    """Barras dos motivos SHAP: comprimento = peso relativo; cor = efeito."""
    if not motivos:
        return f'<div class="ap-empty">{esc(empty_text)}</div>'
    weights = [m.get("peso") or 0 for m in motivos]
    largest = max(weights) or 1
    rows = []
    for m, peso in zip(motivos, weights):
        color = COLOR_INCREASES if m.get("efeito") == "aumenta_risco" else COLOR_DECREASES
        width = 8 + 92 * (peso / largest) if peso else 40
        weight_text = pct(peso, 0) if peso else ""
        rows.append(f"""
            <div class="ap-factor">
                <div class="ap-factor-name">{_reason_description(m)}</div>
                <div class="ap-factor-bar"><div style="width:{width}%;background:{color}"></div></div>
                <div class="ap-factor-w">{weight_text}</div>
            </div>""")
    return compact("".join(rows) + f"""
        <div class="ap-legend">
            <span><i style="background:{COLOR_INCREASES}"></i>Aumenta o risco</span>
            <span><i style="background:{COLOR_DECREASES}"></i>Reduz o risco</span>
        </div>""")


def html_considered_data(variables: list[dict]) -> str:
    """As variáveis do modelo deste contrato: fornecidas (cadastro) e derivadas (pipeline)."""
    def rows(origin):
        out = []
        for v in (x for x in variables if x.get("origem") == origin):
            try:
                value = readable_value(v.get("variavel", ""), v.get("valor"))
            except (TypeError, ValueError):
                value = str(v.get("valor"))
            shown = esc(value) if value else '<span class="ap-muted">sem informação</span>'
            out.append(f'<tr><td>{esc(v.get("rotulo"))}</td><td>{shown}</td></tr>')
        return "".join(out)
    given, derived = rows("fornecida"), rows("derivada")
    return compact(f"""<div class="ap-grid-2">
        <div><div class="ap-card-sub"><b>Fornecidas</b> · vêm do cadastro e do contrato, no banco</div>
            <table class="ap-table ap-data-table"><tbody>{given}</tbody></table></div>
        <div><div class="ap-card-sub"><b>Calculadas</b> · obtidas a partir dos dados fornecidos</div>
            <table class="ap-table ap-data-table"><tbody>{derived}</tbody></table>
            <div class="ap-card-sub" style="margin-top:.8rem">As calculadas usam alguns dados de entrada que não são
            variáveis do modelo, como as parcelas mensais das dívidas (só entram na conta de “dívidas em relação à renda”;
            não confundir com o número de dívidas em aberto, que é fornecida). Ao todo, o modelo usa
            {len(variables)} variáveis.</div>
            <div class="ap-card-sub" style="margin-top:.8rem">Não entram no modelo: juro cobrado e parcela (o preço
            já embute o risco), gênero, idade, estado civil e dependentes (só auditoria de equidade), e a nota de risco e a
            chance de inadimplência calculadas pelo próprio Bondora.</div></div></div>""")


def html_pricing(params: dict | None, r: dict, country: str | None = None) -> str:
    """Precificação: a comparação cobrado × justo e, quando o modelo calculou agora, os parâmetros
    da conta e o juro justo com PD zero (comparação, não uma soma de parcelas)."""
    diff = r.get("diferenca_pp")
    if diff is None and r.get("juro_cobrado") is not None and r.get("juro_justo") is not None:
        diff = round((r["juro_cobrado"] - r["juro_justo"]) * 100, 1)
    rows = [("Juro cobrado", pct(r.get("juro_cobrado"), 2)),
            ("Juro justo (margem: mínimo a máximo)", f'{pct(r.get("juro_justo"), 2)} ({pct(r.get("juro_justo_min"), 2)} a '
                                    f'{pct(r.get("juro_justo_max"), 2)})'),
            ("Cobrado menos justo", pp(diff) if diff is not None else "—"),
            ("Juro mediano de contratos parecidos (2ª opinião)", pct(r.get("juro_pares_mediana"), 2))]
    if params:
        rows += [("Custo do dinheiro (Euribor 12 meses da época)", pct(params["euribor_12m"], 2)),
                 ("Custos e lucro do credor no ano da concessão", pct(params["custo_margem_safra"], 1)),
                 (f"Quanto se perde se o cliente não pagar ({esc(country) if country else 'país'})",
                  pct(params["lgd"], 0)),
                 ("Prazo", f'{params["prazo_meses"]} meses')]
    body = "".join(f"<tr><td>{a}</td><td>{b}</td></tr>" for a, b in rows)
    left = f'<table class="ap-table ap-data-table"><tbody>{body}</tbody></table>'
    if not params:
        return compact(f"""{left}<div class="ap-card-sub" style="margin-top:.6rem">Os parâmetros da conta aparecem
            quando o modelo calcula o contrato na hora.</div>""")
    return compact(f"""<div class="ap-grid-2"><div>{left}</div>
        <div><div class="ap-card-sub"><b>Quanto o risco deste cliente pesa no juro justo</b></div>
            <table class="ap-table ap-data-table"><tbody>
            <tr><td>Se o cliente não tivesse risco nenhum</td><td>{pct(params["juro_justo_sem_risco"], 2)}</td></tr>
            <tr><td>Com o risco deste cliente ({pct(params["pd"], 1)} de chance de inadimplência)</td>
                <td><b>{pct(r.get("juro_justo"), 2)}</b></td></tr>
            <tr><td>Quanto o risco acrescenta ao juro</td><td><b>{pp(params["efeito_do_risco_pp"])}</b></td></tr>
            </tbody></table>
            <div class="ap-card-sub" style="margin-top:.6rem">Não é uma soma de parcelas: o juro justo é o juro que faz
            o valor que se espera receber, mês a mês (já descontada a chance de o cliente não pagar), igualar o valor
            emprestado.</div></div></div>""")


# ---------------------------------------------------------------- laboratório

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


def html_provenance(rows: list[tuple[str, str]]) -> str:
    """Procedência da análise: versão do modelo, data do cálculo, origem dos dados, domínio."""
    body = "".join(f"<tr><td>{esc(a)}</td><td>{esc(b)}</td></tr>" for a, b in rows)
    return compact(f'<table class="ap-table ap-data-table"><tbody>{body}</tbody></table>')


def html_outcome(outcome: dict | None, from_portfolio: dict | None = None, reason: str | None = None) -> str:
    """O que aconteceu de verdade. Do banco (vw_desfecho_contrato) ou, sem banco, do arquivo do lote."""
    explain = ("Prejuízo líquido = valor emprestado − tudo o que voltou (parcelas, juros e multas), "
               "sem correção no tempo.")
    if outcome:
        defaulted = "Sim" if outcome.get("inadimplente") else "Não"
        result = outcome.get("resultado_eur") or 0
        result_color = COLOR_DECREASES if result >= 0 else COLOR_INCREASES
        retorno = outcome.get("retorno_realizado")
        cells = [("O cliente ficou inadimplente?", defaulted), ("Total que voltou", eur(outcome.get("recebido_total"), 2)),
                 ("Ganho ou perda (voltou − emprestado)", f'<span style="color:{result_color}">{eur(result, 2)}</span>'),
                 ("Retorno real do contrato", pct(retorno, 1) if retorno is not None else "—"),
                 ("Valor emprestado que não voltou", eur(outcome.get("principal_perdido"), 2))]
        source = "Fonte: banco de dados (contrato já encerrado)."
    elif from_portfolio and from_portfolio.get("rentabilidade_realizada") is not None:
        cells = [("Retorno real do contrato", pct(from_portfolio["rentabilidade_realizada"], 1)),
                 ("Prejuízo líquido", eur(from_portfolio.get("perda_nao_coberta_eur") or 0, 2))]
        source = "Fonte: arquivo do lote da carteira (sem banco nesta consulta)."
    elif reason:
        return (f'<div class="ap-empty"><b>Sem desfecho</b>: {esc(reason)}. O sistema não mostra perda de um '
                'contrato sem resultado final.</div>')
    else:
        return ('<div class="ap-empty">Sem resultado final observado: o contrato é posterior a 2016 ou ainda não '
                'terminou. O sistema não mostra perda de um contrato que não acabou.</div>')
    body = "".join(f'<div><div class="ap-card-sub">{esc(a)}</div><div class="ap-outcome-v">{b}</div></div>'
                   for a, b in cells)
    return compact(f"""<div class="ap-outcome">{body}</div>
        <div class="ap-card-sub" style="margin-top:.6rem">{esc(explain)} {esc(source)}</div>""")


def html_opinion(opinion: dict | None) -> str:
    if not opinion:
        return ('<div class="ap-empty">Parecer indisponível nesta consulta. '
                'Os números acima continuam válidos para a decisão.</div>')
    fontes = opinion.get("fontes") or []
    if opinion.get("origem") != "llm":
        origem = badge("Template de reserva · sem IA", "#9aa5b5")
    elif fontes:
        origem = badge(f"Gerado por IA · números conferidos · {len(fontes)} fonte(s) recuperada(s)",
                       "#e4bd7d", "rgba(228,189,125,.10)")
    else:
        origem = badge("Gerado por IA · sem fonte normativa: revisão humana", "#f2b48a", "rgba(242,180,138,.10)")
    points = "".join(f"<li>{esc(p)}</li>" for p in opinion.get("pontos_de_atencao", []))
    if fontes:
        sources_html = "".join(
            f'<span class="ap-chip" title="{esc(f.get("trecho_id"))}">'
            f'{esc(f.get("norma"))}, {esc(f.get("artigo"))}</span>' for f in fontes)
    else:
        sources_html = '<span class="ap-muted">Não encontrei base normativa para este caso.</span>'
    rec = RECOMMENDATIONS.get(opinion.get("recomendacao"), opinion.get("recomendacao"))
    context = ""
    if opinion.get("contexto_mercado"):  # frase fixa escrita pelo código (média do BC), nunca pelo LLM
        context = (f'<div class="ap-sec">Referência de mercado (Brasil)</div>'
                    f'<div class="ap-mercado">{esc(opinion["contexto_mercado"])}</div>')
    return compact(f"""
        <div class="ap-parecer-head">
            <div class="ap-card-title">Parecer</div>{origem}
        </div>
        <div class="ap-sec">Resumo</div>
        <p class="ap-text">{esc(opinion.get("resumo"))}</p>
        <div class="ap-sec">Pontos de atenção</div>
        <ul class="ap-list">{points or "<li>Nenhum.</li>"}</ul>
        <div class="ap-sec">Recomendação do sistema · {esc(rec)}</div>
        <p class="ap-text">{esc(opinion.get("recomendacao_texto"))}</p>
        <div class="ap-sec">Fontes consultadas</div>
        <div class="ap-chips">{sources_html}</div>
        <div class="ap-foot">A checagem confere números, palavras e artigos citados; ela não garante que a fonte
        recuperada seja a mais adequada ao caso. Confira as fontes antes de decidir.</div>
        {context}
        <div class="ap-foot">Versão do texto: {esc(opinion.get("versao_prompt"))}</div>
    """)


# ---------------------------------------------------------------- carteira

# Explicação de cada bloco: aparece num ícone "i" no canto do cartão (passe o mouse no cartão e clique no ícone).
INFO = {
    "auditados": "Contratos da carteira (2016 a 2021) que o modelo conseguiu avaliar, no período e filtros "
                 "escolhidos. Os de revisão manual ficam de fora: têm dados fora do que o modelo conhece.",
    "acima": "Juro cobrado acima do teto da margem do juro justo: cobra-se mais do que o risco explica. "
             "É indício para investigar, não conclusão.",
    "abaixo": "Juro cobrado abaixo do piso da margem do juro justo: o juro pode não cobrir as perdas esperadas "
              "com inadimplência.",
    "cobrado_mais": "Estimativa, em euros, do que os clientes acima do justo pagaram além do teto da margem, "
                    "somando as parcelas.",
    "prejuizo": "Nos contratos abaixo do justo já encerrados: valor emprestado menos tudo o que voltou "
                "(parcelas, juros e multas), sem correção no tempo.",
    "risco": "Chance de o cliente ficar inadimplente (PD), calculada pelo modelo de risco com os dados do "
             "contrato. A faixa embaixo é a incerteza do modelo.",
    "cobrado": "A taxa que o contrato cobra de fato, em juros nominais ao ano.",
    "justo": "O juro que paga o risco deste cliente: custo do dinheiro na época + perda esperada com "
             "inadimplência + custos da operação. A margem (mínimo e máximo) é a incerteza desse cálculo.",
    "situacao": "Compara o juro cobrado com a margem do juro justo: acima do teto, abaixo do piso ou dentro. "
                "Revisão manual quando os dados estão fora do que o modelo conhece.",
    "regua": "Onde o juro cobrado cai em relação à margem do juro justo (a faixa dourada). Fora da faixa, "
             "o preço não acompanha o risco.",
    "precificacao": "Os ingredientes do juro justo deste contrato e quanto o risco do cliente acrescenta ao juro.",
    "faixas": "Risco de A (menor) a E (maior). Em cada faixa, quanto dos contratos ficou abaixo, dentro ou "
              "acima da margem do juro justo.",
    "backtest": "Teste com o que aconteceu de verdade: quanto rendeu, em 2016, cada grupo de contratos, por faixa "
                "e situação do preço.",
    "motivos": "Os dados que mais empurraram o risco deste cliente para cima ou para baixo (método SHAP). "
               "Mostra o peso na previsão, não causa e efeito.",
    "parecer": "Texto de apoio gerado por IA a partir dos números do modelo e das normas; o código confere cada "
               "número. Se a IA falhar, entra um texto padrão. Quem decide é o analista.",
    "resultado": "O que aconteceu de verdade com o contrato depois da concessão. Só existe para contratos já "
                 "encerrados.",
}


def info_tip(key: str) -> str:
    """Ícone "i" no canto do cartão; clicar abre a explicação (details/summary: funciona sem JavaScript)."""
    text = INFO.get(key, key)
    return (f'<details class="ap-info"><summary title="O que é isto?">i</summary>'
            f'<div class="ap-info-box">{esc(text)}</div></details>')


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
    body = "".join(
        f'<tr><td>{esc(name)}</td><td class="ap-mono">{esc(a)}</td>'
        f'<td class="ap-mono{" ap-changed" if a != b else ""}">{esc(b)}</td></tr>' for name, a, b in rows)
    body += (f'<tr><td>Situação do preço</td><td>{situation_badge(original.get("situacao_preco"))}</td>'
             f'<td>{situation_badge(changed.get("situacao_preco"))}</td></tr>')
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
        <th>Gênero e idade trocados</th></tr></thead><tbody>{body}</tbody></table>
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


# ---------------------------------------------------------------- imagens (capa e equipe)

IMAGE_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


def image_data_uri(folder: Path, name: str) -> str | None:
    """A imagem <name>.jpg/.jpeg/.png/.webp da pasta, embutida no HTML (data URI), ou None se não existir.

    Embutida porque o st.markdown não serve arquivos locais; assim funciona também sem internet."""
    for suffix, mime in IMAGE_TYPES.items():
        path_ = Path(folder) / f"{name}{suffix}"
        if path_.exists():
            return f"data:{mime};base64,{base64.b64encode(path_.read_bytes()).decode('ascii')}"
    return None


def html_team_avatar(initials: str, photo_uri: str | None) -> str:
    """Foto do integrante, se houver; senão, as iniciais."""
    if photo_uri:
        return f'<div class="team-avatar team-photo" style="background-image:url(\'{photo_uri}\')"></div>'
    return f'<div class="team-avatar">{esc(initials)}</div>'


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

# ---------------------------------------------------------------- ícones
# Traço fino (estilo "line icons"), cor pelo texto em volta (currentColor): brancos no painel.
# Substituem os emojis no HTML; nos botões do Streamlit usamos os ícones Material (icon=":material/...:").

_ICONS = {
    "balanca": '<path d="M12 3v18M7 21h10M5 7h14"/><path d="M5 7l-3 7a3.5 3.5 0 0 0 6 0L5 7zM19 7l-3 7a3.5 3.5 0 0 0 6 0l-3-7z"/>',
    "grafico": '<path d="M3 3v18h18"/><path d="M7 15l4-4 3 3 5-6"/>',
    "chip": '<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4"/>',
    "documento": '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h6"/>',
    "cadeado": '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
}


def line_icon(name_: str, size: int = 18, css_class: str = "ap-ico") -> str:
    """SVG inline de um ícone de linha. Nome desconhecido → string vazia (nunca quebra a tela)."""
    body = _ICONS.get(name_)
    if not body:
        return ""
    return (f'<svg class="{esc(css_class)}" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
            f'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" '
            f'aria-hidden="true">{body}</svg>')
