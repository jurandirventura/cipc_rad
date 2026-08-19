# Define ponto de 0.5 ao redor para obtenção da 
# média dos dados para comparar com o ponto de 
# Observação - CETESB
# get_satellite_mean()

import numpy as np
import rasterio
from rasterio.windows import Window


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

            lon_min = lon_station - delta
            lon_max = lon_station + delta

            lat_min = lat_station - delta
            lat_max = lat_station + delta

            # -------------------------------------------------
            # Converte coordenadas para linhas/colunas
            # -------------------------------------------------

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

            # -------------------------------------------------
            # Limita à extensão do raster
            # -------------------------------------------------

            r0 = max(0, r0)
            c0 = max(0, c0)

            r1 = min(src.height - 1, r1)
            c1 = min(src.width - 1, c1)

            if r1 < r0 or c1 < c0:
                return np.nan

            # -------------------------------------------------
            # Lê SOMENTE a janela necessária
            # -------------------------------------------------

            window = Window(
                c0,
                r0,
                c1 - c0 + 1,
                r1 - r0 + 1
            )

            subset = src.read(
                1,
                window=window
            )

            # -------------------------------------------------
            # Remove NoData
            # -------------------------------------------------

            nodata = src.nodata

            if nodata is not None:

                subset = subset[
                    subset != nodata
                ]

            # -------------------------------------------------
            # Remove NaN / infinito
            # -------------------------------------------------

            subset = subset[
                np.isfinite(subset)
            ]

            if subset.size == 0:
                return np.nan

            return float(
                np.nanmean(subset)
            )

    except Exception as e:

        print(
            "Erro GeoTIFF:",
            tif_file,
            e
        )

        return np.nan


### VERSÃO FUNCIONA MAS PARA GOES DE 10 EM 10 MINUTOS 
### E LÊ A IMAGEM TODA (DESNECESSÁRIO). Pode ler apenas 
### o ponto e limites de interesse.
# import numpy as np
# import rasterio

# # =========================================================
# # FUNÇÃO SATÉLITE
# # =========================================================
# def get_satellite_mean(
#     tif_file,
#     lat_station,
#     lon_station,
#     delta=0.5
# ):

#     try:

#         with rasterio.open(tif_file) as src:

#             band = src.read(1)

#             lon_min = lon_station - delta
#             lon_max = lon_station + delta

#             lat_min = lat_station - delta
#             lat_max = lat_station + delta

#             row_min, col_min = src.index(
#                 lon_min,
#                 lat_max
#             )

#             row_max, col_max = src.index(
#                 lon_max,
#                 lat_min
#             )

#             r0 = min(row_min, row_max)
#             r1 = max(row_min, row_max)

#             c0 = min(col_min, col_max)
#             c1 = max(col_min, col_max)

#             subset = band[
#                 r0:r1+1,
#                 c0:c1+1
#             ]

#             nodata = src.nodata

#             if nodata is not None:

#                 subset = subset[
#                     subset != nodata
#                 ]

#             subset = subset[
#                 np.isfinite(subset)
#             ]

#             if subset.size == 0:

#                 return np.nan

#             return float(
#                 np.nanmean(subset)
#             )

#     except Exception as e:

#         print("Erro GeoTIFF:", e)
#         return np.nan