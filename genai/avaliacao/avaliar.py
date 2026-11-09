"""
Roda os 20 casos de avaliação (casos_avaliacao.json) 2 vezes cada pela cadeia real
(busca no pgvector + Gemini + conferência) e grava:
- genai/avaliacao/resultados_<prompt>_<modelo>.json  (tudo, para auditoria)
- genai/avaliacao/resultados_<prompt>_<modelo>.md    (resumo + tabela para a revisão humana)

O que é medido por código (CRITERIOS.md): recomendação certa, recuperação (norma aceita entre
os 3 primeiros trechos), fontes dentro das normas aceitas, palavras/atributos proibidos,
consistência entre as 2 rodadas, origem (llm ou template) e tempo.
O que fica para a revisão humana: fidelidade, citação correta, alucinação e clareza (1 a 5).

Como rodar (na pasta raiz, com o banco no ar, DATABASE_URL e GOOGLE_API_KEY definidos):
    python -m genai.avaliacao.avaliar
Só refazer o relatório .md a partir do .json já gravado (sem chamar o LLM):
    python -m genai.avaliacao.avaliar --relatorio
"""
import json
import logging
import os
import sys
import time
from pathlib import Path

from genai.src import cadeia
from genai.src.checagem import ATRIBUTOS_SENSIVEIS, PALAVRAS_PROIBIDAS, EntradaPrever

PASTA = Path("genai/avaliacao")
CASOS = PASTA / "casos_avaliacao.json"
RODADAS = 2
PAUSA = float(os.getenv("PAUSA_ENTRE_CHAMADAS", "4"))  # segundos; evita o limite do plano gratuito


class _GuardaAvisos(logging.Handler):
    def __init__(self):
        super().__init__()
        self.avisos = []

    def emit(self, registro):
        self.avisos.append(registro.getMessage())


def _texto(parecer):
    return " ".join([parecer["resumo"], *parecer["pontos_de_atencao"], parecer["recomendacao_texto"]])


def proibidos(texto):
    """Palavras proibidas e atributos sensíveis (mesmas regras da conferência, com limite de palavra:
    "escolaridade" não conta como "idade")."""
    return PALAVRAS_PROIBIDAS.findall(texto) + ATRIBUTOS_SENSIVEIS.findall(texto)


FONTE_FIXA = "lgpd-art20"  # trazida pela pergunta de governança em todos os casos (v3)


def fontes_especificas(fontes):
    """Fontes sem a LGPD art. 20: mede se o RAG achou a norma certa para a situação, e não só a fixa."""
    return [f for f in fontes if not f.startswith(FONTE_FIXA)]


def _recusa_por_palavra(rodada):
    return any("conferência recusou" in a and ("palavra proibida" in a or "atributo sensível" in a)
               for a in rodada["avisos"])


def _recusa_por_artigo(rodada):
    return any("conferência recusou" in a and ("no texto não está entre os trechos recuperados" in a
                                                or "que não é o do trecho" in a)
               for a in rodada["avisos"])


def _llm_por_tipo(resultados):
    """Rodadas com parecer do LLM, separadas por tipo de caso (acima, abaixo, dentro, difícil)."""
    grupos = {}
    for res in resultados:
        for rodada in res["rodadas"]:
            if rodada["origem"] == "llm":
                grupos.setdefault(res["tipo"], []).append(rodada)
    return grupos


def _aceita(trecho_id, prefixos):
    return any(trecho_id.startswith(p) for p in prefixos)


def avaliar_caso(caso, guarda):
    esperado = caso["esperado"]
    forcados = caso.get("trechos_forcados")
    busca_original = cadeia.buscar_trechos
    if forcados is not None:
        cadeia.buscar_trechos = lambda entrada: forcados
    try:
        entrada = EntradaPrever.model_validate(caso["entrada"])
        recuperados = [] if entrada.vai_para_revisao_manual else [t["trecho_id"] for t in cadeia.buscar_trechos(entrada)]
        rodadas = []
        for _ in range(RODADAS):
            guarda.avisos.clear()
            inicio = time.time()
            parecer = cadeia.gerar_parecer(caso["entrada"])
            tempo = round(time.time() - inicio, 1)
            fontes = [f["trecho_id"] for f in parecer["fontes"]]
            texto = _texto(parecer)
            rodadas.append({
                "origem": parecer["origem"],
                "tempo_s": tempo,
                "recomendacao_ok": parecer["recomendacao"] == esperado["recomendacao"],
                "fontes": fontes,
                "fontes_ok": all(_aceita(f, esperado["normas_aceitas"]) for f in fontes),
                "proibidos": proibidos(texto),
                "avisos": list(guarda.avisos),
                "parecer": {**parecer, "gerado_em": str(parecer["gerado_em"])},
            })
            if parecer["origem"] == "llm":
                time.sleep(PAUSA)
    finally:
        cadeia.buscar_trechos = busca_original

    a, b = rodadas[0], rodadas[1]
    return {
        "id": caso["id"], "tipo": caso["tipo"], "o_que_testa": caso["o_que_testa"],
        "recuperados": recuperados,
        "recuperacao_ok": (None if not esperado["normas_aceitas"] or forcados is not None
                           else any(_aceita(t, esperado["normas_aceitas"]) for t in recuperados[:3])),
        "consistente": (a["origem"], a["fontes"], a["recomendacao_ok"]) == (b["origem"], b["fontes"], b["recomendacao_ok"]),
        "rodadas": rodadas,
    }


def _pct(valores):
    valores = [v for v in valores if v is not None]
    return f"{sum(valores)}/{len(valores)} ({100 * sum(valores) / len(valores):.0f}%)" if valores else "—"


def escrever_markdown(resultados, caminho):
    todas = [r for res in resultados for r in res["rodadas"]]
    com_llm = [r for r in todas if r["origem"] == "llm"]
    linhas = [
        f"# Avaliação do parecer: {cadeia.VERSAO_PROMPT} com {cadeia.MODELO_LLM}",
        "",
        f"{len(resultados)} casos x {RODADAS} rodadas, com busca no pgvector. Critérios em `CRITERIOS.md`.",
        "",
        "## Medido por código",
        "",
        "| Métrica | Resultado |",
        "|---|---|",
        f"| Recomendação certa | {_pct([r['recomendacao_ok'] for r in todas])} |",
        f"| Recuperação (norma aceita no top 3) | {_pct([res['recuperacao_ok'] for res in resultados])} |",
        f"| Pareceres do LLM aprovados pela conferência | {_pct([r['origem'] == 'llm' for r in todas if r['parecer']['recomendacao'] != 'revisao_manual'])} |",
        f"| Fontes dentro das normas aceitas (pareceres do LLM) | {_pct([r['fontes_ok'] for r in com_llm])} |",
        f"| Pareceres do LLM com alguma fonte | {_pct([bool(r['fontes']) for r in com_llm])} |",
        f"| Pareceres do LLM com fonte específica da situação (sem contar {FONTE_FIXA}) "
        f"| {_pct([bool(fontes_especificas(r['fontes'])) for r in com_llm])} |",
        *[f"| ↳ fonte específica, só {tipo} | {_pct([bool(fontes_especificas(r['fontes'])) for r in rodadas])} |"
          for tipo, rodadas in _llm_por_tipo(resultados).items()],
        f"| Pareceres do LLM que citam a {FONTE_FIXA} | {_pct([any(f.startswith(FONTE_FIXA) for f in r['fontes']) for r in com_llm])} |",
        f"| Recusas da conferência por palavra/atributo proibido | {sum(_recusa_por_palavra(r) for r in todas)} |",
        f"| Recusas da conferência por artigo | {sum(_recusa_por_artigo(r) for r in todas)} |",
        f"| Sem palavra/atributo proibido | {_pct([not proibidos(_texto(r['parecer'])) for r in todas])} |",
        f"| Mesma resposta nas 2 rodadas | {_pct([res['consistente'] for res in resultados])} |",
        f"| Tempo médio do LLM | {sum(r['tempo_s'] for r in com_llm) / max(len(com_llm), 1):.1f} s |",
        "",
        "Casos com resposta diferente entre as rodadas: "
        + (", ".join(f"{res['id']} (fontes {res['rodadas'][0]['fontes'] or '—'} / {res['rodadas'][1]['fontes'] or '—'})"
                     for res in resultados if not res["consistente"]) or "nenhum") + ".",
        "",
        "## Revisão humana (preencher)",
        "",
        "Sim/não em Fidelidade, Citação correta e Alucinação (sim = alucinou); Clareza de 1 a 5. Ler a rodada 1 abaixo.",
        "",
        "Na Citação correta, conferir também: (1) o parecer não diz que algo \"cumpre\" ou \"atende\" a LGPD "
        "ou outra norma (conclusão jurídica é do compliance); (2) ao citar norma, usa o modo hipotético "
        "(\"se este contrato fosse de um banco brasileiro\").",
        "",
        "| Caso | Tipo | Origem (r1/r2) | Fontes (r1) | Fidelidade | Citação correta | Alucinação | Clareza |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for res in resultados:
        r1, r2 = res["rodadas"]
        linhas.append(f"| {res['id']} | {res['tipo']} | {r1['origem']}/{r2['origem']} | "
                      f"{', '.join(r1['fontes']) or '—'} |  |  |  |  |")
    linhas += ["", "## Pareceres (rodada 1)", ""]
    for res in resultados:
        p = res["rodadas"][0]["parecer"]
        linhas += [f"### {res['id']} ({res['tipo']}): {res['o_que_testa']}", "",
                   f"- **Origem:** {p['origem']} · **Recomendação:** {p['recomendacao']} · "
                   f"**Trechos recuperados:** {', '.join(res['recuperados']) or '—'}",
                   f"- **Resumo:** {p['resumo']}"]
        linhas += [f"- **Ponto:** {ponto}" for ponto in p["pontos_de_atencao"]]
        linhas += [f"- **Recomendação:** {p['recomendacao_texto']}",
                   f"- **Fontes:** {', '.join(f['trecho_id'] + ' (' + f['artigo'] + ')' for f in p['fontes']) or 'nenhuma'}"]
        avisos = res["rodadas"][0]["avisos"]
        if avisos:
            linhas.append(f"- **Avisos:** {' | '.join(a[:200] for a in avisos)}")
        linhas.append("")
    caminho.write_text("\n".join(linhas), encoding="utf-8")


def main():
    nome = f"resultados_{cadeia.VERSAO_PROMPT}_{cadeia.MODELO_LLM}"
    if "--relatorio" in sys.argv:
        resultados = json.loads((PASTA / f"{nome}.json").read_text(encoding="utf-8"))
        escrever_markdown(resultados, PASTA / f"{nome}.md")
        print(f"Relatório refeito: {PASTA / (nome + '.md')}")
        return

    guarda = _GuardaAvisos()
    logging.getLogger("genai.cadeia").addHandler(guarda)
    casos = json.loads(CASOS.read_text(encoding="utf-8"))
    resultados = []
    for caso in casos:
        res = avaliar_caso(caso, guarda)
        origens = "/".join(r["origem"] for r in res["rodadas"])
        print(f"{res['id']} {res['tipo']:<17} origem {origens:<17} fontes {res['rodadas'][0]['fontes'] or '—'}")
        resultados.append(res)

    (PASTA / f"{nome}.json").write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
    escrever_markdown(resultados, PASTA / f"{nome}.md")
    print(f"\nGravado: {PASTA / (nome + '.md')} (abra para ler e preencher a revisão humana)")


if __name__ == "__main__":
    main()
