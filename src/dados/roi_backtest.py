#!/usr/bin/env python3
"""ROI em euros do backtest de 2016: os contratos "abaixo do justo" deram mais prejuízo?

Uso (na raiz do projeto):
    python src/dados/roi_backtest.py                       # só o CSV da carteira
    python src/dados/roi_backtest.py --dsn postgresql://...  # + recorte "só teste" (clientes novos)

Lê `docs/resultados/carteira_auditoria.csv` (gerado pelo lote do Samuel, `src/modelos/carteira.py`)
e resume, por situação do preço, os contratos de 2016 encerrados:
  * resultado_eur = rentabilidade_realizada × valor_concedido (a mesma conta da
    vw_retorno_realizado; a rentabilidade vem arredondada em 4 casas no CSV);
  * roi = soma do resultado ÷ soma do valor concedido (ponderado pelo valor, em euros);
  * perda_nao_coberta_eur = soma de max(0, −resultado), já calculada no CSV.
Reestruturados (`fora_da_auditoria`) ficam fora, como na auditoria de preço.

Se a auditoria funciona, em cada faixa de risco "abaixo do justo" rende menos que "acima do justo".

Só 2016: de 2017 a 2021 não há desfecho, e o `excesso_eur` espera a repontuação do Samuel.
Os números dependem do modelo que gerou o CSV (coluna `versao_modelo`): regerar quando ele mudar.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
CARTEIRA = RAIZ / "docs" / "resultados" / "carteira_auditoria.csv"
ANO_BACKTEST = 2016
SITUACOES = ["abaixo_do_justo", "dentro_da_margem", "acima_do_justo", "revisao_manual"]
FAIXAS = ["A", "B", "C", "D", "E"]


def preparar(carteira: pd.DataFrame, conjunto: pd.DataFrame | None = None) -> pd.DataFrame:
    """Contratos de 2016 com desfecho, sem reestruturados, com resultado_eur.
    conjunto = DataFrame (loan_id, conjunto) da vw_base_modelagem, opcional."""
    df = carteira[(carteira["ano"] == ANO_BACKTEST) & carteira["rentabilidade_realizada"].notna()].copy()
    df = df[~df["fora_da_auditoria"].fillna(False).astype(bool)]
    df["resultado_eur"] = df["rentabilidade_realizada"] * df["valor_concedido"]
    if conjunto is not None:
        df = df.merge(conjunto.rename(columns={"loan_id": "contrato_id"}), on="contrato_id", how="left")
    return df.reset_index(drop=True)


def por_situacao(df: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por situação do preço, mais o total."""
    g = df.groupby("situacao_preco").agg(
        contratos=("contrato_id", "size"),
        concedido_eur=("valor_concedido", "sum"),
        resultado_eur=("resultado_eur", "sum"),
        perda_nao_coberta_eur=("perda_nao_coberta_eur", "sum"),
    ).reindex([s for s in SITUACOES if s in set(df["situacao_preco"])])
    g.loc["total"] = g.sum()
    g["roi"] = g["resultado_eur"] / g["concedido_eur"]
    return g


def por_faixa(df: pd.DataFrame) -> pd.DataFrame:
    """ROI ponderado por faixa × situação (sem revisão manual, que não tem faixa)."""
    d = df[df["situacao_preco"].isin(SITUACOES[:3])]
    soma = d.groupby(["faixa", "situacao_preco"])[["resultado_eur", "valor_concedido"]].sum()
    roi = (soma["resultado_eur"] / soma["valor_concedido"]).unstack()
    n = d.groupby(["faixa", "situacao_preco"]).size().unstack()
    cols = [s for s in SITUACOES[:3] if s in roi.columns]
    out = roi[cols].add_prefix("roi_").join(n[cols].add_prefix("n_"))
    out["abaixo_rende_menos"] = out.get("roi_abaixo_do_justo") < out.get("roi_acima_do_justo")
    return out.reindex([f for f in FAIXAS if f in out.index])


# --------------------------------------------------------------------------
# Saída em Markdown (vírgula decimal, como nos documentos)
# --------------------------------------------------------------------------
def _num(v: float, casas: int = 0) -> str:
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _pct(v: float) -> str:
    return "–" if pd.isna(v) else _num(100 * v, 1).replace("-", "−") + "%"


def _mi(v: float) -> str:
    return _num(v / 1e6, 2).replace("-", "−") + " mi €"


def markdown(df: pd.DataFrame, titulo: str) -> str:
    s = por_situacao(df)
    linhas = [f"**{titulo}** ({_num(len(df))} contratos)", "",
              "| Situação | Contratos | Concedido | Resultado | ROI | Perda não coberta |",
              "| --- | --- | --- | --- | --- | --- |"]
    for nome, r in s.iterrows():
        rot = f"**{nome}**" if nome == "total" else f"`{nome}`"
        linhas.append(f"| {rot} | {_num(r.contratos)} | {_mi(r.concedido_eur)} | {_mi(r.resultado_eur)} "
                      f"| {_pct(r.roi)} | {_mi(r.perda_nao_coberta_eur)} |")
    f = por_faixa(df)
    linhas += ["", "| Faixa | ROI abaixo | ROI dentro | ROI acima | Abaixo rende menos? |",
               "| --- | --- | --- | --- | --- |"]
    for faixa, r in f.iterrows():
        linhas.append(f"| {faixa} | {_pct(r.get('roi_abaixo_do_justo'))} | {_pct(r.get('roi_dentro_da_margem'))} "
                      f"| {_pct(r.get('roi_acima_do_justo'))} | {'sim' if r.abaixo_rende_menos else 'não'} |")
    return "\n".join(linhas)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--carteira", default=str(CARTEIRA))
    ap.add_argument("--dsn", default=os.environ.get("DATABASE_URL"),
                    help="opcional: banco para o recorte 'só teste' (vw_base_modelagem)")
    a = ap.parse_args()
    carteira = pd.read_csv(a.carteira)
    versoes = ", ".join(sorted(carteira["versao_modelo"].dropna().astype(str).unique()))
    conjunto = None
    if a.dsn:
        try:
            from src.dados.validacao import conectar
            conjunto = pd.read_sql("SELECT loan_id, conjunto FROM vw_base_modelagem", conectar(a.dsn))
        except Exception as exc:                      # sem banco: segue só com o CSV
            print(f"aviso: sem o recorte 'só teste' ({str(exc).splitlines()[0][:100]})", file=sys.stderr)
    df = preparar(carteira, conjunto)
    print(f"Modelo do CSV: {versoes}\n")
    print(markdown(df, f"{ANO_BACKTEST}, encerrados, sem reestruturados"))
    if conjunto is not None:
        print()
        print(markdown(df[df["conjunto"] == "teste"], f"{ANO_BACKTEST}, só teste (clientes novos), sem reestruturados"))


if __name__ == "__main__":
    sys.path.insert(0, str(RAIZ))
    main()
