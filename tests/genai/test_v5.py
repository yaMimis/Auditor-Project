"""Testes da v5 (16/11): no caso "acima do justo", ponto de atenção sobre a informação do preço.
Origem: a busca trazia os trechos do CDC sobre a informação do preço em todos os casos "acima", e o modelo
quase não os citava (avaliação v4 e contar_fontes.py de 16/11).

Rodar na pasta raiz:  python -m pytest tests/genai -q
"""
from genai.src.checagem import EntradaPrever, artigos_no_texto
from genai.src.prompt import VERSAO_PROMPT, carregar_prompt, montar_mensagens

ENTRADA = EntradaPrever.model_validate({
    "contrato_id": "BO-1", "versao_modelo": "teste",
    "pd": 0.184, "faixa": "C", "juro_cobrado": 0.249,
    "juro_justo": 0.162, "juro_justo_min": 0.141, "juro_justo_max": 0.183,
    "situacao_preco": "acima_do_justo", "motivos": [],
})


def test_versao_atual_e_a_v5():
    assert VERSAO_PROMPT == "parecer_v5"


def test_v5_pede_ponto_sobre_a_informacao_do_preco_no_acima():
    sistema, _ = montar_mensagens(ENTRADA, "revisar_preco", [])
    assert "No caso \"acima do justo\", se os TRECHOS DE NORMAS trouxerem um trecho do Código de Defesa" in sistema
    assert "vale verificar se isso aconteceu" in sistema
    assert "Esse ponto conta dentro do limite de 3 pontos de atenção" in sistema


def test_v5_continua_sem_artigo_nomeado_nas_regras():
    """Lição da v3: artigo nomeado numa regra virou alucinação. A regra descreve o conteúdo do trecho."""
    sistema, _ = montar_mensagens(ENTRADA, "revisar_preco", [])
    assert artigos_no_texto(sistema) == set()


def test_v5_mantem_as_regras_da_v4():
    sistema_v4, usuario_v4 = carregar_prompt("parecer_v4")
    sistema_v5, usuario_v5 = carregar_prompt("parecer_v5")
    assert usuario_v5 == usuario_v4
    for linha in sistema_v4.splitlines():
        if linha.startswith("- Acima do justo:"):
            assert linha.rstrip() in sistema_v5   # a v5 só acrescenta uma frase no fim desta linha
        else:
            assert linha in sistema_v5


def test_notas_da_v5_nao_vao_para_o_llm():
    sistema, usuario = carregar_prompt()
    assert "Por que existe a v5" not in sistema + usuario
