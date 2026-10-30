import os
import hashlib
from dotenv import load_dotenv

# carrega as variáveis do .env
load_dotenv()

# Puxa o "Sal" (texto secreto) do .env
SAL_SECRETO = os.getenv("CLIENTE_ID_SAL", "")

def gerar_hash_cliente(username: str) -> str:
    """
    Junta o username com o SAL e gera a chave secreta em SHA-256
    """
    # Concatena o nome do usuário com o Salt do Marcos
    texto_base = f"{username}{SAL_SECRETO}"
    
    # Gera o hash criptográfico
    hash_gerado = hashlib.sha256(texto_base.encode('utf-8')).hexdigest()
    
    return hash_gerado