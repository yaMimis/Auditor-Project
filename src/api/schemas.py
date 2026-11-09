"""Schemas da API (entrada do formulário e saída para o painel).

A saída segue o contrato do prever() (genai/FORMATO_JSON.md, seção 3) e reaproveita
os modelos da GenAI (genai/src/checagem.py), que são a fonte da verdade do formato.
Não duplicar esses modelos aqui: se o formato mudar, muda só lá.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from genai.src.checagem import EntradaPrever, Motivo, Parecer

# Sem data, vale a de hoje (combinado com o Samuel em 05/11). A API sempre envia a data
# ao prever(), para funcionar antes e depois do PR samuel-margem.


# ---------- Entrada (o que o Streamlit envia) ----------

class SolicitacaoEmprestimo(BaseModel):
    loan_id: str
    amount: float = Field(gt=0, description="Valor concedido, em euro")
    income_total: float = Field(ge=0, description="Renda total mensal, em euro")
    loan_duration: int = Field(gt=0, le=120, description="Prazo em meses")
    country: str = Field(description="Sigla do país: EE, ES ou FI")
    interest_cobrado: float = Field(ge=0, le=500, description="Juro cobrado em % ao ano (ex.: 24.9)")
    liabilities_total: float | None = Field(default=None, ge=0, description="Total de dívidas, em euro")
    data_emprestimo: date = Field(default_factory=date.today, description="Data de concessão")

    # Só auditoria de equidade: NUNCA vão para o modelo nem para o LLM.
    gender: int | None = Field(default=None, description="0 homem, 1 mulher, 2 indefinido")
    age: int | None = None

    @field_validator("data_emprestimo")
    @classmethod
    def _data_nao_futura(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("a data de concessão não pode ser no futuro")
        return v

    @field_validator("country")
    @classmethod
    def _sigla_do_pais(cls, v: str) -> str:
        # Aceita "EE" ou "EE(Estônia)" e guarda só a sigla em maiúsculas.
        return v.strip()[:2].upper()


# ---------- Saída (o que o painel recebe) ----------

class MotivoPrever(Motivo):
    """Motivo como sai do prever(): o da GenAI + valor e peso (só para a tela)."""
    valor: Any = None
    peso: float | None = None


class RespostaPrever(EntradaPrever):
    """Saída do prever() + parecer.

    Herda do EntradaPrever: mesmas chaves, mesmos tipos, campos nulos em revisao_manual
    e a mesma regra de que fora da revisão manual os números são obrigatórios.
    """
    motivos: list[MotivoPrever] = []
    pd_ic95: list[float] | None = None
    diferenca_pp: float | None = None
    juro_pares_mediana: float | None = None  # o Samuel vai acrescentar no prever()
    parecer_ia: Parecer | None = None


# ---------- Decisão do analista (db/05_decisoes_analista.sql) ----------

DecisaoAnalista = Literal["manter_preco", "revisar_preco", "encaminhar_compliance"]


class NovaDecisao(BaseModel):
    """O que o painel envia ao registrar uma decisão.

    `resultado` é a RESPOSTA do /prever (com o parecer), nunca a solicitação:
    assim gênero e idade não chegam ao registro. Em revisão manual, PD, faixa e
    juros justos seguem nulos (a tabela aceita desde 08/11).
    """
    requisicao_id: UUID | None = Field(default=None, description="Gerado pelo painel a cada clique; evita gravar duas vezes")
    analista: str = Field(min_length=1, max_length=120)
    decisao: DecisaoAnalista
    justificativa: str = Field(min_length=1, max_length=4000)
    taxa_proposta: float | None = Field(default=None, gt=0, le=10, description="Nova taxa, em fração ao ano (nominal)")
    resultado: RespostaPrever

    @field_validator("analista", "justificativa")
    @classmethod
    def _sem_espacos_vazios(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("não pode ficar em branco")
        return v.strip()


class DecisaoRegistrada(BaseModel):
    """Uma linha da tabela decisao_analista, como o painel exibe."""
    decisao_id: int
    registrada_em: datetime
    contrato_id: str
    origem: Literal["carteira", "simulacao"]
    analista: str
    decisao: DecisaoAnalista
    justificativa: str
    taxa_proposta: float | None = None
    recomendacao_sistema: str | None = None
    situacao_preco: str
    pd: float | None = None          # nulos só em revisão manual
    faixa: str | None = None
    juro_cobrado: float
    juro_justo: float | None = None
    juro_justo_min: float | None = None
    juro_justo_max: float | None = None
    versao_modelo: str
    versao_parecer: str | None = None
    origem_parecer: str | None = None


class DecisaoAtual(BaseModel):
    """Decisão mais recente de um contrato da carteira (vw_decisao_atual)."""
    contrato_id: str
    decisao_id: int
    registrada_em: datetime
    analista: str
    decisao: DecisaoAnalista
