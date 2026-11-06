"""Treino e avaliação do modelo de risco.

Dia 01/11: baseline com regressão logística.
O XGBoost (dia 03/11) entra neste mesmo arquivo, usando as mesmas métricas.

Regras (docs/DECISOES.md):
- validação por GroupKFold com cliente_id (o mesmo cliente nunca nos dois lados);
- teste = 2016, só clientes novos (vem pronto do dados.dividir);
- sem rebalanceamento (defaults já são maioria);
- métricas: AUC e KS (ordenação) + Brier e calibração (preço).
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score, roc_curve
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler

from src.modelos.variaveis import CATEGORICAS, NUMERICAS, matriz

RAIZ = Path(__file__).resolve().parents[2]
PASTA_MODELOS = RAIZ / "modelos_salvos"
PASTA_RESULTADOS = RAIZ / "docs" / "resultados"

SEMENTE = 42
N_FOLDS = 5

# Variáveis de valor muito assimétrico: log antes de padronizar.
# Só as que estão em NUMERICAS (variáveis retiradas do modelo saem daqui sozinhas).
NUMERICAS_LOG = [c for c in [
    "valor_concedido", "renda_total", "valor_emprestimos_anteriores",
    "parcela_neutra_sobre_renda", "valor_sobre_renda", "divida_sobre_renda", "renda_relativa",
    "pagamentos_anteriores", "quitacoes_antecipadas_valor",
] if c in NUMERICAS]
NUMERICAS_LINEARES = [c for c in NUMERICAS if c not in NUMERICAS_LOG]


# --------------------------------------------------------------------------
# Métricas
# --------------------------------------------------------------------------
def ks(y, p) -> float:
    """Kolmogorov-Smirnov: maior separação entre bons e maus pagadores."""
    fpr, tpr, _ = roc_curve(y, p)
    return float(np.max(tpr - fpr))


def calibracao_por_faixa(y, p, n_faixas: int = 10) -> pd.DataFrame:
    """Média prevista × taxa real de default em faixas de probabilidade."""
    df = pd.DataFrame({"y": np.asarray(y), "p": np.asarray(p)})
    df["faixa"] = pd.qcut(df["p"], q=n_faixas, duplicates="drop")
    return (df.groupby("faixa", observed=True)
              .agg(contratos=("y", "size"), prevista=("p", "mean"), real=("y", "mean"))
              .round(3))


def metricas(y, p) -> dict:
    y = np.asarray(y)
    return {
        "contratos": int(len(y)),
        "default_real": round(float(y.mean()), 4),
        "default_previsto": round(float(np.mean(p)), 4),
        "auc": round(float(roc_auc_score(y, p)), 4),
        "ks": round(ks(y, p), 4),
        "brier": round(float(brier_score_loss(y, p)), 4),
    }


def metricas_por_grupo(df: pd.DataFrame, p, coluna: str = "pais") -> pd.DataFrame:
    linhas = []
    for valor, idx in df.groupby(coluna).groups.items():
        y = df.loc[idx, "default"]
        if y.nunique() < 2:
            continue
        linhas.append({coluna: valor, **metricas(y, pd.Series(p, index=df.index).loc[idx])})
    return pd.DataFrame(linhas).set_index(coluna)


# --------------------------------------------------------------------------
# Baseline: regressão logística
# --------------------------------------------------------------------------
def _log1p_seguro(x):
    return np.log1p(np.clip(x, 0, None))


def montar_baseline(C: float = 1.0, sem: frozenset | set = frozenset()) -> Pipeline:
    """sem = variáveis a deixar de fora (usado para testar grupos de variáveis)."""
    numericas_log = Pipeline([
        ("imputar", SimpleImputer(strategy="median", add_indicator=True)),
        ("log", FunctionTransformer(_log1p_seguro, feature_names_out="one-to-one")),
        ("escala", StandardScaler()),
    ])
    numericas = Pipeline([
        ("imputar", SimpleImputer(strategy="median", add_indicator=True)),
        ("escala", StandardScaler()),
    ])
    categoricas = OneHotEncoder(handle_unknown="ignore", min_frequency=0.01)

    preparo = ColumnTransformer([
        ("num_log", numericas_log, [c for c in NUMERICAS_LOG if c not in sem]),
        ("num", numericas, [c for c in NUMERICAS_LINEARES if c not in sem]),
        ("cat", categoricas, [c for c in CATEGORICAS if c not in sem]),
    ])
    return Pipeline([
        ("preparo", preparo),
        ("modelo", LogisticRegression(C=C, max_iter=2000, random_state=SEMENTE)),
    ])


def _para_modelo(df: pd.DataFrame) -> pd.DataFrame:
    """Matriz com categóricas como texto (o OneHotEncoder exige tipo uniforme)."""
    X = matriz(df).copy()
    for col in CATEGORICAS:
        X[col] = X[col].astype(str)
    return X


def validar_cruzado(modelo: Pipeline, treino: pd.DataFrame) -> pd.DataFrame:
    """GroupKFold por cliente_id no treino. Devolve as métricas de cada fold."""
    X, y, grupos = _para_modelo(treino), treino["default"], treino["cliente_id"]
    resultados = []
    for i, (idx_tr, idx_va) in enumerate(GroupKFold(n_splits=N_FOLDS).split(X, y, grupos), 1):
        assert not set(grupos.iloc[idx_tr]) & set(grupos.iloc[idx_va])  # segurança
        modelo.fit(X.iloc[idx_tr], y.iloc[idx_tr])
        p = modelo.predict_proba(X.iloc[idx_va])[:, 1]
        resultados.append({"fold": i, **metricas(y.iloc[idx_va], p)})
    return pd.DataFrame(resultados).set_index("fold")


def treinar_e_avaliar(modelo: Pipeline, treino: pd.DataFrame, teste: pd.DataFrame) -> dict:
    """Treina no treino inteiro e avalia uma única vez no teste."""
    modelo.fit(_para_modelo(treino), treino["default"])
    p_teste = modelo.predict_proba(_para_modelo(teste))[:, 1]
    return {
        "modelo": modelo,
        "p_teste": p_teste,
        "teste": metricas(teste["default"], p_teste),
        "teste_por_pais": metricas_por_grupo(teste, p_teste, "pais"),
        "calibracao": calibracao_por_faixa(teste["default"], p_teste),
    }


def comparar_com_bondora(teste: pd.DataFrame, p_modelo) -> pd.DataFrame:
    """Mesmo conjunto de teste: nosso modelo × PD do próprio Bondora (só comparação)."""
    linhas = {"nosso_modelo": metricas(teste["default"], p_modelo)}
    if "pd_bondora" in teste.columns and teste["pd_bondora"].notna().any():
        ok = teste["pd_bondora"].notna()
        linhas["pd_bondora"] = metricas(teste.loc[ok, "default"], teste.loc[ok, "pd_bondora"])
        linhas["nosso_modelo_mesmos_contratos"] = metricas(
            teste.loc[ok, "default"], pd.Series(p_modelo, index=teste.index)[ok])
    return pd.DataFrame(linhas).T


def salvar(modelo: Pipeline, nome: str, resultados: dict) -> Path:
    """Salva o modelo (.joblib, fora do Git) e as métricas (.json, vai para o Git)."""
    PASTA_MODELOS.mkdir(exist_ok=True)
    PASTA_RESULTADOS.mkdir(parents=True, exist_ok=True)
    caminho = PASTA_MODELOS / f"{nome}.joblib"
    joblib.dump(modelo, caminho)
    registro = {"modelo": nome, "data": datetime.now().isoformat(timespec="seconds"), **resultados}
    (PASTA_RESULTADOS / f"{nome}.json").write_text(
        json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8")
    return caminho


# --------------------------------------------------------------------------
# Escolha de variáveis SEM tocar no teste de 2016
# --------------------------------------------------------------------------
GRUPOS_V2 = {
    "historico": {"pagamentos_anteriores", "quitacoes_antecipadas_qtd", "quitacoes_antecipadas_valor"},
    "fracao_concedida": {"fracao_concedida"},
    "orcamento": {"caixa_livre_sobre_renda", "divida_renda_bondora", "refinanciamento_passivos"},
    "renda": {"renda_assistencial_sobre_renda", "renda_pensao_sobre_renda"},
    "scores_bureau": {"score_ee_mini", "score_fi_asiakastieto", "score_es_equifax", "score_es_microl"},
}


def divisao_temporal(treino: pd.DataFrame, ano_validacao: int = 2015):
    """Dentro do treino: ajusta até o ano anterior e valida no ano_validacao,
    só com clientes novos. Imita a divisão treino/teste, sem usar 2016."""
    tr = treino[treino["ano"] < ano_validacao]
    va = treino[(treino["ano"] == ano_validacao) & ~treino["cliente_id"].isin(set(tr["cliente_id"]))]
    return tr, va


def comparar_grupos(treino: pd.DataFrame, ano_validacao: int = 2015) -> pd.DataFrame:
    """Testa o modelo sem cada grupo de variáveis novas, validando em 2015.
    Olhe AUC (ordenação) e, principalmente, default_previsto × default_real e Brier."""
    tr, va = divisao_temporal(treino, ano_validacao)
    todas_v2 = set().union(*GRUPOS_V2.values())
    cenarios = {"v1 (sem as novas)": todas_v2, "v2 completo": set()}
    cenarios.update({f"v2 sem {g}": cols for g, cols in GRUPOS_V2.items()})
    linhas = {}
    for nome, sem in cenarios.items():
        m = montar_baseline(sem=frozenset(sem)).fit(_para_modelo(tr), tr["default"])
        p = m.predict_proba(_para_modelo(va))[:, 1]
        linhas[nome] = metricas(va["default"], p)
    return pd.DataFrame(linhas).T