"""Testes de src/dados/roi_backtest.py, sem banco: uma carteira pequena com contas feitas à mão."""
import numpy as np
import pandas as pd

from src.dados import roi_backtest as r


def _carteira() -> pd.DataFrame:
    linhas = [
        # id, ano, situação, faixa, valor, rentabilidade, reestruturado
        ("a", 2016, "abaixo_do_justo", "A", 1000.0, -0.50, False),
        ("b", 2016, "abaixo_do_justo", "A", 3000.0, 0.10, False),
        ("c", 2016, "acima_do_justo", "A", 2000.0, 0.20, False),
        ("d", 2016, "dentro_da_margem", "B", 500.0, 0.00, False),
        ("e", 2016, "revisao_manual", None, 400.0, -1.00, False),
        ("f", 2016, "acima_do_justo", "A", 9999.0, -1.00, True),     # reestruturado: fora
        ("g", 2019, "abaixo_do_justo", "A", 1000.0, np.nan, False),  # sem desfecho: fora
    ]
    df = pd.DataFrame(linhas, columns=["contrato_id", "ano", "situacao_preco", "faixa", "valor_concedido",
                                       "rentabilidade_realizada", "fora_da_auditoria"])
    res = df["rentabilidade_realizada"] * df["valor_concedido"]
    df["perda_nao_coberta_eur"] = (-res).clip(lower=0).where(df["rentabilidade_realizada"].notna())
    df["versao_modelo"] = "teste"
    return df


def test_so_2016_com_desfecho_e_sem_reestruturados():
    assert set(r.preparar(_carteira())["contrato_id"]) == {"a", "b", "c", "d", "e"}


def test_roi_ponderado_pelo_valor():
    s = r.por_situacao(r.preparar(_carteira()))
    abaixo = s.loc["abaixo_do_justo"]
    assert abaixo.contratos == 2 and abaixo.concedido_eur == 4000
    assert abaixo.resultado_eur == -200                  # −500 + 300
    assert abs(abaixo.roi - (-0.05)) < 1e-12             # −200 ÷ 4.000, e não a média de −50% e +10%
    assert abaixo.perda_nao_coberta_eur == 500           # só o contrato com prejuízo
    total = s.loc["total"]
    assert total.contratos == 5 and total.resultado_eur == -200 + 400 + 0 - 400


def test_faixa_compara_abaixo_com_acima():
    f = r.por_faixa(r.preparar(_carteira()))
    assert list(f.index) == ["A", "B"]                   # revisão manual não tem faixa
    assert bool(f.loc["A", "abaixo_rende_menos"])         # −5% < +20%
    assert f.loc["A", "n_abaixo_do_justo"] == 2


def test_markdown_usa_virgula_decimal():
    md = r.markdown(r.preparar(_carteira()), "exemplo")
    assert "−5,0%" in md and "| A |" in md and "sim" in md
