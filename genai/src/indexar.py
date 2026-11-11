"""
Grava os trechos das normas no PostgreSQL (pgvector), com o embedding de cada um.
Pode ser rodado quantas vezes quiser: apaga a tabela e recria do zero.

Antes de rodar:
  1. Banco no ar:  docker compose up -d db
  2. No .env da raiz:  DATABASE_URL=postgresql://postgres:postgres@localhost:5432/auditor_db

Como rodar (na pasta raiz do repositório):
    python genai/src/indexar.py
"""
import os

import psycopg2
from dotenv import load_dotenv
from pgvector.psycopg2 import register_vector
from psycopg2.extras import execute_values
from sentence_transformers import SentenceTransformer

try:  # funciona como "python genai/src/indexar.py" e como "python -m genai.src.indexar"
    from genai.src.dividir import dividir_normas
except ImportError:
    from dividir import dividir_normas

MODELO = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"  # multilíngue, 384 dimensões
DIMENSAO = 384
TABELA = "trechos_normas"


def texto_para_embedding(trecho):
    """O que vira vetor: nome da norma + artigo + texto (ajuda a busca a achar a norma certa)."""
    return f"{trecho['norma']}, {trecho['artigo']}\n{trecho['texto']}"


def conectar():
    load_dotenv()
    url = os.getenv("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL não encontrada. Confira o arquivo .env na pasta raiz.")
    conexao = psycopg2.connect(url)
    with conexao.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    conexao.commit()
    register_vector(conexao)
    return conexao


def main():
    trechos = dividir_normas()
    print(f"{len(trechos)} trechos lidos das normas.")

    print("Carregando o modelo de embeddings (na 1ª vez, ele é baixado, ~470 MB)...")
    modelo = SentenceTransformer(MODELO)
    vetores = modelo.encode(
        [texto_para_embedding(t) for t in trechos],
        normalize_embeddings=True,
        show_progress_bar=True,
    )

    conexao = conectar()
    with conexao.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS {TABELA};")
        cur.execute(f"""
            CREATE TABLE {TABELA} (
                trecho_id  TEXT PRIMARY KEY,
                norma      TEXT NOT NULL,
                artigo     TEXT NOT NULL,
                parte      INTEGER NOT NULL,
                arquivo    TEXT NOT NULL,
                url        TEXT NOT NULL,
                texto      TEXT NOT NULL,
                embedding  vector({DIMENSAO}) NOT NULL
            );
        """)
        linhas = [
            (t["trecho_id"], t["norma"], t["artigo"], t["parte"], t["arquivo"], t["url"], t["texto"], v)
            for t, v in zip(trechos, vetores)
        ]
        execute_values(
            cur,
            f"INSERT INTO {TABELA} (trecho_id, norma, artigo, parte, arquivo, url, texto, embedding) VALUES %s",
            linhas,
        )
    conexao.commit()

    with conexao.cursor() as cur:
        cur.execute(f"SELECT norma, COUNT(*) FROM {TABELA} GROUP BY norma ORDER BY norma;")
        print(f"\nTabela {TABELA} criada:")
        for norma, qtd in cur.fetchall():
            print(f"  {norma}: {qtd} trechos")
    conexao.close()


if __name__ == "__main__":
    main()