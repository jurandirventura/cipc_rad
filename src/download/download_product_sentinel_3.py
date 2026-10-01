#!/usr/bin/env python3

"""
Download Sentinel-3 SLSTR Level-2 Aerosol Optical Depth (AOD)

Coleção EUMETSAT:
    EO:EUM:DAT:0416

Satélites:
    S3A
    S3B
    S3A + S3B

Exemplos:

# Somente Sentinel-3A
python src/download/download_product_sentinel_3.py \
    S3A_AOD \
    2024-08-15 \
    2024-08-25

# Somente Sentinel-3B
python src/download/download_product_sentinel_3.py \
    S3B_AOD \
    2024-08-15 \
    2024-08-25

# Sentinel-3A + Sentinel-3B
python src/download/download_product_sentinel_3.py \
    S3AB_AOD \
    2024-08-15 \
    2024-08-25

Observação:

O produto SLSTR L2 AOD é aplicável somente durante o período
diurno. Portanto, não é necessário aplicar um filtro horário
artificial no download.
"""

import sys
import shutil
import datetime
from pathlib import Path
import os

import eumdac
from dotenv import load_dotenv

from src.config.settings import DATA_DIR


# ============================================================
# PARÂMETROS
# ============================================================

if len(sys.argv) != 4:

    print()
    print("Uso:")
    print(
        "python src/download/download_product_sentinel_3.py "
        "PRODUCT START_DATE END_DATE"
    )

    print()
    print("PRODUCT:")
    print("  S3A_AOD   -> somente Sentinel-3A")
    print("  S3B_AOD   -> somente Sentinel-3B")
    print("  S3AB_AOD  -> Sentinel-3A + Sentinel-3B")

    print()
    print("Exemplos:")

    print(
        "python src/download/download_product_sentinel_3.py "
        "S3A_AOD 2024-08-15 2024-08-25"
    )

    print(
        "python src/download/download_product_sentinel_3.py "
        "S3B_AOD 2024-08-15 2024-08-25"
    )

    print(
        "python src/download/download_product_sentinel_3.py "
        "S3AB_AOD 2024-08-15 2024-08-25"
    )

    print()

    sys.exit(1)


PRODUCT_TYPE = sys.argv[1]
START_DATE = sys.argv[2]
END_DATE = sys.argv[3]


# ============================================================
# VALIDAÇÃO DO PRODUTO
# ============================================================

VALID_PRODUCTS = {
    "S3A_AOD": ["Sentinel-3A"],
    "S3B_AOD": ["Sentinel-3B"],
    "S3AB_AOD": ["Sentinel-3A", "Sentinel-3B"],
}


if PRODUCT_TYPE not in VALID_PRODUCTS:

    raise ValueError(
        f"Produto inválido: {PRODUCT_TYPE}\n"
        f"Use: {', '.join(VALID_PRODUCTS.keys())}"
    )


SATELLITES = VALID_PRODUCTS[PRODUCT_TYPE]


# ============================================================
# VALIDAÇÃO DAS DATAS
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


# ------------------------------------------------------------
# IMPORTANTE:
#
# END_DATE é inclusiva.
#
# Exemplo:
#
# 2024-08-15 -> 2024-08-25
#
# significa:
#
# 15/08/2024 00:00:00
# até
# 25/08/2024 23:59:59
#
# Para isso usamos o início do dia seguinte como limite
# superior da busca.
# ------------------------------------------------------------

end_exclusive = end + datetime.timedelta(days=1)


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
#
# América do Sul / região utilizada no projeto

BBOX = "-86.17,-59.01,-30.12,11.60"


# ============================================================
# DIRETÓRIO BASE
# ============================================================

YEAR = START_DATE[:4]

BASE_DOWNLOAD_DIR = (
    DATA_DIR
    / "L2"
)


# ============================================================
# AUTENTICAÇÃO
# ============================================================

def create_datastore():

    print()
    print(
        "Autenticando no EUMETSAT Data Store..."
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

def search_products(
    datastore,
    satellite
):

    collection = datastore.get_collection(
        COLLECTION_ID
    )

    print()
    print("=" * 60)
    print(
        f"BUSCA - {satellite}"
    )
    print("=" * 60)

    print(
        f"Coleção: {COLLECTION_ID}"
    )

    print(
        f"Período: "
        f"{START_DATE} -> {END_DATE}"
    )

    print(
        f"BBOX: {BBOX}"
    )

    print(
        f"Satélite: {satellite}"
    )

    print(
        "Produto: SLSTR Level-2 AOD"
    )

    print(
        "Modo: NRT"
    )

    products = collection.search(

        bbox=BBOX,

        dtstart=start,

        dtend=end_exclusive,

        sat=satellite
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

def download_products(
    products,
    satellite
):

    count = 0
    downloaded = 0
    existing = 0
    errors = 0

    # --------------------------------------------------------
    # Diretório específico do satélite
    # --------------------------------------------------------

    if satellite == "Sentinel-3A":

        satellite_dir = "S3A_AOD"

    elif satellite == "Sentinel-3B":

        satellite_dir = "S3B_AOD"

    else:

        raise ValueError(
            f"Satélite não reconhecido: {satellite}"
        )


    download_dir = (
        BASE_DOWNLOAD_DIR
        / satellite_dir
        / YEAR
    )

    download_dir.mkdir(
        parents=True,
        exist_ok=True
    )


    print()
    print(
        f"Diretório de download:"
    )

    print(
        f"  {download_dir}"
    )

    print()


    # --------------------------------------------------------
    # Produtos
    # --------------------------------------------------------

    for product in products:

        count += 1

        product_name = str(product)

        filepath = (
            download_dir
            / f"{product_name}.zip"
        )


        # ----------------------------------------------------
        # Produto já baixado
        # ----------------------------------------------------

        if filepath.exists():

            existing += 1

            print(
                f"[OK] Já existe: "
                f"{filepath.name}"
            )

            continue


        # ----------------------------------------------------
        # Download
        # ----------------------------------------------------

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


            downloaded += 1

            print(
                f"[DONE] "
                f"{filepath}"
            )


        except Exception as error:

            errors += 1

            print(
                f"[ERRO] "
                f"{product_name}: "
                f"{error}"
            )


    # --------------------------------------------------------
    # Resumo
    # --------------------------------------------------------

    print()

    print(
        f"Resumo {satellite}:"
    )

    print(
        f"  Encontrados : {count}"
    )

    print(
        f"  Baixados    : {downloaded}"
    )

    print(
        f"  Já existiam : {existing}"
    )

    print(
        f"  Erros       : {errors}"
    )

    print(
        f"  Diretório   : {download_dir}"
    )

    print()

    return {
        "found": count,
        "downloaded": downloaded,
        "existing": existing,
        "errors": errors,
    }


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
        f"Produto solicitado: {PRODUCT_TYPE}"
    )

    print(
        f"Satélites: "
        f"{', '.join(SATELLITES)}"
    )

    print(
        f"Período: "
        f"{START_DATE} a {END_DATE}"
    )

    print(
        f"BBOX: "
        f"{BBOX}"
    )

    print(
        f"Coleção: "
        f"{COLLECTION_ID}"
    )

    print()
    print(
        "Observação: o produto SLSTR L2 AOD"
    )

    print(
        "é aplicável somente durante o período diurno."
    )

    print(
        "Não será aplicado filtro horário artificial."
    )


    # --------------------------------------------------------
    # Autenticação
    # --------------------------------------------------------

    datastore = create_datastore()


    # --------------------------------------------------------
    # Download de cada satélite
    # --------------------------------------------------------

    total = {
        "found": 0,
        "downloaded": 0,
        "existing": 0,
        "errors": 0,
    }


    for satellite in SATELLITES:

        products = search_products(
            datastore,
            satellite
        )

        result = download_products(
            products,
            satellite
        )


        for key in total:

            total[key] += result[key]


    # --------------------------------------------------------
    # RESUMO FINAL
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print(
        "RESUMO FINAL"
    )
    print("=" * 60)

    print(
        f"Produtos encontrados : "
        f"{total['found']}"
    )

    print(
        f"Produtos baixados    : "
        f"{total['downloaded']}"
    )

    print(
        f"Já existentes        : "
        f"{total['existing']}"
    )

    print(
        f"Erros                : "
        f"{total['errors']}"
    )

    print()

    print(
        "FIM"
    )

    print("=" * 60)


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":

    main()




# #!/usr/bin/env python3

# """
# Download Sentinel-3 SLSTR Level-2 Aerosol Optical Depth (AOD)

# Coleção EUMETSAT:
#     EO:EUM:DAT:0416

# Exemplo:

# python src/download/download_sentinel3_aod.py \
#     S3B_AOD \
#     2024-08-16 \
#     2024-08-26
# """

# import sys
# import shutil
# import datetime
# from pathlib import Path

# import eumdac
# from dotenv import load_dotenv
# import os

# from src.config.settings import DATA_DIR


# # ============================================================
# # PARÂMETROS
# # ============================================================

# if len(sys.argv) != 4:
#     print()
#     print("Uso:")
#     print(
#         "python src/download/download_sentinel3_aod.py "
#         "PRODUCT START_DATE END_DATE"
#     )
#     print()
#     print("Exemplo:")
#     print(
#         "python src/download/download_sentinel3_aod.py "
#         "S3B_AOD 2024-08-16 2024-08-26"
#     )
#     print()
#     sys.exit(1)


# PRODUCT_TYPE = sys.argv[1]
# START_DATE = sys.argv[2]
# END_DATE = sys.argv[3]


# # ============================================================
# # VALIDAÇÃO
# # ============================================================

# try:
#     start = datetime.datetime.strptime(
#         START_DATE,
#         "%Y-%m-%d"
#     )

#     end = datetime.datetime.strptime(
#         END_DATE,
#         "%Y-%m-%d"
#     )

# except ValueError:

#     print(
#         "Formato de data inválido. "
#         "Use YYYY-MM-DD"
#     )

#     sys.exit(1)


# if end < start:

#     raise ValueError(
#         "END_DATE deve ser maior ou igual a START_DATE."
#     )


# # ============================================================
# # CONFIGURAÇÃO EUMETSAT
# # ============================================================

# load_dotenv()

# CONSUMER_KEY = os.getenv(
#     "EUMETSAT_CONSUMER_KEY"
# )

# CONSUMER_SECRET = os.getenv(
#     "EUMETSAT_CONSUMER_SECRET"
# )


# if not CONSUMER_KEY or not CONSUMER_SECRET:

#     raise RuntimeError(
#         "Variáveis EUMETSAT_CONSUMER_KEY e "
#         "EUMETSAT_CONSUMER_SECRET não definidas."
#     )


# # ============================================================
# # COLEÇÃO
# # ============================================================

# COLLECTION_ID = "EO:EUM:DAT:0416"


# # ============================================================
# # ÁREA
# # ============================================================

# # W, S, E, N
# BBOX = "-86.17,-59.01,-30.12,11.60"


# # ============================================================
# # DIRETÓRIO
# # ============================================================

# YEAR = START_DATE[:4]

# DOWNLOAD_DIR = (
#     DATA_DIR
#     / "L2"
#     / PRODUCT_TYPE
#     / YEAR
# )

# DOWNLOAD_DIR.mkdir(
#     parents=True,
#     exist_ok=True
# )


# # ============================================================
# # AUTENTICAÇÃO
# # ============================================================

# def create_datastore():

#     print(
#         "\nAutenticando no EUMETSAT Data Store..."
#     )

#     token = eumdac.AccessToken(
#         (
#             CONSUMER_KEY,
#             CONSUMER_SECRET
#         )
#     )

#     datastore = eumdac.DataStore(token)

#     print(
#         "Autenticação EUMETSAT OK."
#     )

#     return datastore


# # ============================================================
# # BUSCA
# # ============================================================

# def search_products(datastore):

#     collection = datastore.get_collection(
#         COLLECTION_ID
#     )

#     print()
#     print(
#         f"Coleção: {COLLECTION_ID}"
#     )

#     print(
#         f"Período: {START_DATE} -> {END_DATE}"
#     )

#     print(
#         f"BBOX: {BBOX}"
#     )

#     print(
#         "Satélite: Sentinel-3B"
#     )

#     products = collection.search(

#         bbox=BBOX,

#         dtstart=start,

#         dtend=end,

#         sat="Sentinel-3B"
#     )

#     print()

#     print(
#         f"Produtos encontrados: "
#         f"{products.total_results}"
#     )

#     return products


# # ============================================================
# # DOWNLOAD
# # ============================================================

# def download_products(products):

#     count = 0

#     for product in products:

#         count += 1

#         product_name = str(product)

#         filepath = (
#             DOWNLOAD_DIR
#             / f"{product_name}.zip"
#         )

#         if filepath.exists():

#             print(
#                 f"[OK] Já existe: "
#                 f"{filepath.name}"
#             )

#             continue

#         print()
#         print(
#             f"[DOWN] "
#             f"{count}: {product_name}"
#         )

#         try:

#             with product.open() as source:

#                 with open(
#                     filepath,
#                     "wb"
#                 ) as destination:

#                     shutil.copyfileobj(
#                         source,
#                         destination
#                     )

#             print(
#                 f"[DONE] "
#                 f"{filepath}"
#             )

#         except Exception as error:

#             print(
#                 f"[ERRO] "
#                 f"{product_name}: "
#                 f"{error}"
#             )


# # ============================================================
# # MAIN
# # ============================================================

# def main():

#     print()
#     print("=" * 60)
#     print(
#         "DOWNLOAD SENTINEL-3 SLSTR AOD"
#     )
#     print("=" * 60)

#     print(
#         f"Produto: {PRODUCT_TYPE}"
#     )

#     print(
#         f"Período: "
#         f"{START_DATE} a {END_DATE}"
#     )

#     print(
#         f"Destino: "
#         f"{DOWNLOAD_DIR}"
#     )

#     print(
#         f"Coleção: "
#         f"{COLLECTION_ID}"
#     )

#     datastore = create_datastore()

#     products = search_products(
#         datastore
#     )

#     download_products(
#         products
#     )

#     print()
#     print("=" * 60)
#     print("FIM")
#     print("=" * 60)


# if __name__ == "__main__":
#     main()