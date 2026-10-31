"""Testes do baseline com dados sintéticos (rápidos, sem o CSV)."""
import numpy as np
import pandas as pd

from src.modelos.treino import metricas, montar_baseline, treinar_e_avaliar, validar_cruzado
from src.modelos.variaveis import criar_variaveis


def _base_sintetica(n=600, semente=0):
    r = np.random.default_rng(semente)
    renda = r.lognormal(7, 0.5, n)
    divida = r.lognormal(6, 1, n)
    risco = 1 / (1 + np.exp(-(divida / renda - 0.5)))
    return pd.DataFrame({
        "cliente_id": [f"c{i % 400}" for i in range(n)],
        "ano": r.choice([2013, 2014, 2015], n),
        "pais": r.choice(["EE", "ES", "FI"], n),
        "valor_concedido": r.uniform(500, 5000, n),
        "prazo_meses": r.choice([12, 36, 60], n),
        "renda_total": renda,
        "passivos_total": divida,
        "n_emprestimos_anteriores": r.integers(0, 5, n),
        "valor_emprestimos_anteriores": r.uniform(0, 3000, n),
        "passivos_existentes": r.integers(0, 6, n),
        "novo_cliente": r.choice([True, False], n),
        "tempo_emprego_atual": r.choice(["UpTo1Year", "MoreThan5Years"], n),
        "escolaridade": r.choice([1, 2, 3, 4, 5], n),
        "tipo_moradia": r.choice([1, 2, 3], n),
        "tipo_verificacao": r.choice([1, 4], n),
        # colunas usadas pelas variáveis v2
        "valor_solicitado": r.uniform(500, 6000, n),
        "pagamentos_anteriores": r.uniform(0, 2000, n),
        "quitacoes_antecipadas_qtd": r.integers(0, 3, n),
        "quitacoes_antecipadas_valor": r.uniform(0, 1000, n),
        "caixa_livre": r.uniform(0, 800, n),
        "divida_renda": r.uniform(0, 60, n),
        "refinanciamento_passivos": r.integers(0, 2, n),
        "renda_assistencia_social": r.uniform(0, 100, n),
        "renda_auxilio_familiar": r.uniform(0, 50, n),
        "renda_pensao_alimenticia": r.uniform(0, 50, n),
        "renda_pensao": r.uniform(0, 200, n),
        "score_ee_mini": r.uniform(500, 1000, n),
        "score_fi_asiakastieto": r.choice(["1", "3", "5"], n),
        "score_es_equifax": r.choice(["A", "B"], n),
        "score_es_microl": r.choice(["M", "M5"], n),
        "default": (r.uniform(size=n) < risco).astype(int),
    })


def test_metricas_no_intervalo():
    m = metricas([0, 0, 1, 1], [0.1, 0.4, 0.35, 0.8])
    assert 0 <= m["auc"] <= 1 and 0 <= m["ks"] <= 1 and 0 <= m["brier"] <= 1


def test_baseline_treina_e_preve_probabilidades():
    base = criar_variaveis(_base_sintetica())
    treino, teste = base.iloc[:450], criar_variaveis(_base_sintetica(150, 1), referencia=base.iloc[:450])
    r = treinar_e_avaliar(montar_baseline(), treino, teste)
    assert r["p_teste"].min() >= 0 and r["p_teste"].max() <= 1
    assert r["teste"]["auc"] > 0.5   # aprende algo além do acaso


def test_validacao_cruzada_separa_clientes():
    base = criar_variaveis(_base_sintetica())
    folds = validar_cruzado(montar_baseline(), base)   # o próprio método faz assert por fold
    assert len(folds) == 5


def test_comparar_grupos_roda_sem_2016():
    from src.modelos.treino import GRUPOS_V2, comparar_grupos
    base = _base_sintetica(900)
    base["ano"] = np.random.default_rng(1).choice([2013, 2014, 2015], len(base))
    base = criar_variaveis(base)
    tabela = comparar_grupos(base)
    assert len(tabela) == 2 + len(GRUPOS_V2)
    assert (base["ano"] <= 2015).all()