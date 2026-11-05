#!/usr/bin/env python3
"""Relatório de qualidade dos dados: gera docs/qualidade_dados.md.

Uso (na raiz do projeto, com o banco no ar e o .env preenchido):
    python src/dados/relatorio_qualidade.py
    python src/dados/relatorio_qualidade.py --saida docs/qualidade_dados.md --parcial

O que o relatório traz:
  * o resultado das regras de src/dados/validacao.py (erros e alertas), com o % de linhas
    afetadas e o que fazer com cada alerta;
  * três achados que NÃO são regra, mas que a banca e o grupo precisam ver:
      - a proporção de mulheres por ano e país (a codificação do gênero muda em 2017–2019);
      - os zeros no lugar de vazio, por ano;
      - as colunas que ficam em branco depois de 2017.

O arquivo gerado é versionado: reescreva-o sempre que recarregar o banco.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date

import pandas as pd

try:                                    # importado como pacote (pytest, a partir da raiz)
    from src.dados import validacao as v
except ImportError:                     # executado como script: python src/dados/relatorio_qualidade.py
    import validacao as v

ANOS = list(range(2013, 2022))
PAISES = ["EE", "ES", "FI"]
COLUNAS_ZERO = ["divida_renda", "caixa_livre", "renda_empregador_principal",
                "pagamentos_anteriores", "quitacoes_antecipadas_valor"]
COLUNAS_BRANCO = ["finalidade", "situacao_emprego", "area_ocupacao", "experiencia_trabalho"]

# O que fazer com cada alerta (DATA.md, seção 7). Chave: (tabela, trecho da coluna ou da regra).
ACOES = [
    (("cliente", "idade"), "Marcar. Excluir ou manter ainda é decisão aberta (DATA.md, seção 7)."),
    (("cliente", "renda_total"), "Marcar. Excluir ou manter ainda é decisão aberta (DATA.md, seção 7)."),
    (("emprestimo", "Current nao tem data_default"), "Registrar. Conferir se são contratos reestruturados."),
    (("emprestimo", "Repaid nao tem saldo_principal"), "Registrar."),
    (("emprestimo", "valor_concedido <= valor_solicitado"), "Registrar."),
    (("emprestimo", "vencimento original"), "Registrar. Não afeta a base de modelagem."),
    (("emprestimo", "parcela_mensal"), "Registrar. A coluna está na lista negra."),
    (("emprestimo", "prazo_meses"), "Registrar. Atenção ao fluxo de caixa de prazos muito curtos."),
]


def _acao(tabela: str, coluna: str, regra: str) -> str:
    for (t, trecho), texto in ACOES:
        if t == tabela and (trecho in regra or trecho == coluna):
            return texto
    return "Registrar."


def _n(valor: int) -> str:
    return f"{int(valor):,}".replace(",", ".")


def _pct(valor: float, casas: int = 0) -> str:
    if pd.isna(valor):
        return "–"
    return f"{valor:.{casas}f}".replace(".", ",") + "%"


def _tabela_md(cabecalho: list[str], linhas: list[list[str]]) -> str:
    saida = ["| " + " | ".join(cabecalho) + " |", "| " + " | ".join("---" for _ in cabecalho) + " |"]
    saida += ["| " + " | ".join(str(c) for c in linha) + " |" for linha in linhas]
    return "\n".join(saida)


def _base_por_contrato(t: dict[str, pd.DataFrame]) -> pd.DataFrame | None:
    e, c, h = t.get("emprestimo"), t.get("cliente"), t.get("historico_credito")
    if e is None or c is None or h is None or "data_emprestimo" not in e.columns:
        return None
    pegar = lambda df, cols: df[["loan_id"] + [x for x in cols if x in df.columns]]
    base = (e[["loan_id", "data_emprestimo"]]
            .merge(pegar(c, ["pais", "genero", "renda_empregador_principal"] + COLUNAS_BRANCO), on="loan_id")
            .merge(pegar(h, ["divida_renda", "caixa_livre", "pagamentos_anteriores",
                             "quitacoes_antecipadas_valor"]), on="loan_id"))
    # as colunas finalidade e experiencia_trabalho podem estar em outra tabela: junta o que faltar
    for tabela in (e, c, h):
        faltam = [x for x in COLUNAS_BRANCO if x not in base.columns and x in tabela.columns]
        if faltam:
            base = base.merge(tabela[["loan_id"] + faltam], on="loan_id", how="left")
    base["ano"] = base["data_emprestimo"].dt.year
    return base


def _secao_genero(base: pd.DataFrame) -> str:
    x = base[base["genero"].isin([0, 1]) & base["pais"].isin(PAISES) & base["ano"].isin(ANOS)]
    serie = (x.groupby(["ano", "pais"])["genero"].mean() * 100).unstack("pais").reindex(ANOS)
    linhas = [[str(ano)] + [_pct(serie.loc[ano, p]) if p in serie.columns else "–" for p in PAISES]
              for ano in ANOS]
    return ("### Proporção de mulheres por ano e país\n\n"
            "Entre os contratos com gênero 0 ou 1. Quedas abruptas e voltas ao nível anterior "
            "indicam problema de codificação, e não mudança da clientela (DATA.md, seção 7).\n\n"
            + _tabela_md(["Ano"] + PAISES, linhas))


def _secao_zeros(base: pd.DataFrame) -> str:
    colunas = [c for c in COLUNAS_ZERO if c in base.columns]
    x = base[base["ano"].isin(ANOS)]
    linhas = []
    for ano in ANOS:
        g = x[x["ano"] == ano]
        linhas.append([str(ano)] + [_pct(((g[c] == 0).where(g[c].notna())).mean() * 100) for c in colunas])
    return ("### Zeros no lugar de vazio\n\n"
            "% de contratos com valor exatamente zero. Colunas que passam a ter 100% de zeros "
            "deixam de ser informação (DATA.md, seção 6).\n\n"
            + _tabela_md(["Ano"] + [f"`{c}`" for c in colunas], linhas))


def _secao_branco(base: pd.DataFrame) -> str:
    colunas = [c for c in COLUNAS_BRANCO if c in base.columns]
    x = base[base["ano"].isin(ANOS)]
    linhas = []
    for ano in ANOS:
        g = x[x["ano"] == ano]
        linhas.append([str(ano)] + [_pct(g[c].isna().mean() * 100) for c in colunas])
    return ("### Colunas em branco depois de 2017\n\n"
            "% de contratos sem valor (inclui o código -1, que a carga troca por vazio).\n\n"
            + _tabela_md(["Ano"] + [f"`{c}`" for c in colunas], linhas))


def gerar_relatorio(tabelas: dict[str, pd.DataFrame], resultado: pd.DataFrame,
                    hoje: str | None = None) -> str:
    """Monta o texto Markdown do relatório a partir das tabelas lidas e do resultado
    de validacao.validar_tabelas(). Não acessa o banco."""
    hoje = hoje or date.today().isoformat()
    erros = resultado[resultado["severidade"] == "erro"]
    alertas = resultado[resultado["severidade"] == "alerta"]
    e, c = tabelas.get("emprestimo"), tabelas.get("cliente")
    n_contratos = len(e) if e is not None else 0
    n_clientes = c["cliente_id"].nunique() if c is not None and "cliente_id" in c.columns else 0

    partes = ["# Qualidade dos dados · Auditor de Preço Justo", "",
              f"Gerado em {hoje} a partir do banco. As regras estão em `src/dados/validacao.py` "
              "e as decisões sobre os dados, em `DATA.md`.", "",
              "## Resumo", "",
              f"- Contratos: {_n(n_contratos)}; clientes distintos: {_n(n_clientes)}.",
              f"- Regras de **erro** violadas: {len(erros)}. Erro quebra o contrato dos dados "
              "(chaves, domínios, datas, faixas, contagens) e falha o teste.",
              f"- Regras de **alerta** com ocorrências: {len(alertas)}. Alerta é ocorrência conhecida, "
              "registrada sem falhar."]
    v_ = tabelas.get("vw_base_modelagem")
    if v_ is not None and "conjunto" in v_.columns:
        cont = v_["conjunto"].value_counts()
        partes += ["- Base de modelagem (`vw_base_modelagem`): "
                   + "; ".join(f"{k} {_n(cont.get(k, 0))}" for k in ("treino", "teste", "fora_cliente_repetido"))
                   + "."]
    partes += [""]

    partes += ["## Erros", ""]
    if erros.empty:
        partes += ["Nenhum erro.", ""]
    else:
        linhas = [[r.tabela, r.coluna or "–", r.regra, _n(r.violacoes), r.exemplos or "–"]
                  for r in erros.itertuples()]
        partes += [_tabela_md(["Tabela", "Coluna", "Regra", "Ocorrências", "Exemplos"], linhas), ""]

    partes += ["## Alertas", ""]
    if alertas.empty:
        partes += ["Nenhum alerta.", ""]
    else:
        linhas = []
        for r in alertas.itertuples():
            total = len(tabelas[r.tabela]) if r.tabela in tabelas else 0
            exemplo = r.exemplos.split(",")[0].strip() if r.exemplos else "–"
            linhas.append([r.tabela, f"`{r.coluna}`" if r.coluna != "(linha)" else "(várias colunas)",
                           r.regra, _n(r.violacoes), _pct(r.violacoes / total * 100, 2) if total else "–",
                           f"`{exemplo}`" if exemplo != "–" else "–", _acao(r.tabela, r.coluna, r.regra)])
        partes += [_tabela_md(["Tabela", "Coluna", "Regra violada", "Linhas", "% da tabela",
                               "Exemplo (`loan_id`)", "O que fazer"], linhas), ""]

    partes += ["## Achados que não são regra", ""]
    base = _base_por_contrato(tabelas)
    if base is None:
        partes += ["Tabelas insuficientes para calcular os achados.", ""]
    else:
        partes += [_secao_genero(base), "", _secao_zeros(base), "", _secao_branco(base), ""]

    partes += ["## Como reproduzir", "",
               "```", "python src/dados/validacao.py                  # só as regras",
               "python src/dados/relatorio_qualidade.py         # regras e este relatório", "```", ""]
    return "\n".join(partes)


def main() -> None:
    v._carregar_env()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dsn", default=os.environ.get("DATABASE_URL"),
                    help="padrão: variável de ambiente DATABASE_URL")
    ap.add_argument("--saida", default="docs/qualidade_dados.md")
    ap.add_argument("--parcial", action="store_true",
                    help="não confere as contagens fixas (banco carregado com --linhas)")
    a = ap.parse_args()
    if not a.dsn:
        sys.exit("ERRO: informe --dsn ou defina DATABASE_URL.")
    tabelas = v.ler_tabelas(v.conectar_ou_sair(a.dsn))
    resultado = v.validar_tabelas(tabelas, parcial=a.parcial)
    texto = gerar_relatorio(tabelas, resultado)
    with open(a.saida, "w", encoding="utf-8", newline="\n") as f:
        f.write(texto)
    erros = int((resultado["severidade"] == "erro").sum())
    print(f"Relatório gravado em {a.saida} ({erros} erro(s), "
          f"{int((resultado['severidade'] == 'alerta').sum())} alerta(s)).")
    sys.exit(1 if erros else 0)


if __name__ == "__main__":
    main()
