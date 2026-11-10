"""Formatação e blocos HTML do painel (sem Streamlit: tudo aqui é testável com pytest).

Regras de exibição (genai/REGRAS_PARECER.md e FORMATO_JSON.md):
- PD e juros chegam em FRAÇÃO (0.249) e são mostrados com vírgula e 1 casa ("24,9%");
- juros são NOMINAIS ao ano (convenção do Bondora; FORMATO_JSON v1.5): rótulo "a.a. nominal";
- campo nulo vira "—" (nunca 0%);
- todo texto vindo da API passa por html.escape antes de entrar no HTML.
"""
from __future__ import annotations

import html
import math

# ---------------------------------------------------------------- formatação

PAISES = {"EE": "Estônia", "FI": "Finlândia", "ES": "Espanha"}


def esc(texto) -> str:
    return html.escape("" if texto is None else str(texto))


def _num(valor: float, casas: int) -> str:
    """1234.5 -> '1.234,5' (padrão brasileiro)."""
    return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(fracao, casas: int = 1) -> str:
    """0.249 -> '24,9%'; None -> '—'."""
    if fracao is None or (isinstance(fracao, float) and math.isnan(fracao)):
        return "—"
    return f"{_num(fracao * 100, casas)}%"


def pp(valor, casas: int = 1, sinal: bool = True) -> str:
    """6.9 -> '+6,9 pp'."""
    if valor is None:
        return "—"
    texto = _num(abs(valor), casas)
    prefixo = ("+" if valor > 0 else "−" if valor < 0 else "") if sinal else ""
    return f"{prefixo}{texto} pp"


def eur(valor, casas: int = 0) -> str:
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return "—"
    return f"€ {_num(valor, casas)}"


def data_br(iso: str | None) -> str:
    if not iso:
        return "—"
    a, m, d = str(iso)[:10].split("-")
    return f"{d}/{m}/{a}"


def compactar(bloco: str) -> str:
    """Tira indentação e linhas vazias: o Markdown do Streamlit transforma linha
    indentada em bloco de código e linha vazia encerra o bloco HTML."""
    return " ".join(linha.strip() for linha in bloco.splitlines() if linha.strip())


# ---------------------------------------------------------------- situações

SITUACOES = {
    "acima_do_justo": {"rotulo": "Acima do justo", "icone": "↑", "cor": "#e8a462",
                       "fundo": "rgba(232,164,98,.10)", "leitura": "risco de perder bons clientes"},
    "abaixo_do_justo": {"rotulo": "Abaixo do justo", "icone": "↓", "cor": "#c3a6f0",
                        "fundo": "rgba(195,166,240,.10)", "leitura": "juro pode não cobrir a perda esperada"},
    "dentro_da_margem": {"rotulo": "Dentro da margem", "icone": "=", "cor": "#8cc7a1",
                         "fundo": "rgba(140,199,161,.10)", "leitura": "preço compatível com o risco"},
    "revisao_manual": {"rotulo": "Revisão manual", "icone": "!", "cor": "#9aa5b5",
                       "fundo": "rgba(154,165,181,.10)", "leitura": "dados fora da faixa de treino"},
}

RECOMENDACOES = {
    "manter_preco": "Manter preço",
    "revisar_preco": "Revisar preço",
    "encaminhar_compliance": "Encaminhar ao compliance",
    "revisao_manual": "Revisão manual",
}

UNIDADE_JURO = " a.a. nominal"
COR_AUMENTA = "#d9825b"
COR_REDUZ = "#7fa7d9"


def distancia_da_margem_pp(r: dict) -> float | None:
    """Quanto o juro cobrado passa da margem de incerteza, em pontos percentuais."""
    cobrado, jmin, jmax = r.get("juro_cobrado"), r.get("juro_justo_min"), r.get("juro_justo_max")
    if None in (cobrado, jmin, jmax):
        return None
    if cobrado > jmax:
        return round((cobrado - jmax) * 100, 1)
    if cobrado < jmin:
        return round((cobrado - jmin) * 100, 1)
    return 0.0


def badge(texto: str, cor: str, fundo: str | None = None) -> str:
    fundo = fundo or "rgba(255,255,255,.05)"
    return (f'<span class="ap-badge" style="color:{cor};background:{fundo};'
            f'border-color:{cor}55">{esc(texto)}</span>')


def badge_situacao(situacao: str) -> str:
    s = SITUACOES.get(situacao, SITUACOES["revisao_manual"])
    return badge(s["rotulo"], s["cor"], s["fundo"])


# ---------------------------------------------------------------- revisão de contrato

def html_kpi(rotulo: str, valor: str, unidade: str = "", sub: str = "", extra: str = "",
             destaque: dict | None = None) -> str:
    estilo = ""
    cor_valor = ""
    if destaque:  # cartão da situação: cor da situação e fonte menor (texto, não número)
        estilo = f'style="border-color:{destaque["cor"]}66;background:{destaque["fundo"]}"'
        cor_valor = f'style="color:{destaque["cor"]};font-size:1.75rem;white-space:nowrap"'
    return compactar(f"""
        <div class="ap-kpi" {estilo}>
            <div class="ap-kpi-label">{esc(rotulo)}</div>
            <div class="ap-kpi-value" {cor_valor}>{valor}<span class="ap-kpi-unit">{esc(unidade)}</span></div>
            <div class="ap-kpi-sub">{sub}</div>
            {extra}
        </div>
    """)


def casas_juros(r: dict) -> int:
    """Casas decimais dos juros: 1; ou 2 quando dois juros diferentes ficariam iguais com 1 casa
    (mesma regra do parecer, genai/src/checagem.py: evita "30,6% abaixo de 30,6%")."""
    juros = [v for v in (r.get("juro_cobrado"), r.get("juro_justo"), r.get("juro_justo_min"),
                         r.get("juro_justo_max")) if v is not None]
    for i, a in enumerate(juros):
        for b in juros[i + 1:]:
            if abs(a - b) > 1e-9 and pct(a) == pct(b):
                return 2
    return 1


def kpis_revisao(r: dict) -> list[str]:
    """Os 4 cartões do topo: risco, juro cobrado, juro justo e situação."""
    situacao = r.get("situacao_preco", "revisao_manual")
    s = SITUACOES.get(situacao, SITUACOES["revisao_manual"])
    casas = casas_juros(r)
    ic = r.get("pd_ic95")
    ic_txt = f"IC 95%: {pct(ic[0])} – {pct(ic[1])}" if ic else "Chance estimada de não pagar"
    faixa = r.get("faixa")
    faixa_html = (f'<span class="ap-faixa">Faixa {esc(faixa)}</span>' if faixa
                  else '<span class="ap-faixa ap-faixa-off">Sem faixa</span>')

    if r.get("juro_justo") is None:
        justo_sub = "Não calculado: dados fora da faixa de treino"
    else:
        justo_sub = f"Margem de incerteza: {pct(r.get('juro_justo_min'), casas)} – {pct(r.get('juro_justo_max'), casas)}"
    if r.get("juro_pares_mediana") is not None:  # segunda opinião: não muda a situação
        justo_sub += f"<br>Mediana dos pares: {pct(r['juro_pares_mediana'])}"

    dist = distancia_da_margem_pp(r)
    if situacao == "revisao_manual":
        sit_sub = "PD e juro justo não calculados; analista revisa os dados"
    elif situacao == "dentro_da_margem":
        sit_sub = "diferença menor que a incerteza do modelo"
    else:
        sit_sub = f"{pp(dist)} além da margem de incerteza"

    pd_valor = pct(r.get("pd")) if r.get("pd") is not None else "—"
    return [
        html_kpi("Risco de inadimplência", pd_valor, "", esc(ic_txt),
                 extra=f'<div class="ap-kpi-foot">{faixa_html}</div>'),
        html_kpi("Juro cobrado", pct(r.get("juro_cobrado"), casas), UNIDADE_JURO, "Taxa do contrato"),
        html_kpi("Juro justo calculado", pct(r.get("juro_justo"), casas), UNIDADE_JURO if r.get("juro_justo") else "",
                 justo_sub),  # justo_sub só tem números formatados por pct() e texto fixo
        html_kpi("Situação do preço", f'{s["icone"]} {esc(s["rotulo"])}', "", esc(sit_sub), destaque=s),
    ]


def _escala(*valores: float) -> float:
    """Fim do eixo: no mínimo 40%, arredondado para cima de 10 em 10 pontos."""
    maior = max([v for v in valores if v is not None] + [0.0])
    return max(0.40, math.ceil(maior * 1.15 * 10) / 10)


def html_barra_juros(r: dict) -> str:
    """Régua horizontal: margem de incerteza (faixa), juro justo e juro cobrado."""
    cobrado, justo = r.get("juro_cobrado"), r.get("juro_justo")
    jmin, jmax = r.get("juro_justo_min"), r.get("juro_justo_max")
    if None in (cobrado, justo, jmin, jmax):
        return ""
    escala = _escala(cobrado, jmax)
    pos = lambda v: min(max(v / escala * 100, 0), 100)  # noqa: E731
    cor_cobrado = SITUACOES.get(r.get("situacao_preco"), SITUACOES["dentro_da_margem"])["cor"]
    passo = 0.1 if escala <= 0.6 else 0.2 if escala <= 1.2 else 0.5
    n_marcas = int(round(escala / passo))
    marcas = "".join(
        f'<span class="ap-tick" style="left:{pos(i * passo)}%">{pct(i * passo, 0)}</span>'
        for i in range(n_marcas + 1))
    # rótulos acima (justo) e abaixo (cobrado) para não se sobreporem
    return compactar(f"""
        <div class="ap-ruler">
            <div class="ap-ruler-track">
                <div class="ap-ruler-band" style="left:{pos(jmin)}%;width:{pos(jmax) - pos(jmin)}%"></div>
                <div class="ap-ruler-mark" style="left:{pos(justo)}%;background:#e4bd7d"></div>
                <div class="ap-ruler-label ap-up" style="left:{pos(justo)}%;color:#e4bd7d">Justo {pct(justo, casas_juros(r))}</div>
                <div class="ap-ruler-mark" style="left:{pos(cobrado)}%;background:{cor_cobrado}"></div>
                <div class="ap-ruler-label ap-down" style="left:{pos(cobrado)}%;color:{cor_cobrado}">Cobrado {pct(cobrado, casas_juros(r))}</div>
            </div>
            <div class="ap-ruler-ticks">{marcas}</div>
        </div>
        <div class="ap-legend">
            <span><i style="background:rgba(228,189,125,.28)"></i>Margem de incerteza do modelo</span>
            <span>Juros nominais ao ano. Juro justo = custo do dinheiro (Euribor da época) + perda esperada ao longo do contrato + custos e margem calibrados na safra</span>
        </div>
    """)


TEMPO_EMPREGO = {
    "TrialPeriod": "em período de experiência", "UpTo1Year": "até 1 ano", "UpTo2Years": "até 2 anos",
    "UpTo3Years": "até 3 anos", "UpTo4Years": "até 4 anos", "UpTo5Years": "até 5 anos",
    "MoreThan5Years": "mais de 5 anos", "Retiree": "aposentado", "Other": "outro",
}
# Códigos do dicionário do Bondora (conferir com o glossário do Marcos).
CODIGOS = {
    "escolaridade": {"1": "fundamental", "2": "básico", "3": "técnico", "4": "médio", "5": "superior"},
    "tipo_verificacao": {"1": "renda não verificada", "2": "renda conferida por telefone",
                         "3": "renda verificada", "4": "renda e despesas verificadas"},
    "tipo_moradia": {"0": "sem moradia", "1": "própria", "2": "com os pais", "3": "aluguel mobiliado",
                     "4": "aluguel sem mobília", "5": "moradia social", "6": "aluguel compartilhado",
                     "7": "propriedade conjunta", "8": "financiada", "9": "própria com ônus", "10": "outra"},
}
EM_EURO = {"valor_concedido", "renda_total", "valor_emprestimos_anteriores"}
VEZES_A_RENDA = {"valor_sobre_renda", "divida_sobre_renda"}  # podem passar de 1: "6,1× a renda"
QUANTIDADES = {"passivos_existentes", "n_emprestimos_anteriores", "quitacoes_antecipadas_qtd"}


def _codigo(valor) -> str:
    """'5', 5, 5.0 e '5.0' viram '5'."""
    try:
        return str(int(float(valor)))
    except (TypeError, ValueError):
        return str(valor)


def valor_legivel(variavel: str, valor) -> str | None:
    """Valor do motivo como o analista lê (None = não mostrar)."""
    if valor is None or str(valor) in ("", "sem_info", "outros", "nan", "None", "<NA>"):
        return None
    if variavel in VEZES_A_RENDA:
        return f"{_num(float(valor), 1)}× a renda mensal"
    if variavel == "parcela_neutra_sobre_renda":
        return f"{pct(float(valor), 0)} da renda"
    if variavel == "renda_relativa":
        return f"{_num(float(valor), 1)}× a mediana do país"
    if variavel in EM_EURO:
        return eur(float(valor))
    if variavel == "prazo_meses":
        return f"{_codigo(valor)} meses"
    if variavel in QUANTIDADES:
        return _codigo(valor)
    if variavel == "tempo_emprego_atual":
        return TEMPO_EMPREGO.get(str(valor), str(valor))
    if variavel in CODIGOS:
        return CODIGOS[variavel].get(_codigo(valor), _codigo(valor))
    if variavel == "novo_cliente":
        return "sim" if str(valor).lower() in ("true", "1", "sim") else "não"
    if isinstance(valor, float) or variavel == "score_ee_mini":
        numero = float(valor)
        return _num(numero, 0 if numero.is_integer() or abs(numero) >= 10 else 2)
    return str(valor)


def _descricao_motivo(m: dict) -> str:
    rotulo = esc(m.get("rotulo") or m.get("variavel"))
    try:
        valor = valor_legivel(m.get("variavel", ""), m.get("valor"))
    except (TypeError, ValueError):
        valor = str(m.get("valor"))
    if not valor:
        return rotulo
    return f'{rotulo}: <span class="ap-muted">{esc(valor)}</span>'


def html_motivos(motivos: list[dict]) -> str:
    """Barras dos motivos SHAP: comprimento = peso relativo; cor = efeito."""
    if not motivos:
        return '<div class="ap-empty">Sem motivos: o modelo não foi aplicado a este contrato.</div>'
    pesos = [m.get("peso") or 0 for m in motivos]
    maior = max(pesos) or 1
    linhas = []
    for m, peso in zip(motivos, pesos):
        cor = COR_AUMENTA if m.get("efeito") == "aumenta_risco" else COR_REDUZ
        largura = 8 + 92 * (peso / maior) if peso else 40
        peso_txt = pct(peso, 0) if peso else ""
        linhas.append(f"""
            <div class="ap-factor">
                <div class="ap-factor-name">{_descricao_motivo(m)}</div>
                <div class="ap-factor-bar"><div style="width:{largura}%;background:{cor}"></div></div>
                <div class="ap-factor-w">{peso_txt}</div>
            </div>""")
    return compactar("".join(linhas) + f"""
        <div class="ap-legend">
            <span><i style="background:{COR_AUMENTA}"></i>Aumenta o risco</span>
            <span><i style="background:{COR_REDUZ}"></i>Reduz o risco</span>
        </div>""")


def html_parecer(parecer: dict | None) -> str:
    if not parecer:
        return ('<div class="ap-empty">Parecer indisponível nesta consulta. '
                'Os números acima continuam válidos para a decisão.</div>')
    if parecer.get("origem") == "llm":
        origem = badge("Gerado por IA · revise antes de decidir", "#e4bd7d", "rgba(228,189,125,.10)")
    else:
        origem = badge("Template de reserva · sem IA", "#9aa5b5")
    pontos = "".join(f"<li>{esc(p)}</li>" for p in parecer.get("pontos_de_atencao", []))
    fontes = parecer.get("fontes") or []
    if fontes:
        fontes_html = "".join(
            f'<span class="ap-chip" title="{esc(f.get("trecho_id"))}">'
            f'{esc(f.get("norma"))}, {esc(f.get("artigo"))}</span>' for f in fontes)
    else:
        fontes_html = '<span class="ap-muted">Não encontrei base normativa para este caso.</span>'
    rec = RECOMENDACOES.get(parecer.get("recomendacao"), parecer.get("recomendacao"))
    contexto = ""
    if parecer.get("contexto_mercado"):  # frase fixa escrita pelo código (média do BC), nunca pelo LLM
        contexto = (f'<div class="ap-sec">Referência de mercado (Brasil)</div>'
                    f'<div class="ap-mercado">{esc(parecer["contexto_mercado"])}</div>')
    return compactar(f"""
        <div class="ap-parecer-head">
            <div class="ap-card-title">Parecer</div>{origem}
        </div>
        <div class="ap-sec">Resumo</div>
        <p class="ap-text">{esc(parecer.get("resumo"))}</p>
        <div class="ap-sec">Pontos de atenção</div>
        <ul class="ap-list">{pontos or "<li>Nenhum.</li>"}</ul>
        <div class="ap-sec">Recomendação do sistema · {esc(rec)}</div>
        <p class="ap-text">{esc(parecer.get("recomendacao_texto"))}</p>
        <div class="ap-sec">Fontes consultadas</div>
        <div class="ap-chips">{fontes_html}</div>
        {contexto}
        <div class="ap-foot">Versão do texto: {esc(parecer.get("versao_prompt"))}</div>
    """)


# ---------------------------------------------------------------- carteira

def html_barras_faixa(tabela: list[dict]) -> str:
    """tabela = [{"faixa": "A", "abaixo_do_justo": 0.1, "dentro_da_margem": 0.7, "acima_do_justo": 0.2, "n": 120}]"""
    ordem = ["abaixo_do_justo", "dentro_da_margem", "acima_do_justo"]
    linhas = []
    for linha in tabela:
        segmentos = "".join(
            f'<div title="{SITUACOES[s]["rotulo"]}: {pct(linha.get(s, 0))}" '
            f'style="width:{linha.get(s, 0) * 100}%;background:{SITUACOES[s]["cor"]}"></div>'
            for s in ordem)
        linhas.append(f"""
            <div class="ap-stack-row">
                <div class="ap-stack-label">Faixa {esc(linha["faixa"])}</div>
                <div class="ap-stack">{segmentos}</div>
                <div class="ap-stack-n">{_num(linha.get("n", 0), 0)}</div>
            </div>""")
    legenda = "".join(f'<span><i style="background:{SITUACOES[s]["cor"]}"></i>{SITUACOES[s]["rotulo"]}</span>'
                      for s in ordem)
    return compactar("".join(linhas) + f'<div class="ap-legend">{legenda}</div>')


def leitura_equidade(ic_min, ic_max) -> tuple[str, str, str]:
    """IC 95% que cruza o zero = sem indício; que não cruza = indício a investigar."""
    if ic_min is None or ic_max is None:
        return "Aguardando análise", "#9aa5b5", "rgba(154,165,181,.10)"
    if ic_min <= 0 <= ic_max:
        return "Sem indício", "#8cc7a1", "rgba(140,199,161,.10)"
    return "Indício · investigar", "#e8a462", "rgba(232,164,98,.10)"


def html_tabela_equidade(linhas: list[dict]) -> str:
    corpo = []
    for e in linhas:
        leitura = badge(*leitura_equidade(e.get("ic95_min"), e.get("ic95_max")))
        if e.get("ic95_min") is None:
            ic = "[a – b]"
        else:
            ic = f'{pp(e.get("ic95_min"), sinal=True)} a {pp(e.get("ic95_max"), sinal=True)}'
        dif = "[+0,0 pp]" if e.get("diferenca_pp") is None else pp(e.get("diferenca_pp"))
        n = ""
        if e.get("n_grupo_a") is not None:
            n = f'<div class="ap-muted ap-small">n = {_num(e["n_grupo_a"], 0)} × {_num(e["n_grupo_b"], 0)}</div>'
        corpo.append(f"""
            <tr><td><b>{esc(e.get("atributo"))}</b> · {esc(e.get("comparacao"))}{n}</td>
            <td>{dif}</td><td>{ic}</td><td>{leitura}</td></tr>""")
    return compactar(f"""
        <table class="ap-table">
            <thead><tr><th>Comparação</th><th>Diferença</th><th>IC 95%</th><th>Leitura</th></tr></thead>
            <tbody>{"".join(corpo)}</tbody>
        </table>
    """)