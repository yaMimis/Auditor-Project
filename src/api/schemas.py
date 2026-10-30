from pydantic import BaseModel, Field
from typing import Optional, List

#validar os dados que chegam na requisição do JSON
class SolicitacaoAuditoriaSchema(BaseModel):
    loan_id: str
    
    # variáveis Preditivas de Risco p/ o XGBoost do Samuel
    valor_solicitado: float = Field(..., gt=0, description="AppliedAmount em Euros")
    prazo_meses: int = Field(..., gt=0, description="LoanDuration")
    renda_total: float = Field(..., ge=0, description="IncomeTotal")
    situacao_emprego: int = Field(..., description="EmploymentStatus código")
    divida_renda: float = Field(..., description="DebtToIncome")
    caixa_livre: float = Field(..., description="FreeCash")
    
    # preço Auditado Alvo da Comparacao
    juro_aa_cobrado: float = Field(..., description="Juro % a.a. aplicado no contrato pelo Bondora")
    
    # variáveis de Equidade / APENAS para a auditoria de viés
    genero: int = Field(..., description="0=Homem, 1=Mulher, 2=Indefinido")
    idade: int = Field(..., ge=18, le=100)
    pais: str = Field(..., min_length=2, max_length=2, description="EE, ES, FI, SK")


class RespostaAuditoriaSchema(BaseModel):
    loan_id: str

    # metricas de risco e regra de negocio
    pd_calculada: float
    juro_justo_aa: float
    juro_cobrado_aa: float
    delta_injustica_pp: float
    fora_da_margem: bool
    alerta_vies_demografico: bool

    #area de integração com a GenIA p/ RAG da Maria
    parecer_llm: Optional[str] = Field(
        None,
        description="Texto explicativo da LLM(quando ha anomalia ou vies)"
    )
    normas_citadas: List[str] = Field(
        default_factory=list,
        description="Lista de artigos e leis retornados da busca di RAG no pgvector" #verificar formato de retorno do pgvector
    )
    recomendacao_ia: Optional[str] = Field(
        None,
        description="Sugestão de ação gerada pela LLM" #verificar quando a LLM aciona
    )