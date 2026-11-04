"""Segmentação de clientes com K-Means (aprendizado não supervisionado).

Uso no projeto: descrever a carteira em perfis e mostrar, por perfil,
inadimplência, juro cobrado e juro justo. NÃO entra no modelo de risco.

Regras:
- só variáveis de perfil do cliente e do pedido (nada de juro, default,
  gênero, idade ou país): o grupo descreve "quem é o cliente", e depois
  olhamos como o preço e o risco se comportam em cada grupo;
- ajusta no TREINO e só aplica no teste;
- escala padronizada (K-Means usa distância).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.impute import SimpleImputer
from sklearn.metrics import silhouette_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

SEMENTE = 42

VARIAVEIS_PERFIL = [
    "valor_concedido",
    "prazo_meses",
    "renda_relativa",
    "divida_sobre_renda",
    "parcela_neutra_sobre_renda",
    "n_emprestimos_anteriores",
]


def _log1p_seguro(x):
    return np.log1p(np.clip(x, 0, None))


def montar_kmeans(k: int) -> Pipeline:
    return Pipeline([
        ("imputar", SimpleImputer(strategy="median")),
        ("log", FunctionTransformer(_log1p_seguro)),
        ("escala", StandardScaler()),
        ("kmeans", KMeans(n_clusters=k, n_init=10, random_state=SEMENTE)),
    ])


def escolher_k(df: pd.DataFrame, ks=range(2, 9), amostra: int = 5000) -> pd.DataFrame:
    """Cotovelo (inércia) e silhueta para cada k. Silhueta numa amostra, para ser rápido."""
    X = df[VARIAVEIS_PERFIL]
    linhas = []
    for k in ks:
        modelo = montar_kmeans(k).fit(X)
        Xt = modelo[:-1].transform(X)
        rotulos = modelo[-1].labels_
        idx = np.random.default_rng(SEMENTE).choice(len(Xt), min(amostra, len(Xt)), replace=False)
        linhas.append({
            "k": k,
            "inercia": round(float(modelo[-1].inertia_), 1),
            "silhueta": round(float(silhouette_score(Xt[idx], rotulos[idx])), 3),
        })
    return pd.DataFrame(linhas).set_index("k")


def segmentar(treino: pd.DataFrame, k: int) -> Pipeline:
    return montar_kmeans(k).fit(treino[VARIAVEIS_PERFIL])


def descrever(df: pd.DataFrame, modelo: Pipeline) -> pd.DataFrame:
    """Perfil médio de cada grupo + inadimplência e juro (só para leitura, não para o modelo)."""
    d = df.copy()
    d["segmento"] = modelo.predict(d[VARIAVEIS_PERFIL])
    resumo = d.groupby("segmento").agg(
        contratos=("default", "size"),
        default=("default", "mean"),
        **{v: (v, "median") for v in VARIAVEIS_PERFIL},
    )
    if "juro_aa" in d.columns:
        resumo["juro_mediano_pct"] = d.groupby("segmento")["juro_aa"].median()
    resumo["participacao"] = resumo["contratos"] / resumo["contratos"].sum()
    return resumo.round(3)