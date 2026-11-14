"""preparar_contrato() e parametros_preco(): as partes do prever() que a API também usa."""
import pandas as pd
import pytest

pytest.importorskip("xgboost")
from src.modelos import prever as modelo  # noqa: E402

PAC = {"referencia": pd.DataFrame({"pais": ["FI", "FI"], "ano": [2015, 2015], "renda_total": [1800.0, 2200.0]}),
       "euribor_12m": pd.Series([0.06, -0.01], index=pd.to_datetime(["2016-01-01", "2016-06-01"]))}


def test_prepare_contract_keeps_safra_and_clips_reference_year():
    df, year = modelo.preparar_contrato({"pais": "FI", "data_emprestimo": "2018-03-05", "prazo_meses": 36}, PAC)
    assert year == 2018 and int(df["ano"].iloc[0]) == 2015  # renda relativa usa o último ano do país


def test_price_parameters_follow_the_contract_month_and_country():
    df, year = modelo.preparar_contrato({"pais": "FI", "data_emprestimo": "2016-05-10", "prazo_meses": 60}, PAC)
    par = modelo.parametros_preco(df, PAC, year)
    assert par["euribor"] == 0.0006 and par["lgd"] == modelo.LGD_POR_PAIS["FI"] and par["prazo"] == 60
    assert par["custo_anual"] == pytest.approx(0.0006 + modelo.MARGEM_POR_SAFRA[2016])
    df, year = modelo.preparar_contrato({"pais": "FI", "data_emprestimo": "2016-07-01", "prazo_meses": 60}, PAC)
    assert modelo.parametros_preco(df, PAC, year)["euribor"] == 0.0  # Euribor negativa vira zero
