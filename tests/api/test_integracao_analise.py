"""Integração com dados reais: banco + pacote do modelo + lote da carteira.

Roda só quando os três existem (máquina do grupo com docker compose up); no CI é pulado.
Abre contratos reais pela rota e compara com o lote (scripts/conferir_analise.py)."""
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("xgboost")
from fastapi.testclient import TestClient  # noqa: E402

import src.api.main as api  # noqa: E402
from src.api import database, portfolio  # noqa: E402
from scripts.conferir_analise import pick_ids, problems  # noqa: E402

pytestmark = pytest.mark.skipif(
    not (api.PACOTE_PADRAO.exists() and (portfolio.PORTFOLIO_DIR / portfolio.PORTFOLIO_FILE).exists()
         and database.database_available()),
    reason="precisa do banco, do pacote do modelo e do lote da carteira")


@pytest.fixture(scope="module")
def batch():
    return portfolio.load_portfolio()


@pytest.mark.parametrize("position", range(8))
def test_live_analysis_matches_the_batch(batch, position):
    cid = pick_ids(batch, 8)[position]
    resp = TestClient(api.app).get(f"/contracts/{cid}/analysis")
    assert resp.status_code == 200, resp.text
    assert problems(resp.json(), portfolio.find_contract(batch, cid)) == []


def test_unknown_id_is_404():
    assert TestClient(api.app).get("/contracts/nao-existe-000/analysis").status_code == 404
