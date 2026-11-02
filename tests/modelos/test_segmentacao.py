"""K-Means: não usa colunas proibidas e roda ponta a ponta."""
from src.modelos.segmentacao import VARIAVEIS_PERFIL, descrever, escolher_k, segmentar
from src.modelos.variaveis import PROIBIDAS, criar_variaveis
from tests.modelos.test_treino import _base_sintetica


def test_segmentacao_sem_colunas_proibidas():
    assert not set(VARIAVEIS_PERFIL) & PROIBIDAS
    for col in ("juro_aa", "default", "genero", "idade", "pais"):
        assert col not in VARIAVEIS_PERFIL


def test_kmeans_ponta_a_ponta():
    base = criar_variaveis(_base_sintetica())
    tabela = escolher_k(base, ks=range(2, 4), amostra=300)
    assert list(tabela.index) == [2, 3]
    modelo = segmentar(base, k=3)
    resumo = descrever(base, modelo)
    assert len(resumo) == 3 and abs(resumo["participacao"].sum() - 1) < 1e-6