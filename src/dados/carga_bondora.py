#!/usr/bin/env python3
"""Carga do Bondora LoanData em `emprestimo`, `cliente` e `historico_credito`.

Uso:
    export DATABASE_URL=postgresql://usuario:senha@localhost:5432/auditor
    python carga_bondora.py --csv data/raw/LoanData.csv --ddl 01_schema_bondora.sql

Opções úteis:
    --linhas 5000      carrega só as primeiras N linhas (teste rápido)
    --ddl ARQUIVO      aplica o DDL antes de carregar (opcional)

O que faz:
  * lê o CSV em blocos, tudo como texto, e converte coluna a coluna;
  * valor ilegível vira NULL e entra no relatório final (nada some em silêncio);
  * separa cada contrato nas três tabelas, todas ligadas por loan_id;
  * UserName vira cliente_id com hash (pseudonimização);
  * carrega via COPY, em uma única transação, e recarrega do zero a cada
    execução (TRUNCATE) — rodar duas vezes dá o mesmo resultado.

O que NÃO faz: filtrar contratos nem tratar outliers. O recorte "encerrados de
coortes maduras" (DATA.md) e a limpeza estatística ficam em view/consulta e no
pandera, para a tabela bruta continuar auditável.

Teste antivazamento: importe COLUNAS_LISTA_NEGRA e COLUNAS_SO_AUDITORIA daqui
e falhe se alguma aparecer nas variáveis do modelo.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

SAL_CLIENTE = os.environ.get("CLIENTE_ID_SAL", "")  # opcional; mantenha fora do repositório


# --------------------------------------------------------------------------
# Mapeamento CSV -> banco
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Col:
    csv: tuple[str, ...]          # nome(s) possíveis no CSV; vale o primeiro que existir
    db: str                       # nome da coluna no banco
    tipo: str                     # id | hash | texto | upper | int | cod | dep | num | bool | data
    uso: str | None = None        # "lista_negra" | "so_auditoria"
    dominio: frozenset | None = None  # só para tipo "cod": valores aceitos


def c(csv, db, tipo, uso=None, dominio=None) -> Col:
    nomes = (csv,) if isinstance(csv, str) else tuple(csv)
    return Col(nomes, db, tipo, uso, frozenset(dominio) if dominio else None)


LN = "lista_negra"
SA = "so_auditoria"
CHAVE = c("LoanId", "loan_id", "id")

# A ordem do dicionário é a ordem de carga (a tabela pai vem primeiro).
TABELAS: dict[str, list[Col]] = {
    "emprestimo": [
        CHAVE,
        c("LoanNumber", "numero", "int"),
        c("ReportAsOfEOD", "data_referencia", "data"),
        c("LoanApplicationStartedDate", "data_pedido", "data"),
        c("LoanDate", "data_emprestimo", "data"),
        c("FirstPaymentDate", "data_primeira_parcela", "data"),
        c("MaturityDate_Original", "data_vencimento_original", "data"),
        c("NewCreditCustomer", "novo_cliente", "bool"),
        c("AppliedAmount", "valor_solicitado", "num"),
        c("Amount", "valor_concedido", "num"),
        c("Interest", "juro_aa", "num", LN),
        c("LoanDuration", "prazo_meses", "int"),
        c("MonthlyPayment", "parcela_mensal", "num"),
        c("UseOfLoan", "finalidade", "cod"),
        c("VerificationType", "tipo_verificacao", "cod"),
        # saídas do modelo do Bondora
        c("Rating", "rating", "texto", LN),
        c("ModelVersion", "versao_modelo_bondora", "int", LN),
        c("ProbabilityOfDefault", "pd_bondora", "num", LN),
        c("ExpectedLoss", "perda_esperada_bondora", "num", LN),
        c("LossGivenDefault", "lgd_bondora", "num", LN),
        c("ExpectedReturn", "retorno_esperado_bondora", "num", LN),
        # desfecho e pós-concessão
        c("Status", "status", "texto", LN),
        c("DefaultDate", "data_default", "data", LN),
        c("CurrentDebtDaysPrimary", "dias_atraso", "int", LN),
        c("WorseLateCategory", "pior_categoria_atraso", "texto", LN),
        c("Restructured", "reestruturado", "bool", LN),
        c("MaturityDate_Last", "data_vencimento_atual", "data", LN),
        c("ContractEndDate", "data_fim_contrato", "data", LN),
        c("LastPaymentOn", "data_ultimo_pagamento", "data", LN),
        c("PrincipalPaymentsMade", "principal_pago", "num", LN),
        c("InterestAndPenaltyPaymentsMade", "juros_multas_pagos", "num", LN),
        c("PrincipalWriteOffs", "principal_baixado", "num", LN),
        c("InterestAndPenaltyWriteOffs", "juros_baixados", "num", LN),
        c("PrincipalBalance", "saldo_principal", "num", LN),
        c("PrincipalRecovery", "recuperacao_principal", "num", LN),
        c("InterestRecovery", "recuperacao_juros", "num", LN),
        c("EAD1", "ead1", "num", LN),
        c("EAD2", "ead2", "num", LN),
        c("RecoveryStage", "estagio_recuperacao", "cod", LN),
    ],
    "cliente": [
        CHAVE,
        c("UserName", "cliente_id", "hash"),
        c("Gender", "genero", "cod", SA, dominio={0, 1, 2}),
        c("Age", "idade", "int", SA),
        c("Country", "pais", "upper"),
        c("Education", "escolaridade", "cod"),
        c("MaritalStatus", "estado_civil", "cod"),
        c("NrOfDependants", "n_dependentes", "dep"),
        c("EmploymentStatus", "situacao_emprego", "cod"),
        c("EmploymentDurationCurrentEmployer", "tempo_emprego_atual", "texto"),
        c("WorkExperience", "experiencia_trabalho", "texto"),
        c("OccupationArea", "area_ocupacao", "cod"),
        c("HomeOwnershipType", "tipo_moradia", "cod"),
        c("IncomeFromPrincipalEmployer", "renda_empregador_principal", "num"),
        c("IncomeFromPension", "renda_pensao", "num"),
        c("IncomeFromFamilyAllowance", "renda_auxilio_familiar", "num"),
        c("IncomeFromSocialWelfare", "renda_assistencia_social", "num"),
        c("IncomeFromLeavePay", "renda_licenca", "num"),
        c("IncomeFromChildSupport", "renda_pensao_alimenticia", "num"),
        c("IncomeOther", "renda_outras", "num"),
        c("IncomeTotal", "renda_total", "num"),
    ],
    "historico_credito": [
        CHAVE,
        c("NoOfPreviousLoansBeforeLoan", "n_emprestimos_anteriores", "int"),
        c("AmountOfPreviousLoansBeforeLoan", "valor_emprestimos_anteriores", "num"),
        c("PreviousRepaymentsBeforeLoan", "pagamentos_anteriores", "num"),
        # o Bondora grafa "Befole" no CSV; aceitamos as duas grafias
        c(("PreviousEarlyRepaymentsBefoleLoan", "PreviousEarlyRepaymentsBeforeLoan"),
          "quitacoes_antecipadas_valor", "num"),
        c("PreviousEarlyRepaymentsCountBeforeLoan", "quitacoes_antecipadas_qtd", "int"),
        c("ExistingLiabilities", "passivos_existentes", "int"),
        c("LiabilitiesTotal", "passivos_total", "num"),
        c("RefinanceLiabilities", "refinanciamento_passivos", "int"),
        c("DebtToIncome", "divida_renda", "num"),
        c("FreeCash", "caixa_livre", "num"),
        c("CreditScoreEsMicroL", "score_es_microl", "texto"),
        c("CreditScoreEsEquifaxRisk", "score_es_equifax", "texto"),
        c("CreditScoreFiAsiakasTietoRiskGrade", "score_fi_asiakastieto", "texto"),
        c("CreditScoreEeMini", "score_ee_mini", "num"),
    ],
}

COLUNAS_LISTA_NEGRA = frozenset(
    col.db for cols in TABELAS.values() for col in cols if col.uso == LN
)
COLUNAS_SO_AUDITORIA = frozenset(
    col.db for cols in TABELAS.values() for col in cols if col.uso == SA
)


# --------------------------------------------------------------------------
# Conversão de tipos (cada função devolve uma Series pronta para o COPY)
# --------------------------------------------------------------------------
def _hash(valor) -> object:
    if not isinstance(valor, str):
        return np.nan
    return hashlib.sha256((SAL_CLIENTE + valor).encode("utf-8")).hexdigest()[:16]


def _para_int(s: pd.Series) -> pd.Series:
    num = pd.to_numeric(s, errors="coerce").replace([np.inf, -np.inf], np.nan)
    return num.round().astype("Int64")


def _converter(bruto: pd.Series, col: Col) -> pd.Series:
    s = bruto.str.strip().replace("", np.nan)
    t = col.tipo
    if t == "id":
        out = s.str.lower()
    elif t == "hash":
        out = s.map(_hash)
    elif t == "texto":
        out = s
    elif t == "upper":
        out = s.str.upper()
    elif t == "int":
        out = _para_int(s)
    elif t == "cod":  # código categórico do Bondora: -1 = "sem informação"
        out = _para_int(s)
        out = out.mask((out == -1).fillna(False))
        if col.dominio is not None:
            out = out.mask(out.notna() & ~out.isin(list(col.dominio)))
    elif t == "dep":  # "0".."9", "10Plus"
        out = _para_int(s.str.extract(r"(\d+)", expand=False))
    elif t == "num":
        out = pd.to_numeric(s, errors="coerce").replace([np.inf, -np.inf], np.nan)
    elif t == "bool":
        mapa = {"true": True, "false": False, "1": True, "0": False}
        out = s.str.lower().map(mapa).astype("boolean")
    elif t == "data":  # aceita "AAAA-MM-DD" e "AAAA-MM-DD hh:mm:ss"
        dt = pd.to_datetime(s.str[:10], format="%Y-%m-%d", errors="coerce")
        dt = dt.mask(dt.dt.year < 2000)  # sentinelas tipo 0001-01-01 (o Bondora começa em 2008)
        out = dt.dt.strftime("%Y-%m-%d")
    else:
        raise ValueError(f"tipo desconhecido: {t}")
    return out, s


# --------------------------------------------------------------------------
# Leitura, divisão em tabelas e COPY
# --------------------------------------------------------------------------
def _resolver(cabecalho: set[str]):
    """Para cada tabela, lista (Col, nome_no_csv) das colunas presentes + ausentes."""
    presentes: dict[str, list[tuple[Col, str]]] = {}
    ausentes: list[str] = []
    for tabela, cols in TABELAS.items():
        presentes[tabela] = []
        for col in cols:
            achado = next((n for n in col.csv if n in cabecalho), None)
            if achado:
                presentes[tabela].append((col, achado))
            else:
                ausentes.append(f"{tabela}.{col.db} (CSV: {col.csv[0]})")
    return presentes, ausentes


def _copy(cur, tabela: str, colunas: list[str], df: pd.DataFrame) -> None:
    sql = f"COPY {tabela} ({', '.join(colunas)}) FROM STDIN WITH (FORMAT csv, NULL '')"
    buf = io.StringIO()
    df.to_csv(buf, index=False, header=False, na_rep="")
    if hasattr(cur, "copy"):          # psycopg 3
        with cur.copy(sql) as cp:
            cp.write(buf.getvalue())
    else:                             # psycopg2
        buf.seek(0)
        cur.copy_expert(sql, buf)


def _conectar(dsn: str):
    # aceita URL no estilo SQLAlchemy ("postgresql+psycopg2://...")
    dsn = re.sub(r"^postgresql\+\w+://", "postgresql://", dsn)
    try:
        import psycopg as driver      # psycopg 3
    except ImportError:
        import psycopg2 as driver     # psycopg2
    return driver.connect(dsn)


def carregar(csv: Path, dsn: str, ddl: Path | None = None,
             bloco: int = 25_000, linhas: int | None = None) -> None:
    cabecalho = pd.read_csv(csv, nrows=0, encoding="utf-8-sig").columns
    presentes, ausentes = _resolver(set(cabecalho))

    if not any(col.db == "loan_id" for col, _ in presentes["emprestimo"]):
        sys.exit("ERRO: coluna LoanId não encontrada no CSV.")
    if not any(col.db == "cliente_id" for col, _ in presentes["cliente"]):
        sys.exit(
            "ERRO: coluna UserName não encontrada no CSV. Sem ela não existe "
            "divisão por cliente (risco crítico do plano). Confira o dicionário "
            "de dados e a versão do arquivo antes de continuar."
        )

    usar = sorted({nome for lst in presentes.values() for _, nome in lst})
    leitor = pd.read_csv(
        csv, usecols=usar, dtype=str, keep_default_na=False, na_values=[""],
        encoding="utf-8-sig", chunksize=bloco, nrows=linhas,
    )

    lidas = 0
    duplicadas = 0
    sem_id = 0
    vistos: set[str] = set()
    virou_null: Counter = Counter()
    carregadas = Counter()

    conn = _conectar(dsn)
    try:
        with conn, conn.cursor() as cur:
            if ddl:
                cur.execute(Path(ddl).read_text(encoding="utf-8"))
            cur.execute("TRUNCATE emprestimo, cliente, historico_credito")

            for pedaco in leitor:
                lidas += len(pedaco)
                id_csv = next(n for col, n in presentes["emprestimo"] if col.db == "loan_id")
                ids, _ = _converter(pedaco[id_csv], CHAVE)

                sem_id += int(ids.isna().sum())
                repetido = ids.duplicated() | ids.isin(vistos)
                duplicadas += int((repetido & ids.notna()).sum())
                manter = ids.notna() & ~repetido
                vistos.update(ids[manter])
                pedaco = pedaco[manter]
                if pedaco.empty:
                    continue

                for tabela, lista in presentes.items():
                    saida = {}
                    for col, nome in lista:
                        convertido, original = _converter(pedaco[nome], col)
                        virou_null[f"{tabela}.{col.db}"] += int(
                            (original.notna() & convertido.isna()).sum()
                        )
                        saida[col.db] = convertido
                    df = pd.DataFrame(saida)
                    _copy(cur, tabela, list(df.columns), df)
                    carregadas[tabela] += len(df)

            # conferência dentro da mesma transação
            contagens = {}
            for tabela in TABELAS:
                cur.execute(f"SELECT count(*) FROM {tabela}")
                contagens[tabela] = cur.fetchone()[0]
            if len(set(contagens.values())) != 1 or contagens["emprestimo"] != len(vistos):
                raise RuntimeError(f"contagens divergentes entre as tabelas: {contagens}")
            cur.execute("SELECT count(DISTINCT cliente_id) FROM cliente")
            n_clientes = cur.fetchone()[0]
    finally:
        conn.close()

    print("=" * 64)
    print(f"Linhas lidas:                    {lidas:>10,}")
    print(f"Sem LoanId (descartadas):        {sem_id:>10,}")
    print(f"LoanId repetido (descartadas):   {duplicadas:>10,}")
    for tabela, n in contagens.items():
        print(f"Linhas em {tabela:<19}    {n:>10,}")
    print(f"Clientes distintos:              {n_clientes:>10,}")
    if ausentes:
        print("\nColunas do mapeamento ausentes no CSV (ficam NULL):")
        for a in ausentes:
            print(f"  - {a}")
    relevantes = [(k, v) for k, v in virou_null.items() if v]
    if relevantes:
        print("\nValores preenchidos no CSV que viraram NULL (ilegíveis, fora do "
              "domínio ou sentinela -1):")
        for k, v in sorted(relevantes, key=lambda kv: -kv[1]):
            print(f"  {k:<45} {v:>10,}")
    print("=" * 64)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--csv", required=True, type=Path)
    ap.add_argument("--dsn", default=os.environ.get("DATABASE_URL"),
                    help="padrão: variável de ambiente DATABASE_URL")
    ap.add_argument("--ddl", type=Path, help="arquivo .sql aplicado antes da carga")
    ap.add_argument("--bloco", type=int, default=25_000)
    ap.add_argument("--linhas", type=int, help="carrega só as N primeiras linhas")
    args = ap.parse_args()
    if not args.dsn:
        sys.exit("ERRO: informe --dsn ou defina DATABASE_URL.")
    carregar(args.csv, args.dsn, args.ddl, args.bloco, args.linhas)


if __name__ == "__main__":
    main()
