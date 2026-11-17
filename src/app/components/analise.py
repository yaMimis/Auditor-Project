"""Blocos da página Análise: cartões, régua, motivos, dados do contrato, precificação, procedência, resultado observado e parecer.
"""
from __future__ import annotations

import math

from src.app.components.base import (
    badge, COLOR_DECREASES, COLOR_INCREASES, compact, esc, eur, html_kpi, margin_distance_pp, _num, pct,
    pp, RATE_UNIT, RECOMMENDATIONS, SITUATIONS)

__all__ = ["rate_decimals", "review_kpis", "html_rate_bar", "EMPLOYMENT_TIME", "CODE_LABELS", "IN_EUROS",
           "TIMES_INCOME", "QUANTITIES", "readable_value", "html_reasons", "html_considered_data",
           "html_pricing", "UNCERTAINTY", "uncertainty_text", "html_provenance", "html_outcome",
           "html_opinion"]


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


# Como a incerteza do risco foi estimada (Procedência da Análise e Laboratório).
UNCERTAINTY = {
    "bootstrap": "faixa estimada refazendo o modelo várias vezes com amostras diferentes dos clientes (bootstrap)",
    "margem_padrao": "sem faixa de incerteza do risco neste modelo; a margem do juro justo é a padrão de ±2 p.p.",
    "nao_calculada": "não se aplica: revisão manual",
}


def uncertainty_text(kind: str | None, n_resamples: int | None) -> str:
    text = UNCERTAINTY.get(kind, "—")
    if kind == "bootstrap" and n_resamples:
        text += f" · {n_resamples} repetições; leia a faixa como estimativa"
    return text


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
        origem = badge("Gerado por IA · números conferidos · sem norma citada", "#f2b48a", "rgba(242,180,138,.10)")
    points = "".join(f"<li>{esc(p)}</li>" for p in opinion.get("pontos_de_atencao", []))
    if fontes:
        sources_html = "".join(
            f'<span class="ap-chip" title="{esc(f.get("trecho_id"))}">'
            f'{esc(f.get("norma"))}, {esc(f.get("artigo"))}</span>' for f in fontes)
    else:
        sources_html = ('<span class="ap-muted">Parecer padrão (sem IA): este texto não cita normas. Os números '
                        'acima continuam valendo.</span>' if opinion.get("origem") != "llm" else
                        '<span class="ap-muted">A IA não citou norma neste caso: nenhum trecho encontrado pela '
                        'busca nas normas foi pertinente.</span>')
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
