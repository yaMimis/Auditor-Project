"""prever(): saída no formato do FORMATO_JSON.md — versão 2 (05/11).
LGD por país (notebook 07) e margem por safra (notebook 08).
PROVISÓRIO até 09/11: margem de incerteza constante (±2 p.p.)."""
from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd
from scipy.optimize import brentq

from src.modelos.treino import _para_modelo
from src.modelos.variaveis import CATEGORICAS, criar_variaveis
from src.modelos.xgb import motivos

RAIZ = Path(__file__).resolve().parents[2]
PACOTE_PADRAO = RAIZ / "modelos_salvos" / "pacote_prever_v1.joblib"
VERSAO = "xgboost_v2"

FAIXAS = [(0.30, "A"), (0.45, "B"), (0.60, "C"), (0.75, "D"), (1.01, "E")]
LGD_PADRAO = 0.60      
LGD_POR_PAIS = {"EE": 0.34, "ES": 0.76, "FI": 0.55}   # LGD realizada, defaults 2014–2015 (notebook 07)    
MARGEM_PADRAO = 0.05       # custos + margem ao ano, provisório
# custos + margem ao ano por safra: média do justo = média do cobrado (notebook 08)
MARGEM_POR_SAFRA = {2009: 0.1347, 2010: 0.1968, 2011: 0.1915, 2012: 0.1927,
                    2013: 0.2078, 2014: 0.1076, 2015: 0.1527, 2016: 0.3166}
MARGEM_INCERTEZA_PP = 2.0  # provisório: ± pontos percentuais
CHECAR_FAIXA = ["valor_concedido", "prazo_meses", "renda_total"]


def montar_pacote(modelo, treino: pd.DataFrame, euribor_12m: pd.Series) -> dict:
    ref_cols = list(dict.fromkeys(["pais", "ano", "renda_total"] + CATEGORICAS))
    return {
        "modelo": modelo,
        "referencia": treino[[c for c in ref_cols if c in treino.columns]].copy(),
        "faixas_treino": {c: (float(treino[c].quantile(0.005)), float(treino[c].quantile(0.995)))
                          for c in CHECAR_FAIXA},
        "paises": set(treino["pais"].dropna()),
        "euribor_12m": euribor_12m,
    }


def salvar_pacote(pacote: dict, caminho: Path = PACOTE_PADRAO) -> Path:
    caminho.parent.mkdir(exist_ok=True)
    joblib.dump(pacote, caminho)
    return caminho


_CACHE: dict = {}


def _pacote(caminho: Path = PACOTE_PADRAO) -> dict:
    if caminho not in _CACHE:
        _CACHE[caminho] = joblib.load(caminho)
    return _CACHE[caminho]


def juro_justo(prazo: int, pd_total: float, lgd: float, custo_anual: float) -> float:
    """Taxa anual nominal (capitalização mensal, i/12) em que o valor presente
    esperado dos recebimentos = valor emprestado. Mesma convenção do juro do Bondora."""
    prazo = max(int(prazo), 1)
    h = 1 - (1 - pd_total) ** (1 / max(prazo, 12)) 
    d = (1 + custo_anual) ** (1 / 12) - 1

    def vp_menos_1(taxa):
        i = taxa / 12                    # nominal, como o juro do Bondora
        parcela = i / (1 - (1 + i) ** -prazo)
        saldo, vivo, vp = 1.0, 1.0, 0.0
        for t in range(1, prazo + 1):
            vp += (vivo * (1 - h) * parcela + vivo * h * (1 - lgd) * saldo) / (1 + d) ** t
            saldo -= parcela - saldo * i
            vivo *= 1 - h
        return vp - 1.0
    try:
        return float(brentq(vp_menos_1, 1e-6, 5.0))
    except ValueError:
        return 5.0


def _faixa(pd_: float) -> str:
    return next(letra for limite, letra in FAIXAS if pd_ < limite)


def _fora_da_faixa(df: pd.DataFrame, pac: dict) -> bool:
    if df["pais"].iloc[0] not in pac["paises"]:
        return True
    for c, (lo, hi) in pac["faixas_treino"].items():
        v = df[c].iloc[0]
        if pd.isna(v) or v < lo or v > hi:
            return True
    return False


def prever(contrato: dict, pacote: dict | None = None) -> dict:
    """contrato = uma linha da base (nomes do banco), com juro_aa em %."""
    pac = pacote or _pacote()
    df = pd.DataFrame([contrato])
    # sem data (contrato novo vindo da API) → hoje
    if "data_emprestimo" not in df or pd.isna(df["data_emprestimo"].iloc[0]):
        df["data_emprestimo"] = pd.Timestamp.today().normalize()
    if "ano" not in df:
        df["ano"] = pd.to_datetime(df["data_emprestimo"]).dt.year
    ano_contrato = int(df["ano"].iloc[0])   # usado na margem por safra
    # ano além do treino → último ano do país (só serve para a mediana de renda)
    anos_ref = pac["referencia"].loc[pac["referencia"]["pais"] == df["pais"].iloc[0], "ano"]
    if len(anos_ref):
        df["ano"] = min(ano_contrato, int(anos_ref.max()))
    juro_cobrado = round(float(df["juro_aa"].iloc[0]) / 100, 4)
    base = {"contrato_id": str(df.get("loan_id", pd.Series(["?"])).iloc[0]),
            "versao_modelo": VERSAO, "juro_cobrado": juro_cobrado}

    if _fora_da_faixa(df, pac):
        return {**base, "pd": None, "pd_ic95": None, "faixa": None, "juro_justo": None,
                "juro_justo_min": None, "juro_justo_max": None, "diferenca_pp": None,
                "situacao_preco": "revisao_manual", "motivos": [], "alerta_dados": True}

    df = criar_variaveis(df, referencia=pac["referencia"])
    X = _para_modelo(df)
    pd_ = float(pac["modelo"].predict_proba(X)[0, 1])

    mes = pd.to_datetime(df["data_emprestimo"].iloc[0]).to_period("M").to_timestamp()
    e12 = pac["euribor_12m"].sort_index()
    valor = e12.asof(mes)                    # último mês disponível ≤ data do contrato
    if pd.isna(valor):
        valor = e12.iloc[0]
    euribor = max(float(valor) / 100, 0.0)
    lgd = LGD_POR_PAIS.get(df["pais"].iloc[0], LGD_PADRAO)
    margem = MARGEM_POR_SAFRA.get(ano_contrato, MARGEM_POR_SAFRA[max(MARGEM_POR_SAFRA)])  # ano novo → última safra
    justo = round(juro_justo(df["prazo_meses"].iloc[0], pd_, lgd, euribor + margem), 4)
    jmin = round(max(justo - MARGEM_INCERTEZA_PP / 100, 0), 4)
    jmax = round(justo + MARGEM_INCERTEZA_PP / 100, 4)

    if juro_cobrado > jmax:
        situacao = "acima_do_justo"
    elif juro_cobrado < jmin:
        situacao = "abaixo_do_justo"
    else:
        situacao = "dentro_da_margem"

    return {**base,
            "pd": round(pd_, 4), "pd_ic95": None, "faixa": _faixa(pd_),
            "juro_justo": justo, "juro_justo_min": jmin, "juro_justo_max": jmax,
            "diferenca_pp": round((juro_cobrado - justo) * 100, 1),
            "situacao_preco": situacao,
            "motivos": motivos(pac["modelo"], X)[0],
            "alerta_dados": False}

def casos_de_teste(base: pd.DataFrame, pacote: dict | None = None,
                   n: int = 2, semente: int = 0, max_tentativas: int = 3000) -> dict:
    """Contratos reais da base, n por situação, já na saída do prever()."""
    pac = pacote or _pacote()
    casos = {s: [] for s in ("acima_do_justo", "abaixo_do_justo",
                             "dentro_da_margem", "revisao_manual")}
    amostra = base.sample(min(len(base), max_tentativas), random_state=semente)
    for _, linha in amostra.iterrows():
        saida = prever(linha.to_dict(), pac)
        if len(casos[saida["situacao_preco"]]) < n:
            casos[saida["situacao_preco"]].append(saida)
        if all(len(v) >= n for v in casos.values()):
            break
    return casos