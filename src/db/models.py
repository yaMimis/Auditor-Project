from sqlalchemy import Column, String, Integer, Float, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from src.db.database import Base

#entidade dos dados traduzindo pra class python para a API
class Cliente(Base):
    __tablename__ = "cliente"

    # chave primaria
    cliente_id = Column(String, primary_key=True, index=True)
    
    # as variaveis demograficas e sociais
    genero = Column(Integer)  # 0=Homem, 1=Mulher, 2=Indefinido
    idade = Column(Integer)
    pais = Column(String(2))
    situacao_emprego = Column(Integer)
    renda_total = Column(Numeric(16, 2))

    # relacionamento (Um cliente p/ vários empréstimos)
    emprestimos = relationship("Emprestimo", back_populates="cliente")


class HistoricoCredito(Base):
    __tablename__ = "historico_credito"

    # chave Primária
    historico_id = Column(String, primary_key=True, index=True)
    
    # chave Estrangeira
    cliente_id = Column(String, ForeignKey("cliente.cliente_id", ondelete="CASCADE"))
    
    # metricas Financeiras
    divida_renda = Column(Float)
    caixa_livre = Column(Numeric(16, 2))

    # relacionamento
    cliente = relationship("Cliente")


class Emprestimo(Base):
    __tablename__ = "emprestimo"

    # chave Primária
    loan_id = Column(String, primary_key=True, index=True)
    
    # chaves Estrangeiras
    cliente_id = Column(String, ForeignKey("cliente.cliente_id", ondelete="CASCADE"))
    historico_id = Column(String, ForeignKey("historico_credito.historico_id"))
    
    # dados do Contrato Bondora
    valor_solicitado = Column(Numeric(16, 2))
    prazo_meses = Column(Integer)
    juro_aa_cobrado = Column(Numeric(10, 4))
    
    # variável alvo/risco
    pd_bondora = Column(Float, nullable=True)

    # relacionamentos
    cliente = relationship("Cliente", back_populates="emprestimos")
    historico = relationship("HistoricoCredito")