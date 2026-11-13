"""Demonstração para a banca: a conferência por código barra um parecer adulterado.

Pega o parecer REAL do C01 (avaliação v4, rodada 1), aplica sabotagens e roda o mesmo
conferir_parecer() que o sistema usa em todo parecer. Não chama o Gemini nem o banco.

Rodar da raiz do repositório:
    python -m genai.avaliacao.demo_conferencia
    python -m genai.avaliacao.demo_conferencia "Uma frase escrita pela banca."
"""
import json
import sys
from pathlib import Path

from genai.src.checagem import EntradaPrever, RespostaLLM, conferir_parecer

PASTA = Path(__file__).parent
CASO = "C01"
# Os 5 campos que o LLM escreve; o resto do parecer (origem, gerado_em...) é do código.
CAMPOS_DO_LLM = ("resumo", "pontos_de_atencao", "recomendacao_texto", "fontes", "numeros_citados")


def acrescentar_ao_ponto(parecer: dict, frase: str) -> dict:
    """Cópia do parecer com a frase no fim do 2º ponto de atenção (o original não muda)."""
    pontos = list(parecer["pontos_de_atencao"])
    pontos[1] = pontos[1] + " " + frase
    return {**parecer, "pontos_de_atencao": pontos}


def trocar_numero(parecer: dict) -> dict:
    pontos = list(parecer["pontos_de_atencao"])
    pontos[0] = pontos[0].replace("39,0%", "42,0%")
    return {**parecer, "pontos_de_atencao": pontos}


SABOTAGENS = {
    "Trocar um número (39,0% vira 42,0%)": trocar_numero,
    'Palavra proibida ("cobrança abusiva")':
        lambda p: acrescentar_ao_ponto(p, "Trata-se de uma cobrança abusiva."),
    "Artigo que a busca não trouxe (art. 39 do CDC)":
        lambda p: acrescentar_ao_ponto(
            p, "Se este contrato fosse de um banco brasileiro, o art. 39 do CDC seria aplicável."),
    "Atributo sensível (idade)":
        lambda p: acrescentar_ao_ponto(p, "O cliente tem idade avançada."),
}


def carregar():
    """Entrada do prever(), parecer da rodada 1 e trechos recuperados do caso."""
    casos = json.loads((PASTA / "casos_avaliacao.json").read_text(encoding="utf-8"))
    resultados = json.loads(
        (PASTA / "resultados_parecer_v4_gemini-3.5-flash-lite.json").read_text(encoding="utf-8"))
    caso = next(c for c in casos if c["id"] == CASO)
    resultado = next(r for r in resultados if r["id"] == CASO)
    entrada = EntradaPrever.model_validate(caso["entrada"])
    parecer = resultado["rodadas"][0]["parecer"]
    return entrada, parecer, resultado["recuperados"]


def conferir(parecer: dict, entrada: EntradaPrever, recuperados: list[str]) -> list[str]:
    resposta = RespostaLLM.model_validate({c: parecer[c] for c in CAMPOS_DO_LLM})
    return conferir_parecer(resposta, entrada, recuperados)


def mostrar(titulo: str, problemas: list[str]) -> None:
    if problemas:
        print(f"\n{titulo}: RECUSADO -> o analista recebe o template")
        for p in problemas:
            print("   -", p)
    else:
        print(f"\n{titulo}: APROVADO")


def main():
    entrada, parecer, recuperados = carregar()
    print(f"Contrato {entrada.contrato_id} ({CASO}): parecer real do Gemini")

    mostrar("0. Sem sabotagem", conferir(parecer, entrada, recuperados))
    for n, (nome, sabotar) in enumerate(SABOTAGENS.items(), start=1):
        mostrar(f"{n}. {nome}", conferir(sabotar(parecer), entrada, recuperados))

    if len(sys.argv) > 1:  # frase livre, digitada na hora
        frase = " ".join(sys.argv[1:])
        mostrar(f'Frase livre: "{frase}"',
                conferir(acrescentar_ao_ponto(parecer, frase), entrada, recuperados))


if __name__ == "__main__":
    main()