"""A conversão da taxa efetiva do BC para nominal bate com a série mensal oficial (SGS 25464).

12 meses espalhados de 2011 a 2021 vão embutidos aqui (a efetiva anual da série 20742 e a taxa
mensal oficial da 25464), então o teste roda no CI sem os CSVs. Se os arquivos completos estiverem
em data/raw/, o teste confere os 187 meses também. O BC publica 2 casas decimais, então o
arredondamento explica até 0,005 ponto percentual ao mês.
"""
import pandas as pd

from src.dados import validar_conversao_bc as c

# (mês, % ao ano EFETIVA da série 20742, % ao mês oficial da série 25464)
AMOSTRA = [
    ("2011-03", 73.87, 4.72), ("2012-02", 81.34, 5.09), ("2013-05", 68.13, 4.42), ("2014-07", 101.29, 6.0),
    ("2015-08", 119.85, 6.79), ("2015-10", 129.19, 7.16), ("2016-03", 126.2, 7.04), ("2017-01", 140.88, 7.6),
    ("2018-01", 122.58, 6.89), ("2019-10", 98.55, 5.88), ("2020-08", 70.29, 4.54), ("2021-07", 76.99, 4.87),
]


def test_exemplo_do_data_md():
    """126,2% efetiva (mar/2016) = 84,5% nominal = 7,04% ao mês (seção 8 do DATA.md)."""
    assert abs(c.efetiva_para_nominal(126.2) - 84.5) < 0.05
    assert abs(c.efetiva_para_mensal(126.2) - 7.04) < 0.005


def test_conversao_bate_com_a_serie_oficial_em_12_meses():
    for mes, efetiva, oficial in AMOSTRA:
        dif = abs(c.efetiva_para_mensal(efetiva) - oficial)
        assert dif <= 0.005, f"{mes}: convertida {c.efetiva_para_mensal(efetiva):.4f} x oficial {oficial} (dif {dif:.4f})"


def test_nominal_anual_tambem_bate():
    for mes, efetiva, oficial in AMOSTRA:
        assert abs(c.efetiva_para_nominal(efetiva) - 12 * oficial) <= 0.06, mes


def test_comparar_e_resumo():
    serie_e = pd.Series({pd.Timestamp(m + "-01"): e for m, e, _ in AMOSTRA})
    serie_m = pd.Series({pd.Timestamp(m + "-01"): o for m, _, o in AMOSTRA})
    r = c.resumo(c.comparar(serie_e, serie_m))
    assert r["meses"] == 12 and r["dif_max_am"] <= 0.005 and r["acima_da_tolerancia"] == 0


def test_um_mes_errado_e_pego():
    serie_e = pd.Series({pd.Timestamp(m + "-01"): e for m, e, _ in AMOSTRA})
    serie_m = pd.Series({pd.Timestamp(m + "-01"): o for m, _, o in AMOSTRA})
    serie_m.iloc[3] += 0.5                                   # um valor errado
    r = c.resumo(c.comparar(serie_e, serie_m))
    assert r["acima_da_tolerancia"] == 1 and r["dif_max_am"] > 0.4


def test_serie_inteira_se_os_csvs_existirem():
    """Roda nos 187 meses só quando data/raw/ tem as duas séries (os CSVs ficam fora do Git)."""
    efetiva, mensal = c._achar(c.NOMES_EFETIVA), c._achar(c.NOMES_MENSAL)
    if not (efetiva.exists() and mensal.exists()):
        return
    r = c.resumo(c.comparar(c.ler_serie(efetiva), c.ler_serie(mensal)))
    assert r["dif_max_am"] <= 0.005 and r["acima_da_tolerancia"] == 0, r
