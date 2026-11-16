"""
Quantos pareceres da carteira saem com fonte normativa? Amostra pela API em funcionamento.

Para cada situação do preço, sorteia N contratos da carteira (semente fixa), pede a análise
ao vivo (GET /contracts/{id}/analysis, o mesmo caminho da tela) e conta:
- origem "llm" com fonte: o parecer citou ao menos uma norma;
- origem "llm" sem fonte: a IA escreveu, mas nenhum trecho recuperado foi pertinente;
- origem "template": a IA não escreveu (503, tempo esgotado, conferência reprovada ou revisão manual).
  O template nunca tem fonte: é por isso que a tela mostra "Não encontrei base normativa".

Diferente da avaliação dos 20 casos (avaliar.py), aqui não há revisão humana: só a contagem.
Não grava nada no banco nem nos resultados da avaliação.

Como rodar (na pasta raiz, com a API no ar):
    python -m genai.avaliacao.contar_fontes                  # 10 por situação
    python -m genai.avaliacao.contar_fontes --por-situacao 20
Variáveis opcionais: API_URL (padrão http://localhost:8000), PAUSA_ENTRE_CHAMADAS (padrão 4 s).
"""
import argparse
import os
import random
import time
from collections import Counter

import requests

API = os.getenv("API_URL", "http://localhost:8000").rstrip("/")
PAUSA = float(os.getenv("PAUSA_ENTRE_CHAMADAS", "4"))  # evita o limite do plano gratuito do Gemini
SITUACOES = ("acima_do_justo", "abaixo_do_justo", "dentro_da_margem")  # revisão manual nunca chama a IA
SEMENTE = 42


def sortear_ids(situacao: str, quantos: int, sorteio: random.Random) -> list[str]:
    total = requests.get(f"{API}/contracts", params={"situation": situacao, "limit": 1}, timeout=30).json()["total"]
    posicoes = sorteio.sample(range(total), min(quantos, total))
    ids = []
    for posicao in posicoes:
        itens = requests.get(f"{API}/contracts",
                             params={"situation": situacao, "offset": posicao, "limit": 1}, timeout=30).json()["itens"]
        ids.append(str(itens[0]["contrato_id"]))
    return ids


def classificar(parecer: dict | None) -> str:
    if not parecer:
        return "sem parecer"
    if parecer.get("origem") != "llm":
        return "template"
    return "llm com fonte" if parecer.get("fontes") else "llm sem fonte"


def main():
    argumentos = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    argumentos.add_argument("--por-situacao", type=int, default=10)
    quantos = argumentos.parse_args().por_situacao

    sorteio = random.Random(SEMENTE)
    contagem = {s: Counter() for s in SITUACOES}
    normas = Counter()
    for situacao in SITUACOES:
        for contrato_id in sortear_ids(situacao, quantos, sorteio):
            resposta = requests.get(f"{API}/contracts/{contrato_id}/analysis", timeout=120)
            parecer = resposta.json()["resultado"].get("parecer_ia") if resposta.ok else None
            classe = classificar(parecer)
            contagem[situacao][classe] += 1
            for fonte in (parecer or {}).get("fontes", []):
                normas[f"{fonte['norma']}, {fonte['artigo']}"] += 1
            print(f"{situacao:<17} {contrato_id:<40} {classe}")
            time.sleep(PAUSA)

    print("\nSituação           total  IA c/ fonte  IA s/ fonte  template")
    geral = Counter()
    for situacao, c in contagem.items():
        total = sum(c.values())
        geral.update(c)
        print(f"{situacao:<17} {total:>6} {c['llm com fonte']:>12} {c['llm sem fonte']:>12} {c['template']:>9}")
    total = sum(geral.values())
    print(f"{'TOTAL':<17} {total:>6} {geral['llm com fonte']:>12} {geral['llm sem fonte']:>12} {geral['template']:>9}")
    escritos = geral["llm com fonte"] + geral["llm sem fonte"]
    if escritos:
        print(f"\nDos pareceres escritos pela IA, {geral['llm com fonte'] / escritos:.0%} citaram norma.")
    if normas:
        print("Normas mais citadas:", "; ".join(f"{n} ({q})" for n, q in normas.most_common(5)))
    print("Os pareceres do template ficam fora da conta: neles a IA não chegou a escrever.")


if __name__ == "__main__":
    main()
