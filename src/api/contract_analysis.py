"""Análise de um contrato da base: o que o modelo recebeu e como o preço foi calculado.

Nada é recalculado por fora: a preparação do contrato, as variáveis derivadas e os
parâmetros do juro justo vêm das mesmas funções que o prever() usa
(src/modelos/prever.py: preparar_contrato, parametros_preco, juro_justo;
src/modelos/variaveis.py: criar_variaveis).
"""
from __future__ import annotations

import hashlib
import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.modelos import prever as modelo
from src.modelos.variaveis import CATEGORICAS, NUMERICAS, ROTULOS, criar_variaveis

MODEL_FEATURES = NUMERICAS + CATEGORICAS
PROTECTED = {"genero", "idade", "estado_civil", "n_dependentes"}  # nunca chegam aqui (database.py)


def _json_value(value):
    """Valor pronto para JSON: NaN/None → None; numpy → nativo; datas → texto."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if hasattr(value, "item"):  # numpy
        value = value.item()
        return None if isinstance(value, float) and math.isnan(value) else value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def considered_data(row: dict, package: dict) -> list[dict]:
    """As 21 variáveis do modelo com o valor deste contrato.

    origem = "fornecida" (veio do cadastro/contrato no banco) ou "derivada"
    (calculada pelo pipeline do modelo a partir das fornecidas)."""
    frame, _ = modelo.preparar_contrato(row, package)
    derived = criar_variaveis(frame, referencia=package["referencia"])
    out = []
    for name in MODEL_FEATURES:
        provided = name in row
        # fornecida: o valor como está no banco (o modelo agrupa categorias raras em "outros");
        # derivada: o valor que o pipeline calculou e mandou ao modelo
        value = row[name] if provided else (derived[name].iloc[0] if name in derived.columns else None)
        out.append({"variavel": name, "rotulo": ROTULOS.get(name, name.replace("_", " ")),
                    "valor": _json_value(value), "origem": "fornecida" if provided else "derivada",
                    "tipo": "numerica" if name in NUMERICAS else "categorica"})
    return out


def pricing_parameters(row: dict, resultado: dict, package: dict) -> dict | None:
    """Parâmetros da conta do juro justo e o juro justo com PD zero (comparação contrafactual:
    a mesma função com a PD zerada, não uma parcela do juro). None em revisão manual."""
    if resultado.get("pd") is None or resultado.get("juro_justo") is None:
        return None
    frame, year = modelo.preparar_contrato(row, package)
    params = modelo.parametros_preco(frame, package, year)
    without_risk = round(modelo.juro_justo(params["prazo"], 0.0, params["lgd"], params["custo_anual"]), 4)
    return {"euribor_12m": round(params["euribor"], 4), "lgd": params["lgd"],
            "custo_margem_safra": round(params["margem"], 4), "custo_anual": round(params["custo_anual"], 4),
            "prazo_meses": params["prazo"], "pd": resultado["pd"], "juro_justo_sem_risco": without_risk,
            "efeito_do_risco_pp": round((resultado["juro_justo"] - without_risk) * 100, 1)}


def contract_summary(row: dict) -> dict:
    """Identificação do contrato para o topo da tela (sem atributos protegidos)."""
    loan_date = pd.to_datetime(row["data_emprestimo"]).date()
    return {"pais": row.get("pais"), "data_emprestimo": _json_value(loan_date), "ano": loan_date.year,
            "valor_concedido": _json_value(row.get("valor_concedido")),
            "valor_solicitado": _json_value(row.get("valor_solicitado")),
            "prazo_meses": _json_value(row.get("prazo_meses")),
            "juro_cobrado": round(float(row["juro_aa"]) / 100, 4)}


def batch_result(row: dict) -> dict:
    """Saída do prever() montada a partir de uma linha do lote (plano B): sem motivos."""
    def num(key):
        value = row.get(key)
        return None if value is None or pd.isna(value) else float(value)
    ic = (num("pd_ic95_min"), num("pd_ic95_max"))
    return {
        "contrato_id": str(row["contrato_id"]),
        "versao_modelo": str(row.get("versao_modelo") or "lote da carteira"),
        "pd": num("pd"), "faixa": row.get("faixa") or None,
        "juro_cobrado": float(row["juro_cobrado"]), "juro_justo": num("juro_justo"),
        "juro_justo_min": num("juro_justo_min"), "juro_justo_max": num("juro_justo_max"),
        "situacao_preco": row["situacao_preco"], "motivos": [],
        "alerta_dados": row["situacao_preco"] == "revisao_manual",
        "juro_pares_mediana": num("juro_pares_mediana"),
        "pd_ic95": list(ic) if None not in ic else None,
    }


def batch_summary(row: dict) -> dict:
    """Topo da tela a partir da linha do lote (o lote guarda o ano, não a data)."""
    def num(key):
        value = row.get(key)
        return None if value is None or pd.isna(value) else value
    return {"pais": row.get("pais"), "data_emprestimo": None,
            "ano": int(row["ano"]) if num("ano") is not None else None,
            "valor_concedido": num("valor_concedido"), "valor_solicitado": None,
            "prazo_meses": int(row["prazo_meses"]) if num("prazo_meses") is not None else None,
            "juro_cobrado": float(row["juro_cobrado"])}


_ARTIFACT_CACHE: dict = {}


def package_identity(path: Path, package: dict | None = None) -> dict:
    """Identifica o arquivo do modelo de fato carregado: hash, data do arquivo e reamostras do bootstrap.

    A versão escrita no código (VERSAO) não basta: dois .joblib diferentes podem ter o mesmo nome."""
    path = Path(path)
    if not path.exists():
        return {"pacote_arquivo": path.name, "pacote_hash": None, "pacote_data": None,
                "n_reamostras_bootstrap": None}
    stat = path.stat()
    key = (str(path), stat.st_mtime, stat.st_size)
    if key not in _ARTIFACT_CACHE:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1 << 20), b""):
                digest.update(block)
        _ARTIFACT_CACHE.clear()
        _ARTIFACT_CACHE[key] = {
            "pacote_arquivo": path.name, "pacote_hash": digest.hexdigest()[:12],
            "pacote_data": datetime.fromtimestamp(stat.st_mtime, timezone.utc).date().isoformat()}
    boot = (package or {}).get("bootstrap")
    return {**_ARTIFACT_CACHE[key], "n_reamostras_bootstrap": len(boot) if boot else 0}
