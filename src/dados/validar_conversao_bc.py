#!/usr/bin/env python3
"""Confere a conversão da taxa do BC contra a série mensal oficial.

A série SGS 20742 (crédito pessoal não consignado, pessoas físicas) vem em % ao ano EFETIVA.
O parecer a converte para taxa nominal: 12 × [(1 + efetiva)^(1/12) − 1]. O Banco Central
publica a mesma medida já em % ao mês (série SGS 25464). Este script compara, mês a mês, a
taxa mensal que sai da conversão com a oficial.

Uso (na raiz do projeto):
    python src/dados/validar_conversao_bc.py
    python src/dados/validar_conversao_bc.py --efetiva data/raw/bcdata.sgs.20742.csv \\
        --mensal data/raw/bcdata.sgs.25464.csv --tolerancia 0.01

O BC publica as duas séries com 2 casas decimais, então o arredondamento sozinho explica até
0,005 ponto percentual ao mês de diferença. O programa sai com código 1 se algum mês passar da
tolerância (padrão 0,01 ponto, o dobro do arredondamento).

Os CSVs ficam em data/raw/, fora do Git (formato do BC: separador ';', decimal ',', datas dd/mm/aaaa).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
PASTA = RAIZ / "data" / "raw"
NOMES_EFETIVA = ("bcdata.sgs.20742.csv", "bcdata_sgs_20742.csv")
NOMES_MENSAL = ("bcdata.sgs.25464.csv", "bcdata_sgs_25464.csv")
TOLERANCIA_PADRAO = 0.01        # ponto percentual ao mês (o dobro do arredondamento do BC)


def efetiva_para_mensal(efetiva_aa: float) -> float:
    """% ao ano efetiva -> % ao mês: (1 + efetiva)^(1/12) − 1."""
    return ((1 + efetiva_aa / 100) ** (1 / 12) - 1) * 100


def efetiva_para_nominal(efetiva_aa: float) -> float:
    """% ao ano efetiva -> % ao ano nominal (como o contrato): 12 × taxa mensal."""
    return 12 * efetiva_para_mensal(efetiva_aa)


def ler_serie(caminho: Path | str) -> pd.Series:
    """Lê um CSV do BC ("data";"valor") e devolve a série indexada pelo primeiro dia do mês."""
    df = pd.read_csv(caminho, sep=";", decimal=",", quotechar='"')
    datas = pd.to_datetime(df.iloc[:, 0], dayfirst=True)
    return pd.Series(df.iloc[:, 1].astype(float).values, index=datas, name="valor").sort_index()


def comparar(efetiva: pd.Series, mensal: pd.Series) -> pd.DataFrame:
    """Compara, nos meses que as duas séries têm, a conversão da efetiva com a mensal oficial."""
    d = pd.concat({"efetiva_aa": efetiva, "oficial_am": mensal}, axis=1).dropna()
    d["convertida_am"] = d["efetiva_aa"].map(efetiva_para_mensal)
    d["dif_am"] = d["convertida_am"] - d["oficial_am"]
    d["nominal_convertida"] = 12 * d["convertida_am"]
    d["nominal_oficial"] = 12 * d["oficial_am"]
    d["dif_nominal"] = d["nominal_convertida"] - d["nominal_oficial"]
    return d


def resumo(d: pd.DataFrame, tolerancia: float = TOLERANCIA_PADRAO) -> dict:
    """Números para o relatório: meses, maior diferença e quantos passam da tolerância."""
    return {"meses": int(len(d)), "dif_max_am": float(d["dif_am"].abs().max()),
            "dif_media_am": float(d["dif_am"].abs().mean()),
            "dif_max_nominal": float(d["dif_nominal"].abs().max()),
            "acima_da_tolerancia": int((d["dif_am"].abs() > tolerancia).sum()),
            "primeiro_mes": d.index.min(), "ultimo_mes": d.index.max()}


def _achar(nomes: tuple[str, ...]) -> Path:
    for n in nomes:
        if (PASTA / n).exists():
            return PASTA / n
    return PASTA / nomes[0]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--efetiva", type=Path, default=None, help="série 20742 (% ao ano efetiva)")
    ap.add_argument("--mensal", type=Path, default=None, help="série 25464 (% ao mês)")
    ap.add_argument("--tolerancia", type=float, default=TOLERANCIA_PADRAO, help="em pontos percentuais ao mês")
    a = ap.parse_args()
    efetiva_csv, mensal_csv = a.efetiva or _achar(NOMES_EFETIVA), a.mensal or _achar(NOMES_MENSAL)
    for caminho in (efetiva_csv, mensal_csv):
        if not caminho.exists():
            sys.exit(f"ERRO: não achei {caminho}. Coloque os CSVs do BC em data/raw/ (ficam fora do Git).")
    d = comparar(ler_serie(efetiva_csv), ler_serie(mensal_csv))
    r = resumo(d, a.tolerancia)
    print("=" * 74)
    print(f"Conversão da taxa do BC x série mensal oficial (25464): {r['meses']} meses, "
          f"de {r['primeiro_mes']:%m/%Y} a {r['ultimo_mes']:%m/%Y}")
    print(f"  diferença máxima na taxa mensal: {r['dif_max_am']:.4f} p.p. ao mês (média {r['dif_media_am']:.4f})")
    print(f"  diferença máxima no nominal anual: {r['dif_max_nominal']:.3f} p.p. ao ano")
    print(f"  meses acima da tolerância de {a.tolerancia} p.p.: {r['acima_da_tolerancia']}")
    print("  (o BC publica 2 casas, então o arredondamento sozinho explica até 0,005 p.p. ao mês)")
    print("=" * 74)
    if r["acima_da_tolerancia"]:
        print(d.loc[d["dif_am"].abs() > a.tolerancia, ["efetiva_aa", "oficial_am", "convertida_am", "dif_am"]].round(4).to_string())
        sys.exit(1)
    print("OK: a conversão bate com a série oficial em todos os meses.")


if __name__ == "__main__":
    main()
