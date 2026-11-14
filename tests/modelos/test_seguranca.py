"""Testes que protegem o modelo de vazamento (docs/DECISOES.md, seções 3 e 4)."""
import pandas as pd

from src.modelos.dados import dividir
from src.modelos.variaveis import PROIBIDAS, colunas_do_modelo, criar_variaveis


def test_nenhuma_coluna_proibida_no_modelo():
    vazadas = set(colunas_do_modelo()) & PROIBIDAS
    assert not vazadas, f"colunas proibidas no modelo: {vazadas}"


def test_juro_e_parcela_fora_do_modelo():
    for col in ("juro_aa", "parcela_mensal", "pd_bondora", "rating", "genero", "idade",
                "estado_civil", "n_dependentes", "situacao_emprego", "finalidade"):
        assert col not in colunas_do_modelo()


def _base_exemplo():
    return pd.DataFrame({
        "cliente_id": ["a", "a", "b", "c", "c", "d"],
        "ano":        [2014, 2016, 2015, 2013, 2016, 2016],
    })


def test_cliente_nao_aparece_em_treino_e_teste():
    treino, teste = dividir(_base_exemplo())
    assert not set(treino["cliente_id"]) & set(teste["cliente_id"])


def test_teste_so_tem_2016_e_treino_ate_2015():
    treino, teste = dividir(_base_exemplo())
    assert treino["ano"].max() <= 2015
    assert set(teste["ano"]) == {2016}


def test_renda_zero_nao_gera_infinito():
    df = pd.DataFrame({
        "valor_concedido": [1000.0, 2000.0], "prazo_meses": [12, 24],
        "renda_total": [0.0, 1000.0], "passivos_total": [500.0, 300.0],
        "pais": ["EE", "EE"], "ano": [2015, 2015],
        "novo_cliente": [True, False],
        "tempo_emprego_atual": ["UpTo1Year", "MoreThan5Years"],
        "escolaridade": [4, 4], "tipo_moradia": [1, 1], "tipo_verificacao": [4, 4],
    })
    out = criar_variaveis(df)
    for col in ("parcela_neutra_sobre_renda", "valor_sobre_renda", "divida_sobre_renda", "renda_relativa"):
        assert not out[col].isin([float("inf"), float("-inf")]).any()
        assert pd.isna(out.loc[0, col])


def test_variaveis_v2_calculadas():
    df = pd.DataFrame({
        "valor_concedido": [1000.0, 2000.0], "valor_solicitado": [2000.0, 2000.0],
        "prazo_meses": [12, 24], "renda_total": [1000.0, 0.0], "passivos_total": [500.0, 300.0],
        "caixa_livre": [200.0, 50.0], "renda_assistencia_social": [100.0, 0.0],
        "renda_auxilio_familiar": [None, 0.0], "renda_pensao_alimenticia": [0.0, 0.0],
        "renda_pensao": [300.0, 0.0], "score_fi_asiakastieto": ["3", None],
        "pais": ["FI", "EE"], "ano": [2015, 2015], "novo_cliente": [True, False],
        "tempo_emprego_atual": ["UpTo1Year", "MoreThan5Years"],
        "escolaridade": [4, 4], "tipo_moradia": [1, 1], "tipo_verificacao": [4, 4],
    })
    out = criar_variaveis(df)
    assert out.loc[0, "fracao_concedida"] == 0.5
    assert out.loc[0, "caixa_livre_sobre_renda"] == 0.2
    assert out.loc[0, "renda_assistencial_sobre_renda"] == 0.1
    assert out.loc[0, "renda_pensao_sobre_renda"] == 0.3
    assert pd.isna(out.loc[1, "caixa_livre_sobre_renda"])        # renda 0 → vazio
    assert out.loc[1, "score_fi_asiakastieto"] in ("sem_info", "outros")  # fora da Finlândia


def test_variaveis_descartadas_fora_do_modelo():
    from src.modelos.variaveis import TESTADAS_E_DESCARTADAS
    assert not set(TESTADAS_E_DESCARTADAS) & set(colunas_do_modelo())

def test_scores_sem_equivalencia_viram_sem_info():
    """Asiakastieto 1 a 8 e MicroL "M" (a partir de 2017) não existem no treino: sem_info, não "outros"."""
    treino = pd.DataFrame({
        "valor_concedido": [1000.0] * 4, "prazo_meses": [12] * 4, "renda_total": [1000.0] * 4,
        "passivos_total": [0.0] * 4, "pais": ["FI", "FI", "ES", "EE"], "ano": [2015] * 4,
        "score_fi_asiakastieto": ["RL2", "RL1", None, None], "score_es_microl": [None, None, "M3", None],
        "novo_cliente": [True] * 4, "tempo_emprego_atual": ["UpTo1Year"] * 4,
        "escolaridade": [4] * 4, "tipo_moradia": [1] * 4, "tipo_verificacao": [4] * 4,
    })
    carteira = treino.assign(ano=2018, score_fi_asiakastieto=["3", "RL1", None, None],
                             score_es_microl=["M", None, "M", "M"])
    out = criar_variaveis(carteira, referencia=treino)
    assert out.loc[0, "score_fi_asiakastieto"] == "sem_info"
    assert out.loc[1, "score_fi_asiakastieto"] == "RL1"          # escala antiga continua
    assert (out["score_es_microl"].iloc[[0, 2, 3]] == "sem_info").all()
