import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

#ler as variaveis de ambiente do docker p/ criar a sessao no postgresql
# carrega as variáveis de ambiente
load_dotenv()

# Vai puxar o localhost:5432 que o Marcos configurou no .env
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# depen para injetar a sessão do banco nas rotas do nosso FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()