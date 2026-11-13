"""Lote da carteira, servido pela API (GET /portfolio/overview e GET /contracts...).

A API NÃO calcula juro justo nem equidade aqui: só lê e resume o que o lote do Samuel grava
(o prever() rodado em toda a carteira). O painel não lê esses arquivos: pede à API.
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

ROOT = Path(__file__).resolve().parents[2]
PORTFOLIO_DIR = Path(os.getenv("CARTEIRA_DIR", ROOT / "docs" / "resultados"))
PORTFOLIO_FILE = "carteira_auditoria.csv"
FAIRNESS_FILE = "equidade.json"

REQUIRED_COLUMNS = ["contrato_id", "ano", "pais", "pd", "faixa", "juro_cobrado", "juro_justo",
                    "juro_justo_min", "juro_justo_max", "situacao_preco"]
BANDS = ["A", "B", "C", "D", "E"]
PRICE_SITUATIONS = ["abaixo_do_justo", "dentro_da_margem", "acima_do_justo"]

def load_portfolio(folder: Path | None = None) -> pd.DataFrame | None:
    path_ = Path(folder or PORTFOLIO_DIR) / PORTFOLIO_FILE  # pasta lida na hora da chamada
    if not path_.exists():
        return None
    df = pd.read_csv(path_)
    missing_columns = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_columns:
        raise ValueError(f"{PORTFOLIO_FILE} sem as colunas: {', '.join(missing_columns)}")
    if "fora_da_auditoria" in df.columns:  # reestruturados: fora da comparação de preço
        df = df[~df["fora_da_auditoria"].fillna(False).astype(bool)]
    return df


def load_fairness(folder: Path | None = None) -> list[dict] | None:
    path_ = Path(folder or PORTFOLIO_DIR) / FAIRNESS_FILE
    if not path_.exists():
        return None
    rows = json.loads(path_.read_text(encoding="utf-8"))
    # Regra do guia v2: país nunca é grupo auditado.
    return [e for e in rows if str(e.get("atributo", "")).lower() not in {"país", "pais"}]


def filter_portfolio(df: pd.DataFrame, years: tuple[int, int] | None = None,
            pais: str | None = None, faixa: str | None = None) -> pd.DataFrame:
    out = df
    if years:
        out = out[out["ano"].between(*years)]
    if pais:
        out = out[out["pais"] == pais]
    if faixa:
        out = out[out["faixa"] == faixa]
    return out


def summarize(df: pd.DataFrame) -> dict:
    """Números dos cartões do topo. Revisão manual conta à parte (sem juro justo)."""
    audited = df[df["situacao_preco"].isin(PRICE_SITUATIONS)]
    n = len(audited)

    def fraction(situation):
        return (audited["situacao_preco"] == situation).mean() if n else None

    def total(column_, situation):
        if column_ not in df.columns:
            return None
        return float(audited.loc[audited["situacao_preco"] == situation, column_].sum())

    return {
        "auditados": n,
        "revisao_manual": int((df["situacao_preco"] == "revisao_manual").sum()),
        "acima": fraction("acima_do_justo"),
        "abaixo": fraction("abaixo_do_justo"),
        "pago_a_mais_eur": total("excesso_eur", "acima_do_justo"),
        "perda_nao_coberta_eur": total("perda_nao_coberta_eur", "abaixo_do_justo"),
    }


def by_band(df: pd.DataFrame) -> list[dict]:
    audited = df[df["situacao_preco"].isin(PRICE_SITUATIONS)]
    rows = []
    for faixa in BANDS:
        group = audited[audited["faixa"] == faixa]
        if group.empty:
            continue
        share = group["situacao_preco"].value_counts(normalize=True)
        rows.append({"faixa": faixa, "n": len(group),
                       **{s: float(share.get(s, 0.0)) for s in PRICE_SITUATIONS}})
    return rows


def backtest(df: pd.DataFrame) -> pd.DataFrame | None:
    """Rentabilidade realizada média por faixa × situação (guia v2: comparar DENTRO da faixa).
    Esperado: abaixo < dentro < acima em cada faixa."""
    if "rentabilidade_realizada" not in df.columns:
        return None
    base = df[df["situacao_preco"].isin(PRICE_SITUATIONS) & df["rentabilidade_realizada"].notna()]
    if base.empty:
        return None
    table = (base.pivot_table(index="faixa", columns="situacao_preco",
                               values="rentabilidade_realizada", aggfunc="mean")
              .reindex(index=[f for f in BANDS if f in set(base["faixa"])],
                       columns=PRICE_SITUATIONS))
    return table


def list_contracts(df: pd.DataFrame, situations: list[str] | None = None) -> pd.DataFrame:
    """Contratos da base para a lista e a busca: filtra pela situação e ordena do mais
    distante para o mais próximo da margem.
    distancia_pp: quanto passa da margem (0 dentro dela; vazio em revisão manual)."""
    out = df if not situations else df[df["situacao_preco"].isin(situations)]
    out = out.copy()
    above = out["situacao_preco"] == "acima_do_justo"
    below = out["situacao_preco"] == "abaixo_do_justo"
    inside = out["situacao_preco"] == "dentro_da_margem"
    distance = pd.Series(float("nan"), index=out.index)
    distance[above] = out.loc[above, "juro_cobrado"] - out.loc[above, "juro_justo_max"]
    distance[below] = out.loc[below, "juro_justo_min"] - out.loc[below, "juro_cobrado"]
    distance[inside] = 0.0
    out["distancia_pp"] = (distance * 100).round(1)
    return out.sort_values("distancia_pp", ascending=False, na_position="last", kind="stable")


def find_contract(df: pd.DataFrame, contrato_id: str) -> dict | None:
    """Linha de um contrato pelo ID exato (sem diferenciar maiúsculas), ou None."""
    key = (contrato_id or "").strip().lower()
    match = df[df["contrato_id"].astype(str).str.lower() == key] if key else df.iloc[0:0]
    return None if match.empty else json.loads(match.head(1).to_json(orient="records"))[0]


EXPORT_COLUMNS = ["contrato_id", "ano", "pais", "faixa", "pd", "juro_cobrado", "juro_justo",
                  "juro_justo_min", "juro_justo_max", "juro_pares_mediana", "situacao_preco",
                  "distancia_pp", "excesso_eur", "perda_nao_coberta_eur"]


def export_contracts(listing: pd.DataFrame) -> bytes:
    """Lista em CSV (UTF-8 com BOM, abre certo no Excel), só com as colunas úteis."""
    columns_ = [c for c in EXPORT_COLUMNS if c in listing.columns]
    return listing[columns_].to_csv(index=False).encode("utf-8-sig")


# ---------- leitura com cache (o arquivo tem ~150 mil linhas: lê uma vez por versão do arquivo)
_CACHE: dict = {}


def cached_portfolio(folder: Path | None = None) -> pd.DataFrame | None:
    """load_portfolio() com cache pela data de modificação do arquivo; já ordenado pela distância."""
    folder = Path(folder or PORTFOLIO_DIR)
    path_ = folder / PORTFOLIO_FILE
    if not path_.exists():
        _CACHE.pop(str(folder), None)
        return None
    key = path_.stat().st_mtime
    hit = _CACHE.get(str(folder))
    if hit is None or hit[0] != key:
        df = load_portfolio(folder)
        _CACHE[str(folder)] = (key, list_contracts(df) if df is not None else None)
    return _CACHE[str(folder)][1]


def records(df: pd.DataFrame) -> list[dict]:
    """Linhas em dicionários prontos para JSON (NaN → null)."""
    return json.loads(df.to_json(orient="records"))


def overview(df: pd.DataFrame, fairness: list[dict] | None, years: tuple[int, int] | None = None,
             pais: str | None = None, faixa: str | None = None) -> dict:
    """Tudo o que a Home mostra, para os filtros escolhidos."""
    filtered = filter_portfolio(df, years=years, pais=pais, faixa=faixa)
    table = backtest(filtered)
    backtest_rows = None
    if table is not None:
        backtest_rows = [{"faixa": f, **{c: (None if pd.isna(v) else float(v)) for c, v in row.items()}}
                         for f, row in table.iterrows()]
    return {
        "anos": [int(df["ano"].min()), int(df["ano"].max())],
        "paises": sorted(df["pais"].dropna().unique().tolist()),
        "faixas": BANDS,
        "resumo": summarize(filtered),
        "por_faixa": by_band(filtered),
        "backtest": backtest_rows,
        "equidade": fairness,
    }
