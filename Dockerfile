FROM python:3.11-slim

WORKDIR /app

#instalação de pacotes e libs 
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

#copia codigo fonte do projeto local
COPY . .

EXPOSE 8000

#p/ definir o comando que sera iniciado quando o container executar
#servidor uvicorn web, rodando fastapi, na porta 8000 com conexao de fora do container
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]