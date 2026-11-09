"""Acesso da API ao banco (Marcos): decisões do analista e taxa média do BC.

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

URL_PADRAO = "postgresql://postgres:postgres@localhost:5432/auditor_db"

COLUNAS_LISTAGEM = (
    "decisao_id, registrada_em, contrato_id, origem, analista, decisao, justificativa, taxa_proposta, "
    "recomendacao_sistema, situacao_preco, pd, faixa, juro_cobrado, juro_justo, juro_justo_min, "
    "juro_justo_max, versao_modelo, versao_parecer, origem_parecer"
)

SQL_INSERIR = """
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
SQL_POR_REQUISICAO = "SELECT decisao_id FROM decisao_analista WHERE requisicao_id = %s"
SQL_UMA = f"SELECT {COLUNAS_LISTAGEM} FROM decisao_analista WHERE decisao_id = %s"
SQL_LISTAR = f"SELECT {COLUNAS_LISTAGEM} FROM decisao_analista ORDER BY registrada_em DESC, decisao_id DESC LIMIT %s"
SQL_LISTAR_CONTRATO = (f"SELECT {COLUNAS_LISTAGEM} FROM decisao_analista WHERE contrato_id = %s "
                       "ORDER BY registrada_em DESC, decisao_id DESC LIMIT %s")
SQL_BC_CONTRATO = "SELECT bc_credito_pessoal_aa FROM vw_custo_do_dinheiro WHERE loan_id = %s"
SQL_BC_MES = "SELECT taxa_aa FROM bc_credito_pessoal_mensal WHERE mes = date_trunc('month', %s::date)::date"
SQL_ATUAIS = ("SELECT contrato_id, decisao_id, registrada_em, analista, decisao "
              "FROM vw_decisao_atual ORDER BY registrada_em DESC")


class BancoIndisponivel(RuntimeError):
    """Não deu para conectar ao banco (serviço fora do ar ou tabela não criada)."""


class DecisaoRecusada(ValueError):
    """O banco recusou a decisão por uma regra da tabela (CHECK)."""


@contextmanager
def _conexao():
    import psycopg2
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL", URL_PADRAO), connect_timeout=3)
    except psycopg2.OperationalError as exc:
        raise BancoIndisponivel(str(exc).strip()) from exc
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


def banco_disponivel() -> bool:
    """True se conecta e a tabela de decisões existe (para o GET / e o painel)."""
    try:
        with _conexao() as conn, conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.decisao_analista') IS NOT NULL")
            return bool(cur.fetchone()[0])
    except Exception:
        return False


def registrar_decisao(registro: dict) -> dict:
    """Grava uma decisão e devolve a linha gravada. O mesmo requisicao_id não grava duas vezes."""
    import psycopg2
    from psycopg2.extras import Json

    valores = {**registro,
               "requisicao_id": str(registro["requisicao_id"]) if registro.get("requisicao_id") else None,
               "prever_json": Json(registro["prever_json"]) if registro.get("prever_json") is not None else None,
               "parecer_json": Json(registro["parecer_json"]) if registro.get("parecer_json") is not None else None}
    try:
        with _conexao() as conn, _cursor(conn) as cur:
            cur.execute(SQL_INSERIR, valores)
            linha = cur.fetchone()
            if linha is None:  # clique repetido: devolve a decisão já gravada
                cur.execute(SQL_POR_REQUISICAO, (valores["requisicao_id"],))
                linha = cur.fetchone()
            cur.execute(SQL_UMA, (linha["decisao_id"],))
            return dict(cur.fetchone())
    except (psycopg2.errors.CheckViolation, psycopg2.errors.NotNullViolation,
            psycopg2.errors.RaiseException) as exc:
        raise DecisaoRecusada(exc.diag.message_primary or str(exc)) from exc
    except psycopg2.errors.UndefinedTable as exc:
        raise BancoIndisponivel("tabela decisao_analista não existe: aplique db/05_decisoes_analista.sql") from exc


def listar_decisoes(contrato_id: str | None = None, limite: int = 200) -> list[dict]:
    import psycopg2
    try:
        with _conexao() as conn, _cursor(conn) as cur:
            if contrato_id:
                cur.execute(SQL_LISTAR_CONTRATO, (contrato_id, limite))
            else:
                cur.execute(SQL_LISTAR, (limite,))
            return [dict(linha) for linha in cur.fetchall()]
    except psycopg2.errors.UndefinedTable as exc:
        raise BancoIndisponivel("tabela decisao_analista não existe: aplique db/05_decisoes_analista.sql") from exc


def decisoes_atuais() -> list[dict]:
    """Decisão mais recente de cada contrato da carteira (vw_decisao_atual)."""
    import psycopg2
    try:
        with _conexao() as conn, _cursor(conn) as cur:
            cur.execute(SQL_ATUAIS)
            return [dict(linha) for linha in cur.fetchall()]
    except psycopg2.errors.UndefinedTable as exc:
        raise BancoIndisponivel("view vw_decisao_atual não existe: aplique db/05_decisoes_analista.sql") from exc


def taxa_bc(contrato_id: str | None = None, data_emprestimo: str | None = None) -> float | None:
    """Média do BC (crédito pessoal, % a.a. efetiva) no mês da concessão.

    Com data → mês da data (contratos do formulário). Sem data → pelo contrato na
    vw_custo_do_dinheiro (carteira e casos reais). Sem dado ou sem banco → None:
    o parecer só fica sem a frase de referência, nunca falha por isso.
    """
    try:
        with _conexao() as conn, conn.cursor() as cur:
            if data_emprestimo:
                cur.execute(SQL_BC_MES, (str(data_emprestimo)[:10],))
            elif contrato_id:
                cur.execute(SQL_BC_CONTRATO, (contrato_id,))
            else:
                return None
            linha = cur.fetchone()
            return float(linha[0]) if linha and linha[0] is not None else None
    except Exception:
        return None
