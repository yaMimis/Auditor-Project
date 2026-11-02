"""Contrato entre o prever() (Samuel) e o parecer (Maria).

Confere a saída do prever() com o formato da GenAI (genai/FORMATO_JSON.md v1.2):
1. o pydantic EntradaPrever da Maria (fonte da verdade do formato);
2. regras extras do nosso lado: juros em fração, margem coerente,
   situação coerente com os números, país fora dos motivos etc.

Hoje valida o docs/exemplos_prever.json. Quando o prever() existir,
o último teste passa a validá-lo também (até lá, ele é pulado).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import pytest
from pydantic import BaseModel, ConfigDict, Field, model_validator

RAIZ = Path(__file__).resolve().parents[2]
EXEMPLOS = RAIZ / "docs" / "exemplos_prever.json"


# --------------------------------------------------------------------------
# Modelo da Maria: usa o oficial (genai/src/checagem.py) se existir;
# senão, esta cópia da seção 6 do FORMATO_JSON.md v1.2.
# --------------------------------------------------------------------------
try:
    from genai.src.checagem import EntradaPrever  # type: ignore
except ImportError:
    class Motivo(BaseModel):
        model_config = ConfigDict(extra="ignore")
        variavel: str
        rotulo: str
        efeito: Literal["aumenta_risco", "reduz_risco"]

    class EntradaPrever(BaseModel):
        model_config = ConfigDict(extra="ignore")
        contrato_id: str
        versao_modelo: str
        pd: float | None = Field(default=None, ge=0, le=1)
        faixa: Literal["A", "B", "C", "D", "E"] | None = None
        juro_cobrado: float
        juro_justo: float | None = None
        juro_justo_min: float | None = None
        juro_justo_max: float | None = None
        situacao_preco: Literal["acima_do_justo", "abaixo_do_justo",
                                "dentro_da_margem", "revisao_manual"]
        motivos: list[Motivo] = []
        alerta_dados: bool = False

        @model_validator(mode="after")
        def exige_numeros_fora_da_revisao_manual(self):
            if self.situacao_preco != "revisao_manual":
                obrigatorios = ("pd", "faixa", "juro_justo", "juro_justo_min", "juro_justo_max")
                faltando = [c for c in obrigatorios if getattr(self, c) is None]
                if faltando:
                    raise ValueError(f"campos nulos fora de revisao_manual: {faltando}")
            return self


# --------------------------------------------------------------------------
# Validação completa de UMA saída do prever()
# --------------------------------------------------------------------------
def validar_saida_prever(saida: dict) -> None:
    """Levanta AssertionError (ou erro do pydantic) se a saída quebrar o contrato."""
    e = EntradaPrever(**saida)   # 1. formato da Maria

    # 2. revisão manual e alerta sempre juntos
    assert (e.situacao_preco == "revisao_manual") == e.alerta_dados, \
        "alerta_dados e revisao_manual precisam vir juntos"

    # 3. juros em fração (0.249), nunca em percentual (24.9)
    for campo in ("juro_cobrado", "juro_justo", "juro_justo_min", "juro_justo_max"):
        v = getattr(e, campo)
        if v is not None:
            assert 0 <= v <= 5.0, f"{campo}={v}: juros devem vir em fração (até 500% ao ano)"

    if e.situacao_preco == "revisao_manual":
        assert e.motivos == [], "revisão manual não tem motivos"
        return

    # 4. margem coerente e situação coerente com os números
    assert e.juro_justo_min <= e.juro_justo <= e.juro_justo_max, "juro justo fora da própria margem"
    if e.juro_cobrado > e.juro_justo_max:
        esperado = "acima_do_justo"
    elif e.juro_cobrado < e.juro_justo_min:
        esperado = "abaixo_do_justo"
    else:
        esperado = "dentro_da_margem"
    assert e.situacao_preco == esperado, f"situacao {e.situacao_preco}, esperado {esperado}"

    # 5. motivos: sem país/atributos sensíveis, com rótulo, do maior para o menor peso
    proibidos = {"pais", "genero", "idade", "estado_civil", "n_dependentes"}
    for m in e.motivos:
        assert m.variavel not in proibidos, f"motivo proibido no parecer: {m.variavel}"
        assert m.rotulo.strip(), f"motivo sem rótulo: {m.variavel}"
    pesos = [m.get("peso") for m in saida["motivos"] if m.get("peso") is not None]
    assert pesos == sorted(pesos, reverse=True), "motivos devem vir do maior para o menor peso"


def _exemplos():
    return json.loads(EXEMPLOS.read_text(encoding="utf-8"))


def test_exemplos_cobrem_as_quatro_situacoes():
    situacoes = {e["situacao_preco"] for e in _exemplos()}
    assert situacoes == {"acima_do_justo", "abaixo_do_justo", "dentro_da_margem", "revisao_manual"}


@pytest.mark.parametrize("exemplo", _exemplos(), ids=lambda e: e["contrato_id"])
def test_exemplos_respeitam_o_contrato(exemplo):
    validar_saida_prever(exemplo)


def test_contrato_detecta_juro_em_percentual():
    errado = dict(_exemplos()[0], juro_cobrado=24.9)
    with pytest.raises(AssertionError):
        validar_saida_prever(errado)


def test_contrato_detecta_pais_nos_motivos():
    errado = json.loads(json.dumps(_exemplos()[0]))
    errado["motivos"].insert(0, {"variavel": "pais", "rotulo": "país",
                                 "efeito": "aumenta_risco", "peso": 0.9})
    with pytest.raises(AssertionError):
        validar_saida_prever(errado)
