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