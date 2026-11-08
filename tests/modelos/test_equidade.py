"""Equidade: acha uma diferença plantada e não inventa uma que não existe."""
import numpy as np
import pandas as pd

from src.app.carteira import carregar_equidade
from src.modelos.equidade import comparacoes


def _lote(gap_mulher_pp=0.0, gap_jovem_pp=0.0, n=6000, semente=0):
    r = np.random.default_rng(semente)
    pd_ = r.uniform(0.05, 0.9, n)
    pais = r.choice(["EE", "ES", "FI"], n)
    genero = r.choice([0, 1, 2], n)
    idade = r.integers(16, 70, n)
    justo = 0.15 + 0.5 * pd_ + np.where(pais == "ES", 0.05, 0)
    cobrado = (justo + r.normal(0, 0.05, n) + (genero == 1) * gap_mulher_pp / 100
               + ((idade >= 18) & (idade <= 25)) * gap_jovem_pp / 100)
    lote = pd.DataFrame({
        "ano": r.choice([2014, 2016, 2019], n), "pais": pais, "pd": pd_,
        "faixa": pd.cut(pd_, [0, .3, .45, .6, .75, 1.01], labels=list("ABCDE")).astype(str),
        "valor_concedido": r.uniform(500, 5000, n), "prazo_meses": r.choice([12, 36, 60], n),
        "juro_cobrado": cobrado, "juro_justo": justo, "fora_da_auditoria": False})
    return lote, pd.Series(genero), pd.Series(idade)


def test_acha_diferenca_plantada():
    g, i = comparacoes(*_lote(gap_mulher_pp=3.0, gap_jovem_pp=-2.0))
    assert g["ic95_min"] < 3.0 < g["ic95_max"] and g["ic95_min"] > 0
    assert i["ic95_min"] < -2.0 < i["ic95_max"] and i["ic95_max"] < 0


def test_sem_diferenca_ic_cruza_zero():
    g, i = comparacoes(*_lote())
    assert g["ic95_min"] < 0 < g["ic95_max"]
    assert i["ic95_min"] < 0 < i["ic95_max"]


def test_janela_genero_e_formato_do_painel(tmp_path):
    lote, genero, idade = _lote()
    g, i = comparacoes(lote, genero, idade)
    na_janela = lote["ano"].between(2013, 2016)
    assert g["n_grupo_a"] == int((na_janela & (genero == 1)).sum())   # 2019 fora
    assert i["n_grupo_a"] == int(idade.between(18, 25).sum())          # < 18 fora
    import json
    (tmp_path / "equidade.json").write_text(json.dumps([g, i], ensure_ascii=False), encoding="utf-8")
    lido = carregar_equidade(tmp_path)
    assert [e["atributo"] for e in lido] == ["Gênero", "Idade"]
    assert set(lido[0]) >= {"diferenca_pp", "ic95_min", "ic95_max", "n_grupo_a", "n_grupo_b"}


def test_risco_nao_visto_acha_jovem_com_mais_default():
    from src.modelos.equidade import risco_nao_visto
    lote, genero, idade = _lote(n=8000)
    r = np.random.default_rng(1)
    jovem = idade.between(18, 25)
    p_real = np.clip(lote["pd"] + jovem * 0.10, 0, 1)        # jovem: +10 p.p. de default real
    default = pd.Series(r.random(len(lote)) < p_real)
    g, i = risco_nao_visto(lote, default, genero, idade)
    assert i["ic95_min"] < 10 < i["ic95_max"] and i["ic95_min"] > 0
    assert g["ic95_min"] < 0 < g["ic95_max"]
