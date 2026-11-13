"""Laboratório: o mesmo contrato do banco com alguns campos trocados, recalculado pelo prever().

Nada é calculado aqui por fora do modelo: este módulo só aplica as trocas sobre a linha do
banco e chama o prever() (o original, o cenário e um campo de cada vez, para o "O que mudou o
risco"). A parcela usa a função do lote do Samuel (src/modelos/carteira.py).

Gênero, idade, estado civil e dependentes não são editáveis: a linha do banco não os traz
(database.CONTRACT_COLUMNS) e o pedido recusa campos fora da lista (ScenarioChanges).
"""
from __future__ import annotations

import math
from typing import Callable

import numpy as np

from src.modelos.carteira import _parcela
from src.modelos.prever import CHECAR_FAIXA
from src.modelos.variaveis import ROTULOS

# Campos editáveis no Laboratório, na ordem da tela. O juro cobrado é um controle à parte
# (não entra no modelo: muda a situação e a parcela, nunca a PD).
EDITABLE = ["valor_concedido", "prazo_meses", "renda_total", "passivos_total", "passivos_existentes",
            "n_emprestimos_anteriores", "tempo_emprego_atual", "tipo_verificacao"]
INTEGERS = {"prazo_meses", "passivos_existentes", "n_emprestimos_anteriores"}
CATEGORIES = {
    "tempo_emprego_atual": ["TrialPeriod", "UpTo1Year", "UpTo2Years", "UpTo3Years", "UpTo4Years",
                            "UpTo5Years", "MoreThan5Years", "Retiree", "Other"],
    "tipo_verificacao": [1, 2, 3, 4],
}
EXTRA_LABELS = {"passivos_total": "valor total das dívidas (€)"}
# Limites provisórios até o Samuel passar a faixa vista no treino destes campos. Valor, prazo e
# renda usam a faixa guardada no próprio pacote do modelo (faixas_treino, 0,5% a 99,5% do treino):
# fora dela o prever() já manda o contrato para revisão manual.
PROVISIONAL_LIMITS = {"passivos_total": (0.0, 100_000.0), "passivos_existentes": (0, 40),
                      "n_emprestimos_anteriores": (0, 30)}
PD_TOLERANCE = 0.0005  # abaixo disso a PD "não mudou" (arredondamento de 4 casas)


def label(field: str) -> str:
    return EXTRA_LABELS.get(field) or ROTULOS.get(field, field)


def limits(package: dict) -> dict[str, tuple[float, float, str]]:
    """Limite de cada campo numérico: (mínimo, máximo, fonte), fonte = "treino" ou "provisorio"."""
    out = {}
    for field in EDITABLE:
        if field in CATEGORIES:
            continue
        if field in CHECAR_FAIXA and field in package.get("faixas_treino", {}):
            lo, hi = package["faixas_treino"][field]
            out[field] = (float(lo), float(hi), "treino")
        elif field in PROVISIONAL_LIMITS:
            lo, hi = PROVISIONAL_LIMITS[field]
            out[field] = (float(lo), float(hi), "provisorio")
    return out


def _plain(value):
    """Valor do banco pronto para JSON (NaN → None, numpy → Python)."""
    if value is None:
        return None
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def fields(row: dict, package: dict) -> list[dict]:
    """Os campos do formulário do Laboratório, com o valor atual do contrato e os limites."""
    bounds = limits(package)
    out = []
    for field in EDITABLE:
        lo, hi, source = bounds.get(field, (None, None, "nenhum"))
        out.append({"campo": field, "rotulo": label(field),
                    "tipo": "categoria" if field in CATEGORIES else "inteiro" if field in INTEGERS else "numero",
                    "valor_atual": _plain(row.get(field)), "minimo": lo, "maximo": hi,
                    "opcoes": CATEGORIES.get(field), "limite": source})
    return out


def check(changes: dict, package: dict) -> list[str]:
    """Problemas nas trocas pedidas (vazia = ok). Fora dos limites o modelo não deve ser usado."""
    problems = []
    bounds = limits(package)
    for field, value in changes.items():
        if field == "juro_aa" or value is None:
            continue
        if field in CATEGORIES:
            if value not in CATEGORIES[field]:
                problems.append(f"{label(field)}: valor {value!r} não é uma das opções")
        elif field in bounds:
            lo, hi, source = bounds[field]
            if not lo <= float(value) <= hi:
                where = "da faixa vista no treino" if source == "treino" else "do limite provisório"
                problems.append(f"{label(field)}: {value} fora {where} ({lo:g} a {hi:g})")
    return problems


def apply(row: dict, changes: dict) -> dict:
    """Cópia da linha do banco com as trocas (juro_aa em %, como no banco)."""
    return {**row, **{k: v for k, v in changes.items() if v is not None}}


def installment(valor, juro_frac, prazo) -> float | None:
    """Parcela mensal (€) pela função do lote; None sem os três números."""
    if valor is None or juro_frac is None or not prazo:
        return None
    with np.errstate(divide="ignore", invalid="ignore"):  # a função calcula os dois ramos do np.where
        return round(float(_parcela(float(valor), float(juro_frac), float(prazo))), 2)


def run(row: dict, changes: dict, package: dict, prever_fn: Callable[[dict, dict], dict]) -> dict:
    """Original × cenário × um campo de cada vez, tudo pelo prever()."""
    original = prever_fn(row, package)
    scenario_row = apply(row, changes)
    scenario = prever_fn(scenario_row, package) if changes else original

    effects = []
    for field in (f for f in EDITABLE if f in changes and changes[f] is not None):
        alone = prever_fn(apply(row, {field: changes[field]}), package)
        before, after = original.get("pd"), alone.get("pd")
        if before is None or after is None:
            kind = "revisao_manual" if alone.get("situacao_preco") == "revisao_manual" else "sem_pd"
            delta = None
        else:
            delta = round(after - before, 4)
            kind = "aumenta" if delta > PD_TOLERANCE else "reduz" if delta < -PD_TOLERANCE else "neutro"
        effects.append({"campo": field, "rotulo": label(field), "valor_original": _plain(row.get(field)),
                        "valor_novo": changes[field], "pd_original": before, "pd_so_este_campo": after,
                        "diferenca_pd": delta, "efeito": kind})

    return {
        "original": original,
        "cenario": scenario,
        "parcela_original": installment(row.get("valor_concedido"), original.get("juro_cobrado"),
                                        row.get("prazo_meses")),
        "parcela_cenario": installment(scenario_row.get("valor_concedido"), scenario.get("juro_cobrado"),
                                       scenario_row.get("prazo_meses")),
        "efeitos": effects,
        "campos": fields(row, package),
    }
