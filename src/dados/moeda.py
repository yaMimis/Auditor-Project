"""Correção de moeda: renda e passivos de 2009–2010 vêm em coroas estonianas (EEK).

O que se descobriu (EDA, 03/11/2026):
  * até 31/12/2010 a Estônia usava a coroa. A renda e os passivos declarados pelo cliente
    ficaram em coroas no arquivo do Bondora (a renda mediana cai de 12.000 em dez/2010 para
    860 em jan/2011);
  * os valores dos empréstimos já foram convertidos para euros pelo Bondora (o valor pedido
    multiplicado por 15,6466 dá um número redondo de coroas em 100% dos contratos de 2009–2010).

A correção vale SÓ para a Estônia: divide por 15,6466 (taxa fixa da coroa em relação ao euro)
as colunas de renda e `passivos_total` dos contratos da Estônia concedidos antes de 01/01/2011.
Finlândia e Espanha já usavam o euro, e a Eslováquia o adotou em 2009, então nenhum contrato
desses países pode ser convertido. No arquivo atual, os 1.822 contratos anteriores a 2011 são
todos da Estônia (os outros países começam em 2013–2014), mas a regra não depende disso: por
isso `antes_do_euro` exige o país.

Este módulo é a ÚNICA fonte da regra. Quem lê o CSV usa a mesma função:
  * a carga do banco (src/dados/carga_bondora.py);
  * o treino do modelo (src/modelos/dados.py: `ler_base`), que lê o CSV direto.

As colunas usam os nomes do banco (renda_total, passivos_total, data_emprestimo...).
"""
from __future__ import annotations

import pandas as pd

TAXA_EEK_POR_EUR = 15.6466
DATA_EURO = pd.Timestamp("2011-01-01")      # a Estônia adotou o euro em 01/01/2011
PAIS_DA_COROA = "EE"                        # único país do arquivo que usava a coroa

# Colunas em coroas até 31/12/2010 (confirmadas: renda_total, renda_empregador_principal,
# renda_outras e passivos_total; as demais rendas têm poucos casos, mas são do mesmo tipo).
COLUNAS_EM_COROAS = (
    "renda_total", "renda_empregador_principal", "renda_pensao", "renda_auxilio_familiar",
    "renda_assistencia_social", "renda_licenca", "renda_pensao_alimenticia", "renda_outras",
    "passivos_total",
)


def antes_do_euro(datas: pd.Series, paises: pd.Series) -> pd.Series:
    """True só para contratos da Estônia concedidos antes de 01/01/2011.

    Data ou país vazios viram False (na dúvida, não converte). O país é obrigatório de
    propósito: chamar a função sem ele dá erro, em vez de converter outros países por engano.
    """
    antes = pd.to_datetime(datas, errors="coerce") < DATA_EURO
    estonia = paises.astype("string").str.strip().str.upper().eq(PAIS_DA_COROA)
    return (antes & estonia).fillna(False).astype(bool)


def coroas_para_euros(df: pd.DataFrame, antes: pd.Series) -> pd.DataFrame:
    """Divide por 15,6466 as colunas em coroas das linhas marcadas em `antes`.

    Altera e devolve o próprio `df`. Arredonda em 2 casas, como o NUMERIC(16,2) do banco,
    para que o CSV e o banco deem exatamente os mesmos valores. Colunas ausentes são
    ignoradas, e valores vazios continuam vazios.
    """
    antes = antes.reindex(df.index).fillna(False).astype(bool)
    if not antes.any():
        return df
    for coluna in COLUNAS_EM_COROAS:
        if coluna in df.columns:
            valores = pd.to_numeric(df.loc[antes, coluna], errors="coerce")
            df[coluna] = df[coluna].astype("float64")
            df.loc[antes, coluna] = (valores / TAXA_EEK_POR_EUR).round(2)
    return df
