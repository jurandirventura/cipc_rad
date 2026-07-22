"""
process_goes_aod.py

Processamento dos produtos GOES-16 ABI L2 AOD.
"""

from pathlib import Path

from .goes_utils import (
    open_dataset,
    list_goes_files,
    read_aod,
)


# ==========================================================
# Programa principal
# ==========================================================
def main():

    input_dir = Path("/home/jurandir/cipc_data/L2/AOD/2024")

    arquivos = list_goes_files(input_dir)

    print(f"{len(arquivos)} arquivos encontrados.\n")

    for arquivo in arquivos:

        print(f"Lendo: {arquivo.name}")

        # Abre o NetCDF
        ds = open_dataset(arquivo)

        # Lê a variável AOD
        aod, attrs = read_aod(ds)

        print(f"Dimensão: {aod.shape}")
        print(f"Unidade : {attrs.get('units', 'N/D')}")
        print("-" * 60)

        ds.close()


# ==========================================================
if __name__ == "__main__":

    main()