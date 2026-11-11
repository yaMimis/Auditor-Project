"""
Testa a busca no pgvector com 10 perguntas de resposta conhecida.
Meta do plano: pelo menos 8 de 10 com o artigo certo entre os 3 primeiros.

Como rodar (na pasta raiz, depois do indexar.py):
    python genai/src/testar_busca.py
"""
from sentence_transformers import SentenceTransformer

try:  # funciona como arquivo e como módulo (-m)
    from genai.src.indexar import MODELO, TABELA, conectar
except ImportError:
    from indexar import MODELO, TABELA, conectar

QUANTOS = 3

# (pergunta, [respostas aceitas como (norma, artigo)])
PERGUNTAS = [
    ("O cliente pode pedir revisão de uma decisão de crédito tomada só por um sistema automático?",
     [("LGPD", "Art. 20")]),
    ("O que é dado pessoal sensível?",
     [("LGPD", "Art. 5º")]),
    ("Dados anonimizados são considerados dados pessoais?",
     [("LGPD", "Art. 12")]),
    ("O tratamento de dados pessoais pode ser feito para fins discriminatórios?",
     [("LGPD", "Art. 6º")]),
    ("No financiamento, o fornecedor precisa informar a taxa efetiva anual de juros e a soma total a pagar?",
     [("CDC", "Art. 52")]),
    ("Exigir do consumidor vantagem manifestamente excessiva é prática abusiva?",
     [("CDC", "Art. 39")]),
    ("Na oferta de crédito, o que deve ser informado sobre o custo efetivo total?",
     [("CDC", "Art. 54-B"), ("Resolução CMN nº 4.881/2020", "Art. 7º")]),
    ("O que entra no cálculo do Custo Efetivo Total?",
     [("Resolução CMN nº 4.881/2020", "Art. 3º"), ("Resolução CMN nº 4.881/2020", "Art. 2º")]),
    ("O contrato de crédito precisa discriminar a taxa efetiva mensal e anual, as tarifas e os tributos?",
     [("Resolução CMN nº 5.004/2022", "Art. 3º")]),
    ("Na quitação antecipada do empréstimo, qual taxa de juros é usada para calcular o desconto?",
     [("Resolução CMN nº 5.004/2022", "Art. 7º"), ("CDC", "Art. 52")]),
]


def main():
    modelo = SentenceTransformer(MODELO)
    conexao = conectar()
    acertos = 0

    with conexao.cursor() as cur:
        for pergunta, esperadas in PERGUNTAS:
            vetor = modelo.encode(pergunta, normalize_embeddings=True)
            # <=> é a distância de cosseno do pgvector: quanto MENOR, mais parecido.
            cur.execute(
                f"""SELECT norma, artigo, parte, embedding <=> %s AS distancia
                    FROM {TABELA} ORDER BY embedding <=> %s LIMIT %s;""",
                (vetor, vetor, QUANTOS),
            )
            resultados = cur.fetchall()
            achou = any((norma, artigo) in esperadas for norma, artigo, _, _ in resultados)
            acertos += achou

            print(f"\n{'OK  ' if achou else 'ERRO'} | {pergunta}")
            print(f"     esperado: {' ou '.join(f'{n}, {a}' for n, a in esperadas)}")
            for norma, artigo, parte, distancia in resultados:
                print(f"     -> {norma}, {artigo} (parte {parte})  distância={distancia:.3f}")

    conexao.close()
    print(f"\nResultado: {acertos} de {len(PERGUNTAS)} com o artigo certo no top {QUANTOS}. Meta: 8.")


if __name__ == "__main__":
    main()