"""Leitura e recorte da base para o modelo de risco.

Lê o CSV do Bondora com os MESMOS nomes e tipos do banco (reaproveita o
mapeamento do script de carga do Marcos). Quando o PostgreSQL estiver pronto,
basta trocar `ler_base()` por uma consulta SQL: o resto não muda.

Decisões (docs/DECISOES.md):
- coortes maduras 2009–2016, só contratos encerrados;
- fora: Eslováquia (reestruturados ficam no modelo e só saem da auditoria de preço);
- treino 2009–2015; teste 2016 sem clientes que aparecem no treino.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

# Ajuste este import para onde o script do Marcos estiver no repositório.
from src.dados.carga_bondora import TABELAS, _carregar_env, _converter

RAIZ = Path(__file__).resolve().parents[2]
CSV_PADRAO = RAIZ / "data" / "raw" / "LoanData_Bondora.csv"

ANOS_TREINO = range(2009, 2016)   # 2009 a 2015
ANO_TESTE = 2016
PAISES_FORA = {"SK"}


def ler_base(caminho: Path = CSV_PADRAO) -> pd.DataFrame:
    """Uma linha por contrato, com os nomes e tipos das tabelas do banco.

    Precisa da CLIENTE_ID_SAL (a mesma do grupo) no .env da raiz do projeto,
    para o cliente_id sair igual ao do banco.
    """
    _carregar_env(str(RAIZ / ".env"))
    bruto = pd.read_csv(caminho, dtype=str, keep_default_na=False,
                        na_values=[""], encoding="utf-8-sig")
    colunas: dict[str, pd.Series] = {}
    for cols in TABELAS.values():
        for col in cols:
            if col.db in colunas:          # loan_id aparece nas três tabelas
                continue
            nome = next((n for n in col.csv if n in bruto.columns), None)
            if nome is None:
                continue
            convertido, _ = _converter(bruto[nome], col)
            colunas[col.db] = convertido
    df = pd.DataFrame(colunas)
    df["data_emprestimo"] = pd.to_datetime(df["data_emprestimo"], errors="coerce")
    return df


def preparar(df: pd.DataFrame) -> pd.DataFrame:
    """Cria alvo e ano e aplica o recorte das coortes maduras."""
    df = df.copy()
    df["ano"] = df["data_emprestimo"].dt.year
    df["default"] = df["data_default"].notna().astype(int)

    encerrado = (df["status"] == "Repaid") | (df["default"] == 1)
    no_periodo = df["ano"].between(min(ANOS_TREINO), ANO_TESTE)
    fora_pais = df["pais"].isin(PAISES_FORA)

    # Reestruturados FICAM no modelo: tirá-los seria escolher os dados por algo que
    # aconteceu depois da concessão (são 76% de default) e o modelo subestimaria o risco.
    # Eles só saem da AUDITORIA de preço, porque o juro mudou no meio do contrato.
    if "reestruturado" in df.columns:
        df["fora_da_auditoria"] = df["reestruturado"].fillna(False).astype(bool)
    else:
        df["fora_da_auditoria"] = False

    manter = no_periodo & encerrado & ~fora_pais
    return df.loc[manter].reset_index(drop=True)


def dividir(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Treino 2009–2015; teste 2016 só com clientes que o treino não viu."""
    treino = df[df["ano"].isin(ANOS_TREINO)]
    clientes_treino = set(treino["cliente_id"])
    teste = df[(df["ano"] == ANO_TESTE) & ~df["cliente_id"].isin(clientes_treino)]
    return treino.reset_index(drop=True), teste.reset_index(drop=True)