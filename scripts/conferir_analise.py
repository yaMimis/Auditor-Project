"""Confere a Análise do contrato com dados reais (banco + pacote do modelo + lote).

Abre ~20 contratos reais pela rota GET /contracts/{id}/analysis (a mesma que o painel usa)
e compara com o lote da carteira (carteira_auditoria.csv, gerado pelo mesmo prever()):
  - PD e juro justo iguais aos do lote (tolerância de arredondamento);
  - mesma situação do preço;
  - motivos (SHAP) presentes quando não é revisão manual;
  - nenhum atributo protegido (gênero, idade, estado civil, dependentes) na resposta;
  - procedência completa (versão, hash do pacote, incerteza).

Uso, com a API no ar (docker compose up):
    python -m scripts.conferir_analise                 # 20 contratos, API em http://localhost:8000
    python -m scripts.conferir_analise --n 40 --api http://localhost:8000

Sai com código 1 se algum contrato divergir. Só depois disso a Etapa 1 pode ser marcada como
concluída. Se o pacote do modelo mudou depois do lote, a divergência é esperada: gere o lote de novo.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

TOLERANCE = 5e-4  # o lote grava com 4 casas
PROTECTED_KEYS = {"genero", "gender", "sexo", "idade", "age", "data_nascimento", "dateofbirth",
                  "estado_civil", "maritalstatus", "n_dependentes", "nrofdependants"}
SITUATIONS = ["acima_do_justo", "abaixo_do_justo", "dentro_da_margem", "revisao_manual"]


def pick_ids(batch: pd.DataFrame, n: int = 20, seed: int = 7) -> list[str]:
    """Amostra estratificada pela situação do preço (todas as situações aparecem)."""
    per = max(1, n // len(SITUATIONS))
    ids: list[str] = []
    for s in SITUATIONS:
        part = batch[batch["situacao_preco"] == s]
        ids += part.sample(min(per, len(part)), random_state=seed)["contrato_id"].astype(str).tolist()
    rest = batch[~batch["contrato_id"].astype(str).isin(ids)]
    ids += rest.sample(min(max(0, n - len(ids)), len(rest)), random_state=seed)["contrato_id"].astype(str).tolist()
    return ids[:n]


def _keys(obj, out: set[str]) -> set[str]:
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.add(str(k).lower())
            _keys(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _keys(v, out)
    return out


def problems(analysis: dict, batch_row: dict) -> list[str]:
    """Lista do que não bate entre a análise ao vivo e a linha do lote (vazia = ok)."""
    found: list[str] = []
    r = analysis.get("resultado") or {}
    situation = r.get("situacao_preco")
    if situation != batch_row.get("situacao_preco"):
        found.append(f"situação {situation} ≠ lote {batch_row.get('situacao_preco')} "
                     f"(cobrado {r.get('juro_cobrado')} · lote {batch_row.get('juro_cobrado')}; "
                     f"IC da PD {r.get('pd_ic95')} · lote {[batch_row.get('pd_ic95_min'), batch_row.get('pd_ic95_max')]})")
    if situation != "revisao_manual":
        for field in ("pd", "juro_justo", "juro_justo_min", "juro_justo_max"):
            live, ref = r.get(field), batch_row.get(field)
            if live is None or ref is None or pd.isna(ref) or abs(float(live) - float(ref)) > TOLERANCE:
                found.append(f"{field} {live} ≠ lote {ref}")
        if not r.get("motivos"):
            found.append("sem motivos (SHAP)")
        if any(str(m.get("variavel", "")).lower() == "pais" for m in r.get("motivos") or []):
            found.append("país apareceu entre os motivos")
    names = _keys(analysis, set()) | {str(v.get("variavel", "")).lower() for v in analysis.get("dados_considerados") or []}
    leaked = names & PROTECTED_KEYS
    if leaked:
        found.append(f"atributo protegido na resposta: {sorted(leaked)}")
    prov = analysis.get("procedencia") or {}
    for field in ("versao_modelo", "pacote_hash", "incerteza", "calculado_em"):
        if not prov.get(field):
            found.append(f"procedência sem {field}")
    if prov.get("origem_dados") and "banco" not in str(prov["origem_dados"]).lower():
        found.append(f"origem dos dados inesperada: {prov['origem_dados']}")
    return found


def main(argv: list[str] | None = None) -> int:
    import requests

    from src.api import portfolio

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--lote", type=Path, default=portfolio.PORTFOLIO_DIR)
    args = ap.parse_args(argv)

    batch = portfolio.load_portfolio(args.lote)
    if batch is None:
        print(f"Falta {portfolio.PORTFOLIO_FILE} em {args.lote}.")
        return 2
    ids = pick_ids(batch, args.n)
    failures = 0
    for cid in ids:
        row = portfolio.find_contract(batch, cid)
        try:
            resp = requests.get(f"{args.api}/contracts/{cid}/analysis", timeout=60)
        except requests.exceptions.RequestException as exc:
            print(f"ERRO  {cid}: API não respondeu ({exc})")
            return 2
        if resp.status_code != 200:
            failures += 1
            print(f"FALHA {cid}: HTTP {resp.status_code} {resp.text[:120]}")
            continue
        found = problems(resp.json(), row)
        failures += bool(found)
        print(("OK    " if not found else "FALHA ") + f"{cid} [{row['situacao_preco']}]"
              + ("" if not found else ": " + "; ".join(found)))
    print(f"\n{len(ids) - failures}/{len(ids)} contratos conferidos sem divergência.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
