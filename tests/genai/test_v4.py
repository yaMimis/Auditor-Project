"""Testes da v4 (09/11): checagem de artigos e prompt sem artigo nomeado.
Origem: avaliação dos 20 casos com a v3 (C01 escreveu "CDC, art. 6º, III" com o trecho cdc-art54b-1).

Rodar na pasta raiz:  python -m pytest tests/genai -q
"""
from genai.avaliacao.avaliar import _llm_por_tipo, _recusa_por_artigo
from genai.src.checagem import (EntradaPrever, Fonte, RespostaLLM, artigo_do_trecho, artigos_no_texto,
                                conferir_parecer)
from genai.src.prompt import VERSAO_PROMPT, carregar_prompt, montar_mensagens

ENTRADA = EntradaPrever.model_validate({
    "contrato_id": "BO-1", "versao_modelo": "teste",
    "pd": 0.184, "faixa": "C", "juro_cobrado": 0.249,
    "juro_justo": 0.162, "juro_justo_min": 0.141, "juro_justo_max": 0.183,
    "situacao_preco": "acima_do_justo", "motivos": [],
})
RECUPERADOS_ACIMA = ["cdc-art54b-1", "cdc-art52-1", "cdc-art54b-2", "cdc-art54d-1", "lgpd-art20-1"]


def _resposta(ponto, fontes):
    return RespostaLLM(resumo="O juro cobrado passa da margem do juro justo.", pontos_de_atencao=[ponto],
                       recomendacao_texto="Recomenda-se revisar o preço. A decisão final é do analista.",
                       fontes=fontes, numeros_citados={})


# ---------- artigos: extração ----------

def test_artigos_no_texto_pega_numero_e_letra_sem_inciso():
    assert artigos_no_texto("conforme o CDC, art. 6º, III") == {("6", "")}
    assert artigos_no_texto("Art. 54-B e artigo 20") == {("54", "b"), ("20", "")}
    assert artigos_no_texto("art. 54B") == {("54", "b")}


def test_artigos_no_texto_ignora_lei_e_resolucao():
    assert artigos_no_texto("Lei nº 8.078 e Resolução CMN nº 4.881") == set()
    assert artigos_no_texto("o art. 20 o titular") == {("20", "")}  # o "o" não vira letra


def test_artigo_do_trecho():
    assert artigo_do_trecho("cdc-art54b-1") == ("54", "b")
    assert artigo_do_trecho("credito_oferta-art9-1") == ("9", "")
    assert artigo_do_trecho("ref-p14-1") is None


# ---------- artigos: conferência ----------

def test_caso_c01_artigo_inventado_e_recusado():
    resposta = _resposta("Se este contrato fosse de um banco brasileiro, conforme o CDC, art. 6º, III, "
                         "a informação deveria ser clara.",
                         [Fonte(norma="CDC", artigo="art. 6º, III", trecho_id="cdc-art54b-1")])
    problemas = conferir_parecer(resposta, ENTRADA, RECUPERADOS_ACIMA)
    assert any("que não é o do trecho" in p for p in problemas)
    assert any("art. 6 no texto" in p for p in problemas)


def test_artigo_certo_com_inciso_passa():
    resposta = _resposta("Se este contrato fosse de um banco brasileiro, pelo CDC, art. 52, II, a taxa "
                         "deveria ser informada.",
                         [Fonte(norma="CDC", artigo="Art. 52, II", trecho_id="cdc-art52-1")])
    assert conferir_parecer(resposta, ENTRADA, RECUPERADOS_ACIMA) == []


def test_artigo_com_letra_passa():
    resposta = _resposta("Pelo CDC, art. 54-B, a informação deveria ser prévia.",
                         [Fonte(norma="CDC", artigo="Art. 54-B", trecho_id="cdc-art54b-1")])
    assert conferir_parecer(resposta, ENTRADA, RECUPERADOS_ACIMA) == []


def test_fonte_do_ref_sem_artigo_passa():
    resposta = _resposta("A inadimplência faz parte do custo do crédito.",
                         [Fonte(norma="REF", artigo="parágrafo 14", trecho_id="ref-p14-1")])
    assert conferir_parecer(resposta, ENTRADA, ["ref-p14-1", "ref-p15-1"]) == []


def test_artigo_no_texto_sem_trecho_recuperado_e_recusado_mesmo_sem_fonte():
    resposta = _resposta("Pelo CDC, art. 39, a prática deveria ser revista.", [])
    problemas = conferir_parecer(resposta, ENTRADA, RECUPERADOS_ACIMA)
    assert problemas == ["art. 39 no texto não está entre os trechos recuperados"]


# ---------- prompt v4 ----------

def test_versao_atual_e_a_v4():
    assert VERSAO_PROMPT == "parecer_v4"


def test_prompt_v4_nao_nomeia_artigo_nas_regras():
    sistema, _ = montar_mensagens(ENTRADA, "revisar_preco", [])
    assert artigos_no_texto(sistema) == set()
    assert "O número do artigo vem do trecho, nunca da memória" in sistema
    assert "Não a repita no resumo nem nos pontos de atenção" in sistema
    assert "só pode ir para \"fontes\" se o texto disser o que ele diz" in sistema


def test_notas_da_v4_nao_vao_para_o_llm():
    sistema, usuario = carregar_prompt()
    assert "Por que existe a v4" not in sistema + usuario


# ---------- métricas ----------

def test_conta_recusa_por_artigo():
    assert _recusa_por_artigo({"avisos": ["conferência recusou o parecer do LLM: art. 6 no texto não está "
                                          "entre os trechos recuperados"]})
    assert not _recusa_por_artigo({"avisos": ["conferência recusou o parecer do LLM: fonte cdc-art9-1 não "
                                              "está entre os trechos recuperados"]})


def test_metrica_por_tipo_so_conta_pareceres_do_llm():
    resultados = [{"tipo": "acima_do_justo", "rodadas": [{"origem": "llm"}, {"origem": "template"}]},
                  {"tipo": "abaixo_do_justo", "rodadas": [{"origem": "llm"}, {"origem": "llm"}]}]
    grupos = _llm_por_tipo(resultados)
    assert len(grupos["acima_do_justo"]) == 1 and len(grupos["abaixo_do_justo"]) == 2
