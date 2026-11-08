"""Testes dos ajustes de 08/11 (genai v2): unidade nominal, países, referência de mercado do BC
e prompt v2. Origem: decisões do Samuel e do Marcos (DATA.md v0.7) e o primeiro teste real do LLM.

Rodar na pasta raiz:  python -m pytest tests/genai -q
"""
import pytest

from genai.src import cadeia
from genai.src.checagem import (EntradaPrever, RespostaLLM, conferir_parecer, efetiva_para_nominal,
                                montar_contexto_mercado, motivos_permitidos)
from genai.src.prompt import montar_mensagens
from genai.src.template import montar_template

BASE = {
    "contrato_id": "BO-9", "versao_modelo": "teste",
    "pd": 0.554, "faixa": "C", "juro_cobrado": 0.237,
    "juro_justo": 0.202, "juro_justo_min": 0.181, "juro_justo_max": 0.221,
    "situacao_preco": "acima_do_justo",
    "motivos": [
        {"variavel": "prazo_meses", "rotulo": "prazo do empréstimo", "efeito": "aumenta_risco"},
        {"variavel": "score_ee_mini", "rotulo": "score de crédito (Estônia)", "efeito": "reduz_risco"},
        {"variavel": "tipo_verificacao", "rotulo": "verificação da renda", "efeito": "aumenta_risco"},
        {"variavel": "tipo_moradia", "rotulo": "tipo de moradia", "efeito": "reduz_risco"},
        {"variavel": "valor_concedido", "rotulo": "valor do empréstimo", "efeito": "aumenta_risco"},
    ],
}


def entrada(**mudancas):
    return EntradaPrever.model_validate({**BASE, **mudancas})


# ---------- países ----------

def test_pais_entre_parenteses_sai_do_rotulo():
    rotulos = [m.rotulo for m in motivos_permitidos(entrada())]
    assert "score de crédito" in rotulos
    assert not any("Estônia" in r for r in rotulos)


def test_motivo_que_e_so_o_pais_continua_fora():
    motivos = [{"variavel": "pais", "rotulo": "país", "efeito": "aumenta_risco"},
               {"variavel": "x", "rotulo": "cliente da Finlândia", "efeito": "aumenta_risco"}]
    assert motivos_permitidos(entrada(motivos=motivos)) == []


@pytest.mark.parametrize("pais", ["Estônia", "Estonia", "Finlândia", "Espanha", "Eslováquia",
                                  "espanhol", "estoniano", "finlandesa"])
def test_nome_de_pais_no_texto_e_pego(pais):
    resposta = RespostaLLM.model_validate({
        "resumo": "Risco faixa C.", "pontos_de_atencao": [f"O fator {pais} pesa no risco."],
        "recomendacao_texto": "Recomenda-se revisar o preço. A decisão final é do analista.",
        "fontes": [], "numeros_citados": {}})
    assert any("atributo sensível" in p for p in conferir_parecer(resposta, entrada(), []))


def test_template_nao_cita_o_pais():
    parecer = montar_template(entrada())
    texto = " ".join([parecer.resumo, *parecer.pontos_de_atencao])
    assert "Estônia" not in texto
    assert "score de crédito (reduz o risco)" in texto


# ---------- referência de mercado (média do BC) ----------

def test_conversao_efetiva_para_nominal_do_data_md():
    # DATA.md, seção 8: 126,2% efetiva = 84,5% nominal = 7,04% ao mês
    assert efetiva_para_nominal(126.2) == pytest.approx(0.845, abs=0.0005)
    assert efetiva_para_nominal(126.2) / 12 == pytest.approx(0.0704, abs=0.00005)


def test_frase_do_bc_com_nominal_e_efetiva():
    frase = montar_contexto_mercado(entrada(bc_credito_pessoal_aa=126.2))
    assert "84,5% ao ano (nominal)" in frase
    assert "126,2% efetiva, como o BC divulga" in frase
    assert "não uma medida do preço justo" in frase


def test_sem_dado_do_bc_nao_ha_frase():
    assert montar_contexto_mercado(entrada()) is None


def test_bc_negativo_e_recusado():
    with pytest.raises(ValueError):
        entrada(bc_credito_pessoal_aa=-1)


def test_template_preenche_o_contexto_mercado():
    assert "84,5%" in montar_template(entrada(bc_credito_pessoal_aa=126.2)).contexto_mercado
    assert montar_template(entrada()).contexto_mercado is None


def test_revisao_manual_tambem_mostra_o_contexto():
    revisao = EntradaPrever.model_validate({
        "contrato_id": "BO-8", "versao_modelo": "t", "juro_cobrado": 0.22,
        "situacao_preco": "revisao_manual", "bc_credito_pessoal_aa": 126.2})
    assert montar_template(revisao).contexto_mercado is not None


def test_llm_nunca_recebe_a_media_do_bc():
    sistema, usuario = montar_mensagens(entrada(bc_credito_pessoal_aa=126.2), "revisar_preco", [])
    for proibido in ("126,2", "126.2", "84,5", "0.845"):
        assert proibido not in sistema + usuario


def test_cadeia_preenche_o_contexto_mercado(monkeypatch):
    resposta = RespostaLLM.model_validate({
        "resumo": "Risco faixa C (chance de não pagar de 55,4%). O juro cobrado está acima do justo.",
        "pontos_de_atencao": [], "fontes": [], "numeros_citados": {"pd": 0.554},
        "recomendacao_texto": "Recomenda-se revisar o preço. A decisão final é do analista."})
    monkeypatch.setattr(cadeia, "chamar_llm", lambda s, u: resposta)
    monkeypatch.setattr(cadeia, "buscar_trechos", lambda e: [])
    parecer = cadeia.gerar_parecer({**BASE, "bc_credito_pessoal_aa": 126.2})
    assert parecer["origem"] == "llm" and "84,5%" in parecer["contexto_mercado"]


# ---------- prompt v2 ----------

def test_prompt_v2_envia_no_maximo_3_fatores_sem_pais():
    _, usuario = montar_mensagens(entrada(), "revisar_preco", [])
    fatores = usuario.split("FATORES DE RISCO:")[1].split("TRECHOS DE NORMAS:")[0]
    linhas = [linha for linha in fatores.splitlines() if linha.startswith("- ")]
    assert len(linhas) == 3
    assert "Estônia" not in usuario and "score de crédito (reduz o risco)" in usuario


def test_prompt_v2_tem_as_regras_novas():
    sistema, _ = montar_mensagens(entrada(), "revisar_preco", [])
    assert "verbo no condicional" in sistema
    assert 'Não comece frases com "Ponto de atenção:"' in sistema
    assert "Não acrescente nem troque palavras no nome de um fator" in sistema
    assert "os pontos de atenção podem ficar vazios" in sistema
