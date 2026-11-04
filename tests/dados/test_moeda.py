"""Testes da correção de moeda (src/dados/moeda.py): renda e passivos de 2009–2010 em coroas."""
import numpy as np
import pandas as pd

from src.dados.moeda import (
    COLUNAS_EM_COROAS, DATA_EURO, TAXA_EEK_POR_EUR, antes_do_euro, coroas_para_euros,
)
from src.dados.validacao import _cruzamentos


def _df():
    return pd.DataFrame({
        "data_emprestimo": pd.to_datetime(["2010-12-31", "2011-01-01", "2009-05-10", None]),
        "pais": ["EE", "EE", "EE", "EE"],
        "renda_total": [15646.6, 1564.66, 7823.3, 1000.0],
        "passivos_total": [3129.32, 100.0, np.nan, 50.0],
        "valor_concedido": [300.0, 300.0, 300.0, 300.0],
    })


def test_constantes():
    assert TAXA_EEK_POR_EUR == 15.6466
    assert DATA_EURO == pd.Timestamp("2011-01-01")
    assert "renda_total" in COLUNAS_EM_COROAS and "passivos_total" in COLUNAS_EM_COROAS
    assert "valor_concedido" not in COLUNAS_EM_COROAS      # valores de empréstimo já estão em euros


def test_so_antes_de_2011_e_convertido():
    df = _df()
    out = coroas_para_euros(df, antes_do_euro(df["data_emprestimo"], df["pais"]))
    assert out["renda_total"].tolist() == [1000.0, 1564.66, 500.0, 1000.0]
    # 31/12/2010 converte; 01/01/2011 e data vazia não


def test_passivos_vazio_continua_vazio():
    df = _df()
    out = coroas_para_euros(df, antes_do_euro(df["data_emprestimo"], df["pais"]))
    assert out["passivos_total"].iloc[0] == 200.0
    assert out["passivos_total"].iloc[1] == 100.0
    assert np.isnan(out["passivos_total"].iloc[2])          # vazio não vira número


def test_valor_do_emprestimo_nao_muda():
    df = _df()
    out = coroas_para_euros(df, antes_do_euro(df["data_emprestimo"], df["pais"]))
    assert out["valor_concedido"].tolist() == [300.0] * 4


def test_coluna_ausente_e_ignorada():
    df = _df().drop(columns=["passivos_total"])
    out = coroas_para_euros(df, antes_do_euro(df["data_emprestimo"], df["pais"]))
    assert "passivos_total" not in out.columns
    assert out["renda_total"].iloc[0] == 1000.0


def test_sem_contrato_antigo_nada_muda():
    df = _df().iloc[[1, 3]].copy()
    antes = df.copy()
    out = coroas_para_euros(df, antes_do_euro(df["data_emprestimo"], df["pais"]))
    assert out["renda_total"].tolist() == antes["renda_total"].tolist()


def test_so_a_estonia_e_convertida():
    """Outro país com data anterior a 2011 NÃO é convertido (já usava o euro)."""
    df = pd.DataFrame({
        "data_emprestimo": pd.to_datetime(["2010-06-01"] * 5),
        "pais": ["EE", "FI", "ES", "SK", None],
        "renda_total": [15646.6] * 5,
    })
    out = coroas_para_euros(df, antes_do_euro(df["data_emprestimo"], df["pais"]))
    assert out["renda_total"].tolist() == [1000.0, 15646.6, 15646.6, 15646.6, 15646.6]


def test_pais_com_espaco_e_minuscula_ainda_e_estonia():
    datas = pd.Series(pd.to_datetime(["2010-06-01", "2010-06-01"]))
    assert antes_do_euro(datas, pd.Series([" ee ", "Ee"])).tolist() == [True, True]


def test_pais_e_obrigatorio():
    """Chamar sem o país dá erro, em vez de converter outros países por engano."""
    try:
        antes_do_euro(pd.Series(pd.to_datetime(["2010-06-01"])))
    except TypeError:
        return
    raise AssertionError("antes_do_euro deveria exigir o país")


# --- o guarda da validação: renda de 2009–2010 em outra unidade vira ERRO ----------------
def _tabelas_ee(multiplicador_2010):
    n = 40
    datas = pd.to_datetime(["2010-06-15"] * n + ["2012-06-15"] * n)
    ids = [f"{i:08x}-0000-4000-8000-{i:012x}" for i in range(2 * n)]
    renda = [800.0 * multiplicador_2010] * n + [800.0] * n
    e = pd.DataFrame({"loan_id": ids, "data_emprestimo": datas})
    c = pd.DataFrame({"loan_id": ids, "pais": ["EE"] * (2 * n), "renda_total": renda})
    return {"emprestimo": e, "cliente": c}


def _achou_moeda(linhas):
    return any("outra unidade" in linha["regra"] for linha in linhas)


def test_guarda_pega_renda_em_coroas():
    assert _achou_moeda(_cruzamentos(_tabelas_ee(15.6466), parcial=True))


def test_guarda_aceita_renda_convertida():
    assert not _achou_moeda(_cruzamentos(_tabelas_ee(1.0), parcial=True))


def test_guarda_nao_dispara_com_poucos_dados():
    t = _tabelas_ee(15.6466)
    t["emprestimo"], t["cliente"] = t["emprestimo"].iloc[:10], t["cliente"].iloc[:10]
    assert not _achou_moeda(_cruzamentos(t, parcial=True))
