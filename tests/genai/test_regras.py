"""Testes das regras de texto da conferência (REGRAS_PARECER.md, seções 3, 4 e 9).

Rodar na pasta raiz:  python -m pytest tests/genai -q
"""
import pytest

from genai.src.checagem import (EntradaPrever, RespostaLLM, conferir_parecer, contar_frases,
                                motivos_permitidos)

ENTRADA = EntradaPrever.model_validate({
    "contrato_id": "TESTE-1", "versao_modelo": "teste",
    "pd": 0.184, "faixa": "C", "juro_cobrado": 0.249,
    "juro_justo": 0.162, "juro_justo_min": 0.141, "juro_justo_max": 0.183,
    "situacao_preco": "acima_do_justo",
    "motivos": [
        {"variavel": "DebtToIncome", "rotulo": "dívidas em relação à renda", "efeito": "aumenta_risco"},
        {"variavel": "Age", "rotulo": "idade do cliente", "efeito": "reduz_risco"},
        {"variavel": "Gender", "rotulo": "sexo", "efeito": "aumenta_risco"},
        {"variavel": "Country", "rotulo": "país de origem", "efeito": "aumenta_risco"},
        {"variavel": "age_group", "rotulo": "faixa etária", "efeito": "reduz_risco"},
        {"variavel": "LoanDuration", "rotulo": "prazo do empréstimo", "efeito": "aumenta_risco"},
    ],
})

RESPOSTA = {
    "resumo": "Risco faixa C (chance de não pagar de 18,4%). O juro cobrado está acima do justo.",
    "pontos_de_atencao": ["O juro cobrado (24,9% ao ano) está acima da margem do juro justo."],
    "recomendacao_texto": "Recomenda-se revisar o preço. A decisão final é do analista.",
    "fontes": [],
    "numeros_citados": {"pd": 0.184, "juro_cobrado": 0.249},
}


def resposta(**mudancas):
    return RespostaLLM.model_validate({**RESPOSTA, **mudancas})


# ---------- atributos sensíveis nos motivos ----------

def test_motivos_sensiveis_sao_retirados():
    rotulos = [m.rotulo for m in motivos_permitidos(ENTRADA)]
    assert rotulos == ["dívidas em relação à renda", "prazo do empréstimo"]


# ---------- vocabulário ----------

@pytest.mark.parametrize("palavra", ["ilegal", "ilegais", "ilegalmente", "ilícito", "abusiva",
                                     "abusividade", "fraude", "fraudulento", "criminoso", "viola",
                                     "violou", "violado", "violação", "irregular", "irregularidade",
                                     "discriminação", "discriminatório", "Ilegalidade"])
def test_palavra_proibida_e_pega(palavra):
    texto = f"O juro cobrado (24,9% ao ano) parece {palavra}."
    problemas = conferir_parecer(resposta(pontos_de_atencao=[texto]), ENTRADA, [])
    assert any("palavra proibida" in p for p in problemas)


def test_discriminar_no_sentido_de_detalhar_e_permitido():
    texto = "Se este contrato fosse de um banco brasileiro, ele deveria discriminar a taxa de juros."
    assert conferir_parecer(resposta(pontos_de_atencao=[texto]), ENTRADA, []) == []


# ---------- atributos sensíveis no texto ----------

@pytest.mark.parametrize("texto", ["A idade do cliente reduz o risco.",
                                   "O gênero do cliente foi considerado.",
                                   "O país do cliente aumenta o risco."])
def test_atributo_sensivel_no_texto_e_pego(texto):
    problemas = conferir_parecer(resposta(pontos_de_atencao=[texto]), ENTRADA, [])
    assert any("atributo sensível" in p for p in problemas)


@pytest.mark.parametrize("texto", ["A faixa etária do cliente reduz o risco.",
                                   "O cliente é idoso.",
                                   "O cliente é estrangeiro."])
def test_sinonimos_de_idade_e_pais_sao_pegos(texto):
    problemas = conferir_parecer(resposta(pontos_de_atencao=[texto]), ENTRADA, [])
    assert any("atributo sensível" in p for p in problemas)


def test_palavras_parecidas_nao_sao_pegas():
    texto = ("A probabilidade e a capacidade de pagamento foram consideradas na cidade; "
             "a regularização é recomendada.")
    assert conferir_parecer(resposta(pontos_de_atencao=[texto]), ENTRADA, []) == []


# ---------- tamanho ----------

def test_conta_frases_sem_quebrar_em_abreviacao():
    assert contar_frases("Conforme o art. 6º do CDC, há um ponto. Recomenda-se revisar.") == 2


@pytest.mark.parametrize("texto", [
    "Conforme o art. 6º, inc. III, do CDC, o consumidor tem direito à informação.",
    "Se este contrato fosse de um banco brasileiro, a Res. CMN 4.881 exigiria o CET.",
])
def test_abreviacoes_juridicas_nao_terminam_frase(texto):
    assert contar_frases(texto) == 1


def test_resumo_com_3_frases_e_pego():
    resumo = "Risco faixa C. O juro cobrado está acima do justo. Recomenda-se revisar."
    problemas = conferir_parecer(resposta(resumo=resumo), ENTRADA, [])
    assert problemas == ["resumo com 3 frases (máximo 2)"]