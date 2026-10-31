"""Variáveis do modelo de risco.

Regras (docs/DECISOES.md, seção 3):
- nada da lista negra do Marcos, nem parcela_mensal (contém o juro);
- gênero e idade (e o que for só auditoria) nunca entram;
- identificadores nunca entram.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.dados.carga_bondora import (
    COLUNAS_INDISPONIVEIS_RECENTES,
    COLUNAS_LISTA_NEGRA,
    COLUNAS_SO_AUDITORIA,
)

# --------------------------------------------------------------------------
# Colunas proibidas (o teste em tests/modelos/test_seguranca.py usa esta lista)
# --------------------------------------------------------------------------
IDENTIFICADORES = {"loan_id", "numero", "cliente_id"}
PROIBIDAS = frozenset(
    COLUNAS_LISTA_NEGRA            # pós-concessão, preço e saídas do Bondora (inclui parcela_mensal)
    | COLUNAS_SO_AUDITORIA         # genero, idade, estado_civil, n_dependentes
    | COLUNAS_INDISPONIVEIS_RECENTES  # situacao_emprego, finalidade etc. (somem depois de ~2017)
    | IDENTIFICADORES
)

# --------------------------------------------------------------------------
# Variáveis usadas no modelo
# --------------------------------------------------------------------------
NUMERICAS = [
    "valor_concedido",
    "prazo_meses",
    "renda_total",
    "parcela_neutra_sobre_renda",
    "valor_sobre_renda",
    "divida_sobre_renda",
    "renda_relativa",
    "n_emprestimos_anteriores",
    "valor_emprestimos_anteriores",
    "passivos_existentes",
    # v3 (31/10): histórico e bureau. Testado com validação em 2015 (docs/DECISOES.md, seção 12):
    # saíram fracao_concedida (piorava), orçamento e composição da renda (não ajudavam).
    "pagamentos_anteriores",
    "quitacoes_antecipadas_qtd",
    "quitacoes_antecipadas_valor",
    "score_ee_mini",
]

# Calculadas, mas fora do modelo (resultado da comparação de grupos em 2015)
TESTADAS_E_DESCARTADAS = [
    "fracao_concedida",
    "caixa_livre_sobre_renda",
    "divida_renda_bondora",
    "refinanciamento_passivos",
    "renda_assistencial_sobre_renda",
    "renda_pensao_sobre_renda",
]
CATEGORICAS = [
    "pais",
    "novo_cliente",
    "tempo_emprego_atual",
    "escolaridade",
    "tipo_moradia",
    "tipo_verificacao",
    # v2 (31/10): scores de bureau de cada país (vazio fora do país → "sem_info")
    "score_fi_asiakastieto",
    "score_es_equifax",
    "score_es_microl",
]

# Colunas do banco que as variáveis v2 usam. Se faltarem (ex.: dados de teste),
# viram vazias em vez de quebrar.
FONTES_V2 = [
    "valor_solicitado", "pagamentos_anteriores", "quitacoes_antecipadas_qtd",
    "quitacoes_antecipadas_valor", "caixa_livre", "divida_renda", "refinanciamento_passivos",
    "renda_assistencia_social", "renda_auxilio_familiar", "renda_pensao_alimenticia",
    "renda_pensao", "score_ee_mini", "score_fi_asiakastieto", "score_es_equifax",
    "score_es_microl",
]

# Nome legível de cada variável (vai no campo "rotulo" do prever())
ROTULOS = {
    "valor_concedido": "valor do empréstimo",
    "prazo_meses": "prazo do empréstimo",
    "renda_total": "renda total",
    "parcela_neutra_sobre_renda": "parcela em relação à renda",
    "valor_sobre_renda": "valor do empréstimo em relação à renda",
    "divida_sobre_renda": "dívidas em relação à renda",
    "renda_relativa": "renda comparada à média do país",
    "n_emprestimos_anteriores": "empréstimos anteriores na plataforma",
    "valor_emprestimos_anteriores": "valor dos empréstimos anteriores",
    "passivos_existentes": "número de dívidas em aberto",
    "novo_cliente": "primeiro empréstimo na plataforma",
    "tempo_emprego_atual": "tempo no emprego atual",
    "escolaridade": "escolaridade",
    "tipo_moradia": "tipo de moradia",
    "tipo_verificacao": "verificação da renda",
    "pais": "país",
    "pagamentos_anteriores": "valor já pago em empréstimos anteriores",
    "quitacoes_antecipadas_qtd": "quitações antecipadas anteriores",
    "quitacoes_antecipadas_valor": "valor quitado antecipadamente antes",
    "fracao_concedida": "parte do valor pedido que foi concedida",
    "caixa_livre_sobre_renda": "folga no orçamento em relação à renda",
    "divida_renda_bondora": "comprometimento da renda com dívidas",
    "refinanciamento_passivos": "pedido para quitar outras dívidas",
    "renda_assistencial_sobre_renda": "parte da renda vinda de auxílios",
    "renda_pensao_sobre_renda": "parte da renda vinda de pensão",
    "score_ee_mini": "score de crédito (Estônia)",
    "score_fi_asiakastieto": "score de crédito (Finlândia)",
    "score_es_equifax": "score de crédito Equifax (Espanha)",
    "score_es_microl": "score de crédito MicroL (Espanha)",
}

FREQ_MINIMA = 0.01  # categorias com menos de 1% dos contratos viram "outros"


def colunas_do_modelo() -> list[str]:
    return NUMERICAS + CATEGORICAS


def _dividir(a: pd.Series, b: pd.Series) -> pd.Series:
    """Divisão segura: renda zero ou vazia vira NaN, nunca infinito."""
    b = b.where(b > 0)
    return (a / b).replace([np.inf, -np.inf], np.nan)


def parcela_neutra(valor: pd.Series, prazo: pd.Series, taxa_anual: float = 0.0) -> pd.Series:
    """Parcela SEM o juro do contrato (que é vazamento).
    Com taxa 0, é só valor ÷ prazo: mede o peso do pedido, não o preço."""
    prazo = prazo.where(prazo > 0)
    if taxa_anual == 0:
        return valor / prazo
    i = (1 + taxa_anual) ** (1 / 12) - 1
    return valor * i / (1 - (1 + i) ** -prazo)


def criar_variaveis(df: pd.DataFrame, referencia: pd.DataFrame | None = None) -> pd.DataFrame:
    """Cria as variáveis derivadas.

    referencia = base de TREINO. A mediana de renda por país e ano é calculada
    nela e aplicada ao teste, para o teste não "vazar" para o treino.
    """
    ref = df if referencia is None else referencia
    out = df.copy()
    for col in FONTES_V2:
        if col not in out.columns:
            out[col] = np.nan

    out["parcela_neutra_sobre_renda"] = _dividir(
        parcela_neutra(out["valor_concedido"], out["prazo_meses"]), out["renda_total"])
    out["valor_sobre_renda"] = _dividir(out["valor_concedido"], out["renda_total"])
    out["divida_sobre_renda"] = _dividir(out["passivos_total"], out["renda_total"])

    mediana = (ref[ref["renda_total"] > 0]
               .groupby(["pais", "ano"])["renda_total"].median()
               .rename("mediana_renda"))
    out = out.join(mediana, on=["pais", "ano"])
    renda = out["renda_total"].where(out["renda_total"] > 0)  # renda 0 = dado ausente
    out["renda_relativa"] = _dividir(renda, out["mediana_renda"])
    out = out.drop(columns="mediana_renda")

    # v2: histórico, orçamento e composição da renda
    out["fracao_concedida"] = _dividir(out["valor_concedido"], out["valor_solicitado"])
    out["caixa_livre_sobre_renda"] = _dividir(out["caixa_livre"], renda)
    out["divida_renda_bondora"] = pd.to_numeric(out["divida_renda"], errors="coerce")
    auxilios = out[["renda_assistencia_social", "renda_auxilio_familiar",
                    "renda_pensao_alimenticia"]].fillna(0).sum(axis=1)
    out["renda_assistencial_sobre_renda"] = _dividir(auxilios, renda)
    out["renda_pensao_sobre_renda"] = _dividir(out["renda_pensao"].fillna(0), renda)
    for col in ("pagamentos_anteriores", "quitacoes_antecipadas_qtd",
                "quitacoes_antecipadas_valor", "refinanciamento_passivos", "score_ee_mini"):
        out[col] = pd.to_numeric(out[col], errors="coerce")

    for col in CATEGORICAS:
        out[col] = out[col].astype("string").fillna("sem_info")
        ref_col = ref[col] if col in ref.columns else pd.Series(pd.NA, index=ref.index)
        freq = ref_col.astype("string").fillna("sem_info").value_counts(normalize=True)
        raras = set(freq[freq < FREQ_MINIMA].index)
        conhecidas = set(freq.index)
        out[col] = out[col].where(~out[col].isin(raras) & out[col].isin(conhecidas), "outros")

    return out


def matriz(df: pd.DataFrame) -> pd.DataFrame:
    """Só as colunas que o modelo pode ver."""
    return df[colunas_do_modelo()]