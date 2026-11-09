# 1. criar o .env com a chave do gemini, database url e o cliente id sal pois o .env é ignorado no github
# 2. Para o Postgres local se estiver rodando (evita conflito)
Stop-Service postgresql* -ErrorAction SilentlyContinue

# 3. Sobe o container do banco
docker compose up -d postgres

# 4. Aguarda 3 segundos para o banco inicializar totalmente
Start-Sleep -Seconds 3

# 5. Aplica as tabelas atualizadas do Marcos
docker cp db\05_decisoes_analista.sql auditor_postgres:/tmp/05.sql
docker exec auditor_postgres psql -U postgres -d auditor_db -v ON_ERROR_STOP=1 -f /tmp/05.sql

# 6. Indexa as normas jurídicas no pgvector
python genai/src/indexar.py

# 7. Sobe a API e a Interface
docker compose up --build api streamlit

#para rodar esse script no powershell adm
# cd C:\Users\Aluno\Desktop\sua-pasta\Auditor-Project
# .\iniciar.ps1

#caso de erro de segurança
# Set-ExecutionPolicy Unrestricted -Scope Process