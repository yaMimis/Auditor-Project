"""Desenha o DER em 16:9 (3840x2160) para slides, a partir de der_banco.mmd.

O layout vertical gerado pelo Mermaid (der_banco.png) continua sendo o oficial;
esta versão só reorganiza as mesmas tabelas em quatro colunas.

Uso: python docs/der/gerar_der_16x9.py  ->  docs/der/der_banco_16x9.png
"""

import re
from pathlib import Path

import matplotlib
from PIL import Image, ImageDraw, ImageFont

AQUI = Path(__file__).resolve().parent
ENTRADA = AQUI / "der_banco.mmd"
SAIDA = AQUI / "der_banco_16x9.png"

W, H = 3840, 2160
MARGEM_Y = 60
MARGEM_X = 80

# Colunas do slide, de cima para baixo em cada uma.
COLUNAS = [
    ["euribor_mensal", "selic_mensal", "bc_credito_pessoal_mensal", "decisao_analista"],
    ["emprestimo"],
    ["cliente", "historico_credito"],
    ["trechos_normas"],
]
# Linha de cada tabela de onde sai a ligação com emprestimo (a linha é horizontal).
LINHA_LIGACAO = {
    "euribor_mensal": "mes",
    "selic_mensal": "mes",
    "bc_credito_pessoal_mensal": "mes",
    "decisao_analista": "contrato_id",
    "cliente": "loan_id",
    "historico_credito": "loan_id",
}
LEGENDA_SOLTA = {"trechos_normas": "sem ligação: base de conhecimento do RAG"}

COR_BORDA = "#9370DB"
COR_CABECALHO = "#ECECFF"
COR_ZEBRA = "#F4F4FF"
COR_TEXTO = "#333333"
COR_LINHA = "#555555"


def ler_mmd(caminho):
    tabelas, relacoes = {}, []
    atual = None
    for bruta in caminho.read_text(encoding="utf-8").splitlines():
        linha = bruta.strip()
        if not linha or linha == "erDiagram":
            continue
        m = re.match(r"^(\w+)\s*\{$", linha)
        if m:
            atual = m.group(1)
            tabelas[atual] = []
            continue
        if linha == "}":
            atual = None
            continue
        if atual:
            partes = linha.split(None, 2)
            chave = partes[2].replace(" ", "") if len(partes) > 2 else ""
            tabelas[atual].append((partes[0], partes[1], chave))
            continue
        m = re.match(r'^(\w+)\s+(\S{2})--(\S{2})\s+(\w+)\s*:\s*"(.*)"$', linha)
        if m:
            relacoes.append(m.groups())
    return tabelas, relacoes


def fonte(nome, tamanho):
    pasta = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
    return ImageFont.truetype(str(pasta / nome), tamanho)


def main():
    tabelas, relacoes = ler_mmd(ENTRADA)
    faltando = {t for col in COLUNAS for t in col} ^ set(tabelas)
    if faltando:
        raise SystemExit(f"Tabelas fora do layout ou ausentes no .mmd: {faltando}")

    # Altura de linha: a coluna mais alta (em linhas, contando cabeçalhos) ocupa a altura útil.
    linhas_col = [sum(len(tabelas[t]) + 1 for t in col) for col in COLUNAS]
    R = (H - 2 * MARGEM_Y) // max(linhas_col)
    tam = round(R * 0.45)
    f_txt = fonte("DejaVuSans.ttf", tam)
    f_cab = fonte("DejaVuSans-Bold.ttf", round(tam * 1.08))
    f_rot = fonte("DejaVuSans.ttf", round(tam * 0.9))
    f_leg = fonte("DejaVuSans-Oblique.ttf", round(tam * 0.9))
    pad = round(tam * 0.7)

    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)

    def larg(texto, f):
        return d.textlength(texto, font=f)

    # Larguras das três colunas internas, iguais para todas as tabelas de uma coluna do slide.
    dims = []
    for col in COLUNAS:
        cols = tabelas_col = [tabelas[t] for t in col]
        w_tipo = max(larg(c[0], f_txt) for t in tabelas_col for c in t) + 2 * pad
        w_nome = max(larg(c[1], f_txt) for t in tabelas_col for c in t) + 2 * pad
        w_chave = max([larg(c[2], f_txt) for t in tabelas_col for c in t] + [larg("PK", f_txt)]) + 2 * pad
        w_total = max(w_tipo + w_nome + w_chave, max(larg(t, f_cab) for t in col) + 2 * pad)
        w_nome += w_total - (w_tipo + w_nome + w_chave)
        dims.append((round(w_tipo), round(w_nome), round(w_chave)))
    larguras = [sum(x) for x in dims]
    vao = min((W - 2 * MARGEM_X - sum(larguras)) / (len(COLUNAS) - 1), 520)
    x = (W - sum(larguras) - vao * (len(COLUNAS) - 1)) / 2

    caixas = {}  # tabela -> (x0, y0, x1, y1, dict nome_coluna -> y_centro)
    for col, (wt, wn, wk), wcol, nlin in zip(COLUNAS, dims, larguras, linhas_col):
        livre = (H - 2 * MARGEM_Y) - nlin * R
        espaco = livre / (len(col) - 1) if len(col) > 1 else 0
        y = MARGEM_Y
        for t in col:
            cols = tabelas[t]
            x0, x1 = round(x), round(x + wcol)
            y0 = round(y)
            # cabeçalho
            d.rectangle([x0, y0, x1, y0 + R], fill=COR_CABECALHO, outline=COR_BORDA, width=2)
            d.text(((x0 + x1) / 2, y0 + R / 2), t, font=f_cab, fill=COR_TEXTO, anchor="mm")
            centros = {}
            for i, (tipo, nome, chave) in enumerate(cols):
                ya = y0 + (i + 1) * R
                d.rectangle([x0, ya, x1, ya + R], fill=COR_ZEBRA if i % 2 else "white",
                            outline=COR_BORDA, width=2)
                d.line([x0 + wt, ya, x0 + wt, ya + R], fill=COR_BORDA, width=2)
                d.line([x0 + wt + wn, ya, x0 + wt + wn, ya + R], fill=COR_BORDA, width=2)
                yc = ya + R / 2
                d.text((x0 + pad, yc), tipo, font=f_txt, fill=COR_TEXTO, anchor="lm")
                d.text((x0 + wt + pad, yc), nome, font=f_txt, fill=COR_TEXTO, anchor="lm")
                if chave:
                    d.text((x0 + wt + wn + wk / 2, yc), chave, font=f_txt, fill=COR_TEXTO, anchor="mm")
                centros[nome] = yc
            y1 = y0 + (len(cols) + 1) * R
            d.rectangle([x0, y0, x1, y1], outline=COR_BORDA, width=3)
            if t in LEGENDA_SOLTA:
                d.text(((x0 + x1) / 2, y1 + R * 0.8), LEGENDA_SOLTA[t], font=f_leg,
                       fill="#777777", anchor="mm")
            caixas[t] = (x0, y0, x1, y1, centros)
            y = y1 + espaco
        x += wcol + vao

    s = R * 0.45  # tamanho dos marcadores
    lw = 3

    def marcador(px, py, u, externo, interno):
        """Pé de galinha na ponta (px, py); u = +1/-1 aponta para fora da tabela."""
        if externo == "many":
            for dy in (-s * 0.55, 0, s * 0.55):
                d.line([px, py + dy, px + u * s, py], fill=COR_LINHA, width=lw)
        else:
            xt = px + u * s * 0.6
            d.line([xt, py - s * 0.5, xt, py + s * 0.5], fill=COR_LINHA, width=lw)
        if interno == "zero":
            r = s * 0.32
            cx = px + u * (s + r + 4)
            d.ellipse([cx - r, py - r, cx + r, py + r], fill="white", outline=COR_LINHA, width=lw)
        else:
            xt = px + u * s * 1.2
            d.line([xt, py - s * 0.5, xt, py + s * 0.5], fill=COR_LINHA, width=lw)

    def ler_card(token, lado):
        # lado esquerdo: externo no índice 0 (|| |o }o }|); direito: externo no índice 1 (|| o| o{ |{)
        ext, inn = (token[0], token[1]) if lado == "esq" else (token[1], token[0])
        return ("many" if ext in "{}" else "one", "zero" if inn == "o" else "one")

    for a, card_a, card_b, b, rotulo in relacoes:
        outra = b if a == "emprestimo" else a
        ya = caixas[outra][4][LINHA_LIGACAO[outra]]
        ax0, _, ax1, _, _ = caixas[a]
        bx0, _, bx1, _, _ = caixas[b]
        # a está à esquerda de b?
        if ax1 < bx0:
            pa, ua, pb, ub = ax1, +1, bx0, -1
        else:
            pa, ua, pb, ub = ax0, -1, bx1, +1
        d.line([pa, ya, pb, ya], fill=COR_LINHA, width=lw)
        marcador(pa, ya, ua, *ler_card(card_a, "esq"))
        marcador(pb, ya, ub, *ler_card(card_b, "dir"))
        xm = (pa + pb) / 2
        caixa = d.textbbox((xm, ya - R * 0.55), rotulo, font=f_rot, anchor="mm")
        d.rectangle([caixa[0] - 6, caixa[1] - 3, caixa[2] + 6, caixa[3] + 3], fill="white")
        d.text((xm, ya - R * 0.55), rotulo, font=f_rot, fill=COR_TEXTO, anchor="mm")

    img.save(SAIDA, optimize=True)
    print(f"{SAIDA} ({img.width}x{img.height}), linha={R}px, fonte={tam}px, vão={vao:.0f}px")


if __name__ == "__main__":
    main()
