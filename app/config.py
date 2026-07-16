# import os
# from dotenv import load_dotenv

# load_dotenv()

# class Config:
#     DB_HOST = os.getenv("DB_HOST")
#     DB_NAME = os.getenv("DB_NAME")
#     DB_USER = os.getenv("DB_USER")
#     DB_PASSWORD = os.getenv("DB_PASSWORD")
#     DB_PORT = os.getenv("DB_PORT")
import os
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

class Config:
    # 1. Verifica se existe uma DATABASE_URL (padrão do Render/Neon)
    DATABASE_URL = os.getenv("DATABASE_URL")

    if DATABASE_URL:
        # Se existir a URL única, nós "fatiamos" ela para extrair os dados individuais
        parsed = urlparse(DATABASE_URL)
        DB_USER = parsed.username
        DB_PASSWORD = parsed.password
        DB_HOST = parsed.hostname
        DB_PORT = parsed.port or 5432
        DB_NAME = parsed.path.lstrip('/')
    else:
        # Se não existir (desenvolvimento local), usa o seu padrão do .env
        DB_HOST = os.getenv("DB_HOST")
        DB_NAME = os.getenv("DB_NAME")
        DB_USER = os.getenv("DB_USER")
        DB_PASSWORD = os.getenv("DB_PASSWORD")
        DB_PORT = os.getenv("DB_PORT")    