"""
process_goes_aod.py

Processamento dos produtos GOES ABI L2.
"""

import sys
from datetime import datetime
from pathlib import Path

from .goes_utils import (
    open_dataset,
    list_goes_files,
    read_aod,
)

# ==========================================================
# Leitura dos argumentos
# ==========================================================
if len(sys.argv) != 4:

    print(
        "Uso:\n"
        "python -m src.goes.process_goes_aod "
        "<PRODUTO> <DATA_INICIAL> <DATA_FINAL>"
    )

    print("\nExemplo:")

    print(
        "python -m src.goes.process_goes_aod "
        "AOD 2024-08-15 2024-08-20"
    )

    sys.exit(1)

PRODUCT_TYPE = sys.argv[1].upper()

START_DATE = sys.argv[2]

END_DATE = sys.argv[3]


# ==========================================================
# Validação das datas
# ==========================================================
try:

    START_DATE = datetime.strptime(
        START_DATE,
        "%Y-%m-%d"
    )

    END_DATE = datetime.strptime(
        END_DATE,
        "%Y-%m-%d"
    )

except ValueError:

    print("Formato de data inválido. Use YYYY-MM-DD")

    sys.exit(1)


# ==========================================================
def main():

    # input_dir = Path(
    #     f"/home/jurandir/cipc_data/L2/{PRODUCT_TYPE}"
    # )

    input_dir = Path(
        f"/home/jurandir/cipc_data/L2/{PRODUCT_TYPE}/{START_DATE.year}"
    )    

    arquivos = list_goes_files(
        input_dir,
        START_DATE,
        END_DATE
    )

    print(f"{len(arquivos)} arquivos encontrados.\n")

    for arquivo in arquivos:

        print(f"Lendo: {arquivo.name}")

        ds = open_dataset(arquivo)

        aod, attrs = read_aod(ds)

        print(aod.shape)

        ds.close()


# ==========================================================
if __name__ == "__main__":

    main()




# """
# process_goes_aod.py

# Processamento dos produtos GOES-16 ABI L2 AOD.
# """

# from pathlib import Path

# from .goes_utils import (
#     open_dataset,
#     list_goes_files,
#     read_aod,
# )


# # ==========================================================
# # Programa principal
# # ==========================================================
# def main():

#     input_dir = Path("/home/jurandir/cipc_data/L2/AOD/2024")

#     arquivos = list_goes_files(input_dir)

#     print(f"{len(arquivos)} arquivos encontrados.\n")

#     for arquivo in arquivos:

#         print(f"Lendo: {arquivo.name}")

#         # Abre o NetCDF
#         ds = open_dataset(arquivo)

#         # Lê a variável AOD
#         aod, attrs = read_aod(ds)

#         print(f"Dimensão: {aod.shape}")
#         print(f"Unidade : {attrs.get('units', 'N/D')}")
#         print("-" * 60)

#         ds.close()


# # ==========================================================
# if __name__ == "__main__":

#     main()