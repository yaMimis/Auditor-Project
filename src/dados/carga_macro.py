#!/usr/bin/env python3
"""Carga das séries mensais de custo do dinheiro e de referência de mercado:
`euribor_mensal`, `selic_mensal` e `bc_credito_pessoal_mensal`.

Uso (na raiz do projeto, com o banco no ar, o .env preenchido e a carga do Bondora já feita):
    python src/dados/carga_macro.py --ddl db/02_schema_macro.sql

Por padrão lê estes arquivos de data/raw/ (use as opções --euribor-12m, --euribor-3m,
--selic, --selic-meta e --bc-credito para outros caminhos):
    ECB_Euribor_Serie-Mensal-12-Meses_csv.csv   Euribor 12 meses (BCE, série ...EURIBOR1YD_...)
    ECB_Euribor_Serie-Mensal-3-Meses.csv        Euribor 3 meses  (BCE, série ...EURIBOR3MD_...)
    BC-Selic_Acumulada_Mes_Anuzalizada_base252.csv   Selic acumulada no mês anualizada base 252
                                                (Banco Central, SGS 4189, % ao ano)
    BC-Meta_Selic_Mensal.csv                    meta Selic mensal (opcional, só conferência)
    bcdata.sgs.20742.csv                        taxa média do crédito pessoal não consignado,
                                                pessoas físicas (Banco Central, SGS 20742, % ao ano
                                                efetiva, desde 03/2011; opcional; também aceita o nome
                                                bcdata_sgs_20742.csv)

O que faz:
  * confere que cada arquivo é mesmo a série esperada (cabeçalho do BCE; Selic em % ao
    ano e não em % ao mês, o que denunciaria a série 4390 no lugar da 4189);
  * normaliza o mês para o 1º dia (os arquivos do BCE trazem o último dia);
  * aborta, sem tocar no banco, se faltar qualquer mês da janela 01/2009 a 07/2021
    em qualquer série;
  * carrega o histórico completo dos arquivos (o recorte é feito na consulta),
    via COPY, numa única transação, recarregando do zero a cada execução;
  * a série 20742 é opcional: se o arquivo não existir, a carga a pula e deixa a tabela como está.
    Ela só existe a partir de 03/2011, então 2009 a 02/2011 ficam sem benchmark (decisão do
    projeto; não emendar com a série de crédito pessoal total, que inclui o consignado). Aborta
    se faltar algum mês de 03/2011 a 07/2021 ou se a série parecer estar em % ao mês;
  * se a tabela `emprestimo` já existir, confere que todo contrato tem a Euribor e a Selic
    do mês da concessão e, com a 20742 carregada, a taxa do BC em todo contrato de 03/2011 em
    diante (se faltar alguma, desfaz tudo).

Importa funções de carga_bondora.py: mantenha os dois arquivos na mesma pasta.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from carga_bondora import _carregar_env, _conectar, _copy

JANELA_INI = "2009-01"
JANELA_FIM = "2021-07"
BC_INI = "2011-03"  # a série 20742 do BC começa aqui
MESES_PT = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
PASTA_PADRAO = Path("data/raw")
NOMES_BC_20742 = ("bcdata.sgs.20742.csv", "bcdata_sgs_20742.csv")


# --------------------------------------------------------------------------
# Leitura (cada função devolve uma Series indexada pelo 1º dia do mês)
# --------------------------------------------------------------------------
def _ler_euribor(caminho: Path, chave: str, nome: str) -> pd.Series:
    df = pd.read_csv(caminho, dtype=str, encoding="utf-8-sig")
    if df.shape[1] < 3 or "DATE" not in df.columns or chave not in df.columns[2]:
        sys.exit(f"ERRO: {caminho.name} não parece a série {nome} "
                 f"(esperava '{chave}' no cabeçalho da 3ª coluna).")
    mes = pd.to_datetime(df["DATE"], format="%Y-%m-%d").dt.to_period("M").dt.to_timestamp()
    valor = pd.to_numeric(df.iloc[:, 2], errors="coerce")
    s = pd.Series(valor.values, index=mes, name=nome)
    if s.index.duplicated().any():
        sys.exit(f"ERRO: {caminho.name} tem meses repetidos.")
    return s


def _ler_sgs(caminho: Path, nome: str) -> pd.Series:
    df = pd.read_csv(caminho, sep=";", dtype=str, encoding="utf-8-sig")
    if list(df.columns) != ["data", "valor"]:
        sys.exit(f"ERRO: {caminho.name} deveria ter as colunas \"data\";\"valor\" (SGS do Banco Central).")
    mes = pd.to_datetime(df["data"], format="%d/%m/%Y").dt.to_period("M").dt.to_timestamp()
    valor = pd.to_numeric(df["valor"].str.replace(",", ".", regex=False), errors="coerce")
    s = pd.Series(valor.values, index=mes, name=nome)
    if s.index.duplicated().any():
        sys.exit(f"ERRO: {caminho.name} tem meses repetidos.")
    return s


def _ler_selic(caminho: Path) -> pd.Series:
    s = _ler_sgs(caminho, "selic_aa")
    janela = s[JANELA_INI:JANELA_FIM]
    if janela.notna().any() and janela.max() < 3:
        sys.exit(f"ERRO: {caminho.name} parece estar em % ao MÊS (máximo {janela.max():.2f} na janela). "
                 "Use a série 4189 (anualizada base 252), não a 4390.")
    return s


def _ler_bc(caminho: Path) -> pd.Series:
    s = _ler_sgs(caminho, "taxa_aa")
    janela = s[BC_INI:JANELA_FIM]
    if janela.notna().any() and janela.median() < 15:
        sys.exit(f"ERRO: {caminho.name} parece estar em % ao MÊS (mediana {janela.median():.2f} na janela). "
                 "Use a série 20742 (% ao ano), não a 25464. Confira também que o código é 20742 "
                 "(crédito pessoal NÃO consignado), e não o de crédito pessoal total.")
    return s


def _ler_meta(caminho: Path) -> pd.Series:
    df = pd.read_csv(caminho, dtype=str, encoding="utf-8-sig")
    saida = {}
    for _, linha in df.iterrows():
        for i, nome in enumerate(MESES_PT, start=1):
            v = linha.get(nome)
            if isinstance(v, str) and "%" in v:
                saida[pd.Timestamp(int(linha["Ano"]), i, 1)] = float(
                    v.replace("%", "").replace(",", ".").strip())
    return pd.Series(saida, name="selic_meta_aa").sort_index()


# --------------------------------------------------------------------------
# Validação e carga
# --------------------------------------------------------------------------
def _checar_janela(series: dict[str, pd.Series], ini: str = JANELA_INI,
                   fim: str = JANELA_FIM) -> pd.DatetimeIndex:
    janela = pd.period_range(ini, fim, freq="M").to_timestamp()
    for nome, s in series.items():
        faltam = [d.strftime("%Y-%m") for d in janela if pd.isna(s.get(d, np.nan))]
        if faltam:
            sys.exit(f"ERRO: a série {nome} não cobre a janela {ini} a {fim}; "
                     f"faltam {len(faltam)} meses (ex.: {', '.join(faltam[:5])}).")
    return janela


def _preparar(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_index().rename_axis("mes").reset_index()
    df["mes"] = df["mes"].dt.strftime("%Y-%m-%d")
    return df


def carregar(dsn: str, ddl: Path | None, arq: dict[str, Path | None]) -> None:
    e12 = _ler_euribor(arq["euribor_12m"], "EURIBOR1YD_", "euribor_12m")
    e3 = _ler_euribor(arq["euribor_3m"], "EURIBOR3MD_", "euribor_3m")
    selic = _ler_selic(arq["selic"])
    meta = _ler_meta(arq["selic_meta"]) if arq["selic_meta"] else None
    bc = _ler_bc(arq["bc_credito"]) if arq.get("bc_credito") else None

    series = {"euribor_12m": e12, "euribor_3m": e3, "selic_aa": selic}
    if meta is not None:
        series["selic_meta_aa"] = meta
    janela = _checar_janela(series)
    if bc is not None:
        _checar_janela({"bc_credito (20742)": bc}, BC_INI, JANELA_FIM)

    euribor = _preparar(pd.concat([e3, e12], axis=1))
    selic_df = _preparar(pd.concat([selic] + ([meta] if meta is not None else []), axis=1))
    bc_df = _preparar(pd.concat([bc], axis=1)) if bc is not None else None
    ini = janela[0].date().isoformat()
    fim = janela[-1].date().isoformat()
    bc_ini = f"{BC_INI}-01"

    conn = _conectar(dsn)
    try:
        with conn, conn.cursor() as cur:
            if ddl:
                cur.execute(Path(ddl).read_text(encoding="utf-8"))
            cur.execute("TRUNCATE euribor_mensal, selic_mensal")
            _copy(cur, "euribor_mensal", list(euribor.columns), euribor)
            _copy(cur, "selic_mensal", list(selic_df.columns), selic_df)
            if bc_df is not None:
                cur.execute("TRUNCATE bc_credito_pessoal_mensal")
                _copy(cur, "bc_credito_pessoal_mensal", list(bc_df.columns), bc_df)

            n = {}
            conferir = [("euribor_mensal", len(euribor)), ("selic_mensal", len(selic_df))]
            if bc_df is not None:
                conferir.append(("bc_credito_pessoal_mensal", len(bc_df)))
            for tabela, esperado in conferir:
                cur.execute(f"SELECT count(*) FROM {tabela}")
                n[tabela] = cur.fetchone()[0]
                if n[tabela] != esperado:
                    raise RuntimeError(f"{tabela}: {n[tabela]} linhas no banco, {esperado} no arquivo")

            cur.execute("SELECT to_regclass('emprestimo') IS NOT NULL")
            sem_taxa = sem_bc = antes_bc = None
            if cur.fetchone()[0]:
                cur.execute(
                    "SELECT count(*) FROM emprestimo e "
                    "LEFT JOIN euribor_mensal t ON t.mes = date_trunc('month', e.data_emprestimo)::date "
                    "LEFT JOIN selic_mensal s ON s.mes = date_trunc('month', e.data_emprestimo)::date "
                    "WHERE e.data_emprestimo IS NOT NULL "
                    "AND (t.euribor_3m IS NULL OR t.euribor_12m IS NULL OR s.selic_aa IS NULL)"
                )
                sem_taxa = cur.fetchone()[0]
                if sem_taxa:
                    raise RuntimeError(f"{sem_taxa} contratos sem Euribor ou Selic no mês da concessão")
                if bc_df is not None:
                    cur.execute(
                        "SELECT count(*) FROM emprestimo e "
                        "LEFT JOIN bc_credito_pessoal_mensal b ON b.mes = date_trunc('month', e.data_emprestimo)::date "
                        f"WHERE e.data_emprestimo >= '{bc_ini}' AND b.taxa_aa IS NULL"
                    )
                    sem_bc = cur.fetchone()[0]
                    if sem_bc:
                        raise RuntimeError(f"{sem_bc} contratos de {BC_INI} em diante sem a taxa do BC "
                                           "no mês da concessão")
                    cur.execute(f"SELECT count(*) FROM emprestimo WHERE data_emprestimo < '{bc_ini}'")
                    antes_bc = cur.fetchone()[0]
    finally:
        conn.close()

    print("=" * 64)
    print(f"Janela do projeto: {JANELA_INI} a {JANELA_FIM} ({len(janela)} meses, sem buracos)")
    print(f"Linhas em euribor_mensal: {n['euribor_mensal']:>6,}   (histórico completo do arquivo)")
    print(f"Linhas em selic_mensal:   {n['selic_mensal']:>6,}")
    print(f"\nNa janela ({ini} a {fim}), em % ao ano:")
    for nome, s in series.items():
        j = s[ini:fim]
        print(f"  {nome:<14} min {j.min():>7.2f} | máx {j.max():>7.2f} | meses negativos: {int((j < 0).sum())}")
    if meta is not None:
        dif = (selic[ini:fim] - meta[ini:fim]).abs()
        print(f"\nConferência Selic 4189 x meta (1º dia do mês): |dif| média {dif.mean():.2f} p.p., "
              f"máxima {dif.max():.2f} p.p.")
    if bc is None:
        print("\nSérie 20742 do BC não carregada (arquivo não informado ou ausente).")
    else:
        jb = bc[bc_ini:fim]
        print(f"\nBC, crédito pessoal não consignado (20742), {BC_INI} a {JANELA_FIM} "
              f"({len(jb)} meses, sem buracos), em % ao ano:")
        print(f"  min {jb.min():.2f} | mediana {jb.median():.2f} | máx {jb.max():.2f}")
        print(f"Linhas em bc_credito_pessoal_mensal: {n['bc_credito_pessoal_mensal']:>6,}")
    if sem_taxa is None:
        print("\nTabela emprestimo ainda não existe: conferência de contratos sem taxa não feita.")
    else:
        print("\nContratos sem Euribor ou Selic no mês da concessão: 0")
        if sem_bc is not None:
            print(f"Contratos de {BC_INI} em diante sem a taxa do BC: 0")
            print(f"Contratos anteriores a {BC_INI}, sem benchmark do BC (decisão do projeto): {antes_bc:,}")
    print("=" * 64)


def main() -> None:
    _carregar_env()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dsn", default=os.environ.get("DATABASE_URL"),
                    help="padrão: variável de ambiente DATABASE_URL")
    ap.add_argument("--ddl", type=Path, help="arquivo .sql aplicado antes da carga")
    ap.add_argument("--euribor-12m", type=Path,
                    default=PASTA_PADRAO / "ECB_Euribor_Serie-Mensal-12-Meses.csv")
    ap.add_argument("--euribor-3m", type=Path,
                    default=PASTA_PADRAO / "ECB_Euribor_Serie-Mensal-3-Meses.csv")
    ap.add_argument("--selic", type=Path,
                    default=PASTA_PADRAO / "BC-Selic_Acumulada_Mes_Anuzalizada_base252.csv")
    ap.add_argument("--selic-meta", type=Path, default=PASTA_PADRAO / "BC-Meta_Selic_Mensal.csv",
                    help="opcional; se o arquivo não existir, a conferência é pulada")
    ap.add_argument("--bc-credito", type=Path, default=None,
                    help="opcional; série SGS 20742 do BC (padrão: data/raw/bcdata.sgs.20742.csv); "
                         "se o arquivo não existir, a carga a pula")
    a = ap.parse_args()
    if not a.dsn:
        sys.exit("ERRO: informe --dsn ou defina DATABASE_URL.")
    obrigatorios = {"euribor_12m": a.euribor_12m, "euribor_3m": a.euribor_3m, "selic": a.selic}
    for nome, caminho in obrigatorios.items():
        if not caminho.is_file():
            sys.exit(f"ERRO: arquivo não encontrado: {caminho}")
    bc = a.bc_credito or next((PASTA_PADRAO / n for n in NOMES_BC_20742 if (PASTA_PADRAO / n).is_file()), None)
    if a.bc_credito is not None and not a.bc_credito.is_file():
        sys.exit(f"ERRO: arquivo não encontrado: {a.bc_credito}")
    arquivos = dict(obrigatorios,
                    selic_meta=a.selic_meta if a.selic_meta.is_file() else None,
                    bc_credito=bc)
    try:
        carregar(a.dsn, a.ddl, arquivos)
    except RuntimeError as erro:
        sys.exit(f"ERRO: {erro}. Nada foi gravado no banco.")


if __name__ == "__main__":
    main()
