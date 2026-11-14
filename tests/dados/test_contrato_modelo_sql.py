"""A view do contrato no formato do prever() (db/08_view_contrato_modelo.sql), sem banco: lê o SQL
e compara as colunas com as listas do código (src/modelos/variaveis.py e src/modelos/prever.py).

O cuidado principal: o criar_variaveis() preenche com vazio, sem erro, toda coluna de FONTES_V2 que
faltar. Se a view esquecesse uma delas (como score_ee_mini), o prever() rodaria com outra PD.
"""
import re
from pathlib import Path

import numpy as np
import pandas as pd

from src.dados.carga_bondora import COLUNAS_LISTA_NEGRA, COLUNAS_SO_AUDITORIA
from src.modelos.variaveis import CATEGORICAS, FONTES_V2, NUMERICAS, colunas_do_modelo, criar_variaveis

SQL = Path(__file__).resolve().parents[2] / "db" / "08_view_contrato_modelo.sql"
# o que o prever() lê da linha além das variáveis do modelo (src/modelos/prever.py)
LIDAS_PELO_PREVER = {"loan_id", "data_emprestimo", "juro_aa", "pais", "prazo_meses",
                     "valor_concedido", "renda_total"}          # CHECAR_FAIXA
EXCECOES_LISTA_NEGRA = {"juro_aa"}                               # o preço auditado (PR #81)


def _sem_comentarios(texto: str) -> str:
    return re.sub(r"--.*$", "", texto, flags=re.M)


def _colunas() -> list[str]:
    corpo = _sem_comentarios(SQL.read_text(encoding="utf-8"))
    corpo = corpo.split("CREATE OR REPLACE VIEW vw_contrato_modelo AS", 1)[1]
    corpo = corpo.split("SELECT", 1)[1].split("FROM emprestimo", 1)[0]
    return [item.strip().split(".")[-1] for item in corpo.split(",") if item.strip()]


def _linha_ficticia(colunas: list[str]) -> pd.DataFrame:
    """Uma linha com todas as colunas da view, para rodar o criar_variaveis() sem banco."""
    valores = {c: 1.0 for c in colunas}
    valores.update(loan_id="x", data_emprestimo=pd.Timestamp("2016-03-01"), pais="EE",
                   tempo_emprego_atual="MoreThan5Years", score_fi_asiakastieto=np.nan,
                   score_es_equifax=np.nan, score_es_microl=np.nan, novo_cliente=True)
    df = pd.DataFrame([valores])
    df["ano"] = 2016
    return df


def test_view_existe_e_e_idempotente():
    assert "CREATE OR REPLACE VIEW vw_contrato_modelo AS" in _sem_comentarios(SQL.read_text(encoding="utf-8"))


def test_sem_colunas_proibidas():
    colunas = set(_colunas())
    assert not colunas & (set(COLUNAS_LISTA_NEGRA) - EXCECOES_LISTA_NEGRA), "coluna da lista negra na view"
    assert not colunas & set(COLUNAS_SO_AUDITORIA), "gênero, idade, estado civil ou dependentes na view"
    assert "cliente_id" not in colunas


def test_tem_tudo_que_o_prever_le():
    faltam = LIDAS_PELO_PREVER - set(_colunas())
    assert not faltam, f"o prever() lê e a view não tem: {sorted(faltam)}"


def test_variaveis_do_modelo_vem_da_view_e_nao_do_preenchimento_com_vazio():
    """Cada variável do modelo tem que estar na view ou ser calculada a partir dela; nenhuma pode
    sair do preenchimento automático de FONTES_V2 com vazio."""
    colunas = _colunas()
    df = _linha_ficticia(colunas)
    saida = criar_variaveis(df, referencia=df)
    calculadas = set(saida.columns) - set(df.columns) - set(FONTES_V2)
    faltam = set(colunas_do_modelo()) - set(colunas) - calculadas
    assert not faltam, f"variáveis do modelo sem fonte na view: {sorted(faltam)}"
    assert set(colunas_do_modelo()) == set(NUMERICAS + CATEGORICAS)


def test_nao_sobra_coluna_sem_uso():
    """Toda coluna da view é lida pelo prever() ou é variável do modelo (ou fonte de uma)."""
    fontes_de_derivadas = {"passivos_total"}                     # divida_sobre_renda
    usadas = LIDAS_PELO_PREVER | set(colunas_do_modelo()) | fontes_de_derivadas
    sobram = set(_colunas()) - usadas
    assert not sobram, f"colunas sem uso no prever(): {sorted(sobram)}"


def test_uma_coluna_por_nome_e_21_no_total():
    colunas = _colunas()
    assert len(colunas) == len(set(colunas)) == 21
