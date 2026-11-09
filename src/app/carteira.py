"""Dados do painel de auditoria da carteira.

O painel NÃO calcula juro justo nem equidade: só lê e resume o que o lote do Samuel grava.
Arquivos esperados (pasta CARTEIRA_DIR, padrão docs/resultados/):

carteira_auditoria.csv — uma linha por contrato pontuado
    obrigatórias: contrato_id, ano, pais, pd, faixa, juro_cobrado, juro_justo,
                  juro_justo_min, juro_justo_max, situacao_preco   (juros em fração)
    opcionais:    valor_concedido, prazo_meses, fora_da_auditoria (reestruturados),
                  excesso_eur: só acima_do_justo; prazo × (parcela no juro cobrado − parcela
                      no juro_justo_max), com i/12: o que o cliente paga acima do teto da margem
                  perda_nao_coberta_eur: só encerrados; max(0, −resultado_eur) da vw_retorno_realizado
                  rentabilidade_realizada: retorno_realizado da vw_retorno_realizado (vazio em 2017–2021)
    Contratos: 2016 (teste) e 2017–2021, pontuados pelo prever(). Formato aprovado pelo Samuel em 06/11.

equidade.json — lista de comparações (só gênero e idade; país é controle, não grupo)
    [{"atributo": "Gênero", "comparacao": "feminino × masculino", "diferenca_pp": 0.4,
      "ic95_min": -0.1, "ic95_max": 0.9, "n_grupo_a": 5100, "n_grupo_b": 6200}]
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
CARTEIRA_DIR = Path(os.getenv("CARTEIRA_DIR", RAIZ / "docs" / "resultados"))
ARQ_CARTEIRA = "carteira_auditoria.csv"
ARQ_EQUIDADE = "equidade.json"

OBRIGATORIAS = ["contrato_id", "ano", "pais", "pd", "faixa", "juro_cobrado", "juro_justo",
                "juro_justo_min", "juro_justo_max", "situacao_preco"]
FAIXAS = ["A", "B", "C", "D", "E"]
SITUACOES_PRECO = ["abaixo_do_justo", "dentro_da_margem", "acima_do_justo"]

# Linhas que aparecem enquanto a análise de equidade não chega (mesmo layout do protótipo).
EQUIDADE_VAZIA = [
    {"atributo": "Gênero", "comparacao": "feminino × masculino (dentro do país)"},
    {"atributo": "Idade", "comparacao": "18–25 × 35–44 anos"},
]


def carregar_carteira(pasta: Path = CARTEIRA_DIR) -> pd.DataFrame | None:
    caminho = Path(pasta) / ARQ_CARTEIRA
    if not caminho.exists():
        return None
    df = pd.read_csv(caminho)
    faltando = [c for c in OBRIGATORIAS if c not in df.columns]
    if faltando:
        raise ValueError(f"{ARQ_CARTEIRA} sem as colunas: {', '.join(faltando)}")
    if "fora_da_auditoria" in df.columns:  # reestruturados: fora da comparação de preço
        df = df[~df["fora_da_auditoria"].fillna(False).astype(bool)]
    return df


def carregar_equidade(pasta: Path = CARTEIRA_DIR) -> list[dict] | None:
    caminho = Path(pasta) / ARQ_EQUIDADE
    if not caminho.exists():
        return None
    linhas = json.loads(caminho.read_text(encoding="utf-8"))
    # Regra do guia v2: país nunca é grupo auditado.
    return [e for e in linhas if str(e.get("atributo", "")).lower() not in {"país", "pais"}]


def filtrar(df: pd.DataFrame, anos: tuple[int, int] | None = None,
            pais: str | None = None, faixa: str | None = None) -> pd.DataFrame:
    out = df
    if anos:
        out = out[out["ano"].between(*anos)]
    if pais:
        out = out[out["pais"] == pais]
    if faixa:
        out = out[out["faixa"] == faixa]
    return out


def resumo(df: pd.DataFrame) -> dict:
    """Números dos cartões do topo. Revisão manual conta à parte (sem juro justo)."""
    auditados = df[df["situacao_preco"].isin(SITUACOES_PRECO)]
    n = len(auditados)

    def fracao(situacao):
        return (auditados["situacao_preco"] == situacao).mean() if n else None

    def soma(coluna, situacao):
        if coluna not in df.columns:
            return None
        return float(auditados.loc[auditados["situacao_preco"] == situacao, coluna].sum())

    return {
        "auditados": n,
        "revisao_manual": int((df["situacao_preco"] == "revisao_manual").sum()),
        "acima": fracao("acima_do_justo"),
        "abaixo": fracao("abaixo_do_justo"),
        "pago_a_mais_eur": soma("excesso_eur", "acima_do_justo"),
        "perda_nao_coberta_eur": soma("perda_nao_coberta_eur", "abaixo_do_justo"),
    }


def por_faixa(df: pd.DataFrame) -> list[dict]:
    auditados = df[df["situacao_preco"].isin(SITUACOES_PRECO)]
    linhas = []
    for faixa in FAIXAS:
        grupo = auditados[auditados["faixa"] == faixa]
        if grupo.empty:
            continue
        prop = grupo["situacao_preco"].value_counts(normalize=True)
        linhas.append({"faixa": faixa, "n": len(grupo),
                       **{s: float(prop.get(s, 0.0)) for s in SITUACOES_PRECO}})
    return linhas


def backtest(df: pd.DataFrame) -> pd.DataFrame | None:
    """Rentabilidade realizada média por faixa × situação (guia v2: comparar DENTRO da faixa).
    Esperado: abaixo < dentro < acima em cada faixa."""
    if "rentabilidade_realizada" not in df.columns:
        return None
    base = df[df["situacao_preco"].isin(SITUACOES_PRECO) & df["rentabilidade_realizada"].notna()]
    if base.empty:
        return None
    tabela = (base.pivot_table(index="faixa", columns="situacao_preco",
                               values="rentabilidade_realizada", aggfunc="mean")
              .reindex(index=[f for f in FAIXAS if f in set(base["faixa"])],
                       columns=SITUACOES_PRECO))
    return tabela


def fila_revisao(df: pd.DataFrame, limite: int | None = 50) -> pd.DataFrame:
    """Contratos fora da margem, do mais distante para o mais próximo da margem."""
    fora = df[df["situacao_preco"].isin(["acima_do_justo", "abaixo_do_justo"])].copy()
    acima = fora["situacao_preco"] == "acima_do_justo"
    fora["distancia_pp"] = ((fora["juro_cobrado"] - fora["juro_justo_max"]).where(acima,
                            fora["juro_justo_min"] - fora["juro_cobrado"]) * 100).round(1)
    fora = fora.sort_values("distancia_pp", ascending=False)
    return fora if limite is None else fora.head(limite)


COLUNAS_EXPORTACAO = ["contrato_id", "ano", "pais", "faixa", "pd", "juro_cobrado", "juro_justo",
                      "juro_justo_min", "juro_justo_max", "juro_pares_mediana", "situacao_preco",
                      "distancia_pp", "excesso_eur", "perda_nao_coberta_eur"]


def exportar_fila(df: pd.DataFrame) -> bytes:
    """Fila completa de revisão em CSV (UTF-8 com BOM, abre certo no Excel), só com as colunas úteis."""
    fila = fila_revisao(df, limite=None)
    colunas = [c for c in COLUNAS_EXPORTACAO if c in fila.columns]
    return fila[colunas].to_csv(index=False).encode("utf-8-sig")
