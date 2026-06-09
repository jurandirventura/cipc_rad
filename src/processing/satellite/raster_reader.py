# Define ponto de 0.5 ao redor para obtenção da 
# média dos dados para comparar com o ponto de 
# Observação - CETESB
# get_satellite_mean()
import numpy as np
import rasterio

# =========================================================
# FUNÇÃO SATÉLITE
# =========================================================
def get_satellite_mean(
    tif_file,
    lat_station,
    lon_station,
    delta=0.5
):

    try:

        with rasterio.open(tif_file) as src:

            band = src.read(1)

            lon_min = lon_station - delta
            lon_max = lon_station + delta

            lat_min = lat_station - delta
            lat_max = lat_station + delta

            row_min, col_min = src.index(
                lon_min,
                lat_max
            )

            row_max, col_max = src.index(
                lon_max,
                lat_min
            )

            r0 = min(row_min, row_max)
            r1 = max(row_min, row_max)

            c0 = min(col_min, col_max)
            c1 = max(col_min, col_max)

            subset = band[
                r0:r1+1,
                c0:c1+1
            ]

            nodata = src.nodata

            if nodata is not None:

                subset = subset[
                    subset != nodata
                ]

            subset = subset[
                np.isfinite(subset)
            ]

            if subset.size == 0:

                return np.nan

            return float(
                np.nanmean(subset)
            )

    except Exception as e:

        print("Erro GeoTIFF:", e)
        return np.nan