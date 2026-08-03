"""
process_goes_aod.py

Processamento dos produtos GOES ABI L2.
"""

import sys
from datetime import datetime
from pathlib import Path
import numpy as np

from .goes_utils import (
    open_dataset,
    list_goes_files,
    read_aod,
    read_quality_flag,
    apply_quality_mask,
    read_projection,
    goes_xy_to_latlon,
    crop_bbox,
    create_output_filename,
    get_metadata,
)

from .interpolate_goes import (
    interpolate_grid
)

from .export_geotiff import export_geotiff

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

        print("\nApós read_aod")
        print("AOD válidos:", np.isfinite(aod).sum())        

        dqf, _ = read_quality_flag(ds)

        aod = apply_quality_mask(
            aod,
            dqf
        )

        proj = read_projection(ds)

        lon, lat = goes_xy_to_latlon(proj)

        print("\nApós goes_xy_to_latlon")
        print("Lon válidos:", np.isfinite(lon).sum())
        print("Lat válidos:", np.isfinite(lat).sum())        

        lon, lat, aod = crop_bbox(
            lon,
            lat,
            aod,
            (-90, -60, -30, 15)
        )       

        print("\nApós crop_bbox")
        print("AOD válidos:", np.isfinite(aod).sum())
        print("Shape:", aod.shape)

        try:
            grid_lon, grid_lat, grid_aod = interpolate_grid(
                lon,
                lat,
                aod,
                resolution=0.05,
                method="linear",
            )
        except ValueError as e:
            print(f"Pulando {arquivo.name}: {e}")
            ds.close()
            continue


        print("AOD min:", np.nanmin(aod))
        print("AOD max:", np.nanmax(aod))

        print("DQF únicos:", np.unique(dqf))


        # output_dir = Path(
        #     "/home/jurandir/cipc_output/geotiff/goes_aod"
        # )


        # metadata = get_metadata(ds)

        # output_file = create_output_filename(
        #     metadata,
        #     output_dir
        # )        

        metadata = get_metadata(ds)

        print("\nMETADATA")
        for k, v in metadata.items():
            print(f"{k}: {v}")

        # Ano do arquivo GOES
        # year = metadata["start_time"].strftime("%Y")
        year = metadata["time_coverage_start"][:4]

        # Diretório de saída organizado por ano
        output_dir = Path(
            "/home/jurandir/cipc_output/geotiff/goes_aod"
        ) / year

        # Cria o diretório caso não exista
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = create_output_filename(
            metadata,
            output_dir
        )       

        export_geotiff(
            output_file,
            grid_lon,
            grid_lat,
            grid_aod,
            metadata=metadata,
        )

        print("---> Arquivo existe?", output_file.exists())

        print(f"Saída: {output_file}")

        print(f"AOD original : {aod.shape}")
        print(f"Pontos úteis : {aod.size:,}")
        print(f"Longitude    : {lon.min():.2f} -> {lon.max():.2f}")
        print(f"Latitude     : {lat.min():.2f} -> {lat.max():.2f}")        

        ds.close()


# ==========================================================
if __name__ == "__main__":

    main()


