from sqlalchemy import Column, String, Integer, Float, ForeignKey, Numeric, Boolean, Date
from sqlalchemy.orm import relationship
from src.db.database import Base

#MAPEAMENTO DAS ENTIDADES DO BONDORA
class Cliente(Base):
    __tablename__ = "cliente"

    # chave primaria
    cliente_id = Column(String, primary_key=True, index=True)
    
    # as variaveis demograficas e sociais
    genero = Column(Integer)  # 0=Homem, 1=Mulher, 2=Indefinido
    idade = Column(Integer)
    pais = Column(String(2))
    escolaridade = Column(Integer)
    estado_civil = Column(Integer)
    n_dependentes = Column(Integer)
    situacao_emprego = Column(Integer)
    tempo_emprego_atual = Column(String)
    experiencia_trabalho = Column(String)
    area_ocupacao = Column(Integer)
    tipo_moradia = Column(Integer)
    
    # rendas
    renda_empregador_principal = Column(Numeric(16, 2))
    renda_pensao = Column(Numeric(16, 2))
    renda_auxilio_familiar = Column(Numeric(16, 2))
    renda_assistencia_social = Column(Numeric(16, 2))
    renda_licenca = Column(Numeric(16, 2))
    renda_pensao_alimenticia = Column(Numeric(16, 2))
    renda_outras = Column(Numeric(16, 2))
    renda_total = Column(Numeric(16, 2))

    # relacionamento (Um cliente p/ vários empréstimos)
    emprestimos = relationship("Emprestimo", back_populates="cliente")


class HistoricoCredito(Base):
    __tablename__ = "historico_credito"

   # a chave primária é o loan_id, para manter a relação 1:1 com o empréstimo original
    loan_id = Column(String, primary_key=True, index=True)
    
    # metricas Financeiras e histórico
    n_emprestimos_anteriores = Column(Integer)
    valor_emprestimos_anteriores = Column(Numeric(16, 2))
    pagamentos_anteriores = Column(Numeric(16, 2))
    quitacoes_antecipadas_valor = Column(Numeric(16, 2))
    quitacoes_antecipadas_qtd = Column(Integer)
    passivos_existentes = Column(Integer)
    passivos_total = Column(Numeric(16, 2))
    refinanciamento_passivos = Column(Integer)
    divida_renda = Column(Numeric(10, 4))
    caixa_livre = Column(Numeric(16, 2))
    
    # scores externos
    score_es_microl = Column(String)
    score_es_equifax = Column(String)
    score_fi_asiakastieto = Column(String)
    score_ee_mini = Column(Numeric(10, 2))

    # relacionamento invertido (O histórico pertence a um empréstimo)
    emprestimo = relationship("Emprestimo", back_populates="historico")


class Emprestimo(Base):
    __tablename__ = "emprestimo"

    # chave Primária
    loan_id = Column(String, primary_key=True, index=True)
    
    # chaves Estrangeiras
    cliente_id = Column(String, ForeignKey("cliente.cliente_id", ondelete="CASCADE"))
    
    # identificadores e datas
    numero = Column(Integer)
    data_referencia = Column(Date)
    data_pedido = Column(Date)
    data_emprestimo = Column(Date)
    data_primeira_parcela = Column(Date)
    data_vencimento_original = Column(Date)
    
    # dados do Contrato Bondora
    novo_cliente = Column(Boolean)
    valor_solicitado = Column(Numeric(16, 2))
    valor_concedido = Column(Numeric(16, 2))
    juro_aa = Column(Numeric(10, 4))
    prazo_meses = Column(Integer)
    parcela_mensal = Column(Numeric(16, 2))
    finalidade = Column(Integer)
    tipo_verificacao = Column(Integer)

    # saídas do modelo do Bondora
    rating = Column(String)
    versao_modelo_bondora = Column(Integer)
    pd_bondora = Column(Numeric(10, 4))
    perda_esperada_bondora = Column(Numeric(10, 4))
    lgd_bondora = Column(Numeric(10, 4))
    retorno_esperado_bondora = Column(Numeric(10, 4))
    
    # desfecho e pós-concessão
    status = Column(String)
    data_default = Column(Date)
    dias_atraso = Column(Integer)
    pior_categoria_atraso = Column(String)
    reestruturado = Column(Boolean)
    data_vencimento_atual = Column(Date)
    data_fim_contrato = Column(Date)
    data_ultimo_pagamento = Column(Date)
    principal_pago = Column(Numeric(16, 2))
    juros_multas_pagos = Column(Numeric(16, 2))
    principal_baixado = Column(Numeric(16, 2))
    juros_baixados = Column(Numeric(16, 2))
    saldo_principal = Column(Numeric(16, 2))
    recuperacao_principal = Column(Numeric(16, 2))
    recuperacao_juros = Column(Numeric(16, 2))
    ead1 = Column(Numeric(16, 2))
    ead2 = Column(Numeric(16, 2))
    estagio_recuperacao = Column(Integer)

    # relacionamentos
    cliente = relationship("Cliente", back_populates="emprestimos")
    historico = relationship("HistoricoCredito", back_populates="emprestimo", uselist=False)

    #MAPEAMENTO DO SCHEMAS 02 P/ MACROENTIDADES

class EuriborMensal(Base):
    __tablename__ = "euribor_mensal"
    
    mes = Column(Date, primary_key=True, index=True) 
    euribor_3m = Column(Numeric(10, 7))
    euribor_12m = Column(Numeric(10, 7))

class SelicMensal(Base):
    __tablename__ = "selic_mensal"
    
    mes = Column(Date, primary_key=True, index=True)
    selic_aa = Column(Numeric(10, 2))
    selic_meta_aa = Column(Numeric(6, 2))