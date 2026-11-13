"""Testes de src/dados/validacao.py, sem banco: tabelas pequenas e inventadas.

Cada caso estraga UM campo de uma tabela válida e confere que a regra certa acusa.
"""
import pandas as pd

from src.dados.validacao import validar_tabelas
from tests.dados._dados_exemplo import tabelas_validas


def _achou(res, tabela, trecho, severidade="erro"):
    r = res[(res["severidade"] == severidade) & (res["tabela"] == tabela)]
    return bool((r["coluna"].astype(str).str.contains(trecho, regex=False)
                 | r["regra"].astype(str).str.contains(trecho, regex=False)).any())


def _erros(res):
    return res[res["severidade"] == "erro"]


def test_dados_validos_nao_geram_erro_nem_alerta():
    res = validar_tabelas(tabelas_validas(), parcial=True)
    assert res.empty, f"a base de exemplo deveria ser limpa:\n{res.to_string()}"


# --- cada regra de erro pega o problema que lhe cabe ------------------------------------
def _loan_id_duplicado(t):
    t["emprestimo"].loc[1, "loan_id"] = t["emprestimo"].loc[0, "loan_id"]


def _idade_negativa(t):
    t["cliente"].loc[0, "idade"] = -5


def _status_invalido(t):
    t["emprestimo"].loc[0, "status"] = "Foo"


def _pedido_depois_da_concessao(t):
    e = t["emprestimo"]
    e.loc[0, "data_pedido"] = e.loc[0, "data_emprestimo"] + pd.Timedelta(days=10)


def _default_antes_da_concessao(t):
    e = t["emprestimo"]
    e.loc[1, "data_default"] = e.loc[1, "data_emprestimo"] - pd.Timedelta(days=30)


def _juro_zero(t):
    t["emprestimo"].loc[0, "juro_aa"] = 0


def _prazo_61(t):
    t["emprestimo"].loc[0, "prazo_meses"] = 61


def _pd_maior_que_1(t):
    t["emprestimo"].loc[0, "pd_bondora"] = 1.7


def _genero_7(t):
    t["cliente"].loc[0, "genero"] = 7


def _cliente_id_fora_do_padrao(t):
    t["cliente"].loc[0, "cliente_id"] = "ABC"


def _pais_invalido(t):
    t["cliente"].loc[0, "pais"] = "BR"


def _coluna_removida(t):
    t["emprestimo"] = t["emprestimo"].drop(columns=["juro_aa"])


def _coluna_extra(t):
    t["emprestimo"]["coluna_nova"] = 1


def _euribor_fora_da_faixa(t):
    t["euribor_mensal"].loc[10, "euribor_12m"] = 9.0


def _selic_fora_do_dia_1(t):
    t["selic_mensal"].loc[10, "mes"] = t["selic_mensal"].loc[10, "mes"] + pd.Timedelta(days=14)


def _falta_mes_de_euribor(t):
    e = t["euribor_mensal"]
    t["euribor_mensal"] = e[e["mes"] != pd.Timestamp("2015-06-01")].reset_index(drop=True)


def _mesmo_cliente_no_treino_e_no_teste(t):
    v = t["vw_base_modelagem"]
    v.loc[v["conjunto"] == "teste", "cliente_id"] = v.loc[v["conjunto"] == "treino", "cliente_id"].iloc[0]


def _teste_fora_de_2016(t):
    v = t["vw_base_modelagem"]
    v.loc[v["conjunto"] == "teste", "ano"] = 2015


def _tabela_ausente(t):
    del t["vw_base_modelagem"]


def _decisao_fora_do_dominio(t):
    t["decisao_analista"].loc[0, "decisao"] = "foo"


def _justificativa_vazia(t):
    t["decisao_analista"].loc[0, "justificativa"] = "   "


def _json_com_genero_aninhado(t):
    t["decisao_analista"].at[1, "prever_json"] = {"entrada": {"gender": 1}, "pd": 0.3}


def _decisao_da_carteira_que_nao_existe(t):
    t["decisao_analista"].loc[0, "contrato_id"] = "nao-existe-na-carteira"


def _simulacao_com_contrato_da_carteira(t):
    t["decisao_analista"].loc[1, "contrato_id"] = t["emprestimo"].loc[1, "loan_id"]


def _view_da_decisao_atual_repetida(t):
    v = t["vw_decisao_atual"]
    t["vw_decisao_atual"] = pd.concat([v, v], ignore_index=True)


def _decisao_registrada_no_futuro(t):
    t["decisao_analista"].loc[0, "registrada_em"] = pd.Timestamp("2099-01-01", tz="UTC")


def _numeros_nulos_fora_da_revisao_manual(t):
    t["decisao_analista"].loc[0, "pd"] = float("nan")


def _recebido_nao_fecha(t):
    t["vw_retorno_realizado"].loc[0, "recebido_total"] = 9999.0


def _retorno_menor_que_menos_1(t):
    t["vw_retorno_realizado"].loc[0, "retorno_realizado"] = -1.5


def _recuperacao_maior_que_o_recebido(t):
    t["vw_retorno_realizado"].loc[1, "recuperado_eur"] = 900.0


def _retorno_com_contrato_a_menos(t):
    t["vw_retorno_realizado"] = t["vw_retorno_realizado"].iloc[:-1]


def _desfecho_com_loan_id_repetido(t):
    t["vw_desfecho_contrato"].loc[1, "loan_id"] = t["vw_desfecho_contrato"].loc[0, "loan_id"]


def _desfecho_com_contrato_a_menos(t):
    t["vw_desfecho_contrato"] = t["vw_desfecho_contrato"].iloc[:-1]


def _sem_desfecho_mas_com_inadimplente(t):
    d = t["vw_desfecho_contrato"]
    d.loc[0, "tem_desfecho"] = False
    d.loc[0, "motivo_sem_desfecho"] = "concedido depois de 2016"


def _com_desfecho_e_com_motivo(t):
    t["vw_desfecho_contrato"].loc[0, "motivo_sem_desfecho"] = "concedido depois de 2016"


def _motivo_fora_do_combinado(t):
    d = t["vw_desfecho_contrato"]
    d.loc[0, "tem_desfecho"] = False
    d.loc[0, "motivo_sem_desfecho"] = "sem dados"


CASOS = [
    ("loan_id duplicado", _loan_id_duplicado, "emprestimo", "loan_id"),
    ("idade negativa", _idade_negativa, "cliente", "idade"),
    ("status fora do domínio", _status_invalido, "emprestimo", "status"),
    ("pedido depois da concessão", _pedido_depois_da_concessao, "emprestimo", "data_pedido <= data_emprestimo"),
    ("default antes da concessão", _default_antes_da_concessao, "emprestimo", "data_emprestimo <= data_default"),
    ("juro_aa igual a zero", _juro_zero, "emprestimo", "juro_aa"),
    ("prazo de 61 meses", _prazo_61, "emprestimo", "prazo_meses"),
    ("pd_bondora maior que 1", _pd_maior_que_1, "emprestimo", "pd_bondora"),
    ("genero = 7", _genero_7, "cliente", "genero"),
    ("cliente_id fora do padrão", _cliente_id_fora_do_padrao, "cliente", "cliente_id"),
    ("país fora do domínio", _pais_invalido, "cliente", "pais"),
    ("coluna removida do banco", _coluna_removida, "emprestimo", "juro_aa"),
    ("coluna extra no banco", _coluna_extra, "emprestimo", "coluna_nova"),
    ("Euribor fora da faixa", _euribor_fora_da_faixa, "euribor_mensal", "euribor_12m"),
    ("mês fora do dia 1", _selic_fora_do_dia_1, "selic_mensal", "primeiro_dia_do_mes"),
    ("mês faltando na Euribor", _falta_mes_de_euribor, "(cruzamento)", "euribor_mensal: meses da janela"),
    ("mesmo cliente no treino e no teste", _mesmo_cliente_no_treino_e_no_teste, "(cruzamento)",
     "cliente no treino e no teste"),
    ("teste com concessão fora de 2016", _teste_fora_de_2016, "vw_base_modelagem", "teste so com concessoes de 2016"),
    ("view ausente no banco", _tabela_ausente, "vw_base_modelagem", "ausente"),
    ("decisão fora do domínio", _decisao_fora_do_dominio, "decisao_analista", "decisao"),
    ("justificativa vazia", _justificativa_vazia, "decisao_analista", "justificativa"),
    ("JSON da decisão com gênero em nível aninhado", _json_com_genero_aninhado, "decisao_analista",
     "JSON sem genero nem idade"),
    ("decisão da carteira com contrato inexistente", _decisao_da_carteira_que_nao_existe, "(cruzamento)",
     "contrato 'carteira' que nao existe"),
    ("simulação com contrato que existe na carteira", _simulacao_com_contrato_da_carteira, "(cruzamento)",
     "contrato 'simulacao' que existe"),
    ("decisão atual repetida na view", _view_da_decisao_atual_repetida, "vw_decisao_atual", "contrato_id"),
    ("decisão registrada no futuro", _decisao_registrada_no_futuro, "decisao_analista",
     "registrada_em nao esta no futuro"),
    ("pd nulo fora da revisão manual", _numeros_nulos_fora_da_revisao_manual, "decisao_analista",
     "numeros obrigatorios fora de revisao_manual"),
    ("recebido_total não fecha com principal + juros", _recebido_nao_fecha, "vw_retorno_realizado",
     "recebido_total = principal_recebido + juros_recebidos"),
    ("retorno realizado menor que -100%", _retorno_menor_que_menos_1, "vw_retorno_realizado", "retorno_realizado"),
    ("recuperação maior que o recebido", _recuperacao_maior_que_o_recebido, "vw_retorno_realizado",
     "recuperado_eur <= recebido_total"),
    ("view de retorno com contrato a menos", _retorno_com_contrato_a_menos, "(cruzamento)",
     "vw_retorno_realizado com contratos diferentes"),
    ("desfecho com loan_id repetido", _desfecho_com_loan_id_repetido, "vw_desfecho_contrato", "loan_id"),
    ("desfecho com contrato a menos", _desfecho_com_contrato_a_menos, "(cruzamento)",
     "vw_desfecho_contrato com contratos diferentes de emprestimo"),
    ("sem desfecho mas com inadimplente", _sem_desfecho_mas_com_inadimplente, "vw_desfecho_contrato",
     "inadimplente so preenchido quando ha desfecho"),
    ("sem desfecho fora da vw_retorno_realizado", _sem_desfecho_mas_com_inadimplente, "(cruzamento)",
     "contratos com desfecho diferentes da vw_retorno_realizado"),
    ("com desfecho e com motivo", _com_desfecho_e_com_motivo, "vw_desfecho_contrato",
     "motivo_sem_desfecho vazio so quando ha desfecho"),
    ("motivo fora do combinado", _motivo_fora_do_combinado, "vw_desfecho_contrato", "motivo_sem_desfecho"),
]


def test_cada_regra_de_erro_pega_o_problema():
    nao_pegou = []
    for nome, estraga, tabela, trecho in CASOS:
        t = tabelas_validas()
        estraga(t)
        res = validar_tabelas(t, parcial=True)
        if not _achou(res, tabela, trecho):
            nao_pegou.append(nome)
    assert not nao_pegou, f"regras que não pegaram o problema: {nao_pegou}"


def test_contrato_sem_desfecho_bem_formado_passa():
    """Contrato fora da vw_retorno_realizado: sem desfecho, com motivo e colunas do desfecho vazias."""
    t = tabelas_validas()
    t["vw_retorno_realizado"] = t["vw_retorno_realizado"].iloc[:-1]
    t["vw_base_modelagem"] = t["vw_base_modelagem"].iloc[:-1]
    d = t["vw_desfecho_contrato"]
    d.loc[3, "tem_desfecho"] = False
    # como o banco devolve: números com vazio viram float; texto e booleano com vazio viram object
    for coluna in ("inadimplente", "valor_concedido", "recebido_total", "resultado_eur",
                   "retorno_realizado", "principal_perdido"):
        d[coluna] = d[coluna].astype(float)
        d.loc[3, coluna] = float("nan")
    for coluna in ("motivo_sem_desfecho", "conjunto", "reestruturado"):
        d[coluna] = d[coluna].astype(object)
        d.loc[3, coluna] = None
    d.loc[3, "motivo_sem_desfecho"] = "não encerrado até o corte de 20/07/2021"
    res = _erros(validar_tabelas(t, parcial=True))
    assert res.empty, res.to_string()


# --- comportamento geral ------------------------------------------------------------------
def test_varios_problemas_saem_de_uma_vez():
    """lazy=True: três problemas em tabelas diferentes viram três erros, não um só."""
    t = tabelas_validas()
    _juro_zero(t)
    _genero_7(t)
    _euribor_fora_da_faixa(t)
    res = _erros(validar_tabelas(t, parcial=True))
    assert {"emprestimo", "cliente", "euribor_mensal"} <= set(res["tabela"])


def test_alerta_nao_e_erro():
    t = tabelas_validas()
    t["cliente"].loc[0, "idade"] = 15
    t["cliente"].loc[1, "renda_total"] = 0.0
    res = validar_tabelas(t, parcial=True)
    assert _erros(res).empty
    assert _achou(res, "cliente", "idade", "alerta")
    assert _achou(res, "cliente", "renda_total", "alerta")


def test_contagens_fixas_so_valem_fora_do_modo_parcial():
    t = tabelas_validas()
    assert _achou(validar_tabelas(t, parcial=False), "(cruzamento)", "nº de contratos diferente")
    assert _erros(validar_tabelas(tabelas_validas(), parcial=True)).empty


def test_estrito_falso_aceita_coluna_a_mais():
    t = tabelas_validas()
    _coluna_extra(t)
    res = validar_tabelas(t, parcial=True, estrito=False)
    assert not _achou(res, "emprestimo", "coluna_nova")


def test_regra_de_linha_conta_linhas_e_nao_colunas():
    """Uma regra que olha várias colunas deve aparecer UMA vez, com o nº de linhas."""
    t = tabelas_validas()
    e = t["emprestimo"]
    e.loc[0, "data_pedido"] = e.loc[0, "data_emprestimo"] + pd.Timedelta(days=10)
    e.loc[2, "data_pedido"] = e.loc[2, "data_emprestimo"] + pd.Timedelta(days=10)
    res = _erros(validar_tabelas(t, parcial=True))
    r = res[res["regra"].str.contains("data_pedido <= data_emprestimo")]
    assert len(r) == 1 and int(r["violacoes"].iloc[0]) == 2
