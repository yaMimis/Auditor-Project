"""XGBoost + calibração + SHAP (dia 03/11).

Regras (docs/DECISOES.md): parâmetros escolhidos e calibração ajustada em 2015,
nunca em 2016. Mesmas 23 variáveis do baseline.
"""
from __future__ import annotations

from itertools import product

import numpy as np
import pandas as pd
import shap
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBClassifier

from src.modelos.treino import _para_modelo, divisao_temporal, metricas
from src.modelos.variaveis import CATEGORICAS, NUMERICAS, ROTULOS

SEMENTE = 42
GRADE = {"max_depth": [3, 4, 5], "min_child_weight": [5, 20], "reg_lambda": [1, 10]}
FIXOS = dict(learning_rate=0.05, subsample=0.8, colsample_bytree=0.8,
             n_estimators=2000, eval_metric="logloss", random_state=SEMENTE, n_jobs=-1)


def _preparo() -> ColumnTransformer:
    # XGBoost lida com vazios sozinho: numéricas passam direto.
    return ColumnTransformer([
        ("num", "passthrough", NUMERICAS),
        ("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=0.01,
                              sparse_output=False), CATEGORICAS),
    ], verbose_feature_names_out=False)


def _numerico(X: pd.DataFrame) -> pd.DataFrame:
    """Colunas inteiras do banco vêm como Int64 com pd.NA; o XGBoost só aceita np.nan."""
    X = X.copy()
    X[NUMERICAS] = X[NUMERICAS].astype("float64")
    return X


class ModeloXGB:
    """Preparo + XGBoost + calibração (Platt). Tem predict_proba como o sklearn."""

    def __init__(self, params: dict):
        self.params = params
        self.calibrador = None

    def fit(self, X, y, X_val=None, y_val=None):
        X = _numerico(X)
        self.preparo = _preparo().fit(X)
        self.xgb = XGBClassifier(**{**FIXOS, **self.params},
                                 early_stopping_rounds=50 if X_val is not None else None)
        kw = {"eval_set": [(self.preparo.transform(_numerico(X_val)), y_val)], "verbose": False} \
            if X_val is not None else {}
        self.xgb.fit(self.preparo.transform(X), y, **kw)
        return self

    def _p_bruta(self, X):
        return self.xgb.predict_proba(self.preparo.transform(_numerico(X)))[:, 1]

    def calibrar(self, X, y):
        """Platt: logística sobre o logit da probabilidade bruta."""
        z = _logit(self._p_bruta(X)).reshape(-1, 1)
        self.calibrador = LogisticRegression().fit(z, y)
        return self

    def predict_proba(self, X):
        p = self._p_bruta(X)
        if self.calibrador is not None:
            p = self.calibrador.predict_proba(_logit(p).reshape(-1, 1))[:, 1]
        return np.column_stack([1 - p, p])


def _logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def buscar_parametros(treino: pd.DataFrame) -> pd.DataFrame:
    """Ajusta até 2014, avalia em 2015 com early stopping. Ordena por AUC."""
    tr, va = divisao_temporal(treino)
    Xtr, Xva = _para_modelo(tr), _para_modelo(va)
    linhas = []
    for valores in product(*GRADE.values()):
        params = dict(zip(GRADE, valores))
        m = ModeloXGB(params).fit(Xtr, tr["default"], Xva, va["default"])
        p = m.predict_proba(Xva)[:, 1]
        linhas.append({**params, "n_arvores": m.xgb.best_iteration + 1,
                       **metricas(va["default"], p)})
    return pd.DataFrame(linhas).sort_values("auc", ascending=False).reset_index(drop=True)


def treinar_final(treino: pd.DataFrame, params: dict, n_arvores: int) -> ModeloXGB:
    """Árvores ajustadas até 2014; calibração em 2015 (o ano mais recente do treino)."""
    tr, va = divisao_temporal(treino)
    m = ModeloXGB({**params, "n_estimators": n_arvores}).fit(_para_modelo(tr), tr["default"])
    return m.calibrar(_para_modelo(va), va["default"])


def motivos(modelo: ModeloXGB, X: pd.DataFrame, n: int = 5,
            excluir: set = frozenset({"pais"})) -> list[list[dict]]:
    """Top-n motivos SHAP por contrato, somando as colunas one-hot de cada variável."""
    X = _numerico(X)
    Xt = modelo.preparo.transform(X)
    valores = shap.TreeExplainer(modelo.xgb).shap_values(Xt)
    nomes = modelo.preparo.get_feature_names_out()
    origem = [next(v for v in NUMERICAS + CATEGORICAS if c == v or c.startswith(v + "_"))
              for c in nomes]
    por_var = pd.DataFrame(valores, columns=nomes).T.groupby(origem).sum().T
    por_var = por_var.drop(columns=[c for c in excluir if c in por_var.columns])
    saida = []
    for i, linha in por_var.iterrows():
        top = linha.reindex(linha.abs().sort_values(ascending=False).index)[:n]
        total = linha.abs().sum() or 1.0
        saida.append([{
            "variavel": v,
            "rotulo": ROTULOS.get(v, v),
            "efeito": "aumenta_risco" if s > 0 else "reduz_risco",
            "valor": None if pd.isna(X.iloc[i][v]) else X.iloc[i][v],
            "peso": round(float(abs(s) / total), 3),
        } for v, s in top.items()])
    return saida


def treinar_final_completo(treino: pd.DataFrame, params: dict, n_arvores: int,
                           n_folds: int = 5) -> ModeloXGB:
    """Árvores com TODO o treino (2009–2015). Calibração Platt com previsões
    fora da amostra (GroupKFold por cliente), sem usar 2016."""
    from sklearn.model_selection import GroupKFold

    X, y, grupos = _para_modelo(treino), treino["default"], treino["cliente_id"]
    oof = np.zeros(len(X))
    for idx_tr, idx_va in GroupKFold(n_splits=n_folds).split(X, y, grupos):
        m = ModeloXGB({**params, "n_estimators": n_arvores}).fit(X.iloc[idx_tr], y.iloc[idx_tr])
        oof[idx_va] = m._p_bruta(X.iloc[idx_va])

    final = ModeloXGB({**params, "n_estimators": n_arvores}).fit(X, y)
    final.calibrador = LogisticRegression().fit(_logit(oof).reshape(-1, 1), y)
    return final