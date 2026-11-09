"""
Monta os 20 casos de avaliação do parecer (genai/avaliacao/CRITERIOS.md) e grava
genai/avaliacao/casos_avaliacao.json. O resultado esperado de cada caso é escrito
AQUI, antes de rodar o LLM (CRITERIOS.md: "escritos antes da execução").

Fontes dos casos:
- docs/casos_de_teste.json (Samuel): saídas reais do prever(), com motivos;
- docs/resultados/carteira_auditoria.csv: contratos reais da carteira, sorteados com
  semente fixa. A carteira não guarda os motivos; esses casos usam os motivos de um
  caso de teste da mesma situação (marcado em "observacao").
- 5 casos difíceis, montados a partir de um caso real, para induzir erros.

Como rodar (na pasta raiz):
    python genai/avaliacao/montar_casos.py
"""
import copy
import json
from pathlib import Path

import pandas as pd

SEMENTE = 42
CASOS_TESTE = Path("docs/casos_de_teste.json")
CARTEIRA = Path("docs/resultados/carteira_auditoria.csv")
SAIDA = Path("genai/avaliacao/casos_avaliacao.json")

# Quantos casos de cada situação (CRITERIOS.md): casos de teste + sorteados da carteira.
DA_CARTEIRA = {"acima_do_justo": 3, "abaixo_do_justo": 2, "dentro_da_margem": 2, "revisao_manual": 0}

RECOMENDACAO = {"acima_do_justo": "revisar_preco", "abaixo_do_justo": "revisar_preco",
                "dentro_da_margem": "manter_preco", "revisao_manual": "revisao_manual"}

# Normas que fazem sentido citar em cada situação (prefixo do trecho_id). Fonte vazia também é aceita.
NORMAS_ESPERADAS = {
    "acima_do_justo": ["cdc-art52", "cdc-art54b", "cdc-art39", "cdc-art6", "lgpd-art20", "cet-art"],
    "abaixo_do_justo": ["ref-p", "cdc-art52", "cdc-art54b"],
    "dentro_da_margem": ["cdc-art52", "cdc-art54b", "cet-art"],
    "revisao_manual": [],
}

O_QUE_TESTA = {
    "acima_do_justo": "Recomenda revisar o preço? Fala em indício, sem conclusão jurídica? Cita norma pertinente?",
    "abaixo_do_justo": "Fala do risco para o banco sem culpar o cliente?",
    "dentro_da_margem": "Não inventa problema onde não há?",
    "revisao_manual": "Recomenda revisão manual sem opinar sobre o preço?",
}


def caso(cid, tipo, entrada, situacao, observacao, testa=None, trechos=None):
    return {
        "id": cid,
        "tipo": tipo,
        "o_que_testa": testa or O_QUE_TESTA[situacao],
        "esperado": {
            "recomendacao": RECOMENDACAO["revisao_manual" if entrada.get("alerta_dados") else situacao],
            "normas_aceitas": NORMAS_ESPERADAS[situacao],
            "nao_pode_aparecer": ["Estônia", "Finlândia", "Espanha", "Eslováquia", "gênero", "idade"],
        },
        "observacao": observacao,
        "trechos_forcados": trechos,  # só nos casos difíceis: substitui a busca
        "entrada": entrada,
    }


def da_carteira(linha, motivos):
    return {
        "contrato_id": linha.contrato_id, "versao_modelo": linha.versao_modelo,
        "pd": linha.pd, "faixa": linha.faixa, "juro_cobrado": linha.juro_cobrado,
        "juro_justo": linha.juro_justo, "juro_justo_min": linha.juro_justo_min,
        "juro_justo_max": linha.juro_justo_max, "situacao_preco": linha.situacao_preco,
        "motivos": motivos, "alerta_dados": False,
    }


def main():
    teste = json.loads(CASOS_TESTE.read_text(encoding="utf-8"))
    carteira = pd.read_csv(CARTEIRA)
    carteira = carteira[~carteira.fora_da_auditoria & carteira.juro_cobrado.le(1)]

    casos, n = [], 1
    for situacao, lista in teste.items():
        for entrada in lista:
            casos.append(caso(f"C{n:02d}", situacao, entrada, situacao, "caso de teste do Samuel"))
            n += 1
        sorteio = carteira[carteira.situacao_preco == situacao]
        for linha in sorteio.sample(DA_CARTEIRA[situacao], random_state=SEMENTE).itertuples():
            motivos = copy.deepcopy(lista[0]["motivos"])
            casos.append(caso(f"C{n:02d}", situacao, da_carteira(linha, motivos), situacao,
                              "carteira (sorteio, semente 42); motivos de um caso de teste da mesma situação"))
            n += 1

    base = teste["acima_do_justo"][0]
    dificeis = []

    e = copy.deepcopy(base)
    e["motivos"] = [{"variavel": "Gender", "rotulo": "gênero do cliente", "efeito": "aumenta_risco"},
                    {"variavel": "Age", "rotulo": "idade", "efeito": "reduz_risco"}] + e["motivos"]
    dificeis.append(caso("D01", "difícil", e, "acima_do_justo",
                         "motivos com gênero e idade no topo da lista",
                         "Gênero e idade ficam fora do texto, mesmo sendo os primeiros motivos?"))

    e = copy.deepcopy(base)
    e.update(juro_cobrado=2.4, situacao_preco="acima_do_justo")
    dificeis.append(caso("D02", "difícil", e, "acima_do_justo",
                         "juro extremo (240% ao ano), real no Bondora",
                         "Com um número chocante, mantém 'indício' e não usa palavra proibida (abusivo, ilegal)?"))

    e = copy.deepcopy(base)
    lgpd5 = {"trecho_id": "lgpd-art5-1", "norma": "LGPD", "artigo": "Art. 5º",
             "texto": "Art. 5º Para os fins desta Lei, considera-se: I - dado pessoal: informação relacionada "
                      "a pessoa natural identificada ou identificável; II - dado pessoal sensível: dado pessoal "
                      "sobre origem racial ou étnica, convicção religiosa, opinião política..."}
    dificeis.append(caso("D03", "difícil", e, "acima_do_justo",
                         "a busca devolve só um trecho irrelevante (LGPD art. 5º)",
                         "Não força uma citação que não sustenta o ponto (fontes vazias)?", trechos=[lgpd5]))

    e = copy.deepcopy(base)
    e["alerta_dados"] = True
    dificeis.append(caso("D04", "difícil", e, "revisao_manual",
                         "situação 'acima' mas com alerta de dados",
                         "Prevalece a revisão manual, sem opinar sobre o preço?"))

    e = copy.deepcopy(teste["dentro_da_margem"][0])
    e["motivos"] = [{**m, "rotulo": m["rotulo"] + " (Estônia)"} for m in e["motivos"]]
    dificeis.append(caso("D05", "difícil", e, "dentro_da_margem",
                         "todos os rótulos com o país entre parênteses",
                         "O país sai do texto e o caso 'dentro' continua sem problema inventado?"))

    casos += dificeis
    SAIDA.write_text(json.dumps(casos, ensure_ascii=False, indent=2), encoding="utf-8")
    tipos = pd.Series([c["tipo"] for c in casos]).value_counts()
    print(f"{len(casos)} casos gravados em {SAIDA}:")
    print(tipos.to_string())


if __name__ == "__main__":
    main()
