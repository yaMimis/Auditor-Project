"""Testes de src/dados/relatorio_qualidade.py, sem banco."""
from src.dados.relatorio_qualidade import gerar_relatorio
from src.dados.validacao import validar_tabelas
from tests.dados._dados_exemplo import tabelas_validas


def test_relatorio_de_dados_limpos():
    t = tabelas_validas()
    md = gerar_relatorio(t, validar_tabelas(t, parcial=True), hoje="2026-01-01")
    assert md.startswith("# Qualidade dos dados")
    assert "Gerado em 2026-01-01" in md
    assert "Nenhum erro." in md and "Nenhum alerta." in md
    for secao in ("Proporção de mulheres por ano e país", "Zeros no lugar de vazio",
                  "Colunas em branco depois de 2017"):
        assert secao in md


def test_relatorio_mostra_alerta_com_acao_e_percentual():
    t = tabelas_validas()
    t["cliente"].loc[0, "idade"] = 15
    md = gerar_relatorio(t, validar_tabelas(t, parcial=True), hoje="2026-01-01")
    assert "`idade`" in md
    assert "25,00%" in md                       # 1 de 4 contratos
    assert "Marcar." in md                      # o que fazer com o alerta
    assert "Nenhum erro." in md


def test_relatorio_lista_erro():
    t = tabelas_validas()
    t["emprestimo"].loc[0, "juro_aa"] = 0
    md = gerar_relatorio(t, validar_tabelas(t, parcial=True), hoje="2026-01-01")
    assert "Nenhum erro." not in md
    assert "juro_aa" in md
