"""Tabelas pequenas e inventadas, válidas pelas regras de src/dados/validacao.py.

Os testes copiam estas tabelas e estragam um campo por vez. Nada aqui usa banco nem o CSV.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.dados.carga_bondora import TABELAS

ANOS = [2013, 2015, 2016, 2016]          # um contrato por linha
STATUS = ["Repaid", "Late", "Repaid", "Current"]


def _guid(i: int) -> str:
    return f"{i:08x}-0000-4000-8000-{i:012x}"


def _hex16(i: int) -> str:
    return f"{i:016x}"


def _vazia(tabela: str, n: int) -> pd.DataFrame:
    """DataFrame com TODAS as colunas da tabela (as mesmas da carga), vazias."""
    df = pd.DataFrame(index=range(n))
    for c in TABELAS[tabela]:
        if c.tipo == "data":
            df[c.db] = pd.Series([pd.NaT] * n, dtype="datetime64[ns]")
        else:
            df[c.db] = pd.Series([np.nan] * n, dtype="float64")
    return df


def _meses(ini: str, fim: str) -> pd.DatetimeIndex:
    return pd.date_range(ini, fim, freq="MS")


def tabelas_validas() -> dict[str, pd.DataFrame]:
    n = len(ANOS)
    ids = [_guid(i) for i in range(n)]
    conc = [pd.Timestamp(f"{a}-03-15") for a in ANOS]

    e = _vazia("emprestimo", n)
    e["loan_id"] = ids
    e["numero"] = [1, 2, 3, 4]
    e["status"] = STATUS
    e["data_referencia"] = pd.Timestamp("2021-07-20")
    e["data_emprestimo"] = pd.Series(conc)
    e["data_pedido"] = pd.Series([d - pd.Timedelta(days=1) for d in conc])
    e["data_primeira_parcela"] = pd.Series([d + pd.Timedelta(days=30) for d in conc])
    e["data_vencimento_original"] = pd.Series([d + pd.DateOffset(months=12) for d in conc])
    e["data_default"] = pd.Series([pd.NaT, conc[1] + pd.Timedelta(days=200), pd.NaT, pd.NaT])
    e["valor_solicitado"] = 1000.0
    e["valor_concedido"] = 1000.0
    e["juro_aa"] = 30.0
    e["prazo_meses"] = 12

    c = _vazia("cliente", n)
    c["loan_id"] = ids
    c["cliente_id"] = [_hex16(i) for i in range(n)]
    c["genero"] = [0, 1, 0, 1]
    c["idade"] = 30
    c["pais"] = ["EE", "FI", "ES", "EE"]
    c["renda_total"] = 1000.0

    h = _vazia("historico_credito", n)
    h["loan_id"] = ids
    h["n_emprestimos_anteriores"] = 0
    h["passivos_total"] = 100.0

    janela = _meses("2009-01-01", "2021-07-01")
    euribor = pd.DataFrame({"mes": janela, "euribor_3m": 0.5, "euribor_12m": 0.6})
    selic = pd.DataFrame({"mes": janela, "selic_aa": 10.0, "selic_meta_aa": 10.0})
    bc = pd.DataFrame({"mes": _meses("2011-03-01", "2021-07-01"), "taxa_aa": 80.0})

    vw = pd.DataFrame({
        "loan_id": ids,
        "cliente_id": c["cliente_id"],
        "pais": c["pais"],
        "ano": ANOS,
        "inadimplente": [0, 1, 0, 0],
        "reestruturado": [False] * n,
        "conjunto": ["treino" if a <= 2015 else "teste" for a in ANOS],
    })
    recebido_principal = [1000.0, 400.0, 1000.0, 1000.0]
    recebido_juros = [200.0, 50.0, 150.0, 100.0]
    retorno = pd.DataFrame({
        "loan_id": ids,
        "ano": ANOS,
        "pais": c["pais"],
        "conjunto": vw["conjunto"],
        "reestruturado": [False] * n,
        "inadimplente": [0, 1, 0, 0],
        "valor_concedido": [1000.0] * n,
        "prazo_meses": [12] * n,
        "juro_aa": [30.0] * n,
        "duracao_meses": [11.0, 20.0, 12.0, np.nan],
        "principal_recebido": recebido_principal,
        "juros_recebidos": recebido_juros,
        "recebido_total": [a + b for a, b in zip(recebido_principal, recebido_juros)],
        "resultado_eur": [a + b - 1000.0 for a, b in zip(recebido_principal, recebido_juros)],
        "retorno_realizado": [(a + b - 1000.0) / 1000.0 for a, b in zip(recebido_principal, recebido_juros)],
        "principal_perdido": [max(1000.0 - a, 0.0) for a in recebido_principal],
        "recuperado_eur": [0.0, 150.0, 0.0, 0.0],
    })
    agora = pd.Timestamp("2026-11-05 14:00", tz="UTC")
    decisoes = pd.DataFrame({
        "decisao_id": [1, 2],
        "registrada_em": [agora, agora + pd.Timedelta(hours=1)],
        "requisicao_id": [None, None],
        "contrato_id": [ids[0], "EXEMPLO-1"],                  # um da carteira e uma simulação
        "origem": ["carteira", "simulacao"],
        "analista": ["analista.teste", "analista.teste"],
        "decisao": ["manter_preco", "revisar_preco"],
        "justificativa": ["dentro da margem", "acima do justo para o risco"],
        "taxa_proposta": [np.nan, 0.162],
        "recomendacao_sistema": ["manter_preco", "revisar_preco"],
        "situacao_preco": ["dentro_da_margem", "acima_do_justo"],
        "pd": [0.18, 0.30],
        "faixa": ["C", "D"],
        "juro_cobrado": [0.249, 0.45],
        "juro_justo": [0.25, 0.30],
        "juro_justo_min": [0.22, 0.27],
        "juro_justo_max": [0.28, 0.33],
        "versao_modelo": ["teste", "teste"],
        "versao_parecer": ["v1", "v1"],
        "origem_parecer": ["llm", "template"],
        "prever_json": [{"pd": 0.18, "faixa": "C"}, {"pd": 0.30, "faixa": "D"}],
        "parecer_json": [{"resumo": "ok"}, None],
    })
    decisao_atual = decisoes.loc[decisoes["origem"] == "carteira",
                                 ["decisao_id", "contrato_id", "registrada_em", "analista", "decisao",
                                  "justificativa", "taxa_proposta", "recomendacao_sistema",
                                  "situacao_preco"]].reset_index(drop=True)
    return {"emprestimo": e, "cliente": c, "historico_credito": h, "euribor_mensal": euribor,
            "selic_mensal": selic, "bc_credito_pessoal_mensal": bc, "vw_base_modelagem": vw,
            "vw_retorno_realizado": retorno, "decisao_analista": decisoes,
            "vw_decisao_atual": decisao_atual}
