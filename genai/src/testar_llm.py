"""
Teste rápido da chave do Gemini (não envia nenhum dado do projeto).

Como rodar (na pasta raiz):
    python genai/src/testar_llm.py                 -> lista os modelos "flash"
    python genai/src/testar_llm.py <nome-do-modelo> -> faz uma pergunta de teste
"""
import os
import sys

from dotenv import load_dotenv
from google import genai

load_dotenv()
if not os.getenv("GOOGLE_API_KEY"):
    raise SystemExit("Falta a linha GOOGLE_API_KEY=... no arquivo .env (pasta raiz).")

cliente = genai.Client()

if len(sys.argv) == 1:
    print("Modelos Flash disponíveis para a sua chave:")
    for modelo in cliente.models.list():
        if "flash" in modelo.name and "generateContent" in (modelo.supported_actions or []):
            print("  ", modelo.name.removeprefix("models/"))
else:
    resposta = cliente.models.generate_content(
        model=sys.argv[1],
        contents="Responda em uma frase, em português: o que é um juro nominal ao ano?",
    )
    print(resposta.text)