"""Equidade: clientes de MESMO RISCO pagam juro diferente por gênero ou idade?

Auditoria de resíduos: resíduo = juro cobrado − juro justo (p.p.). Regressão do resíduo
no grupo, controlando por PD, faixa, país × ano, valor e prazo; IC 95% robusto (HC1).
- Gênero: 1 (mulher) × 0 (homem); 2 = ausente. Janela 2013–2016 (codificação suspeita
  em 2017–2019, DATA.md 7), comparação DENTRO do país (efeito fixo país × ano).
- Idade: 18–25 × 35–44, 2013–2021; idade < 18 fica fora.
- País nunca é grupo comparado. Reestruturados e revisão manual ficam fora.
Resultado é INDÍCIO, nunca conclusão (proxies; DECISOES.md).

Grava docs/resultados/equidade.json no formato de src/api/portfolio.py.
Uso:  python -m src.modelos.equidade
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.modelos.carteira import pontuar_lote, selecionar

RAIZ = Path(__file__).resolve().parents[2]
SAIDA_PADRAO = RAIZ / "docs" / "resultados" / "equidade.json"
ANOS_GENERO = (2013, 2016)
ANOS_IDADE = (2013, 2021)


def diferenca(df: pd.DataFrame, grupo_a: pd.Series, grupo_b: pd.Series,
              resposta: pd.Series | None = None) -> dict:
    """Diferença de resíduo (p.p.) do grupo A contra o B, entre clientes de mesmo risco.
    resposta = outro resíduo (p.p.) no lugar de cobrado − justo (ex.: default − PD)."""
    sel = (grupo_a | grupo_b) & df["pd"].notna() & ~df["fora_da_auditoria"].fillna(False).astype(bool)
    if resposta is not None:
        sel &= resposta.notna()
    d = df[sel]
    y = (((d["juro_cobrado"] - d["juro_justo"]) * 100) if resposta is None
         else resposta[sel]).to_numpy(float)
    controles = pd.concat([
        d[["pd"]], d[["pd"]].pow(2).rename(columns={"pd": "pd2"}),
        np.log(d[["valor_concedido"]].astype(float)),
        pd.get_dummies(d["faixa"], prefix="f", drop_first=True, dtype=float),
        pd.get_dummies(d["prazo_meses"].astype(int), prefix="p", drop_first=True, dtype=float),
        pd.get_dummies(d["pais"].astype(str) + "_" + d["ano"].astype(str), prefix="pa",
                       drop_first=True, dtype=float),
    ], axis=1)
    X = np.column_stack([np.ones(len(d)), grupo_a[sel].astype(float).to_numpy(),
                         controles.to_numpy(float)])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ beta
    n, k = X.shape
    pinv = np.linalg.pinv(X.T @ X)
    cov = pinv @ (X.T * e ** 2) @ X @ pinv * n / (n - k)        # HC1
    ep = float(np.sqrt(cov[1, 1]))
    return {"diferenca_pp": round(float(beta[1]), 2),
            "ic95_min": round(float(beta[1]) - 1.96 * ep, 2),
            "ic95_max": round(float(beta[1]) + 1.96 * ep, 2),
            "n_grupo_a": int(grupo_a[sel].sum()), "n_grupo_b": int(grupo_b[sel].sum())}


def comparacoes(lote: pd.DataFrame, genero: pd.Series, idade: pd.Series) -> list[dict]:
    genero = pd.to_numeric(genero, errors="coerce")
    idade = pd.to_numeric(idade, errors="coerce")
    jan_g = lote["ano"].between(*ANOS_GENERO)
    jan_i = lote["ano"].between(*ANOS_IDADE)
    return [
        {"atributo": "Gênero", "comparacao": "feminino × masculino (dentro do país)",
         **diferenca(lote, jan_g & (genero == 1), jan_g & (genero == 0))},
        {"atributo": "Idade", "comparacao": "18–25 × 35–44 anos",
         **diferenca(lote, jan_i & idade.between(18, 25), jan_i & idade.between(35, 44))},
    ]


def risco_nao_visto(lote: pd.DataFrame, default: pd.Series, genero: pd.Series,
                    idade: pd.Series) -> list[dict]:
    """O grupo deu MAIS default do que a PD previa? (encerrados 2013–2016; default − PD, p.p.)
    Se sim, a diferença de juro tem base em risco que o modelo não vê (o rating do Bondora
    usa idade; o nosso não). Se não, a diferença de juro não se explica por risco."""
    genero = pd.to_numeric(genero, errors="coerce")
    idade = pd.to_numeric(idade, errors="coerce")
    jan = lote["ano"].between(2013, 2016)
    resid = ((default.astype(float) - lote["pd"]) * 100).where(jan)
    return [
        {"atributo": "Gênero", **diferenca(lote, jan & (genero == 1), jan & (genero == 0), resid)},
        {"atributo": "Idade", **diferenca(lote, jan & idade.between(18, 25), jan & idade.between(35, 44), resid)},
    ]


def base_equidade(bruto: pd.DataFrame) -> pd.DataFrame:
    """2013–2015 encerrados (coortes maduras) + o mesmo recorte da carteira (2016–2021)."""
    from src.modelos.dados import preparar
    antigos = preparar(bruto)
    antigos = antigos[antigos["ano"].between(2013, 2015)]
    return pd.concat([antigos, selecionar(bruto)], ignore_index=True)


def main(saida: Path = SAIDA_PADRAO) -> list[dict]:
    from src.modelos.dados import ler_base
    base = base_equidade(ler_base())
    lote = pontuar_lote(base)                    # mesma ordem de linhas da base
    resultado = comparacoes(lote, base["genero"], base["idade"])
    saida.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    for r in resultado:
        cruza = r["ic95_min"] <= 0 <= r["ic95_max"]
        print(f"{r['atributo']}: {r['diferenca_pp']:+.2f} p.p. "
              f"[{r['ic95_min']:+.2f}; {r['ic95_max']:+.2f}]  n={r['n_grupo_a']}×{r['n_grupo_b']}  "
              f"→ {'sem indício' if cruza else 'INDÍCIO · investigar'}")
    print(f"→ {saida}")

    print("\nDefault realizado − PD prevista (encerrados 2013–2016; > 0 = deu mais calote que o previsto):")
    for r in risco_nao_visto(lote, base["data_default"].notna(), base["genero"], base["idade"]):
        print(f"{r['atributo']}: {r['diferenca_pp']:+.2f} p.p. [{r['ic95_min']:+.2f}; {r['ic95_max']:+.2f}]"
              f"  n={r['n_grupo_a']}×{r['n_grupo_b']}")

    # backtest 2016: rentabilidade realizada por faixa × situação (esperado: abaixo < dentro < acima)
    bt = lote[(lote["ano"] == 2016) & lote["pd"].notna() & ~lote["fora_da_auditoria"].astype(bool)]
    print("\nBacktest 2016 (rentabilidade realizada média; n entre parênteses):")
    tab = bt.pivot_table(index="faixa", columns="situacao_preco", values="rentabilidade_realizada",
                         aggfunc=["mean", "count"])
    print(tab.round(3).to_string())
    return resultado


if __name__ == "__main__":
    main()
