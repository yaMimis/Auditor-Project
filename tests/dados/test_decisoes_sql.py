"""O SQL da tabela de decisões (db/05_decisoes_analista.sql) tem que contar a mesma história que
o código: os domínios iguais aos do validacao.py e aos da API, e as proteções de privacidade e
de auditoria presentes. Sem banco: lê o texto do SQL.
"""
import re
from pathlib import Path

from src.dados import validacao as v

SQL = Path(__file__).resolve().parents[2] / "db" / "05_decisoes_analista.sql"


def _sql() -> str:
    return SQL.read_text(encoding="utf-8")


def _sem_comentarios(texto: str) -> str:
    return re.sub(r"--.*$", "", texto, flags=re.M)


def _dominios() -> dict[str, set[str]]:
    """Cada CHECK (coluna IN ('a', 'b', ...)) do SQL vira {coluna: {a, b, ...}}."""
    achados = {}
    for coluna, lista in re.findall(r"CHECK \((\w+) IN \(([^)]*)\)\)", _sem_comentarios(_sql())):
        achados[coluna] = set(re.findall(r"'([^']*)'", lista))
    return achados


def _criar_tabela() -> str:
    sem = _sem_comentarios(_sql())
    inicio = sem.index("CREATE TABLE IF NOT EXISTS decisao_analista")
    return sem[inicio:sem.index(");", inicio)]


def test_dominios_do_sql_sao_os_do_codigo():
    d = _dominios()
    esperado = {"origem": v.ORIGENS_DECISAO, "decisao": v.DECISOES_ANALISTA,
                "recomendacao_sistema": v.RECOMENDACOES, "situacao_preco": v.SITUACOES_PRECO,
                "faixa": ["A", "B", "C", "D", "E"], "origem_parecer": ["llm", "template"]}
    for coluna, valores in esperado.items():
        assert d.get(coluna) == set(valores), f"{coluna}: SQL {d.get(coluna)} x código {set(valores)}"


def test_dominios_do_sql_sao_os_da_api():
    """Se a API mudar um valor (src/api/schemas.py), este teste avisa que o banco precisa mudar."""
    try:
        from typing import get_args

        from src.api.schemas import ParecerIA, RespostaPrever
    except ImportError:          # pydantic não instalado neste ambiente
        return

    def valores(modelo, campo):
        campos = getattr(modelo, "model_fields", None) or modelo.__fields__
        info = campos[campo]
        anotacao = getattr(info, "annotation", None) or info.outer_type_
        return set(get_args(anotacao))

    d = _dominios()
    assert d["situacao_preco"] == valores(RespostaPrever, "situacao_preco")
    assert d["faixa"] == valores(RespostaPrever, "faixa")
    assert d["recomendacao_sistema"] == valores(ParecerIA, "recomendacao")
    assert d["origem_parecer"] == valores(ParecerIA, "origem")


def test_nao_ha_coluna_de_genero_nem_idade():
    tabela = _criar_tabela().lower()
    for nome in ("genero", "idade", "gender", "age "):
        assert not re.search(rf"^\s*{nome.strip()}\s", tabela, flags=re.M), f"coluna {nome!r} não pode existir"


def test_json_recusa_genero_e_idade():
    sem = _sem_comentarios(_sql())
    for coluna in ("prever_json", "parecer_json"):
        assert re.search(rf"{coluna} IS NULL OR NOT \({coluna} \?\| ARRAY\[", sem), coluna
    for chave in v.CHAVES_PROIBIDAS_NO_JSON:
        assert f"'{chave}'" in sem, f"a chave {chave!r} deveria estar na lista proibida do SQL"


def test_protecoes_de_auditoria_presentes():
    sem = _sem_comentarios(_sql())
    assert "BEFORE UPDATE OR DELETE ON decisao_analista" in sem      # só inclusão
    assert "BEFORE TRUNCATE ON decisao_analista" in sem
    assert "BEFORE INSERT ON decisao_analista" in sem                # data do servidor e origem
    assert "NEW.registrada_em := now()" in sem
    assert "DISTINCT ON (contrato_id)" in sem                         # vw_decisao_atual
    assert "ON decisao_analista (contrato_id, registrada_em DESC)" in sem


def test_colunas_do_sql_sao_as_do_esquema_de_validacao():
    colunas_sql = set(re.findall(r"^\s{4}(\w+)\s+(?:BIGINT|TIMESTAMPTZ|UUID|TEXT|DOUBLE|JSONB)", _criar_tabela(), flags=re.M))
    esquema = set(v._regras_erro()["decisao_analista"])
    assert colunas_sql == esquema, f"só no SQL {sorted(colunas_sql - esquema)}; só na validação {sorted(esquema - colunas_sql)}"
