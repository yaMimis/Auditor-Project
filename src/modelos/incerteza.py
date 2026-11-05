"""Margem de incerteza por bootstrap por cliente (IC 95%)."""
import numpy as np
import pandas as pd
from src.modelos.xgb import treinar_final


def treinar_bootstrap(treino, params, n_arvores, n_reamostras=20, semente=42):
    rng = np.random.default_rng(semente)
    clientes = treino["cliente_id"].unique()
    modelos = []
    for _ in range(n_reamostras):
        cont = pd.Series(rng.choice(clientes, len(clientes))).value_counts()
        r = treino[treino["cliente_id"].isin(cont.index)]
        r = r.loc[r.index.repeat(r["cliente_id"].map(cont))].reset_index(drop=True)
        modelos.append(treinar_final(r, params, n_arvores))   # 1 ajuste: rápido
    return modelos


def intervalo(modelos, X, juro_justo, prazo, lgd, custo):
    pds = np.array([m.predict_proba(X)[0, 1] for m in modelos])
    justos = [juro_justo(prazo, p, lgd, custo) for p in pds]
    return np.percentile(pds, [2.5, 97.5]), np.percentile(justos, [2.5, 97.5])