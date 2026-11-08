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

def faixa_pd(modelos, X, pd_central, nivel: float = 95.0):
    """IC da PD por bootstrap, CENTRADO no modelo final.

    As reamostras usam treinar_final (calibração em 2015) e o modelo final usa
    treinar_final_completo (calibração fora da amostra), então o NÍVEL delas difere.
    Por isso usamos só a DISPERSÃO das reamostras, em logit, em torno da mediana
    delas, e a aplicamos à PD do modelo final. Vale para vários contratos de uma vez.
    """
    eps = 1e-6
    logit = lambda p: np.log(np.clip(p, eps, 1 - eps) / (1 - np.clip(p, eps, 1 - eps)))
    expit = lambda z: 1 / (1 + np.exp(-z))
    L = np.vstack([logit(m.predict_proba(X)[:, 1]) for m in modelos])   # (reamostras, contratos)
    desvio = L - np.median(L, axis=0)
    a = (100 - nivel) / 2
    centro = logit(np.asarray(pd_central, float))
    return expit(centro + np.percentile(desvio, a, axis=0)), expit(centro + np.percentile(desvio, 100 - a, axis=0))
