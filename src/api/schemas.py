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

# Sem data, vale a de hoje (combinado com o Samuel em 05/11). A API sempre envia a data ao prever().


# ---------- Entrada (o que o Streamlit envia) ----------

class LoanRequest(BaseModel):
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
    def _date_not_in_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("a data de concessão não pode ser no futuro")
        return v

    @field_validator("country")
    @classmethod
    def _country_code(cls, v: str) -> str:
        # Aceita "EE" ou "EE(Estônia)" e guarda só a sigla em maiúsculas.
        return v.strip()[:2].upper()


# ---------- Saída (o que o painel recebe) ----------

class PredictionReason(Motivo):
    """Motivo como sai do prever(): o da GenAI + valor e peso (só para a tela)."""
    valor: Any = None
    peso: float | None = None


class PredictionResponse(EntradaPrever):
    """Saída do prever() + parecer.

    Herda do EntradaPrever: mesmas chaves, mesmos tipos, campos nulos em revisao_manual
    e a mesma regra de que fora da revisão manual os números são obrigatórios.
    """
    motivos: list[PredictionReason] = []
    pd_ic95: list[float] | None = None
    diferenca_pp: float | None = None
    juro_pares_mediana: float | None = None  # mediana do juro dos pares (null sem grupo)
    parecer_ia: Parecer | None = None


# ---------- Lote da carteira (GET /portfolio/overview, GET /contracts) ----------

class PortfolioOverview(BaseModel):
    anos: list[int]
    paises: list[str]
    faixas: list[str]
    resumo: dict[str, Any]
    por_faixa: list[dict[str, Any]]
    backtest: list[dict[str, Any]] | None = None
    equidade: list[dict[str, Any]] | None = None


class ContractList(BaseModel):
    total: int
    itens: list[dict[str, Any]] = Field(description="Linhas do lote (nomes de coluna do carteira_auditoria.csv)")


# ---------- Análise de um contrato da base (GET /contracts/{id}/analysis) ----------

class ConsideredVariable(BaseModel):
    variavel: str
    rotulo: str
    valor: float | int | str | bool | None = None
    origem: Literal["fornecida", "derivada"]
    tipo: Literal["numerica", "categorica"]


class PricingParameters(BaseModel):
    """Parâmetros da conta do juro justo (fluxo de caixa). Não é uma soma de parcelas."""
    euribor_12m: float
    lgd: float = Field(description="Perda se o cliente não pagar, por país")
    custo_margem_safra: float
    custo_anual: float = Field(description="Euribor + custos e margem da safra")
    prazo_meses: int
    pd: float
    juro_justo_sem_risco: float = Field(description="Mesma conta com PD zero (comparação, não parcela)")
    efeito_do_risco_pp: float


class ObservedOutcome(BaseModel):
    """Desfecho real (vw_desfecho_contrato, db/06): só contratos 2009–2016 já encerrados."""
    inadimplente: bool
    recebido_total: float
    resultado_eur: float = Field(description="Recebido − concedido, sem desconto no tempo")
    retorno_realizado: float | None = None
    principal_perdido: float
    duracao_meses: float | None = None


class ContractSummary(BaseModel):
    pais: str | None = None
    data_emprestimo: str | None = None   # null no modo lote (o lote guarda só o ano)
    ano: int | None = None
    valor_concedido: float | None = None
    valor_solicitado: float | None = None
    prazo_meses: int | None = None
    juro_cobrado: float


class Provenance(BaseModel):
    modo: Literal["ao_vivo", "lote"] = Field(
        default="ao_vivo", description="ao_vivo = prever() rodado agora com o contrato do banco; "
                                       "lote = números calculados antes (plano B), sem motivos nem parâmetros")
    motivo_lote: str | None = Field(default=None, description="Por que caiu para o lote (só no modo lote)")
    versao_modelo: str
    calculado_em: str | None = Field(default=None, description="Quando o prever() rodou; null no modo lote")
    tempo_ms: int
    origem_dados: str
    fora_do_dominio: bool = Field(description="Dados fora do que o modelo viu no treino (revisão manual)")
    incerteza: Literal["bootstrap", "margem_padrao", "nao_calculada"] = Field(
        description="bootstrap = intervalo estimado por reamostragem; margem_padrao = pacote sem bootstrap "
                    "(sem intervalo da PD; margem do juro justo fixa em ±2 p.p.)")
    pacote_arquivo: str
    pacote_hash: str | None = Field(default=None, description="sha256 (12 primeiros) do .joblib carregado")
    pacote_data: str | None = Field(default=None, description="Data do arquivo do modelo")
    n_reamostras_bootstrap: int | None = None


class ContractAnalysis(BaseModel):
    resultado: PredictionResponse
    contrato: ContractSummary
    dados_considerados: list[ConsideredVariable]
    precificacao: PricingParameters | None = None
    resultado_observado: ObservedOutcome | None = None
    motivo_sem_desfecho: str | None = Field(
        default=None, description="Por que não há desfecho (vw_desfecho_contrato), p. ex. 'concedido depois de 2016'")
    procedencia: Provenance



# ---------- Laboratório (POST /contracts/{id}/scenario) ----------

class ScenarioChanges(BaseModel):
    """Campos trocados no Laboratório (os outros ficam como no banco). Nenhum campo = só o original.

    Gênero, idade, estado civil e dependentes não existem aqui: um campo fora da lista é recusado (422)."""
    model_config = {"extra": "forbid"}

    valor_concedido: float | None = Field(default=None, gt=0, description="€")
    prazo_meses: int | None = Field(default=None, ge=1, le=120)
    renda_total: float | None = Field(default=None, ge=0, description="€ por mês")
    passivos_total: float | None = Field(default=None, ge=0,
                                        description="parcelas mensais das dívidas, €/mês (não é o saldo devedor)")
    passivos_existentes: int | None = Field(default=None, ge=0, description="número de dívidas em aberto")
    n_emprestimos_anteriores: int | None = Field(default=None, ge=0)
    tempo_emprego_atual: str | None = None
    tipo_verificacao: int | None = None
    juro_aa: float | None = Field(default=None, gt=0, le=500,
                                  description="juro cobrado em % a.a. nominal, como no banco (não entra no modelo)")


class ScenarioField(BaseModel):
    campo: str
    rotulo: str
    tipo: Literal["numero", "inteiro", "categoria"]
    valor_atual: Any = None
    minimo: float | None = None
    maximo: float | None = None
    opcoes: list[Any] | None = None
    limite: Literal["treino", "provisorio", "nenhum"] = Field(
        description="treino = faixa vista no treino (0,5% a 99,5%); provisorio = sem faixa do treino ainda")


class ScenarioEffect(BaseModel):
    """O que um campo, trocado sozinho, fez com a PD (o prever() rodado só com essa troca)."""
    campo: str
    rotulo: str
    valor_original: Any = None
    valor_novo: Any = None
    pd_original: float | None = None
    pd_so_este_campo: float | None = None
    diferenca_pd: float | None = None
    efeito: Literal["aumenta", "reduz", "neutro", "revisao_manual", "sem_pd"]


class ScenarioResult(BaseModel):
    contrato_id: str
    alteracoes: dict[str, Any]
    original: PredictionResponse
    cenario: PredictionResponse
    parcela_original: float | None = Field(default=None, description="€ por mês, no juro cobrado original")
    parcela_cenario: float | None = Field(default=None, description="€ por mês, no juro cobrado do cenário")
    efeitos: list[ScenarioEffect]
    campos: list[ScenarioField]
    procedencia: Provenance



# ---------- Teste de invariância (POST /contracts/{id}/invariance) ----------

class InvarianceSnapshot(BaseModel):
    """O que se compara entre as duas execuções. Nenhum atributo protegido aqui."""
    pd: float | None = None
    faixa: str | None = None
    juro_justo: float | None = None
    juro_justo_min: float | None = None
    juro_justo_max: float | None = None
    situacao_preco: str
    motivos: list[str] = Field(description="Rótulos dos motivos, na ordem do peso")


class InvarianceResult(BaseModel):
    """Gênero e idade trocados mudam o resultado? Sem os valores reais nem os trocados."""
    contrato_id: str
    atributos_trocados: list[str]
    como_foi_trocado: str
    original: InvarianceSnapshot
    trocado: InvarianceSnapshot
    identico: bool
    diferencas: list[str] = Field(description="Campos que mudaram (vazia = idêntico); motivos compara peso e efeito")
    modelo_sem_atributos_protegidos: bool = Field(description="As 21 variáveis do modelo não incluem gênero nem idade")
    procedencia: Provenance


# ---------- Decisão do analista (db/05_decisoes_analista.sql) ----------

AnalystDecision = Literal["manter_preco", "revisar_preco", "encaminhar_compliance"]


class NewDecision(BaseModel):
    """O que o painel envia ao registrar uma decisão.

    `resultado` é a RESPOSTA do /predict (com o parecer), nunca a solicitação:
    assim gênero e idade não chegam ao registro. Em revisão manual, PD, faixa e
    juros justos seguem nulos (a tabela aceita desde 08/11).
    """
    requisicao_id: UUID | None = Field(default=None, description="Gerado pelo painel a cada clique; evita gravar duas vezes")
    analista: str = Field(min_length=1, max_length=120)
    decisao: AnalystDecision
    justificativa: str = Field(min_length=1, max_length=4000)
    taxa_proposta: float | None = Field(default=None, gt=0, le=10, description="Nova taxa, em fração ao ano (nominal)")
    resultado: PredictionResponse

    @field_validator("analista", "justificativa")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("não pode ficar em branco")
        return v.strip()


class RecordedDecision(BaseModel):
    """Uma linha da tabela decisao_analista, como o painel exibe."""
    decisao_id: int
    registrada_em: datetime
    contrato_id: str
    origem: Literal["carteira", "simulacao"]
    analista: str
    decisao: AnalystDecision
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


class CurrentDecision(BaseModel):
    """Decisão mais recente de um contrato da carteira (vw_decisao_atual)."""
    contrato_id: str
    decisao_id: int
    registrada_em: datetime
    analista: str
    decisao: AnalystDecision
