#!/usr/bin/env python3
"""Validação dos dados do Bondora no banco, com pandera.

Uso (na raiz do projeto, com o banco no ar e o .env preenchido):
    python src/dados/validacao.py
    python src/dados/validacao.py --parcial         # banco de desenvolvimento (poucas linhas)
    python src/dados/validacao.py --saida qualidade.csv

O que faz:
  * lê do banco, com pd.read_sql, as tabelas emprestimo, cliente, historico_credito,
    euribor_mensal, selic_mensal, bc_credito_pessoal_mensal, decisao_analista (decisões do
    analista) e as views vw_base_modelagem, vw_retorno_realizado, vw_desfecho_contrato e
    vw_decisao_atual;
  * valida cada tabela com um esquema do pandera, com lazy=True: todas as violações
    saem de uma vez, em vez de parar na primeira;
  * separa as regras em dois níveis:
      - ERRO: a regra é do contrato dos dados (chaves, domínios, datas, contagens).
        Se houver violação, o programa sai com código 1 (serve para o CI e o pytest).
      - ALERTA: a violação é conhecida e vira registro no relatório de qualidade,
        sem falhar (por exemplo, idade menor que 18);
  * confere o que cruza tabelas (mesmos loan_id, meses de Euribor e Selic para cada
    contrato, contagens da view e clientes do treino fora do teste).

As regras seguem o DATA.md (seções 6 e 7). Os esquemas das três tabelas do Bondora são
gerados a partir do mapeamento da carga (carga_bondora.TABELAS): se alguém acrescentar
ou tirar uma coluna lá e não aqui, o esquema acusa (strict=True).

Para testes sem banco, use validar_tabelas(dict_de_dataframes, parcial=True). O DataFrame de
cada tabela precisa ter TODAS as colunas (coluna faltando é erro); estrito=False só deixa
passar colunas a mais.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

import pandas as pd

try:                                    # pandera >= 0.24
    import pandera.pandas as pa
except ImportError:                     # versões antigas
    import pandera as pa
from pandera.errors import SchemaErrors

try:                                    # importado como pacote (pytest, a partir da raiz)
    from src.dados.carga_bondora import TABELAS, _carregar_env
except ImportError:                     # executado como script: python src/dados/validacao.py
    from carga_bondora import TABELAS, _carregar_env

# --------------------------------------------------------------------------
# Constantes do projeto (DATA.md)
# --------------------------------------------------------------------------
JANELA_INI = pd.Timestamp("2009-01-01")      # concessões do Bondora: 02/2009 a 07/2021
JANELA_FIM = pd.Timestamp("2021-07-01")
BC_INI = pd.Timestamp("2011-03-01")          # a série 20742 do BC começa em 03/2011
N_CONTRATOS = 179_235                        # versão do arquivo (SHA-256 no DATA.md)
BASE_ESPERADA = {"treino": 20_011, "teste": 7_311, "fora_cliente_repetido": 2_594}

GUID = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
HEX16 = r"^[0-9a-f]{16}$"
FINALIDADES = list(range(0, 9)) + list(range(101, 111))
# decisões do analista (db/05_decisoes_analista.sql; os mesmos valores de src/api/schemas.py)
DECISOES_ANALISTA = ["manter_preco", "revisar_preco", "encaminhar_compliance"]
RECOMENDACOES = DECISOES_ANALISTA + ["revisao_manual"]
SITUACOES_PRECO = ["acima_do_justo", "abaixo_do_justo", "dentro_da_margem", "revisao_manual"]
ORIGENS_DECISAO = ["carteira", "simulacao"]
CHAVES_PROIBIDAS_NO_JSON = ("genero", "idade", "gender", "age")   # gênero e idade nunca entram no registro
# motivos da vw_desfecho_contrato (db/06), na ordem em que o SQL testa (os filtros do db/03)
MOTIVOS_SEM_DESFECHO = ["concedido depois de 2016", "Eslováquia (fora da base)",
                        "não encerrado até o corte de 20/07/2021"]
TABELAS_MACRO = ("euribor_mensal", "selic_mensal", "bc_credito_pessoal_mensal")
DATAS_BONDORA = ("data_referencia", "data_pedido", "data_emprestimo", "data_primeira_parcela",
                 "data_vencimento_original", "data_vencimento_atual", "data_fim_contrato",
                 "data_default", "data_ultimo_pagamento")
CHAVES = {"emprestimo": "loan_id", "cliente": "loan_id", "historico_credito": "loan_id",
          "euribor_mensal": "mes", "selic_mensal": "mes",
          "bc_credito_pessoal_mensal": "mes", "vw_base_modelagem": "loan_id",
          "vw_retorno_realizado": "loan_id", "vw_desfecho_contrato": "loan_id",
          "decisao_analista": "decisao_id",
          "vw_decisao_atual": "contrato_id"}
DATAS_EXTRAS = {"decisao_analista": ["registrada_em"], "vw_decisao_atual": ["registrada_em"]}


# --------------------------------------------------------------------------
# Atalhos para escrever as regras
# --------------------------------------------------------------------------
_NOMES_LINHA: set[str] = set()     # nomes das regras que olham a linha inteira (várias colunas)


def _col(nulo: bool = True, unico: bool = False, *checks) -> "pa.Column":
    return pa.Column(nullable=nulo, unique=unico, checks=list(checks))


def _linha(nome: str, colunas: tuple[str, ...], fn) -> "pa.Check":
    """Regra que olha várias colunas. O fn recebe o DataFrame inteiro e devolve
    uma Series de booleanos, tratando os vazios por conta própria (ignore_na=False,
    senão o pandera ignora a linha inteira quando QUALQUER coluna está vazia).
    Se uma coluna não existir (tabela parcial), a regra passa."""
    _NOMES_LINHA.add(nome)

    def seguro(df):
        if not all(c in df.columns for c in colunas):
            return pd.Series(True, index=df.index)
        return fn(df)
    return pa.Check(seguro, name=nome, error=nome, ignore_na=False)


def _ate(a: str, b: str, tolerancia_dias: int = 0, nome: str | None = None) -> "pa.Check":
    """a <= b (+ tolerância); vazio em qualquer lado passa."""
    tol = pd.Timedelta(days=tolerancia_dias)
    return _linha(nome or f"{a} <= {b}", (a, b),
                  lambda df: df[a].isna() | df[b].isna() | (df[a] <= df[b] + tol))


def _nao_vazio() -> "pa.Check":
    return pa.Check(lambda s: s.astype(str).str.strip().str.len() > 0, name="nao_vazio", error="nao_vazio")


def _tem_chave_proibida(valor) -> bool:
    """True se o JSON (dict, lista ou texto JSON) tem gênero ou idade em QUALQUER nível."""
    if isinstance(valor, str):
        try:
            valor = json.loads(valor)
        except ValueError:
            return False
    if isinstance(valor, dict):
        return any(str(k).lower() in CHAVES_PROIBIDAS_NO_JSON or _tem_chave_proibida(v)
                   for k, v in valor.items())
    if isinstance(valor, (list, tuple)):
        return any(_tem_chave_proibida(v) for v in valor)
    return False


def _inteiro() -> "pa.Check":
    return pa.Check(lambda s: s % 1 == 0, name="valor_inteiro", error="valor_inteiro")


def _dia_1() -> "pa.Check":
    return pa.Check(lambda s: s.dt.day == 1, name="primeiro_dia_do_mes", error="primeiro_dia_do_mes")


def _maior_que(v, nome=None):
    return pa.Check.greater_than(v, name=nome) if nome else pa.Check.greater_than(v)


# --------------------------------------------------------------------------
# Regras de ERRO por tabela (todas medidas nos dados reais: 0 violações hoje)
# --------------------------------------------------------------------------
def _regras_erro() -> dict[str, dict[str, "pa.Column"]]:
    ge0 = pa.Check.greater_than_or_equal_to(0)
    emp = {
        "loan_id": _col(False, True, pa.Check.str_matches(GUID)),
        "numero": _col(False, True),
        "status": _col(False, False, pa.Check.isin(["Current", "Late", "Repaid"])),
        "data_referencia": _col(False),
        "data_pedido": _col(False),
        "data_emprestimo": _col(False, False, pa.Check.greater_than_or_equal_to(JANELA_INI)),
        "data_primeira_parcela": _col(False),
        "data_vencimento_original": _col(False),
        "valor_solicitado": _col(False, False, _maior_que(0)),
        "valor_concedido": _col(False, False, _maior_que(0)),
        "juro_aa": _col(False, False, _maior_que(0)),
        "prazo_meses": _col(False, False, pa.Check.in_range(1, 60), _inteiro()),
        "finalidade": _col(True, False, pa.Check.isin(FINALIDADES)),
        "tipo_verificacao": _col(True, False, pa.Check.isin([0, 1, 2, 3, 4])),
        "rating": _col(True, False, pa.Check.isin(["AA", "A", "B", "C", "D", "E", "F", "HR"])),
        "versao_modelo_bondora": _col(True, False, pa.Check.isin([0, 1, 2, 3, 4, 5, 6, 99])),
        "pd_bondora": _col(True, False, pa.Check.in_range(0, 1)),
        "lgd_bondora": _col(True, False, pa.Check.in_range(0, 1)),
        "dias_atraso": _col(True, False, ge0),
        "estagio_recuperacao": _col(True, False, pa.Check.isin([1, 2])),
    }
    cli = {
        "loan_id": _col(False, True, pa.Check.str_matches(GUID)),
        "cliente_id": _col(False, False, pa.Check.str_matches(HEX16)),
        "genero": _col(True, False, pa.Check.isin([0, 1, 2])),
        "idade": _col(True, False, pa.Check.in_range(0, 100)),
        "pais": _col(False, False, pa.Check.isin(["EE", "ES", "FI", "SK"])),
        "escolaridade": _col(True, False, pa.Check.isin([0, 1, 2, 3, 4, 5])),
        "estado_civil": _col(True, False, pa.Check.isin([0, 1, 2, 3, 4, 5])),
        "n_dependentes": _col(True, False, pa.Check.in_range(0, 10)),
        "situacao_emprego": _col(True, False, pa.Check.isin([0, 1, 2, 3, 4, 5, 6])),
        "area_ocupacao": _col(True, False, pa.Check.in_range(0, 19)),
        "tipo_moradia": _col(True, False, pa.Check.in_range(0, 10)),
    }
    for c in ("renda_empregador_principal", "renda_pensao", "renda_auxilio_familiar",
              "renda_assistencia_social", "renda_licenca", "renda_pensao_alimenticia",
              "renda_outras", "renda_total"):
        cli[c] = _col(True, False, ge0)
    hist = {
        "loan_id": _col(False, True, pa.Check.str_matches(GUID)),
        "n_emprestimos_anteriores": _col(True, False, ge0),
        "passivos_total": _col(True, False, ge0),
        "divida_renda": _col(True, False, ge0),
        "score_es_equifax": _col(True, False, pa.Check.isin(["AAA", "AA", "A", "B", "C", "D"])),
    }
    macro_mes = _col(False, True, _dia_1())
    return {
        "emprestimo": emp, "cliente": cli, "historico_credito": hist,
        "euribor_mensal": {"mes": macro_mes,
                           "euribor_3m": _col(False, False, pa.Check.in_range(-1, 5)),
                           "euribor_12m": _col(False, False, pa.Check.in_range(-1, 5))},
        "selic_mensal": {"mes": macro_mes,
                         "selic_aa": _col(False, False, pa.Check.in_range(0, 20)),
                         "selic_meta_aa": _col(True, False, pa.Check.in_range(0, 20))},
        "bc_credito_pessoal_mensal": {"mes": macro_mes,
                                      "taxa_aa": _col(False, False, _maior_que(0))},
        "vw_base_modelagem": {
            "loan_id": _col(False, True, pa.Check.str_matches(GUID)),
            "cliente_id": _col(False, False, pa.Check.str_matches(HEX16)),
            "pais": _col(False, False, pa.Check.isin(["EE", "ES", "FI"])),
            "ano": _col(False, False, pa.Check.in_range(2009, 2016)),
            "inadimplente": _col(False, False, pa.Check.isin([0, 1])),
            "reestruturado": _col(True),
            "conjunto": _col(False, False, pa.Check.isin(["treino", "teste", "fora_cliente_repetido"])),
        },
        "decisao_analista": {
            "decisao_id": _col(False, True),
            "registrada_em": _col(False),
            "requisicao_id": _col(True),                       # único no banco; vazio é permitido
            "contrato_id": _col(False),
            "origem": _col(False, False, pa.Check.isin(ORIGENS_DECISAO)),
            "analista": _col(False, False, _nao_vazio()),
            "decisao": _col(False, False, pa.Check.isin(DECISOES_ANALISTA)),
            "justificativa": _col(False, False, _nao_vazio()),
            "taxa_proposta": _col(True, False, _maior_que(0), pa.Check.less_than_or_equal_to(10)),
            "recomendacao_sistema": _col(True, False, pa.Check.isin(RECOMENDACOES)),
            "situacao_preco": _col(False, False, pa.Check.isin(SITUACOES_PRECO)),
            "pd": _col(True, False, pa.Check.in_range(0, 1)),
            "faixa": _col(True, False, pa.Check.isin(["A", "B", "C", "D", "E"])),
            "juro_cobrado": _col(False, False, pa.Check.in_range(0, 10)),
            "juro_justo": _col(True, False, pa.Check.in_range(0, 10)),
            "juro_justo_min": _col(True, False, pa.Check.in_range(0, 10)),
            "juro_justo_max": _col(True, False, pa.Check.in_range(0, 10)),
            "versao_modelo": _col(False, False, _nao_vazio()),
            "versao_parecer": _col(True),
            "origem_parecer": _col(True, False, pa.Check.isin(["llm", "template"])),
            "prever_json": _col(True),
            "parecer_json": _col(True),
        },
        "vw_decisao_atual": {
            "decisao_id": _col(False, True),
            "contrato_id": _col(False, True),
            "registrada_em": _col(False),
            "analista": _col(False, False, _nao_vazio()),
            "decisao": _col(False, False, pa.Check.isin(DECISOES_ANALISTA)),
            "justificativa": _col(False, False, _nao_vazio()),
            "taxa_proposta": _col(True, False, _maior_que(0), pa.Check.less_than_or_equal_to(10)),
            "recomendacao_sistema": _col(True, False, pa.Check.isin(RECOMENDACOES)),
            "situacao_preco": _col(False, False, pa.Check.isin(SITUACOES_PRECO)),
        },
        "vw_retorno_realizado": {
            "loan_id": _col(False, True, pa.Check.str_matches(GUID)),
            "ano": _col(False, False, pa.Check.in_range(2009, 2016)),
            "pais": _col(False, False, pa.Check.isin(["EE", "ES", "FI"])),
            "conjunto": _col(False, False, pa.Check.isin(["treino", "teste", "fora_cliente_repetido"])),
            "reestruturado": _col(True),
            "inadimplente": _col(False, False, pa.Check.isin([0, 1])),
            "valor_concedido": _col(False, False, _maior_que(0)),
            "prazo_meses": _col(False, False, pa.Check.in_range(1, 60)),
            "juro_aa": _col(False, False, _maior_que(0)),
            "duracao_meses": _col(True, False, ge0),
            "principal_recebido": _col(False, False, ge0),
            "juros_recebidos": _col(False, False, ge0),
            "recebido_total": _col(False, False, ge0),
            "resultado_eur": _col(False),
            "retorno_realizado": _col(False, False, pa.Check.in_range(-1, 10)),
            "principal_perdido": _col(False, False, ge0),
            "recuperado_eur": _col(False, False, ge0),
        },
        # uma linha por contrato de emprestimo; as colunas do desfecho ficam vazias sem desfecho
        "vw_desfecho_contrato": {
            "loan_id": _col(False, True, pa.Check.str_matches(GUID)),
            "ano": _col(False, False, pa.Check.in_range(2009, 2021)),
            "pais": _col(False, False, pa.Check.isin(["EE", "ES", "FI", "SK"])),
            "tem_desfecho": _col(False),
            "motivo_sem_desfecho": _col(True, False, pa.Check.isin(MOTIVOS_SEM_DESFECHO)),
            "inadimplente": _col(True, False, pa.Check.isin([0, 1])),
            "valor_concedido": _col(True, False, _maior_que(0)),
            "recebido_total": _col(True, False, ge0),
            "resultado_eur": _col(True),
            "retorno_realizado": _col(True, False, pa.Check.in_range(-1, 10)),
            "principal_perdido": _col(True, False, ge0),
            "conjunto": _col(True, False, pa.Check.isin(["treino", "teste", "fora_cliente_repetido"])),
            "reestruturado": _col(True),
        },
    }


def _checks_linha_erro() -> dict[str, list]:
    return {
        "emprestimo": [
            _ate("data_pedido", "data_emprestimo", 1, "data_pedido <= data_emprestimo (+1 dia)"),
            _ate("data_emprestimo", "data_primeira_parcela"),
            _ate("data_primeira_parcela", "data_vencimento_original"),
            _ate("data_emprestimo", "data_referencia"),
            _ate("data_emprestimo", "data_default"),
            _ate("data_default", "data_referencia"),
            _ate("data_emprestimo", "data_fim_contrato"),
            _ate("data_emprestimo", "data_ultimo_pagamento"),
        ],
        "decisao_analista": [
            _linha("JSON sem genero nem idade", ("prever_json", "parecer_json"),
                   lambda df: ~df["prever_json"].map(_tem_chave_proibida).astype(bool)
                   & ~df["parecer_json"].map(_tem_chave_proibida).astype(bool)),
            _linha("numeros obrigatorios fora de revisao_manual",
                   ("situacao_preco", "pd", "faixa", "juro_justo", "juro_justo_min", "juro_justo_max"),
                   lambda df: (df["situacao_preco"] == "revisao_manual")
                   | df[["pd", "faixa", "juro_justo", "juro_justo_min", "juro_justo_max"]].notna().all(axis=1)),
            _linha("registrada_em nao esta no futuro", ("registrada_em",),
                   lambda df: pd.to_datetime(df["registrada_em"], utc=True)
                   <= pd.Timestamp.now(tz="UTC") + pd.Timedelta(days=1)),
        ],
        "vw_retorno_realizado": [
            _linha("recebido_total = principal_recebido + juros_recebidos",
                   ("recebido_total", "principal_recebido", "juros_recebidos"),
                   lambda df: (df["recebido_total"] - df["principal_recebido"] - df["juros_recebidos"]).abs() <= 0.02),
            _linha("resultado_eur = recebido_total - valor_concedido",
                   ("resultado_eur", "recebido_total", "valor_concedido"),
                   lambda df: (df["resultado_eur"] - (df["recebido_total"] - df["valor_concedido"])).abs() <= 0.02),
            _linha("principal_perdido <= valor_concedido", ("principal_perdido", "valor_concedido"),
                   lambda df: df["principal_perdido"] <= df["valor_concedido"] + 0.01),
            # as recuperações já estão dentro dos pagamentos: se passarem do recebido, a definição quebrou
            _linha("recuperado_eur <= recebido_total (recuperacao ja esta nos pagamentos)",
                   ("recuperado_eur", "recebido_total"),
                   lambda df: df["recuperado_eur"] <= df["recebido_total"] + 0.01),
        ],
        "vw_desfecho_contrato": [
            _linha("motivo_sem_desfecho vazio so quando ha desfecho", ("tem_desfecho", "motivo_sem_desfecho"),
                   lambda df: df["tem_desfecho"].astype(bool) == df["motivo_sem_desfecho"].isna()),
            _linha("inadimplente so preenchido quando ha desfecho", ("tem_desfecho", "inadimplente"),
                   lambda df: df["tem_desfecho"].astype(bool) == df["inadimplente"].notna()),
        ],
        "vw_base_modelagem": [
            _linha("treino so com concessoes ate 2015", ("conjunto", "ano"),
                   lambda df: (df["conjunto"] != "treino") | (df["ano"] <= 2015)),
            _linha("teste so com concessoes de 2016", ("conjunto", "ano"),
                   lambda df: (df["conjunto"] != "teste") | (df["ano"] == 2016)),
        ],
    }


# --------------------------------------------------------------------------
# Regras de ALERTA (violações conhecidas: entram no relatório, não falham)
# --------------------------------------------------------------------------
def _regras_alerta() -> dict[str, dict[str, "pa.Column"]]:
    return {
        "emprestimo": {
            "prazo_meses": _col(True, False, pa.Check.greater_than_or_equal_to(3)),
            "parcela_mensal": _col(True, False, _maior_que(0)),
            "saldo_principal": _col(True, False, pa.Check.greater_than_or_equal_to(0)),
            "perda_esperada_bondora": _col(True, False, pa.Check.in_range(0, 1)),
        },
        "cliente": {
            "idade": _col(True, False, pa.Check.greater_than_or_equal_to(18)),
            "renda_total": _col(True, False, _maior_que(0)),
        },
        "historico_credito": {
            "caixa_livre": _col(True, False, pa.Check.greater_than_or_equal_to(0)),
            "divida_renda": _col(True, False, pa.Check.less_than_or_equal_to(100)),
        },
        "bc_credito_pessoal_mensal": {"taxa_aa": _col(False, False, pa.Check.in_range(30, 200))},
    }


def _checks_linha_alerta() -> dict[str, list]:
    meses = pd.Timedelta(days=61)
    return {"decisao_analista": [
        _linha("juro_justo entre juro_justo_min e juro_justo_max", ("juro_justo", "juro_justo_min", "juro_justo_max"),
               lambda df: df["juro_justo"].isna()
               | ((df["juro_justo_min"] <= df["juro_justo"]) & (df["juro_justo"] <= df["juro_justo_max"]))),
        _linha("revisar_preco traz taxa_proposta", ("decisao", "taxa_proposta"),
               lambda df: (df["decisao"] != "revisar_preco") | df["taxa_proposta"].notna()),
    ], "emprestimo": [
        _linha("valor_concedido <= valor_solicitado", ("valor_concedido", "valor_solicitado"),
               lambda df: df["valor_concedido"].isna() | df["valor_solicitado"].isna()
               | (df["valor_concedido"] <= df["valor_solicitado"] + 0.015)),
        _linha("vencimento original = concessao + prazo (tolerancia de 2 meses)",
               ("data_vencimento_original", "data_emprestimo", "prazo_meses"),
               lambda df: df["data_vencimento_original"].isna() | df["data_emprestimo"].isna()
               | df["prazo_meses"].isna()
               | (((df["data_vencimento_original"] - df["data_emprestimo"]).dt.days / 30.44
                   - df["prazo_meses"]).abs() <= 2)),
        _linha("Current nao tem data_default", ("status", "data_default"),
               lambda df: (df["status"] != "Current") | df["data_default"].isna()),
        _linha("Repaid nao tem saldo_principal", ("status", "saldo_principal"),
               lambda df: (df["status"] != "Repaid") | df["saldo_principal"].isna()
               | (df["saldo_principal"] <= 0.5)),
    ]}


# --------------------------------------------------------------------------
# Montagem dos esquemas
# --------------------------------------------------------------------------
def _colunas_do_banco(tabela: str) -> list[str]:
    return [c.db for c in TABELAS[tabela]]


def esquema_erro(tabela: str, estrito: bool = True) -> "pa.DataFrameSchema":
    regras = _regras_erro()[tabela]
    if tabela in TABELAS:                       # as três tabelas do Bondora: colunas da carga
        colunas = {c: pa.Column(nullable=True) for c in _colunas_do_banco(tabela)}
    else:
        colunas = {}
    colunas.update(regras)
    return pa.DataFrameSchema(colunas, checks=_checks_linha_erro().get(tabela, []),
                              strict=estrito, name=f"{tabela} (erro)")


def esquema_alerta(tabela: str) -> "pa.DataFrameSchema | None":
    colunas = _regras_alerta().get(tabela, {})
    checks = _checks_linha_alerta().get(tabela, [])
    if not colunas and not checks:
        return None
    return pa.DataFrameSchema(colunas, checks=checks, strict=False, name=f"{tabela} (alerta)")


# --------------------------------------------------------------------------
# Execução
# --------------------------------------------------------------------------
COLUNAS_RESULTADO = ["severidade", "tabela", "coluna", "regra", "violacoes", "exemplos"]

# Coluna que sumiu ou sobrou no banco: o pandera guarda o NOME da coluna no failure_case,
# e deixa o campo "column" vazio.
ESTRUTURA = {"column_in_dataframe": "coluna ausente no banco",
             "column_in_schema": "coluna a mais no banco (fora do esquema)"}


def _nome_da_coluna(caso, coluna) -> str:
    if isinstance(caso, (list, tuple, set)):
        return ", ".join(str(x) for x in caso)
    if caso is not None and not (isinstance(caso, float) and pd.isna(caso)):
        return str(caso)
    return str(coluna) if coluna is not None and not pd.isna(coluna) else "(tabela)"


def _vazio() -> pd.DataFrame:
    return pd.DataFrame(columns=COLUNAS_RESULTADO)


def _coletar(df: pd.DataFrame, esquema, tabela: str, severidade: str) -> list[dict]:
    """Roda o esquema com lazy=True e resume as violações por coluna e regra."""
    try:
        esquema.validate(df, lazy=True)
        return []
    except SchemaErrors as erro:
        fc = erro.failure_cases
    chave = CHAVES.get(tabela, "")
    saida = []
    fc = fc.assign(_chk=fc["check"].astype(str))
    # O pandera reporta uma regra de linha (várias colunas) uma vez para CADA coluna da
    # tabela; aqui ela vira uma só, com a contagem de linhas distintas.
    fc["_col"] = fc["column"].fillna("(linha)").astype(str).where(~fc["_chk"].isin(_NOMES_LINHA), "(linha)")
    estrutura = fc["_chk"].isin(ESTRUTURA)
    if estrutura.any():
        fc.loc[estrutura, "_col"] = [_nome_da_coluna(caso, col) for caso, col in
                                     zip(fc.loc[estrutura, "failure_case"], fc.loc[estrutura, "column"])]
    for (col, regra), g in fc.groupby(["_col", "_chk"]):
        idx = g["index"].dropna()
        n = int(idx.nunique()) if len(idx) else int(len(g))
        exemplos = ""
        if len(idx) and chave in df.columns:
            alvo = idx.drop_duplicates().head(3).tolist()
            exemplos = ", ".join(str(v) for v in df.loc[alvo, chave].tolist())
        saida.append({"severidade": severidade, "tabela": tabela, "coluna": col,
                      "regra": ESTRUTURA.get(regra, regra), "violacoes": n, "exemplos": exemplos})
    return saida


def _janela(df: pd.DataFrame, tabela: str) -> pd.DataFrame:
    """As tabelas de séries guardam o histórico inteiro; valida só a janela do projeto."""
    ini = BC_INI if tabela == "bc_credito_pessoal_mensal" else JANELA_INI
    if "mes" not in df.columns:
        return df
    return df[(df["mes"] >= ini) & (df["mes"] <= JANELA_FIM)].reset_index(drop=True)


def _razao_renda_2009_2010(e, c) -> float | None:
    """Mediana da renda (Estônia) em 2009–2010 dividida pela de 2011–2012. Em coroas sem
    conversão a razão é cerca de 14; convertida, cerca de 0,9. Sem dados suficientes, None."""
    if e is None or c is None or "data_emprestimo" not in e.columns \
            or not {"pais", "renda_total"} <= set(c.columns):
        return None
    d = e[["loan_id", "data_emprestimo"]].merge(c[["loan_id", "pais", "renda_total"]], on="loan_id")
    d = d[(d["pais"] == "EE") & (d["renda_total"] > 0)]
    ano = d["data_emprestimo"].dt.year
    antes, depois = d.loc[ano <= 2010, "renda_total"], d.loc[ano.isin([2011, 2012]), "renda_total"]
    if len(antes) < 30 or len(depois) < 30:
        return None
    return float(antes.median() / depois.median())


def _cruzamentos(t: dict[str, pd.DataFrame], parcial: bool) -> list[dict]:
    saida = []

    def erro(regra, n, exemplos=""):
        if n:
            saida.append({"severidade": "erro", "tabela": "(cruzamento)", "coluna": "",
                          "regra": regra, "violacoes": int(n), "exemplos": exemplos})

    e, c, h = t.get("emprestimo"), t.get("cliente"), t.get("historico_credito")
    if e is not None and c is not None and h is not None:
        ids = {k: set(df["loan_id"].dropna()) for k, df in (("e", e), ("c", c), ("h", h))}
        erro("loan_id só em emprestimo ou só em cliente", len(ids["e"] ^ ids["c"]))
        erro("loan_id só em emprestimo ou só em historico_credito", len(ids["e"] ^ ids["h"]))
        if not parcial:
            erro(f"nº de contratos diferente de {N_CONTRATOS:,}".replace(",", "."),
                 abs(len(e) - N_CONTRATOS), f"há {len(e):,}".replace(",", "."))
    # moeda: a renda de 2009–2010 não pode estar em outra unidade que a de 2011–2012
    razao = _razao_renda_2009_2010(e, c)
    if razao is not None and (razao > 3 or razao < 1 / 3):
        erro("renda de 2009–2010 em outra unidade (coroas?): rode a carga com a correção de moeda",
             1, f"mediana 2009–2010 / 2011–2012 = {razao:.1f} (esperado perto de 1)")
    # cobertura das séries na janela do projeto e nos meses de concessão
    if e is not None and "data_emprestimo" in e.columns:
        meses_contrato = e["data_emprestimo"].dropna().dt.to_period("M").dt.to_timestamp()
        for tabela, colunas, ini in (("euribor_mensal", ("euribor_3m", "euribor_12m"), JANELA_INI),
                                     ("selic_mensal", ("selic_aa",), JANELA_INI),
                                     ("bc_credito_pessoal_mensal", ("taxa_aa",), BC_INI)):
            s = t.get(tabela)
            if s is None or not all(col in s.columns for col in colunas):
                continue
            com_valor = s.dropna(subset=list(colunas))["mes"]
            esperados = pd.date_range(ini, JANELA_FIM, freq="MS")
            faltam = esperados.difference(pd.DatetimeIndex(com_valor))
            erro(f"{tabela}: meses da janela sem valor", len(faltam),
                 ", ".join(d.strftime("%Y-%m") for d in faltam[:3]))
            precisa = meses_contrato[meses_contrato >= ini]
            erro(f"{tabela}: contratos sem o valor do mês da concessão",
                 int((~precisa.isin(com_valor)).sum()))
    # decisões do analista: origem coerente com a carteira e view da decisão atual
    d, va = t.get("decisao_analista"), t.get("vw_decisao_atual")
    if d is not None and e is not None and {"contrato_id", "origem"} <= set(d.columns):
        ids_carteira = set(e["loan_id"].dropna())
        cart, simu = d[d["origem"] == "carteira"], d[d["origem"] == "simulacao"]
        fora = cart.loc[~cart["contrato_id"].isin(ids_carteira), "contrato_id"]
        erro("decisao_analista: contrato 'carteira' que nao existe em emprestimo", len(fora),
             ", ".join(map(str, fora.head(3))))
        # compara o ID normalizado: uma decisão da carteira digitada em maiúsculas ou com espaços
        # ficaria como 'simulacao' e sumiria da fila (o db/07 impede isso no banco)
        erro("decisao_analista: contrato 'simulacao' que existe em emprestimo",
             int(simu["contrato_id"].astype(str).str.strip().str.lower().isin(ids_carteira).sum()))
    if d is not None and va is not None and "contrato_id" in va.columns and {"contrato_id", "origem"} <= set(d.columns):
        esperado = set(d.loc[d["origem"] == "carteira", "contrato_id"])
        erro("vw_decisao_atual com contratos diferentes da decisao_analista (carteira)",
             len(esperado ^ set(va["contrato_id"])))
    # retorno realizado: tem que cobrir exatamente os contratos da base de modelagem
    vb, vr = t.get("vw_base_modelagem"), t.get("vw_retorno_realizado")
    if vb is not None and vr is not None and "loan_id" in vb.columns and "loan_id" in vr.columns:
        erro("vw_retorno_realizado com contratos diferentes da vw_base_modelagem",
             len(set(vb["loan_id"]) ^ set(vr["loan_id"])))
    # desfecho: todo contrato de emprestimo, com desfecho exatamente nos da vw_retorno_realizado
    vd = t.get("vw_desfecho_contrato")
    if vd is not None and {"loan_id", "tem_desfecho"} <= set(vd.columns):
        if e is not None:
            erro("vw_desfecho_contrato com contratos diferentes de emprestimo",
                 len(set(vd["loan_id"]) ^ set(e["loan_id"])))
        if vr is not None and "loan_id" in vr.columns:
            com = set(vd.loc[vd["tem_desfecho"].astype(bool), "loan_id"])
            erro("vw_desfecho_contrato: contratos com desfecho diferentes da vw_retorno_realizado",
                 len(com ^ set(vr["loan_id"])))
    # base de modelagem
    v = t.get("vw_base_modelagem")
    if v is not None and {"conjunto", "cliente_id"} <= set(v.columns):
        tr = set(v.loc[v["conjunto"] == "treino", "cliente_id"])
        te = set(v.loc[v["conjunto"] == "teste", "cliente_id"])
        erro("cliente no treino e no teste ao mesmo tempo", len(tr & te))
        if not parcial:
            contagem = v["conjunto"].value_counts()
            for conj, esperado in BASE_ESPERADA.items():
                erro(f"vw_base_modelagem: conjunto '{conj}' diferente do DECISOES.md ({esperado:,})"
                     .replace(",", "."), abs(int(contagem.get(conj, 0)) - esperado),
                     f"há {int(contagem.get(conj, 0)):,}".replace(",", "."))
    return saida


def validar_tabelas(tabelas: dict[str, pd.DataFrame], parcial: bool = False,
                    estrito: bool = True) -> pd.DataFrame:
    """Valida o dicionário {nome da tabela: DataFrame} e devolve um DataFrame com uma
    linha por (severidade, tabela, coluna, regra) violada. Vazio = nada a registrar.
    estrito=False deixa passar colunas a mais no DataFrame (colunas a menos continuam sendo erro)."""
    linhas: list[dict] = []
    for tabela in _regras_erro():
        df = tabelas.get(tabela)
        if df is None:
            linhas.append({"severidade": "erro", "tabela": tabela, "coluna": "",
                           "regra": "tabela ou view ausente no banco", "violacoes": 1,
                           "exemplos": ""})
            continue
        if tabela in TABELAS_MACRO:
            df = _janela(df, tabela)
        linhas += _coletar(df, esquema_erro(tabela, estrito), tabela, "erro")
        alerta = esquema_alerta(tabela)
        if alerta is not None:
            linhas += _coletar(df, alerta, tabela, "alerta")
    linhas += _cruzamentos(tabelas, parcial)
    if not linhas:
        return _vazio()
    res = pd.DataFrame(linhas, columns=COLUNAS_RESULTADO)
    return res.sort_values(["severidade", "tabela", "coluna", "regra"]).reset_index(drop=True)


# --------------------------------------------------------------------------
# Banco
# --------------------------------------------------------------------------
def _url_sqlalchemy(url: str) -> str:
    url = re.sub(r"^postgresql\+\w+://", "postgresql://", url)
    try:
        import psycopg2  # noqa: F401
    except ImportError:
        try:
            import psycopg  # noqa: F401
        except ImportError:
            return url
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def conectar(url: str):
    from sqlalchemy import create_engine
    return create_engine(_url_sqlalchemy(url))


def conectar_ou_sair(dsn: str):
    """Abre a conexão e confere que ela funciona. Falha de conexão sai com código 2
    (não é o mesmo que "tabela ausente")."""
    motor = conectar(dsn)
    try:
        with motor.connect():
            pass
    except Exception as exc:
        primeiras = " ".join(str(exc).splitlines()[:2])[:260]
        print("ERRO: não consegui conectar ao banco.\n  " + primeiras +
              "\nConfira a DATABASE_URL (usuário, senha e, principalmente, a PORTA) e se o "
              "contêiner está no ar (docker compose ps).", file=sys.stderr)
        sys.exit(2)
    return motor


def ler_tabelas(conexao) -> dict[str, pd.DataFrame]:
    """Lê as tabelas e a view com pd.read_sql (SQLAlchemy engine ou conexão sqlite3).
    O que não existir no banco fica de fora e vira erro na validação."""
    tabelas: dict[str, pd.DataFrame] = {}
    for nome in _regras_erro():
        datas = (list(DATAS_BONDORA) if nome in TABELAS else (["mes"] if nome in TABELAS_MACRO
                 else DATAS_EXTRAS.get(nome, [])))
        try:
            df = pd.read_sql(f"SELECT * FROM {nome}", conexao, parse_dates=datas or None)
        except Exception as exc:                      # tabela/view inexistente
            print(f"aviso: não consegui ler {nome}: {str(exc).splitlines()[0][:120]}", file=sys.stderr)
            continue
        tabelas[nome] = df
    return tabelas


def main() -> None:
    _carregar_env()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dsn", default=os.environ.get("DATABASE_URL"),
                    help="padrão: variável de ambiente DATABASE_URL")
    ap.add_argument("--parcial", action="store_true",
                    help="não confere as contagens fixas (banco carregado com --linhas)")
    ap.add_argument("--saida", help="salva o resultado completo neste CSV")
    a = ap.parse_args()
    if not a.dsn:
        sys.exit("ERRO: informe --dsn ou defina DATABASE_URL.")
    motor = conectar_ou_sair(a.dsn)
    res = validar_tabelas(ler_tabelas(motor), parcial=a.parcial)
    if a.saida:
        res.to_csv(a.saida, index=False)
    erros, alertas = res[res["severidade"] == "erro"], res[res["severidade"] == "alerta"]
    pd.set_option("display.width", 200, "display.max_colwidth", 70)
    print("=" * 78)
    print(f"ERROS: {len(erros)} regra(s) violada(s) | ALERTAS: {len(alertas)} regra(s) com ocorrências")
    for titulo, parte in (("ERROS", erros), ("ALERTAS", alertas)):
        if len(parte):
            print(f"\n{titulo}")
            print(parte.drop(columns="severidade").to_string(index=False))
    print("=" * 78)
    sys.exit(1 if len(erros) else 0)


if __name__ == "__main__":
    main()
