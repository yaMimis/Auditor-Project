"""Teste de invariância em lote: gênero e idade trocados em N contratos sorteados do lote.

Para cada contrato, roda o prever() duas vezes (gênero e idade reais × trocados), com a mesma
lógica da rota POST /contracts/{id}/invariance (src/api/invariance.py), e grava o resumo em
docs/resultados/invariancia_lote.json, que a página Auditoria mostra.

O arquivo não guarda gênero nem idade: só quantos contratos deram resultado idêntico, os IDs dos
que deram diferente (se houver) e a identificação do modelo.

Uso, na máquina com o banco e o pacote do modelo (leva alguns minutos):
    python -m scripts.invariancia_lote               # 500 contratos, semente 7
    python -m scripts.invariancia_lote --n 200 --semente 11

Sai com código 1 se algum contrato der resultado diferente.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def summarize(results: list[dict], n_requested: int, seed: int, model: dict) -> dict:
    """Resumo gravado no JSON (sem atributo protegido nenhum)."""
    from src.api import invariance

    different = [r["contrato_id"] for r in results if not r["identico"]]
    return {
        "n_sorteados": n_requested,
        "n_testados": len(results),
        "identicos": len(results) - len(different),
        "diferentes": different,
        "semente": seed,
        "atributos_trocados": invariance.ATTRIBUTE_LABELS,
        "como_foi_trocado": invariance.HOW_SWAPPED,
        **model,
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def main(argv: list[str] | None = None) -> int:
    from src.api import contract_analysis, database, invariance, portfolio
    from src.modelos import prever as modelo

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--semente", type=int, default=7)
    ap.add_argument("--lote", type=Path, default=portfolio.PORTFOLIO_DIR)
    args = ap.parse_args(argv)

    batch = portfolio.load_portfolio(args.lote)
    if batch is None:
        print(f"Falta {portfolio.PORTFOLIO_FILE} em {args.lote}.")
        return 2
    ids = batch["contrato_id"].astype(str).sample(min(args.n, len(batch)), random_state=args.semente).tolist()
    package = modelo._pacote()
    results = []
    for i, cid in enumerate(ids, 1):
        row = database.load_contract(cid)
        if row is None:
            continue
        out = invariance.run(row, database.load_protected(row["loan_id"]) or {}, package, modelo.prever)
        results.append({"contrato_id": row["loan_id"], "identico": out["identico"]})
        if i % 50 == 0:
            print(f"{i}/{len(ids)} contratos testados")

    identity = contract_analysis.package_identity(modelo.PACOTE_PADRAO, package)
    model = {"versao_modelo": modelo.VERSAO, "pacote_hash": identity.get("pacote_hash")}
    summary = summarize(results, len(ids), args.semente, model)
    path_ = Path(args.lote) / portfolio.INVARIANCE_FILE
    path_.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{summary['identicos']}/{summary['n_testados']} contratos com resultado idêntico. Gravado em {path_}.")
    if summary["diferentes"]:
        print("Diferentes:", ", ".join(summary["diferentes"][:20]))
    return 1 if summary["diferentes"] else 0


if __name__ == "__main__":
    sys.exit(main())
