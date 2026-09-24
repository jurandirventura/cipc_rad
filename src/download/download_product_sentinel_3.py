#!/usr/bin/env python3

"""
Download Sentinel-3 SLSTR Level-2 Aerosol Optical Depth (AOD)

Coleção EUMETSAT:
    EO:EUM:DAT:0416

Exemplo:

python src/download/download_sentinel3_aod.py \
    S3B_AOD \
    2024-08-16 \
    2024-08-26
"""

import sys
import shutil
import datetime
from pathlib import Path

import eumdac
from dotenv import load_dotenv
import os

from src.config.settings import DATA_DIR


# ============================================================
# PARÂMETROS
# ============================================================

if len(sys.argv) != 4:
    print()
    print("Uso:")
    print(
        "python src/download/download_sentinel3_aod.py "
        "PRODUCT START_DATE END_DATE"
    )
    print()
    print("Exemplo:")
    print(
        "python src/download/download_sentinel3_aod.py "
        "S3B_AOD 2024-08-16 2024-08-26"
    )
    print()
    sys.exit(1)


PRODUCT_TYPE = sys.argv[1]
START_DATE = sys.argv[2]
END_DATE = sys.argv[3]


# ============================================================
# VALIDAÇÃO
# ============================================================

try:
    start = datetime.datetime.strptime(
        START_DATE,
        "%Y-%m-%d"
    )

    end = datetime.datetime.strptime(
        END_DATE,
        "%Y-%m-%d"
    )

except ValueError:

    print(
        "Formato de data inválido. "
        "Use YYYY-MM-DD"
    )

    sys.exit(1)


if end < start:

    raise ValueError(
        "END_DATE deve ser maior ou igual a START_DATE."
    )


# ============================================================
# CONFIGURAÇÃO EUMETSAT
# ============================================================

load_dotenv()

CONSUMER_KEY = os.getenv(
    "EUMETSAT_CONSUMER_KEY"
)

CONSUMER_SECRET = os.getenv(
    "EUMETSAT_CONSUMER_SECRET"
)


if not CONSUMER_KEY or not CONSUMER_SECRET:

    raise RuntimeError(
        "Variáveis EUMETSAT_CONSUMER_KEY e "
        "EUMETSAT_CONSUMER_SECRET não definidas."
    )


# ============================================================
# COLEÇÃO
# ============================================================

COLLECTION_ID = "EO:EUM:DAT:0416"


# ============================================================
# ÁREA
# ============================================================

# W, S, E, N
BBOX = "-86.17,-59.01,-30.12,11.60"


# ============================================================
# DIRETÓRIO
# ============================================================

YEAR = START_DATE[:4]

DOWNLOAD_DIR = (
    DATA_DIR
    / "L2"
    / PRODUCT_TYPE
    / YEAR
)

DOWNLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# AUTENTICAÇÃO
# ============================================================

def create_datastore():

    print(
        "\nAutenticando no EUMETSAT Data Store..."
    )

    token = eumdac.AccessToken(
        (
            CONSUMER_KEY,
            CONSUMER_SECRET
        )
    )

    datastore = eumdac.DataStore(token)

    print(
        "Autenticação EUMETSAT OK."
    )

    return datastore


# ============================================================
# BUSCA
# ============================================================

def search_products(datastore):

    collection = datastore.get_collection(
        COLLECTION_ID
    )

    print()
    print(
        f"Coleção: {COLLECTION_ID}"
    )

    print(
        f"Período: {START_DATE} -> {END_DATE}"
    )

    print(
        f"BBOX: {BBOX}"
    )

    print(
        "Satélite: Sentinel-3B"
    )

    products = collection.search(

        bbox=BBOX,

        dtstart=start,

        dtend=end,

        sat="Sentinel-3B"
    )

    print()

    print(
        f"Produtos encontrados: "
        f"{products.total_results}"
    )

    return products


# ============================================================
# DOWNLOAD
# ============================================================

def download_products(products):

    count = 0

    for product in products:

        count += 1

        product_name = str(product)

        filepath = (
            DOWNLOAD_DIR
            / f"{product_name}.zip"
        )

        if filepath.exists():

            print(
                f"[OK] Já existe: "
                f"{filepath.name}"
            )

            continue

        print()
        print(
            f"[DOWN] "
            f"{count}: {product_name}"
        )

        try:

            with product.open() as source:

                with open(
                    filepath,
                    "wb"
                ) as destination:

                    shutil.copyfileobj(
                        source,
                        destination
                    )

            print(
                f"[DONE] "
                f"{filepath}"
            )

        except Exception as error:

            print(
                f"[ERRO] "
                f"{product_name}: "
                f"{error}"
            )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 60)
    print(
        "DOWNLOAD SENTINEL-3 SLSTR AOD"
    )
    print("=" * 60)

    print(
        f"Produto: {PRODUCT_TYPE}"
    )

    print(
        f"Período: "
        f"{START_DATE} a {END_DATE}"
    )

    print(
        f"Destino: "
        f"{DOWNLOAD_DIR}"
    )

    print(
        f"Coleção: "
        f"{COLLECTION_ID}"
    )

    datastore = create_datastore()

    products = search_products(
        datastore
    )

    download_products(
        products
    )

    print()
    print("=" * 60)
    print("FIM")
    print("=" * 60)


if __name__ == "__main__":
    main()