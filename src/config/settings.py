import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega .env
load_dotenv()

# Caminho raiz do projeto
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# diretório config do projeto
CONFIG_DIR = BASE_DIR / "config"


# Carrega .env
#load_dotenv(BASE_DIR / ".env")

# Converte para Path
DATA_DIR = Path(os.getenv("DATA_DIR"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR"))
LOG_DIR = Path(os.getenv("LOG_DIR"))


