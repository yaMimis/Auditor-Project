from sqlalchemy import Column, String, Float, Integer, Date, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from src.db.database import Base

class Emprestimo(Base):
    __tablename__ = "emprestimo"
    
    loan_id = Column(String, primary_key=True, index=True)
    # Demais colunas da tabela emprestimo conforme o banco
    
    # Relacionamentos 1 para 1 baseados no loan_id
    cliente = relationship("Cliente", back_populates="emprestimo", uselist=False)
    historico = relationship("HistoricoCredito", back_populates="emprestimo", uselist=False)


class Cliente(Base):
    __tablename__ = "cliente"
    
    # loan_id é a chave primária que vincula o cliente a um contrato específico
    loan_id = Column(String, ForeignKey("emprestimo.loan_id", ondelete="CASCADE"), primary_key=True)
    cliente_id = Column(String, index=True)  # Repete entre múltiplos contratos do mesmo cliente
    
    age = Column(Integer, nullable=True)
    gender = Column(Integer, nullable=True)
    country = Column(String, nullable=True)
    # Demais colunas do cliente...

    emprestimo = relationship("Emprestimo", back_populates="cliente")


class HistoricoCredito(Base):
    __tablename__ = "historico_credito"
    
    loan_id = Column(String, ForeignKey("emprestimo.loan_id", ondelete="CASCADE"), primary_key=True)
    # Demais colunas de historico_credito...

    emprestimo = relationship("Emprestimo", back_populates="historico")


class BcCreditoPessoalMensal(Base):
    __tablename__ = "bc_credito_pessoal_mensal"

    mes = Column(Date, primary_key=True)
    taxa_aa = Column(Numeric)