"""
Contratos de dados da frente de GenAI (fonte da verdade do FORMATO_JSON.md, seção 6).

EntradaPrever valida o que chega do prever(); RespostaLLM é o que o LLM devolve;
Parecer é o que gerar_parecer() entrega para a tela.

Teste rápido (na pasta raiz):
    python genai/src/checagem.py
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ChaveNumero = Literal["pd", "juro_cobrado", "juro_justo", "juro_justo_min", "juro_justo_max"]


# ---------- Entrada (do prever) ----------

class Motivo(BaseModel):
    model_config = ConfigDict(extra="ignore")  # descarta valor e peso
    variavel: str
    rotulo: str
    efeito: Literal["aumenta_risco", "reduz_risco"]


class EntradaPrever(BaseModel):
    model_config = ConfigDict(extra="ignore")  # descarta pd_ic95, diferenca_pp etc.
    contrato_id: str
    versao_modelo: str
    pd: float | None = Field(default=None, ge=0, le=1)
    faixa: Literal["A", "B", "C", "D", "E"] | None = None
    juro_cobrado: float
    juro_justo: float | None = None
    juro_justo_min: float | None = None
    juro_justo_max: float | None = None
    situacao_preco: Literal["acima_do_justo", "abaixo_do_justo", "dentro_da_margem", "revisao_manual"]
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

    @property
    def vai_para_revisao_manual(self) -> bool:
        return self.situacao_preco == "revisao_manual" or self.alerta_dados


# ---------- Saída (para a tela) ----------

class Fonte(BaseModel):
    norma: str
    artigo: str
    trecho_id: str


class RespostaLLM(BaseModel):
    """O que o LLM devolve (saída estruturada)."""
    resumo: str
    pontos_de_atencao: list[str] = Field(max_length=3)
    recomendacao_texto: str
    fontes: list[Fonte]
    numeros_citados: dict[ChaveNumero, float]


class Parecer(RespostaLLM):
    """O que gerar_parecer() devolve para a tela."""
    contrato_id: str
    recomendacao: Literal["manter_preco", "revisar_preco", "encaminhar_compliance", "revisao_manual"]
    origem: Literal["llm", "template"]
    versao_prompt: str
    gerado_em: datetime


if __name__ == "__main__":
    import json
    from pathlib import Path

    from pydantic import ValidationError

    exemplos = json.loads(Path("docs/exemplos_prever.json").read_text(encoding="utf-8"))
    validos = 0
    for exemplo in exemplos:
        try:
            entrada = EntradaPrever.model_validate(exemplo)
        except ValidationError as erro:
            print(f"ERRO {exemplo.get('contrato_id', '?')}: {erro.error_count()} problema(s)")
            for problema in erro.errors()[:3]:
                campo = ".".join(str(parte) for parte in problema["loc"])
                print(f"     - {campo}: {problema['msg']}")
            continue
        validos += 1
        print(f"OK   {entrada.contrato_id:<10} {entrada.situacao_preco:<17} "
              f"revisão manual: {entrada.vai_para_revisao_manual}")
    print(f"\n{validos} de {len(exemplos)} exemplos do prever() validados contra o contrato.")