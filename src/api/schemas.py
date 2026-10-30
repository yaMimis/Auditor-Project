from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Dict
from datetime import datetime

#validar os dados que chegam na requisição do JSON
class SolicitacaoEmprestimo(BaseModel):
    loan_id: str
    
    # variáveis Preditivas de Risco p/ o XGBoost do Samuel
    amount: float
    income_total: float
    employment_status: Optional[str] = "Unemployed"
    verification_type: Optional[str] = "Not Verified"
    gender: int
    age: int
    country: str
    interest_cobrado: float  # Recebido em %, ex: 24.9

#Schemas de saida e integração(Maria)
ChaveNumero = Literal["pd", "juro_cobrado", "juro_justo", "juro_justo_min", "juro_justo_max"]

class Fonte(BaseModel):
    norma: str
    artigo: str
    trecho_id: str

class ParecerIA(BaseModel):
    """Reflete o modelo 'Parecer' definido no FORMATO_JSON.md"""
    contrato_id: str
    resumo: str
    pontos_de_atencao: List[str] = Field(max_length=3)
    recomendacao_texto: str
    fontes: List[Fonte]
    numeros_citados: Dict[ChaveNumero, float]
    recomendacao: Literal["manter_preco", "revisar_preco", "encaminhar_compliance", "revisao_manual"]
    origem: Literal["llm", "template"]
    versao_prompt: str
    gerado_em: datetime

class MotivoSHAP(BaseModel):
    variavel: str
    efeito: Literal["aumenta_risco", "reduz_risco"]

class RespostaPrever(BaseModel):
    """Reflete a Entrada exigida pela Maria e o Retorno final para o Streamlit"""
    contrato_id: str
    versao_modelo: str
    pd: float
    faixa: Literal["A", "B", "C", "D", "E"]
    juro_cobrado: float     # Deve ser fração (0.249)
    juro_justo: float       # Deve ser fração (0.162)
    juro_justo_min: float   # Deve ser fração
    juro_justo_max: float   # Deve ser fração
    situacao_preco: Literal["acima_do_justo", "abaixo_do_justo", "dentro_da_margem"]
    motivos: List[MotivoSHAP]
    alerta_dados: bool
    
    # O Parecer da IA é devolvido dentro desta chave
    parecer_ia: Optional[ParecerIA] = None