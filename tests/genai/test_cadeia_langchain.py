"""Testes da cadeia em LangChain (LCEL): a chain tem os 4 passos, a chamada ao Gemini usa
o ChatGoogleGenerativeAI com saída estruturada, e sem LangChain os mesmos passos rodam.
Os testes que precisam do LangChain são pulados onde ele não está instalado (ex.: CI mínimo).

Rodar na pasta raiz:  python -m pytest tests/genai -q
"""
import pytest

from genai.src import cadeia
from genai.src.checagem import EntradaPrever, RespostaLLM

ENTRADA = {
    "contrato_id": "BO-1", "versao_modelo": "teste",
    "pd": 0.184, "faixa": "C", "juro_cobrado": 0.249,
    "juro_justo": 0.162, "juro_justo_min": 0.141, "juro_justo_max": 0.183,
    "situacao_preco": "acima_do_justo", "motivos": [],
}
TRECHOS = [{"trecho_id": "cdc-art52-1", "norma": "CDC", "artigo": "Art. 52",
            "texto": "Art. 52. No fornecimento de produtos ou serviços que envolva outorga de crédito {...}"}]
BOA = {
    "resumo": "O juro cobrado está acima do juro justo.",
    "pontos_de_atencao": [],
    "recomendacao_texto": "Recomenda-se revisar o preço.",
    "fontes": [{"norma": "CDC", "artigo": "Art. 52, II", "trecho_id": "cdc-art52-1"}],
    "numeros_citados": {},
}


@pytest.fixture
def falsos(monkeypatch):
    recebido = {}

    def llm_falso(sistema, usuario):
        recebido["usuario"] = usuario
        return RespostaLLM.model_validate(BOA)

    monkeypatch.setattr(cadeia, "chamar_llm", llm_falso)
    monkeypatch.setattr(cadeia, "buscar_trechos", lambda entrada: TRECHOS)
    return recebido


def _estado():
    return {"entrada": EntradaPrever.model_validate(ENTRADA), "recomendacao": "revisar_preco"}


def test_cadeia_e_lcel_com_os_4_passos():
    pytest.importorskip("langchain_core")
    from langchain_core.runnables import RunnableSequence
    rag = cadeia._montar_cadeia_rag()
    assert isinstance(rag, RunnableSequence)
    assert [passo.name for passo in rag.steps] == ["busca_normas", "monta_prompt", "gemini", "conferencia"]


def test_cadeia_lcel_roda_de_ponta_a_ponta(falsos):
    pytest.importorskip("langchain_core")
    estado = cadeia._montar_cadeia_rag().invoke(_estado())
    assert estado["problemas"] == []
    assert estado["resposta"].recomendacao_texto.endswith("A decisão final é do analista.")
    assert "{...}" in falsos["usuario"]  # chaves nos trechos não quebram o prompt


def test_sem_langchain_os_mesmos_passos_dao_o_mesmo_resultado(falsos):
    estado = cadeia._CadeiaSemLangChain().invoke(_estado())
    assert estado["problemas"] == []
    assert [t["trecho_id"] for t in estado["trechos"]] == ["cdc-art52-1"]


def test_chamar_llm_usa_chatgooglegenerativeai_com_saida_estruturada(monkeypatch):
    pytest.importorskip("langchain_google_genai")
    import langchain_google_genai
    criado = {}

    class ModeloFalso:
        def __init__(self, **opcoes):
            criado["opcoes"] = opcoes

        def with_structured_output(self, esquema):
            criado["esquema"] = esquema
            return self

        def invoke(self, mensagens):
            criado["mensagens"] = mensagens
            return cadeia._RespostaGemini.model_validate({**BOA, "numeros_citados": {"pd": 0.184}})

    monkeypatch.setattr(langchain_google_genai, "ChatGoogleGenerativeAI", ModeloFalso)
    resposta = cadeia.chamar_llm("regras do sistema", "dados do contrato")
    assert criado["opcoes"]["temperature"] == 0
    assert criado["opcoes"]["timeout"] >= 10          # mínimo aceito pelo Gemini
    assert criado["opcoes"]["max_retries"] == 1
    assert criado["esquema"] is cadeia._RespostaGemini
    assert [m.content for m in criado["mensagens"]] == ["regras do sistema", "dados do contrato"]
    assert resposta.numeros_citados == {"pd": 0.184}
