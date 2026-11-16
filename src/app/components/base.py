"""Formatação brasileira (%, €, p.p.), situações do preço, selos, cartão de número, ícone "i" e ícones de linha.
"""
from __future__ import annotations

import html
import math

__all__ = ["COUNTRIES", "esc", "pct", "pp", "eur", "compact", "SITUATIONS", "RECOMMENDATIONS", "RATE_UNIT",
           "COLOR_INCREASES", "COLOR_DECREASES", "margin_distance_pp", "badge", "situation_badge", "html_kpi",
           "INFO", "info_tip", "line_icon"]


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
    "dados": "Os dados do contrato e do cliente que o modelo de risco usou. Gênero e idade não estão aqui: "
             "não entram no modelo.",
    "equidade": "Clientes com o mesmo risco pagam juros diferentes por gênero ou idade? A barra mostra a "
                "diferença de juro (cobrado − justo) entre os grupos e a faixa de confiança de 95%. Se a faixa "
                "não cruza o zero, a diferença é um indício a investigar.",
    "invariancia": "Roda o modelo com o gênero e a idade reais e de novo com os dois trocados. Como nenhum dos "
                   "dois entra no modelo, o resultado tem de ser idêntico. Não prova que o preço é justo: isso é "
                   "a equidade.",
    "resultado": "O que aconteceu de verdade com o contrato depois da concessão. Só existe para contratos já "
                 "encerrados.",
}


def info_tip(key: str) -> str:
    """Ícone "i" no canto do cartão; clicar abre a explicação (details/summary: funciona sem JavaScript)."""
    text = INFO.get(key, key)
    return (f'<details class="ap-info"><summary title="O que é isto?">i</summary>'
            f'<div class="ap-info-box">{esc(text)}</div></details>')


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
