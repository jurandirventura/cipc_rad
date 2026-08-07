# Organiza a leitura dos produtos de satélite
# get_satellite_series()

import pandas as pd
import numpy as np

from satellite.raster_reader import get_satellite_mean

# =========================================================
# Função para leitura dos produtos de satélite
# =========================================================
def get_satellite_series(
    sat_index,
    datas_unicas,
    lat_station,
    lon_station,
    delta,
    scale=1.0
):

    sat_dates = []
    sat_values = []

    for data_ref in datas_unicas:

        yyyymmdd = pd.Timestamp(
            data_ref
        ).strftime("%Y%m%d")

        tif_file = sat_index.get(yyyymmdd)

        if tif_file is None:
            continue

        valor = get_satellite_mean(
            tif_file,
            lat_station,
            lon_station,
            delta
        )

        if np.isfinite(valor):

            sat_dates.append(
                pd.Timestamp(data_ref)
            )

            sat_values.append(
                valor * scale
            )

    return sat_dates, sat_values


# =========================================================
# Função para leitura dos produtos GOES com data + hora
# =========================================================
def get_goes_series(
    goes_index,
    datas_unicas,
    lat_station,
    lon_station,
    delta,
    scale=1.0
):
    """
    Extrai série temporal dos produtos GOES.

    O índice GOES utiliza chaves no formato:

        YYYYMMDD_HHMMSS

    Exemplo:

        20240816_143020
        20240816_152020
        20240816_181020

    Retorna um ponto para cada arquivo GOES disponível.
    """

    goes_dates = []
    goes_values = []

    for data_ref in datas_unicas:

        data_ref = pd.Timestamp(data_ref)

        prefix = data_ref.strftime(
            "%Y%m%d"
        )

        # -------------------------------------------------
        # Todos os arquivos GOES daquele dia
        # -------------------------------------------------

        arquivos_dia = sorted(
            (
                key,
                tif_file
            )
            for key, tif_file in goes_index.items()
            if key.startswith(prefix + "_")
        )

        # -------------------------------------------------
        # Processa cada horário
        # -------------------------------------------------

        for key, tif_file in arquivos_dia:

            valor = get_satellite_mean(
                tif_file,
                lat_station,
                lon_station,
                delta
            )

            if not np.isfinite(valor):
                continue

            # ---------------------------------------------
            # YYYYMMDD_HHMMSS
            # →
            # Timestamp
            # ---------------------------------------------

            data_hora = pd.to_datetime(
                key,
                format="%Y%m%d_%H%M%S"
            )

            goes_dates.append(
                data_hora
            )

            goes_values.append(
                valor * scale
            )

    return goes_dates, goes_values

