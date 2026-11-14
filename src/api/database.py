"""Acesso da API ao banco (Marcos): contratos, desfecho, decisões do analista e taxa média do BC.

- Contrato pelo ID (db/01): junta emprestimo + cliente + historico_credito com os nomes de
  coluna que o prever() usa. Gênero, idade, estado civil e dependentes NÃO são lidos:
  servem só para a auditoria de equidade, nunca para a análise de um contrato.
- Desfecho (db/04, vw_retorno_realizado): só contratos de 2009–2016 já encerrados.

- decisao_analista (db/05): só de inclusão; a API grava e lê, nunca altera. Data e
  origem ('carteira' ou 'simulacao') são definidas pelo próprio banco.
- Taxa do BC (db/02): % a.a. EFETIVA, de 03/2011 a 07/2021; vai para o gerar_parecer()
  como bc_credito_pessoal_aa, e o código da Maria escreve o contexto_mercado.
"""

from __future__ import annotations


import os
from contextlib import contextmanager

try:  # lê o .env quando a API roda fora do Docker
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # pragma: no cover
    pass

DEFAULT_URL = "postgresql://postgres:postgres@localhost:5432/auditor_db"

LISTING_COLUMNS = (
    "decisao_id, registrada_em, contrato_id, origem, analista, decisao, justificativa, taxa_proposta, "
    "recomendacao_sistema, situacao_preco, pd, faixa, juro_cobrado, juro_justo, juro_justo_min, "
    "juro_justo_max, versao_modelo, versao_parecer, origem_parecer"
)

SQL_INSERT = """
    INSERT INTO decisao_analista
        (requisicao_id, contrato_id, analista, decisao, justificativa, taxa_proposta,
         recomendacao_sistema, situacao_preco, pd, faixa, juro_cobrado, juro_justo,
         juro_justo_min, juro_justo_max, versao_modelo, versao_parecer, origem_parecer,
         prever_json, parecer_json)
    VALUES
        (%(requisicao_id)s, %(contrato_id)s, %(analista)s, %(decisao)s, %(justificativa)s, %(taxa_proposta)s,
         %(recomendacao_sistema)s, %(situacao_preco)s, %(pd)s, %(faixa)s, %(juro_cobrado)s, %(juro_justo)s,
         %(juro_justo_min)s, %(juro_justo_max)s, %(versao_modelo)s, %(versao_parecer)s, %(origem_parecer)s,
         %(prever_json)s, %(parecer_json)s)
    ON CONFLICT (requisicao_id) DO NOTHING
    RETURNING decisao_id
"""
SQL_BY_REQUEST = "SELECT decisao_id FROM decisao_analista WHERE requisicao_id = %s"
SQL_ONE = f"SELECT {LISTING_COLUMNS} FROM decisao_analista WHERE decisao_id = %s"
SQL_LIST = f"SELECT {LISTING_COLUMNS} FROM decisao_analista ORDER BY registrada_em DESC, decisao_id DESC LIMIT %s"
SQL_LIST_BY_CONTRACT = (f"SELECT {LISTING_COLUMNS} FROM decisao_analista WHERE contrato_id = %s "
                       "ORDER BY registrada_em DESC, decisao_id DESC LIMIT %s")
# Colunas que o prever() lê (variáveis do modelo e as fontes das derivadas, src/modelos/variaveis.py).
# Lista fechada de propósito: nada da lista negra além do juro (o preço auditado) e da data.
CONTRACT_COLUMNS = {
    "e": ["loan_id", "data_emprestimo", "novo_cliente", "valor_solicitado", "valor_concedido", "juro_aa",
          "prazo_meses", "tipo_verificacao"],
    "c": ["pais", "escolaridade", "tempo_emprego_atual", "tipo_moradia", "renda_total", "renda_pensao",
          "renda_auxilio_familiar", "renda_assistencia_social", "renda_pensao_alimenticia"],
    "h": ["n_emprestimos_anteriores", "valor_emprestimos_anteriores", "pagamentos_anteriores",
          "quitacoes_antecipadas_valor", "quitacoes_antecipadas_qtd", "passivos_existentes", "passivos_total",
          "refinanciamento_passivos", "divida_renda", "caixa_livre", "score_es_microl", "score_es_equifax",
          "score_fi_asiakastieto", "score_ee_mini"],
}
SQL_CONTRACT = (
    "SELECT " + ", ".join(f"{alias}.{col}" for alias, cols in CONTRACT_COLUMNS.items() for col in cols)
    + " FROM emprestimo e JOIN cliente c ON c.loan_id = e.loan_id"
    + " LEFT JOIN historico_credito h ON h.loan_id = e.loan_id WHERE e.loan_id = %s"  # ID já normalizado no Python (usa a chave primária)
)
SQL_OUTCOME = ("SELECT inadimplente, recebido_total, resultado_eur, retorno_realizado, principal_perdido, "
               "duracao_meses FROM vw_retorno_realizado WHERE loan_id = %s")
# db/06 (Marcos, 13/11): uma linha por contrato, com o motivo quando não há desfecho
SQL_OUTCOME_STATUS = ("SELECT tem_desfecho, motivo_sem_desfecho, inadimplente, recebido_total, resultado_eur, "
                      "retorno_realizado, principal_perdido FROM vw_desfecho_contrato WHERE loan_id = %s")
SQL_BC_BY_CONTRACT = "SELECT bc_credito_pessoal_aa FROM vw_custo_do_dinheiro WHERE loan_id = %s"
SQL_BC_BY_MONTH = "SELECT taxa_aa FROM bc_credito_pessoal_mensal WHERE mes = date_trunc('month', %s::date)::date"
SQL_CURRENT = ("SELECT contrato_id, decisao_id, registrada_em, analista, decisao "
              "FROM vw_decisao_atual ORDER BY registrada_em DESC")


class DatabaseUnavailable(RuntimeError):
    """Não deu para conectar ao banco (serviço fora do ar ou tabela não criada)."""


class DecisionRejected(ValueError):
    """O banco recusou a decisão por uma regra da tabela (CHECK)."""


@contextmanager
def _connection():
    import psycopg2
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL", DEFAULT_URL), connect_timeout=3)
    except psycopg2.OperationalError as exc:
        raise DatabaseUnavailable(str(exc).strip()) from exc
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _cursor(conn):
    from psycopg2.extras import RealDictCursor
    return conn.cursor(cursor_factory=RealDictCursor)


def database_available() -> bool:
    """True se conecta e a tabela de decisões existe (para o GET / e o painel)."""
    try:
        with _connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.decisao_analista') IS NOT NULL")
            return bool(cur.fetchone()[0])
    except Exception:
        return False


def record_decision(record_: dict) -> dict:
    """Grava uma decisão e devolve a linha gravada. O mesmo requisicao_id não grava duas vezes."""
    import psycopg2
    from psycopg2.extras import Json

    values_ = {**record_,
               "requisicao_id": str(record_["requisicao_id"]) if record_.get("requisicao_id") else None,
               "prever_json": Json(record_["prever_json"]) if record_.get("prever_json") is not None else None,
               "parecer_json": Json(record_["parecer_json"]) if record_.get("parecer_json") is not None else None}
    try:
        with _connection() as conn, _cursor(conn) as cur:
            cur.execute(SQL_INSERT, values_)
            row = cur.fetchone()
            if row is None:  # clique repetido: devolve a decisão já gravada
                cur.execute(SQL_BY_REQUEST, (values_["requisicao_id"],))
                row = cur.fetchone()
            cur.execute(SQL_ONE, (row["decisao_id"],))
            return dict(cur.fetchone())
    except (psycopg2.errors.CheckViolation, psycopg2.errors.NotNullViolation,
            psycopg2.errors.RaiseException) as exc:
        raise DecisionRejected(exc.diag.message_primary or str(exc)) from exc
    except psycopg2.errors.UndefinedTable as exc:
        raise DatabaseUnavailable("tabela decisao_analista não existe: aplique db/05_decisoes_analista.sql") from exc


def list_decisions(contrato_id: str | None = None, limit: int = 200) -> list[dict]:
    import psycopg2
    try:
        with _connection() as conn, _cursor(conn) as cur:
            if contrato_id:
                cur.execute(SQL_LIST_BY_CONTRACT, (contrato_id, limit))
            else:
                cur.execute(SQL_LIST, (limit,))
            return [dict(row) for row in cur.fetchall()]
    except psycopg2.errors.UndefinedTable as exc:
        raise DatabaseUnavailable("tabela decisao_analista não existe: aplique db/05_decisoes_analista.sql") from exc


def current_decisions() -> list[dict]:
    """Decisão mais recente de cada contrato da carteira (vw_decisao_atual)."""
    import psycopg2
    try:
        with _connection() as conn, _cursor(conn) as cur:
            cur.execute(SQL_CURRENT)
            return [dict(row) for row in cur.fetchall()]
    except psycopg2.errors.UndefinedTable as exc:
        raise DatabaseUnavailable("view vw_decisao_atual não existe: aplique db/05_decisoes_analista.sql") from exc


def bc_rate(contrato_id: str | None = None, data_emprestimo: str | None = None) -> float | None:
    """Média do BC (crédito pessoal, % a.a. efetiva) no mês da concessão.

    Com data → mês da data (contratos do formulário). Sem data → pelo contrato na
    vw_custo_do_dinheiro (carteira e casos reais). Sem dado ou sem banco → None:
    o parecer só fica sem a frase de referência, nunca falha por isso.
    """
    try:
        with _connection() as conn, conn.cursor() as cur:
            if data_emprestimo:
                cur.execute(SQL_BC_BY_MONTH, (str(data_emprestimo)[:10],))
            elif contrato_id:
                cur.execute(SQL_BC_BY_CONTRACT, (contrato_id,))
            else:
                return None
            row = cur.fetchone()
            return float(row[0]) if row and row[0] is not None else None
    except Exception:
        return None


def _plain(value):
    """Decimal → float (o psycopg2 devolve NUMERIC como Decimal); o resto fica igual."""
    from decimal import Decimal
    return float(value) if isinstance(value, Decimal) else value


def normalize_id(contrato_id: str) -> str:
    """Combinado do loan_id (13/11): o banco guarda em minúsculas; normaliza aqui, nunca com
    lower(loan_id) na coluna (desligaria o índice). Depois da busca, o fluxo usa o loan_id do banco."""
    return (contrato_id or "").strip().lower()


def load_contract(contrato_id: str) -> dict | None:
    """Uma linha com tudo o que o prever() precisa, ou None se o contrato não existe no banco."""
    import psycopg2
    try:
        with _connection() as conn, _cursor(conn) as cur:
            cur.execute(SQL_CONTRACT, (normalize_id(contrato_id),))
            row = cur.fetchone()
    except psycopg2.errors.UndefinedTable as exc:
        raise DatabaseUnavailable("tabelas do Bondora não existem: aplique db/01 e rode a carga") from exc
    return None if row is None else {k: _plain(v) for k, v in row.items()}


def observed_outcome(contrato_id: str) -> dict | None:
    """O que aconteceu com o contrato (vw_retorno_realizado), ou None se ele não tem desfecho
    conhecido (concedido depois de 2016, ainda ativo, Eslováquia) ou a view não existe."""
    import psycopg2
    try:
        with _connection() as conn, _cursor(conn) as cur:
            cur.execute(SQL_OUTCOME, (normalize_id(contrato_id),))
            row = cur.fetchone()
    except psycopg2.errors.UndefinedTable:
        return None
    return None if row is None else {k: _plain(v) for k, v in row.items()}


def contract_outcome(loan_id: str) -> tuple[dict | None, str | None]:
    """(desfecho, motivo de não ter desfecho) pela vw_desfecho_contrato (db/06).

    Sem a view (banco montado antes de 13/11): cai na vw_retorno_realizado, sem o motivo."""
    import psycopg2
    try:
        with _connection() as conn, _cursor(conn) as cur:
            cur.execute(SQL_OUTCOME_STATUS, (normalize_id(loan_id),))
            row = cur.fetchone()
    except psycopg2.errors.UndefinedTable:
        return observed_outcome(loan_id), None
    if row is None:
        return None, None
    row = {k: _plain(v) for k, v in row.items()}
    if not row.pop("tem_desfecho"):
        return None, row.get("motivo_sem_desfecho")
    row.pop("motivo_sem_desfecho", None)
    return row, None

