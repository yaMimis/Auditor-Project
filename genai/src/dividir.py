"""
<<<<<<< HEAD
Divide as normas de genai/normas/*.md em trechos: um trecho por artigo.
Artigos longos viram mais de um trecho, sempre quebrando entre linhas
(incisos, parágrafos), nunca no meio de uma frase.
=======
Divide as normas de genai/normas/*.md em trechos.

- Leis e resoluções (arquivos com "Art."): um trecho por artigo. Artigos longos
  viram mais de um trecho, sempre quebrando entre linhas (incisos, parágrafos).
- Relatórios sem artigos (ex.: ref.md): um trecho por parágrafo do texto.
>>>>>>> 1f820b3c914b802dbd014244569ce101f8323b73

Como rodar (na pasta raiz do repositório):
    python genai/src/dividir.py
"""
import random
import re
from pathlib import Path

PASTA_NORMAS = Path("genai/normas")
TAMANHO_MAXIMO = 1000  # caracteres por trecho
TAMANHO_MINIMO = 300   # pedaço final menor que isso é juntado ao anterior
TAMANHO_CAPUT = 150    # quanto do caput é repetido nas partes seguintes


def ler_norma(caminho):
<<<<<<< HEAD
    """Lê o arquivo e pega o nome da norma na 1ª linha ('# LGPD — ...' -> 'LGPD')."""
    texto = caminho.read_text(encoding="utf-8-sig")
    titulo = texto.strip().splitlines()[0].lstrip("#").strip()
    norma = titulo.split("—")[0].strip()
    return norma, texto
=======
    """Lê o arquivo e pega o nome da norma na 1ª linha ('# LGPD — ...' -> 'LGPD')
    e o link oficial na linha que começa com 'URL:'."""
    texto = caminho.read_text(encoding="utf-8-sig")
    titulo = texto.strip().splitlines()[0].lstrip("#").strip()
    norma = titulo.split("—")[0].strip()
    achado = re.search(r"^URL:\s*(\S+)", texto, re.MULTILINE)
    if not achado:
        raise SystemExit(f"{caminho.name}: falta a linha 'URL: <link>' no cabeçalho.")
    return norma, achado.group(1), texto
>>>>>>> 1f820b3c914b802dbd014244569ce101f8323b73


def separar_artigos(texto):
    """Quebra o texto antes de cada linha que começa com 'Art. <número>'."""
    partes = re.split(r"\n(?=Art\. \d)", texto)
    # A 1ª parte é o cabeçalho do arquivo (não começa com 'Art.'): fica de fora.
    return [p.strip() for p in partes if p.strip().startswith("Art.")]


<<<<<<< HEAD
=======
def separar_paragrafos(texto):
    """Para documentos sem artigos: devolve os parágrafos do corpo do texto,
    pulando o título (#) e as linhas de cabeçalho 'URL:' e 'Fonte:'."""
    blocos = re.split(r"\n\s*\n", texto.strip())
    cabecalho = ("#", "URL:", "Fonte:")
    return [b.strip() for b in blocos if b.strip() and not b.strip().startswith(cabecalho)]


>>>>>>> 1f820b3c914b802dbd014244569ce101f8323b73
def numero_do_artigo(artigo_texto):
    """'Art. 5º Para os fins...' -> 'Art. 5º';  'Art. 54-A. Este...' -> 'Art. 54-A'."""
    return re.match(r"Art\. \d+º?(?:-[A-Z])?", artigo_texto).group(0)


def quebrar_artigo(artigo_texto):
    """Se o artigo passar do tamanho máximo, divide por linhas.
    Cada parte depois da 1ª repete o início do caput, para não perder o contexto.
    Um pedaço final muito curto é juntado ao anterior, para não ficar solto."""
    if len(artigo_texto) <= TAMANHO_MAXIMO:
        return [artigo_texto]

    linhas = artigo_texto.splitlines()
    caput = linhas[0]
    # Na repetição, usa só o começo do caput (alguns caputs são muito longos).
    resumo = caput if len(caput) <= TAMANHO_CAPUT else caput[:TAMANHO_CAPUT].rsplit(" ", 1)[0] + "…"
    cabecalho = resumo + " (continuação)"

    partes, atual = [], [caput]
    for linha in linhas[1:]:
        tamanho = len("\n".join(atual + [linha]))
        if tamanho > TAMANHO_MAXIMO and len(atual) > 1:
            partes.append(atual)
            atual = [cabecalho, linha]
        else:
            atual.append(linha)
    partes.append(atual)

    # Se a última parte ficou curta demais, junta com a anterior.
    if len(partes) > 1 and len("\n".join(partes[-1][1:])) < TAMANHO_MINIMO:
        sobra = partes.pop()
        partes[-1].extend(sobra[1:])

    return ["\n".join(p) for p in partes]


def dividir_normas():
    """Devolve a lista de trechos de todas as normas, cada um com seus metadados."""
    trechos = []
    for caminho in sorted(PASTA_NORMAS.glob("*.md")):
        if caminho.name == "FONTES.md":
            continue
<<<<<<< HEAD
        norma, texto = ler_norma(caminho)
        for artigo_texto in separar_artigos(texto):
            artigo = numero_do_artigo(artigo_texto)
            slug = re.sub(r"[^0-9a-z]", "", artigo.lower())  # 'Art. 54-A' -> 'art54a'
            for i, parte in enumerate(quebrar_artigo(artigo_texto), start=1):
=======
        norma, url, texto = ler_norma(caminho)
        artigos = separar_artigos(texto)
        if artigos:  # lei ou resolução: um bloco por artigo
            blocos = [(numero_do_artigo(a), a) for a in artigos]
        else:        # relatório: um bloco por parágrafo
            blocos = [(f"parágrafo {n}", p) for n, p in enumerate(separar_paragrafos(texto), start=1)]
        for artigo, bloco_texto in blocos:
            # 'Art. 54-A' -> 'art54a';  'parágrafo 3' -> 'p3'
            slug = re.sub(r"[^0-9a-z]", "", artigo.lower()) if artigo.startswith("Art.") else "p" + artigo.split()[-1]
            for i, parte in enumerate(quebrar_artigo(bloco_texto), start=1):
>>>>>>> 1f820b3c914b802dbd014244569ce101f8323b73
                trechos.append({
                    "trecho_id": f"{caminho.stem}-{slug}-{i}",
                    "norma": norma,
                    "artigo": artigo,
                    "parte": i,
                    "arquivo": caminho.name,
<<<<<<< HEAD
=======
                    "url": url,
>>>>>>> 1f820b3c914b802dbd014244569ce101f8323b73
                    "texto": parte,
                })
    return trechos


if __name__ == "__main__":
    trechos = dividir_normas()

    print(f"Total: {len(trechos)} trechos\n")
    for norma in sorted({t["norma"] for t in trechos}):
        qtd = sum(1 for t in trechos if t["norma"] == norma)
        print(f"  {norma}: {qtd} trechos")

    maior = max(trechos, key=lambda t: len(t["texto"]))
    print(f"\nMaior trecho: {maior['trecho_id']} ({len(maior['texto'])} caracteres)")

    print("\n10 trechos aleatórios para conferir:")
    for t in random.sample(trechos, min(10, len(trechos))):
        print(f"\n--- {t['trecho_id']} | {t['norma']}, {t['artigo']} (parte {t['parte']}) ---")
        print(t["texto"][:300] + ("..." if len(t["texto"]) > 300 else ""))