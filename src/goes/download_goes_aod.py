#!/usr/bin/env python3
"""
Download do produto GOES-16 ABI Aerosol Optical Depth (AOD)

Uso:

python src/goes/download_goes_aod.py 2023-10-10 2023-10-22

Os arquivos são gravados em:

DATA/L2/GOES_AOD/ANO/

"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

import boto3
from botocore import UNSIGNED
from botocore.config import Config

from src.config.settings import DATA_DIR
from src.config.goes_products import GOES_PRODUCTS

# ---------------------------------------------------------
# PARÂMETROS
# ---------------------------------------------------------

if len(sys.argv) != 4:
    print()
    print("Uso:")
    print("python -m src.goes.download_goes_aod PRODUCT START_DATE END_DATE")
    print()
    print("Exemplo:")
    print("python -m src.goes.download_goes_aod AOD 2024-08-15 2024-08-25")
    sys.exit(1)

PRODUCT_NAME = sys.argv[1].upper()
START_DATE = datetime.strptime(sys.argv[2], "%Y-%m-%d")
END_DATE = datetime.strptime(sys.argv[3], "%Y-%m-%d")

if PRODUCT_NAME not in GOES_PRODUCTS:
    raise ValueError(f"Produto '{PRODUCT_NAME}' não suportado.")

PRODUCT = GOES_PRODUCTS[PRODUCT_NAME]["product"]
BUCKET = GOES_PRODUCTS[PRODUCT_NAME]["bucket"]

DOWNLOAD_DIR = DATA_DIR / "L2" / PRODUCT_NAME / str(START_DATE.year)
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------
# S3 Público
# ---------------------------------------------------------

s3 = boto3.client(
    "s3",
    config=Config(signature_version=UNSIGNED)
)


# ---------------------------------------------------------
# Download
# ---------------------------------------------------------

def download_file(key):

    filename = key.split("/")[-1]

    outfile = DOWNLOAD_DIR / filename

    if outfile.exists():
        print(f"[OK] {filename}")
        return

    print(f"[DOWN] {filename}")

    s3.download_file(
        BUCKET,
        key,
        str(outfile)
    )


# ---------------------------------------------------------
# Listar arquivos de um dia
# ---------------------------------------------------------

def process_day(date):

    year = date.strftime("%Y")
    julian = date.strftime("%j")

    print(f"\nProcessando {date.date()}")

    total = 0

    for hour in range(24):

        prefix = f"{PRODUCT}/{year}/{julian}/{hour:02d}/"

        paginator = s3.get_paginator("list_objects_v2")

        for page in paginator.paginate(Bucket=BUCKET, Prefix=prefix):

            if "Contents" not in page:
                continue

            for obj in page["Contents"]:

                download_file(obj["Key"])
                total += 1

    print(f"{total} arquivos encontrados.")


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

def main():

    print()
    print("==============================")
    print("DOWNLOAD GOES-16 AOD")
    print("==============================")

    current = START_DATE

    while current <= END_DATE:

        process_day(current)

        current += timedelta(days=1)

    print()
    print("Fim.")


if __name__ == "__main__":
    main()