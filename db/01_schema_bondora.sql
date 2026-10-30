-- =====================================================================
-- Auditor de Preço Justo · esquema do Bondora LoanData
-- PostgreSQL 14+ · idempotente (pode rodar mais de uma vez)
--
-- Três tabelas, uma linha por contrato, ligadas por loan_id:
--   emprestimo         termos do contrato + saídas do Bondora + desfecho (pai)
--   cliente            perfil do tomador NO MOMENTO DO PEDIDO
--   historico_credito  endividamento e histórico de crédito ANTES do contrato
--
-- Marcações (valem para o DATA.md e para o teste antivazamento):
--   [LISTA NEGRA]   pós-concessão ou saída do modelo do Bondora:
--                   NUNCA entra como variável do modelo. Fica no banco
--                   só para montar o alvo, o preço cobrado, a comparação
--                   com a PD do Bondora e o backtest.
--   [SÓ AUDITORIA]  gênero, idade, estado civil e dependentes: usados apenas
--                   na auditoria de equidade, nunca para prever risco.
--   [INDISPONÍVEL APÓS 2017]  preenchidas só nos contratos até ~2017 (cerca de
--                   81% em branco no período de teste): fora do modelo.
--
-- Valores monetários em euro. Juros em % ao ano, como vêm do Bondora.
-- A carga NÃO filtra nada (inclui contratos ativos): o recorte "encerrados
-- de coortes maduras" do DATA.md é aplicado depois, em view/consulta.
-- =====================================================================

-- ---------------------------------------------------------------------
-- emprestimo (tabela pai)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS emprestimo (
    loan_id                   TEXT PRIMARY KEY,           -- LoanId (GUID em minúsculas)
    numero                    INTEGER,                    -- LoanNumber
    data_referencia           DATE,                       -- ReportAsOfEOD (data de corte do arquivo)

    -- termos do contrato na concessão
    data_pedido               DATE,                       -- LoanApplicationStartedDate
    data_emprestimo           DATE,                       -- LoanDate
    data_primeira_parcela     DATE,                       -- FirstPaymentDate
    data_vencimento_original  DATE,                       -- MaturityDate_Original
    novo_cliente              BOOLEAN,                    -- NewCreditCustomer
    valor_solicitado          NUMERIC(16,2),              -- AppliedAmount
    valor_concedido           NUMERIC(16,2),              -- Amount
    juro_aa                   NUMERIC(10,4),              -- Interest  [LISTA NEGRA] (é o preço auditado)
    prazo_meses               INTEGER,                    -- LoanDuration
    parcela_mensal            NUMERIC(16,2),              -- MonthlyPayment  [LISTA NEGRA] (embute o juro)
    finalidade                SMALLINT,                   -- UseOfLoan (código; -1 vira NULL)  [INDISPONÍVEL APÓS 2017]
    tipo_verificacao          SMALLINT,                   -- VerificationType (código; -1 vira NULL)

    -- saídas do modelo do Bondora
    rating                    TEXT,                       -- Rating            [LISTA NEGRA]
    versao_modelo_bondora     INTEGER,                    -- ModelVersion      [LISTA NEGRA]
    pd_bondora                DOUBLE PRECISION,           -- ProbabilityOfDefault [LISTA NEGRA]
    perda_esperada_bondora    DOUBLE PRECISION,           -- ExpectedLoss      [LISTA NEGRA]
    lgd_bondora               DOUBLE PRECISION,           -- LossGivenDefault  [LISTA NEGRA]
    retorno_esperado_bondora  DOUBLE PRECISION,           -- ExpectedReturn    [LISTA NEGRA]

    -- desfecho e dados pós-concessão
    status                    TEXT,                       -- Status            [LISTA NEGRA]
    data_default              DATE,                       -- DefaultDate       [LISTA NEGRA]
    dias_atraso               INTEGER,                    -- CurrentDebtDaysPrimary [LISTA NEGRA]
    pior_categoria_atraso     TEXT,                       -- WorseLateCategory [LISTA NEGRA]
    reestruturado             BOOLEAN,                    -- Restructured      [LISTA NEGRA]
    data_vencimento_atual     DATE,                       -- MaturityDate_Last [LISTA NEGRA]
    data_fim_contrato         DATE,                       -- ContractEndDate   [LISTA NEGRA]
    data_ultimo_pagamento     DATE,                       -- LastPaymentOn     [LISTA NEGRA]
    principal_pago            NUMERIC(16,2),              -- PrincipalPaymentsMade [LISTA NEGRA]
    juros_multas_pagos        NUMERIC(16,2),              -- InterestAndPenaltyPaymentsMade [LISTA NEGRA]
    principal_baixado         NUMERIC(16,2),              -- PrincipalWriteOffs [LISTA NEGRA]
    juros_baixados            NUMERIC(16,2),              -- InterestAndPenaltyWriteOffs [LISTA NEGRA]
    saldo_principal           NUMERIC(16,2),              -- PrincipalBalance  [LISTA NEGRA]
    recuperacao_principal     NUMERIC(16,2),              -- PrincipalRecovery [LISTA NEGRA]
    recuperacao_juros         NUMERIC(16,2),              -- InterestRecovery  [LISTA NEGRA]
    ead1                      NUMERIC(16,2),              -- EAD1              [LISTA NEGRA]
    ead2                      NUMERIC(16,2),              -- EAD2              [LISTA NEGRA]
    estagio_recuperacao       SMALLINT                    -- RecoveryStage     [LISTA NEGRA]
);

CREATE INDEX IF NOT EXISTS ix_emprestimo_data_emprestimo ON emprestimo (data_emprestimo);
CREATE INDEX IF NOT EXISTS ix_emprestimo_status          ON emprestimo (status);

-- ---------------------------------------------------------------------
-- cliente (perfil no momento do pedido; 1 linha por contrato)
-- O mesmo cliente aparece em vários contratos: cliente_id é a chave da
-- divisão treino/teste "por cliente".
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cliente (
    loan_id                    TEXT PRIMARY KEY REFERENCES emprestimo (loan_id) ON DELETE CASCADE,
    cliente_id                 TEXT,                      -- UserName pseudonimizado: HMAC-SHA256 com chave secreta, 16 caracteres hex

    genero                     SMALLINT CHECK (genero IN (0, 1, 2)),  -- Gender: 0 homem, 1 mulher, 2 indefinido  [SÓ AUDITORIA]
    idade                      SMALLINT,                  -- Age                [SÓ AUDITORIA]
    pais                       CHAR(2),                   -- Country (EE, ES, FI, SK)

    escolaridade               SMALLINT,                  -- Education (código; -1 vira NULL)
    estado_civil               SMALLINT,                  -- MaritalStatus (código)  [SÓ AUDITORIA] [INDISPONÍVEL APÓS 2017]
    n_dependentes              SMALLINT,                  -- NrOfDependants ("10Plus" vira 10)  [SÓ AUDITORIA] [INDISPONÍVEL APÓS 2017]
    situacao_emprego           SMALLINT,                  -- EmploymentStatus (código)  [INDISPONÍVEL APÓS 2017]
    tempo_emprego_atual        TEXT,                      -- EmploymentDurationCurrentEmployer
    experiencia_trabalho       TEXT,                      -- WorkExperience  [INDISPONÍVEL APÓS 2017]
    area_ocupacao              SMALLINT,                  -- OccupationArea (código)  [INDISPONÍVEL APÓS 2017]
    tipo_moradia               SMALLINT,                  -- HomeOwnershipType (código)

    renda_empregador_principal NUMERIC(16,2),             -- IncomeFromPrincipalEmployer
    renda_pensao               NUMERIC(16,2),             -- IncomeFromPension
    renda_auxilio_familiar     NUMERIC(16,2),             -- IncomeFromFamilyAllowance
    renda_assistencia_social   NUMERIC(16,2),             -- IncomeFromSocialWelfare
    renda_licenca              NUMERIC(16,2),             -- IncomeFromLeavePay
    renda_pensao_alimenticia   NUMERIC(16,2),             -- IncomeFromChildSupport
    renda_outras               NUMERIC(16,2),             -- IncomeOther
    renda_total                NUMERIC(16,2)              -- IncomeTotal
);

CREATE INDEX IF NOT EXISTS ix_cliente_cliente_id ON cliente (cliente_id);
CREATE INDEX IF NOT EXISTS ix_cliente_pais       ON cliente (pais);

-- ---------------------------------------------------------------------
-- historico_credito (situação de crédito ANTES do contrato)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS historico_credito (
    loan_id                        TEXT PRIMARY KEY REFERENCES emprestimo (loan_id) ON DELETE CASCADE,

    n_emprestimos_anteriores       INTEGER,               -- NoOfPreviousLoansBeforeLoan
    valor_emprestimos_anteriores   NUMERIC(16,2),         -- AmountOfPreviousLoansBeforeLoan
    pagamentos_anteriores          NUMERIC(16,2),         -- PreviousRepaymentsBeforeLoan
    quitacoes_antecipadas_valor    NUMERIC(16,2),         -- PreviousEarlyRepaymentsBefoleLoan (typo do Bondora)
    quitacoes_antecipadas_qtd      INTEGER,               -- PreviousEarlyRepaymentsCountBeforeLoan

    passivos_existentes            INTEGER,               -- ExistingLiabilities
    passivos_total                 NUMERIC(16,2),         -- LiabilitiesTotal
    refinanciamento_passivos       INTEGER,               -- RefinanceLiabilities (qtd. de passivos refinanciados)
    divida_renda                   DOUBLE PRECISION,      -- DebtToIncome
    caixa_livre                    NUMERIC(16,2),         -- FreeCash

    score_es_microl                TEXT,                  -- CreditScoreEsMicroL
    score_es_equifax               TEXT,                  -- CreditScoreEsEquifaxRisk
    score_fi_asiakastieto          TEXT,                  -- CreditScoreFiAsiakasTietoRiskGrade
    score_ee_mini                  NUMERIC(10,2)          -- CreditScoreEeMini
);
