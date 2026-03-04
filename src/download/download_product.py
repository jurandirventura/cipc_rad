# # Ps.: Download Sentinel-5P products by date range
import requests
import time
import sys
from datetime import datetime
from pathlib import Path

from src.config.settings import DATA_DIR

# =========================
# PARÂMETROS DE ENTRADA
# =========================

if len(sys.argv) != 4:
    print("\nUso:")
    print("python src/download/download_product.py PRODUCT_TYPE START_DATE END_DATE\n")
    print("Exemplo:")
    print("python src/download/download_product.py AER_AI 2023-10-10 2023-10-22\n")
    sys.exit(1)

PRODUCT_TYPE = sys.argv[1]
START_DATE = sys.argv[2]
END_DATE = sys.argv[3]

# Validar datas
try:
    datetime.strptime(START_DATE, "%Y-%m-%d")
    datetime.strptime(END_DATE, "%Y-%m-%d")
except ValueError:
    print("Formato de data inválido. Use YYYY-MM-DD")
    sys.exit(1)

MAX_RETRIES = 3
BBOX_WKT = "POLYGON((-85 -60, -85 15, -30 15, -30 -60, -85 -60))"

# =========================
# DEFINIR DIRETÓRIO AUTOMÁTICO
# =========================

YEAR = START_DATE[:4]

DOWNLOAD_DIR = DATA_DIR / "L2" / PRODUCT_TYPE / YEAR
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# AUTENTICAÇÃO
# =========================

from dotenv import load_dotenv
import os

load_dotenv()

USERNAME = os.getenv("CDSE_USER")
PASSWORD = os.getenv("CDSE_PASS")

if USERNAME is None or PASSWORD is None:
    raise ValueError("Variáveis CDSE_USER e CDSE_PASS não definidas.")

def get_access_token():
    token_url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"

    data = {
        "client_id": "cdse-public",
        "grant_type": "password",
        "username": USERNAME,
        "password": PASSWORD,
    }

    response = requests.post(token_url, data=data)
    response.raise_for_status()
    return response.json()["access_token"]

# =========================
# BUSCA PRODUTOS
# =========================

def search_products(access_token):

    headers = {"Authorization": f"Bearer {access_token}"}

    filter_query = (
        f"Collection/Name eq 'SENTINEL-5P' "
        f"and contains(Name,'{PRODUCT_TYPE}') "
        f"and ContentDate/Start ge {START_DATE}T00:00:00.000Z "
        f"and ContentDate/Start le {END_DATE}T23:59:59.999Z "
        f"and hour(ContentDate/Start) ge 14 "
        f"and hour(ContentDate/Start) le 18 "
        f"and OData.CSC.Intersects(area=geography'SRID=4326;{BBOX_WKT}')"
    )

    url = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"

    params = {
        "$filter": filter_query,
        "$top": 1000
    }

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()

    return response.json()["value"]

# =========================
# DOWNLOAD
# =========================

def download_product(access_token, product):

    headers = {"Authorization": f"Bearer {access_token}"}
    product_id = product["Id"]
    name = product["Name"]

    filepath = DOWNLOAD_DIR / name

    if filepath.exists():
        print(f"[OK] Já existe: {name}")
        return

    download_url = f"https://zipper.dataspace.copernicus.eu/odata/v1/Products({product_id})/$value"

    for attempt in range(MAX_RETRIES):
        try:
            print(f"[DOWN] Baixando {name}...")
            with requests.get(download_url, headers=headers, stream=True) as r:
                r.raise_for_status()
                with open(filepath, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            print(f"[DONE] {name}")
            return
        except Exception as e:
            print(f"[ERRO] Tentativa {attempt+1}: {e}")
            time.sleep(5)

    print(f"[FAIL] Não foi possível baixar {name}")

# =========================
# MAIN
# =========================

def main():

    print("\n=== DOWNLOAD SENTINEL-5P ===")
    print(f"Produto: {PRODUCT_TYPE}")
    print(f"Período: {START_DATE} a {END_DATE}")
    print(f"Destino: {DOWNLOAD_DIR}\n")

    token = get_access_token()
    print("Token obtido com sucesso.\n")

    products = search_products(token)
    print(f"{len(products)} produtos encontrados\n")

    for product in products:
        download_product(token, product)

    print("\n=== FIM ===")

if __name__ == "__main__":
    main()




# import requests
# import os
# import time
# import sys
# from datetime import datetime
# from urllib.parse import quote
# from dotenv import load_dotenv

# load_dotenv()

# # =========================
# # PARÂMETROS DE ENTRADA
# # =========================

# if len(sys.argv) != 5:
#     print("\nUso:")
#     print("python download_s5p.py PRODUCT_TYPE START_DATE END_DATE DOWNLOAD_DIR\n")
#     print("Exemplo:")
#     print("python download_s5p.py AER_AI 2023-10-10 2023-10-22 S5P_2023_AEROSOL\n")
#     sys.exit(1)

# PRODUCT_TYPE = sys.argv[1]
# START_DATE = sys.argv[2]
# END_DATE = sys.argv[3]
# DOWNLOAD_DIR = sys.argv[4]

# # Validar datas
# try:
#     datetime.strptime(START_DATE, "%Y-%m-%d")
#     datetime.strptime(END_DATE, "%Y-%m-%d")
# except ValueError:
#     print("Formato de data inválido. Use YYYY-MM-DD")
#     sys.exit(1)

# MAX_RETRIES = 3

# BBOX_WKT = "POLYGON((-85 -60, -85 15, -30 15, -30 -60, -85 -60))"

# os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# # =========================
# # AUTENTICAÇÃO
# # =========================

# USERNAME = os.getenv("CDSE_USER")
# PASSWORD = os.getenv("CDSE_PASS")

# if USERNAME is None or PASSWORD is None:
#     raise ValueError("Variáveis CDSE_USER e CDSE_PASS não definidas.")

# def get_access_token():
#     token_url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"

#     data = {
#         "client_id": "cdse-public",
#         "grant_type": "password",
#         "username": USERNAME,
#         "password": PASSWORD,
#     }

#     response = requests.post(token_url, data=data)
#     response.raise_for_status()
#     return response.json()["access_token"]

# # =========================
# # BUSCA PRODUTOS
# # =========================

# def search_products(access_token):

#     headers = {"Authorization": f"Bearer {access_token}"}

#     filter_query = (
#         "Collection/Name eq 'SENTINEL-5P' "
#         f"and contains(Name,'{PRODUCT_TYPE}') "
#         f"and
#           ContentDate/Start ge {START_DATE}T00:00:00.000Z "
#         f"and ContentDate/Start le {END_DATE}T23:59:59.999Z "
#         "and hour(ContentDate/Start) ge 14 "
#         "and hour(ContentDate/Start) le 18 "
#         f"and OData.CSC.Intersects(area=geography'SRID=4326;{BBOX_WKT}')"
#     )

#     url = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"

#     params = {
#         "$filter": filter_query,
#         "$top": 1000
#     }

#     response = requests.get(url, headers=headers, params=params)
#     response.raise_for_status()

#     return response.json()["value"]

# # =========================
# # DOWNLOAD
# # =========================

# def download_product(access_token, product):

#     headers = {"Authorization": f"Bearer {access_token}"}
#     product_id = product["Id"]
#     name = product["Name"]

#     filepath = os.path.join(DOWNLOAD_DIR, f"{name}")

#     if os.path.exists(filepath):
#         print(f"[OK] Já existe: {name}")
#         return

#     download_url = f"https://zipper.dataspace.copernicus.eu/odata/v1/Products({product_id})/$value"

#     for attempt in range(MAX_RETRIES):
#         try:
#             print(f"[DOWN] Baixando {name}...")
#             with requests.get(download_url, headers=headers, stream=True) as r:
#                 r.raise_for_status()
#                 with open(filepath, "wb") as f:
#                     for chunk in r.iter_content(chunk_size=8192):
#                         f.write(chunk)
#             print(f"[DONE] {name}")
#             return
#         except Exception as e:
#             print(f"[ERRO] Tentativa {attempt+1}: {e}")
#             time.sleep(5)

#     print(f"[FAIL] Não foi possível baixar {name}")

# # =========================
# # MAIN
# # =========================

# def main():

#     print(f"\n=== DOWNLOAD SENTINEL-5P ===")
#     print(f"Produto: {PRODUCT_TYPE}")
#     print(f"Período: {START_DATE} a {END_DATE}")
#     print(f"Diretório: {DOWNLOAD_DIR}\n")

#     token = get_access_token()
#     print("Token obtido com sucesso.\n")

#     products = search_products(token)
#     print(f"{len(products)} produtos encontrados\n")

#     for product in products:
#         download_product(token, product)

#     print("\n=== FIM ===")

# if __name__ == "__main__":
#     main()
