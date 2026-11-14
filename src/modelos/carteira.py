"""Lote da carteira: pontua 2016 (teste, encerrados) e 2017–2021 e grava
docs/resultados/carteira_auditoria.csv no formato de src/api/portfolio.py.

Mesma regra do prever(), mas vetorizada (o prever() linha a linha, com SHAP,
levaria horas na carteira inteira). test_carteira_lote.py confere que os dois
dão o mesmo resultado.

Uso:  python -m src.modelos.carteira
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.modelos.prever import (ARQ_MARGEM, ARQ_PARES, MIN_PARES, _tabela_pares, FAIXAS, LGD_PADRAO, LGD_POR_PAIS,
                                MARGEM_INCERTEZA_PP, MARGEM_POR_SAFRA, VERSAO, _pacote)
from src.modelos.incerteza import faixa_pd
from src.modelos.treino import _para_modelo
from src.modelos.variaveis import criar_variaveis

RAIZ = Path(__file__).resolve().parents[2]
SAIDA_PADRAO = RAIZ / "docs" / "resultados" / "carteira_auditoria.csv"
ANO_TESTE = 2016
ANOS_NOVOS = range(2017, 2022)
PAISES_FORA = {"SK"}


def selecionar(bruto: pd.DataFrame) -> pd.DataFrame:
    """2016 só encerrados (tem desfecho) + 2017–2021 todos; sem a Eslováquia."""
    df = bruto.copy()
    df["ano"] = pd.to_datetime(df["data_emprestimo"]).dt.year
    encerrado = (df["status"] == "Repaid") | df["data_default"].notna()
    manter = (((df["ano"] == ANO_TESTE) & encerrado) | df["ano"].isin(ANOS_NOVOS)) \
        & ~df["pais"].isin(PAISES_FORA)
    df = df.loc[manter].reset_index(drop=True)
    df["fora_da_auditoria"] = (df["reestruturado"].fillna(False).astype(bool)
                               if "reestruturado" in df else False)
    return df


def juro_justo_vetor(prazo, pd_total, lgd, custo_anual, iteracoes: int = 60) -> np.ndarray:
    """Igual a prever.juro_justo, para vários contratos de uma vez (bisseção)."""
    prazo = np.maximum(np.asarray(prazo, dtype=int), 1)
    pd_total, lgd = np.asarray(pd_total, float), np.asarray(lgd, float)
    h = 1 - (1 - pd_total) ** (1 / np.maximum(prazo, 12))
    d = (1 + np.asarray(custo_anual, float)) ** (1 / 12) - 1
    t_max = int(prazo.max())

    def vp_menos_1(taxa):
        i = taxa / 12
        parcela = i / (1 - (1 + i) ** -prazo)
        saldo, vivo, vp = np.ones_like(i), np.ones_like(i), np.zeros_like(i)
        for t in range(1, t_max + 1):
            ativo = t <= prazo
            vp += np.where(ativo, (vivo * (1 - h) * parcela + vivo * h * (1 - lgd) * saldo)
                           / (1 + d) ** t, 0.0)
            saldo = np.where(ativo, saldo - (parcela - saldo * i), saldo)
            vivo = np.where(ativo, vivo * (1 - h), vivo)
        return vp - 1.0

    lo, hi = np.full(prazo.shape, 1e-6), np.full(prazo.shape, 5.0)
    f_lo, f_hi = vp_menos_1(lo), vp_menos_1(hi)
    sem_raiz = np.sign(f_lo) == np.sign(f_hi)        # no prever(): brentq falha → 5.0
    for _ in range(iteracoes):
        meio = (lo + hi) / 2
        f_meio = vp_menos_1(meio)
        mesmo = np.sign(f_meio) == np.sign(f_lo)
        lo, f_lo = np.where(mesmo, meio, lo), np.where(mesmo, f_meio, f_lo)
        hi = np.where(mesmo, hi, meio)
    return np.where(sem_raiz, 5.0, (lo + hi) / 2)


def _parcela(valor, taxa_aa, prazo):
    i = np.asarray(taxa_aa, float) / 12
    prazo = np.asarray(prazo, float)
    return np.where(i > 0, valor * i / (1 - (1 + i) ** -prazo), valor / prazo)


def _preparar(base: pd.DataFrame, pac: dict):
    """Fora da faixa de treino (→ revisão manual) e ano da mediana de renda, como no prever()."""
    df = base.reset_index(drop=True).copy()
    if "ano" not in df:
        df["ano"] = pd.to_datetime(df["data_emprestimo"]).dt.year
    ano_contrato = df["ano"].astype(int)
    fora = ~df["pais"].isin(pac["paises"])
    for c, (lo, hi) in pac["faixas_treino"].items():
        v = pd.to_numeric(df[c], errors="coerce")
        fora |= v.isna() | (v < lo) | (v > hi)
    # ano além do treino → último ano do país (só para a mediana de renda)
    ultimo = pac["referencia"].groupby("pais")["ano"].max()
    teto = df["pais"].map(ultimo)
    df["ano"] = np.where(teto.notna(), np.minimum(ano_contrato, teto.fillna(0)), ano_contrato).astype(int)
    return df, ano_contrato, fora


def _risco_e_custos(sub: pd.DataFrame, pac: dict):
    """PD, LGD por país, Euribor 12m do mês do contrato (fração) e a matriz do modelo."""
    var = criar_variaveis(sub, referencia=pac["referencia"])
    X = _para_modelo(var)
    pd_ = pac["modelo"].predict_proba(X)[:, 1]
    mes = pd.to_datetime(var["data_emprestimo"]).dt.to_period("M").dt.to_timestamp()
    e12 = pac["euribor_12m"].sort_index()
    euribor = pd.Series(e12.asof(pd.DatetimeIndex(mes)).values, index=sub.index)
    euribor = (euribor.fillna(e12.iloc[0]) / 100).clip(lower=0).to_numpy()
    lgd = sub["pais"].map(LGD_POR_PAIS).fillna(LGD_PADRAO).to_numpy()
    return pd_, lgd, euribor, X


def _margem(anos: pd.Series, margens: dict | None = None) -> np.ndarray:
    m = MARGEM_POR_SAFRA if margens is None else margens
    return anos.map(m).fillna(m[max(m)]).to_numpy()


def calibrar_margem_mediana(base: pd.DataFrame, pacote: dict | None = None,
                            amostra: int = 4000, semente: int = 0) -> dict[int, float]:
    """Por safra, a margem em que a MEDIANA de (cobrado − justo) é zero: metade dos
    contratos fica acima do justo e metade abaixo. Usa só o juro cobrado (nunca o
    desfecho), então vale também para 2017–2021. Reestruturados ficam fora."""
    pac = pacote or _pacote()
    df, ano_contrato, fora = _preparar(base, pac)
    ok = ~fora & ~df.get("fora_da_auditoria", pd.Series(False, index=df.index)).fillna(False).astype(bool)
    margens = {}
    for ano in sorted(ano_contrato[ok].unique()):
        idx = ano_contrato[ok & (ano_contrato == ano)].index
        sub = df.loc[idx].sample(min(len(idx), amostra), random_state=semente)
        pd_, lgd, euribor, _ = _risco_e_custos(sub, pac)
        cobrado = pd.to_numeric(sub["juro_aa"]).to_numpy() / 100

        def gap(m):   # decresce com a margem
            return np.median(cobrado - juro_justo_vetor(sub["prazo_meses"], pd_, lgd, euribor + m, 40))

        lo, hi = -0.30, 1.00
        for _ in range(25):
            meio = (lo + hi) / 2
            lo, hi = (meio, hi) if gap(meio) > 0 else (lo, meio)
        margens[int(ano)] = round((lo + hi) / 2, 4)
    return margens


def tabela_pares(treino: pd.DataFrame, pacote: dict | None = None) -> pd.DataFrame:
    """Mediana do juro cobrado no TREINO por país × faixa × ano (30+ contratos).
    Faixa pela PD do modelo; reestruturados e revisão manual ficam fora."""
    pac = pacote or _pacote()
    df, ano_contrato, fora = _preparar(treino, pac)
    ok = ~fora & ~df.get("fora_da_auditoria", pd.Series(False, index=df.index)).fillna(False).astype(bool)
    pd_, *_ = _risco_e_custos(df[ok], pac)
    t = pd.DataFrame({"pais": df.loc[ok, "pais"].to_numpy(), "ano": ano_contrato[ok].to_numpy(),
                      "faixa": [next(l for lim, l in FAIXAS if p < lim) for p in pd_],
                      "juro": pd.to_numeric(df.loc[ok, "juro_aa"]).to_numpy() / 100})
    g = t.groupby(["pais", "faixa", "ano"])["juro"].agg(juro_pares_mediana="median", n="size").reset_index()
    g = g[g["n"] >= MIN_PARES]
    g["juro_pares_mediana"] = g["juro_pares_mediana"].round(4)
    return g.reset_index(drop=True)


def _com_pares(out: pd.DataFrame, tabela: pd.DataFrame | None) -> pd.Series:
    """Mesma regra de prever.mediana_pares, para a carteira inteira."""
    if tabela is None:
        return pd.Series(np.nan, index=out.index)
    ultimo = tabela.groupby("pais")["ano"].max()
    chave = pd.DataFrame({"pais": out["pais"], "faixa": out["faixa"],
                          "ano": np.minimum(out["ano"], out["pais"].map(ultimo).fillna(-1)).astype(int)})
    m = chave.merge(tabela[["pais", "faixa", "ano", "juro_pares_mediana"]], how="left",
                    on=["pais", "faixa", "ano"])
    return pd.Series(m["juro_pares_mediana"].to_numpy(), index=out.index)


def pontuar_lote(base: pd.DataFrame, pacote: dict | None = None,
                 margens: dict | None = None) -> pd.DataFrame:
    """Uma linha por contrato com as colunas de carteira_auditoria.csv."""
    pac = pacote or _pacote()
    df, ano_contrato, fora = _preparar(base, pac)
    juro_cobrado = (pd.to_numeric(df["juro_aa"]) / 100).round(4)

    out = pd.DataFrame({
        "contrato_id": df["loan_id"].astype(str), "ano": ano_contrato, "pais": df["pais"],
        "valor_concedido": df["valor_concedido"], "prazo_meses": df["prazo_meses"],
        "juro_cobrado": juro_cobrado,
        "fora_da_auditoria": df.get("fora_da_auditoria", False),
        "versao_modelo": VERSAO,
    })
    for c in ("pd", "juro_justo", "juro_justo_min", "juro_justo_max"):
        out[c] = np.nan
    out["faixa"] = None
    out["situacao_preco"] = "revisao_manual"

    ok = ~fora
    if ok.any():
        sub = df[ok]
        pd_, lgd, euribor, X = _risco_e_custos(sub, pac)
        margem = _margem(ano_contrato[ok], margens)
        justo = np.round(juro_justo_vetor(sub["prazo_meses"], pd_, lgd, euribor + margem), 4)
        out.loc[ok, "pd"] = np.round(pd_, 4)
        out.loc[ok, "faixa"] = [next(l for lim, l in FAIXAS if p < lim) for p in pd_]
        out.loc[ok, "juro_justo"] = justo
        if pac.get("bootstrap"):      # IC 95% por bootstrap, como no prever()
            lo, hi = faixa_pd(pac["bootstrap"], X, pd_)
            lo, hi = np.round(lo, 4), np.round(hi, 4)
            out.loc[ok, "pd_ic95_min"], out.loc[ok, "pd_ic95_max"] = lo, hi
            jmin = juro_justo_vetor(sub["prazo_meses"], lo, lgd, euribor + margem)
            jmax = juro_justo_vetor(sub["prazo_meses"], hi, lgd, euribor + margem)
            out.loc[ok, "juro_justo_min"] = np.round(np.minimum(jmin, justo), 4)
            out.loc[ok, "juro_justo_max"] = np.round(np.maximum(jmax, justo), 4)
        else:
            out.loc[ok, "juro_justo_min"] = np.round(np.maximum(justo - MARGEM_INCERTEZA_PP / 100, 0), 4)
            out.loc[ok, "juro_justo_max"] = np.round(justo + MARGEM_INCERTEZA_PP / 100, 4)
        jc = out.loc[ok, "juro_cobrado"]
        out.loc[ok, "situacao_preco"] = np.select(
            [jc > out.loc[ok, "juro_justo_max"], jc < out.loc[ok, "juro_justo_min"]],
            ["acima_do_justo", "abaixo_do_justo"], "dentro_da_margem")

    out["juro_pares_mediana"] = _com_pares(out, _tabela_pares(pac)).where(out["pd"].notna())

    # o que o cliente paga acima do teto da margem, se pagar até o fim (i/12)
    acima = out["situacao_preco"] == "acima_do_justo"
    excesso = out["prazo_meses"] * (_parcela(out["valor_concedido"], out["juro_cobrado"], out["prazo_meses"])
                                    - _parcela(out["valor_concedido"], out["juro_justo_max"].fillna(0),
                                               out["prazo_meses"]))
    out["excesso_eur"] = np.where(acima, np.round(excesso, 2), np.nan)

    # resultado realizado: mesma conta da vw_retorno_realizado, só 2016 (encerrados)
    if {"principal_pago", "juros_multas_pagos"} <= set(df.columns):
        recebido = (pd.to_numeric(df["principal_pago"]).fillna(0)
                    + pd.to_numeric(df["juros_multas_pagos"]).fillna(0))
        resultado = recebido - df["valor_concedido"]
        encerrado = ano_contrato == ANO_TESTE
        out["rentabilidade_realizada"] = np.where(
            encerrado, (resultado / df["valor_concedido"].replace(0, np.nan)).round(4), np.nan)
        out["perda_nao_coberta_eur"] = np.where(encerrado, np.round((-resultado).clip(lower=0), 2), np.nan)
    return out


def main(saida: Path = SAIDA_PADRAO) -> pd.DataFrame:
    from src.modelos.dados import ler_base, preparar, ANOS_TREINO
    bruto = ler_base()
    base = selecionar(bruto)
    treino = preparar(bruto)
    pares = tabela_pares(treino[treino["ano"].isin(ANOS_TREINO)])
    pares.to_csv(ARQ_PARES, index=False)
    print(f"pares: {len(pares)} grupos país × faixa × ano (30+ contratos) → {ARQ_PARES}")
    pac = {**_pacote(), "pares": pares}

    margens = calibrar_margem_mediana(base, pac)
    ARQ_MARGEM.parent.mkdir(parents=True, exist_ok=True)
    ARQ_MARGEM.write_text(json.dumps(margens, indent=2), encoding="utf-8")
    MARGEM_POR_SAFRA.update(margens)       # o prever() desta sessão também passa a usar
    print("margem por safra (mediana):", margens, "→", ARQ_MARGEM)

    carteira = pontuar_lote(base, pac)
    carteira.to_csv(saida, index=False)
    print(f"{len(carteira)} contratos → {saida}")
    larg = (carteira["juro_justo_max"] - carteira["juro_justo_min"]) * 100
    print(f"largura da margem de incerteza (p.p.): mediana {larg.median():.1f}, "
          f"p10 {larg.quantile(.1):.1f}, p90 {larg.quantile(.9):.1f}")
    print(carteira.groupby("ano")["situacao_preco"].value_counts(normalize=True)
          .unstack().round(3).to_string())
    return carteira


if __name__ == "__main__":
    main()
