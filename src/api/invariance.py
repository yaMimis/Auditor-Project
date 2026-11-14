"""Teste de invariância (Auditoria): gênero e idade trocados mudam o resultado do modelo?

Roda o mesmo prever() duas vezes no mesmo contrato do banco: uma com o gênero e a idade reais do
cliente e outra com os dois trocados. Como nenhum dos dois é variável do modelo, o resultado tem
de ser idêntico. O teste mostra isso na prática, mas não prova que o preço é justo: a diferença que
sobra entre grupos, a risco igual, é medida na equidade agregada (equidade.json).

Os valores reais (e os trocados) nunca saem daqui: a resposta diz só QUAIS atributos foram trocados.
"""
from __future__ import annotations

from typing import Callable

from src.modelos.variaveis import colunas_do_modelo

PROTECTED_FIELDS = ("genero", "idade")
ATTRIBUTE_LABELS = ["gênero", "idade"]
COMPARED = ("pd", "faixa", "juro_justo", "juro_justo_min", "juro_justo_max", "situacao_preco")
HOW_SWAPPED = ("gênero trocado pelo outro valor (homem ↔ mulher; indefinido vira homem) e idade deslocada em "
               "25 anos (para mais até 44 anos, para menos a partir de 45), dentro de 18 a 75")


def swapped(protected: dict) -> dict:
    """O outro gênero e uma idade de outra faixa etária (25 anos de diferença)."""
    gender = protected.get("genero")
    age = protected.get("idade")
    new_gender = {0: 1, 1: 0}.get(gender, 0)
    if age is None:
        new_age = 60
    elif age < 45:
        new_age = min(age + 25, 75)
    else:
        new_age = max(age - 25, 18)
    return {"genero": new_gender, "idade": new_age}


def snapshot(result: dict) -> dict:
    """O que se compara entre as duas execuções (nenhum atributo protegido aqui)."""
    reasons = result.get("motivos") or []
    return {**{k: result.get(k) for k in COMPARED},
            "motivos": [m.get("rotulo") or m.get("variavel") for m in reasons],
            "_motivos_completos": [(m.get("variavel"), m.get("peso"), m.get("efeito")) for m in reasons]}


def run(row: dict, protected: dict, package: dict, prever_fn: Callable[[dict, dict], dict]) -> dict:
    """Original × trocado, com a lista do que mudou (vazia = idêntico)."""
    original = snapshot(prever_fn({**row, **protected}, package))
    changed = snapshot(prever_fn({**row, **swapped(protected)}, package))
    differences = [k for k in COMPARED if original[k] != changed[k]]
    if original.pop("_motivos_completos") != changed.pop("_motivos_completos"):
        differences.append("motivos")
    return {
        "atributos_trocados": ATTRIBUTE_LABELS,
        "como_foi_trocado": HOW_SWAPPED,
        "original": original,
        "trocado": changed,
        "identico": not differences,
        "diferencas": differences,
        "modelo_sem_atributos_protegidos": not (set(colunas_do_modelo()) & set(PROTECTED_FIELDS)),
    }
