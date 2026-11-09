"""Ajustes finais no código depois da avaliação da v4 (09/11). O prompt continua na v4.
1. Recomendação repetida: sai dos pontos e do resumo (a regra do prompt falhou duas vezes).
2. Casas decimais: 2 casas quando dois juros diferentes ficariam iguais com 1 (C07: 30,56% e 30,58%).
3. LGPD art. 20 decorativa: sai das fontes quando o texto não fala de revisão de decisão automatizada.

Rodar na pasta raiz:  python -m pytest tests/genai -q
"""
import pytest

from genai.src import cadeia
from genai.src.checagem import (EntradaPrever, Fonte, RespostaLLM, ajustar_resposta, casas_decimais,
                                conferir_parecer)
from genai.src.prompt import montar_mensagens
from genai.src.template import montar_template

# Números do C07 da avaliação.
C07 = {"contrato_id": "C07", "versao_modelo": "teste", "pd": 0.8153, "faixa": "E",
       "juro_cobrado": 0.3056, "juro_justo": 0.3368, "juro_justo_min": 0.3058, "juro_justo_max": 0.3583,
       "situacao_preco": "abaixo_do_justo", "motivos": []}
ACIMA = {"contrato_id": "BO-1", "versao_modelo": "teste", "pd": 0.184, "faixa": "C",
         "juro_cobrado": 0.249, "juro_justo": 0.162, "juro_justo_min": 0.141, "juro_justo_max": 0.183,
         "situacao_preco": "acima_do_justo", "motivos": []}
LGPD = Fonte(norma="LGPD", artigo="Art. 20", trecho_id="lgpd-art20-1")
CDC = Fonte(norma="CDC", artigo="Art. 52, II", trecho_id="cdc-art52-1")


def _resposta(resumo="O juro cobrado passa da margem do juro justo.", pontos=(), fontes=(),
              recomendacao="Recomenda-se revisar o preço. A decisão final é do analista."):
    return RespostaLLM(resumo=resumo, pontos_de_atencao=list(pontos), recomendacao_texto=recomendacao,
                       fontes=list(fontes), numeros_citados={})


# ---------- 1. recomendação repetida ----------

def test_ponto_que_repete_a_recomendacao_sai():
    r = _resposta(pontos=["O juro passa da margem.", "Recomenda-se revisar o preço; se a política..."])
    assert ajustar_resposta(r) == ["1 ponto(s) repetindo a recomendação"]
    assert r.pontos_de_atencao == ["O juro passa da margem."]


def test_frase_do_resumo_que_repete_a_recomendacao_sai():
    r = _resposta(resumo="O juro está dentro da margem esperada. Recomenda-se manter o preço.")
    ajustar_resposta(r)
    assert r.resumo == "O juro está dentro da margem esperada."


def test_resumo_so_com_recomendacao_fica_como_esta():
    r = _resposta(resumo="Recomenda-se revisar o preço.")
    assert ajustar_resposta(r) == []
    assert r.resumo == "Recomenda-se revisar o preço."


def test_abreviacao_nao_quebra_o_resumo():
    r = _resposta(resumo="Pelo art. 52 do CDC, a taxa deveria ser informada. Recomenda-se revisar.")
    ajustar_resposta(r)
    assert r.resumo == "Pelo art. 52 do CDC, a taxa deveria ser informada."


def test_recomendacao_texto_nao_e_mexida():
    r = _resposta()
    ajustar_resposta(r)
    assert r.recomendacao_texto.startswith("Recomenda-se revisar o preço.")


# ---------- 3. LGPD art. 20 ----------

def test_lgpd_20_decorativa_sai_das_fontes():
    r = _resposta(pontos=["O juro passa da margem."], fontes=[LGPD, CDC])
    assert ajustar_resposta(r) == ["LGPD art. 20 nas fontes sem o texto falar dela"]
    assert [f.trecho_id for f in r.fontes] == ["cdc-art52-1"]


def test_lgpd_20_usada_como_no_c02_fica():
    r = _resposta(recomendacao="Recomenda-se revisar o preço. Se este contrato fosse de um banco brasileiro, "
                               "o cliente teria direito a solicitar a revisão de decisões tomadas unicamente "
                               "com base em tratamento automatizado de dados pessoais, conforme a LGPD. "
                               "A decisão final é do analista.",
                  fontes=[LGPD])
    assert ajustar_resposta(r) == []
    assert r.fontes == [LGPD]


def test_ajuste_vem_depois_da_conferencia(monkeypatch):
    """Uma fonte não recuperada continua indo para o template: o ajuste não a esconde."""
    def llm_falso(sistema, usuario):
        return _resposta(fontes=[LGPD])
    monkeypatch.setattr(cadeia, "chamar_llm", llm_falso)
    monkeypatch.setattr(cadeia, "buscar_trechos", lambda entrada: [])
    assert cadeia.gerar_parecer(ACIMA)["origem"] == "template"


def test_parecer_aprovado_sai_ajustado(monkeypatch):
    trechos = [{"trecho_id": "lgpd-art20-1", "norma": "LGPD", "artigo": "Art. 20", "texto": "..."}]
    monkeypatch.setattr(cadeia, "chamar_llm", lambda s, u: _resposta(
        pontos=["Recomenda-se revisar o preço."], fontes=[LGPD]))
    monkeypatch.setattr(cadeia, "buscar_trechos", lambda entrada: trechos)
    parecer = cadeia.gerar_parecer(ACIMA)
    assert parecer["origem"] == "llm"
    assert parecer["pontos_de_atencao"] == [] and parecer["fontes"] == []


# ---------- 2. casas decimais ----------

def test_duas_casas_quando_os_juros_empatam_com_uma():
    assert casas_decimais(EntradaPrever.model_validate(C07)) == 2
    assert casas_decimais(EntradaPrever.model_validate(ACIMA)) == 1


def test_prompt_mostra_os_juros_do_c07_com_duas_casas():
    _, usuario = montar_mensagens(EntradaPrever.model_validate(C07), "revisar_preco", [])
    assert "juro cobrado: 30,56% ao ano (nominal)" in usuario
    assert "limite inferior da margem do juro justo: 30,58% ao ano (nominal)" in usuario
    assert "chance de não pagar: 81,5%" in usuario  # a chance de não pagar continua com 1 casa


def test_template_do_c07_nao_se_contradiz():
    parecer = montar_template(EntradaPrever.model_validate(C07))
    texto = " ".join(parecer.pontos_de_atencao)
    assert "30,56%" in texto and "30,58%" in texto


@pytest.mark.parametrize("numero", ["30,56%", "30,6%"])
def test_conferencia_aceita_o_juro_com_uma_ou_duas_casas(numero):
    r = _resposta(pontos=[f"O juro cobrado é de {numero} ao ano (nominal)."])
    r.numeros_citados = {"juro_cobrado": 0.3056}
    assert conferir_parecer(r, EntradaPrever.model_validate(C07), []) == []
