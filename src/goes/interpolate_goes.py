"""
interpolate_goes.py

Rotinas de interpolação/binning dos dados GOES.
"""

import numpy as np
from scipy.interpolate import griddata


def interpolate_grid(
    lon,
    lat,
    aod,
    resolution=0.05,
    method="linear",
):
    """
    Gera uma grade regular a partir dos pixels GOES.

    Parameters
    ----------
    lon : ndarray
    lat : ndarray
    aod : ndarray
    resolution : float
    method : {"linear","nearest","cubic","binning"}

    Returns
    -------
    grid_lon
    grid_lat
    grid_aod
    """

    lon = np.asarray(lon).ravel()
    lat = np.asarray(lat).ravel()
    aod = np.asarray(aod).ravel()

    mask = (
        np.isfinite(lon)
        & np.isfinite(lat)
        & np.isfinite(aod)
    )

    if mask.sum() == 0:
        raise ValueError(
            "Nenhum ponto válido para interpolação."
        )

    lon = lon[mask]
    lat = lat[mask]
    aod = aod[mask]

    print("Pontos válidos:", len(aod))

    # # Definidos por limites mínimos e máximos da passagem
    # xmin = lon.min()
    # xmax = lon.max()
    # ymin = lat.min()
    # ymax = lat.max()

    # Definidos limites iguais aos utilizados para o Sentinel-5P
    # Assim a saída GeoTIFF do AOD-GOES segue o mesmo padrão
    xmin = -85
    xmax = -30
    ymin = -60
    ymax = 15

    # =====================================================
    # MÉTODO BINNING (igual ao Sentinel)
    # =====================================================
    if method.lower() == "binning":

        lon_bins = np.arange(
            xmin,
            xmax + resolution,
            resolution
        )

        lat_bins = np.arange(
            ymin,
            ymax + resolution,
            resolution
        )

        lon_idx = np.digitize(
            lon,
            lon_bins
        ) - 1

        lat_idx = np.digitize(
            lat,
            lat_bins
        ) - 1

        grid_sum = np.zeros(
            (len(lat_bins), len(lon_bins)),
            dtype=np.float64
        )

        grid_count = np.zeros_like(grid_sum)

        for x, y, valor in zip(
            lon_idx,
            lat_idx,
            aod
        ):

            if (
                0 <= x < len(lon_bins)
                and
                0 <= y < len(lat_bins)
            ):

                grid_sum[y, x] += valor
                grid_count[y, x] += 1

        grid_aod = np.full_like(
            grid_sum,
            np.nan,
            dtype=np.float32
        )

        np.divide(
            grid_sum,
            grid_count,
            out=grid_aod,
            where=grid_count > 0
        )

        grid_lon, grid_lat = np.meshgrid(
            lon_bins,
            lat_bins
        )

        return (
            grid_lon,
            grid_lat,
            grid_aod
        )

    # =====================================================
    # INTERPOLAÇÃO (método antigo)
    # =====================================================

    points = np.column_stack(
        (lon, lat)
    )

    xi = np.arange(
        xmin,
        xmax + resolution,
        resolution
    )

    yi = np.arange(
        ymin,
        ymax + resolution,
        resolution
    )

    grid_lon, grid_lat = np.meshgrid(
        xi,
        yi
    )

    grid_aod = griddata(
        points,
        aod,
        (grid_lon, grid_lat),
        method=method
    )

    return (
        grid_lon,
        grid_lat,
        grid_aod
    )



# """
# interpolate_goes.py

# Rotinas de interpolação dos dados GOES.
# """

# import numpy as np
# from scipy.interpolate import griddata


# def interpolate_grid(
#     lon,
#     lat,
#     aod,
#     resolution=0.05,
#     method="linear",
# ):
#     """
#     Interpola os dados GOES para uma grade regular.

#     Parameters
#     ----------
#     lon : ndarray
#     lat : ndarray
#     aod : ndarray
#     resolution : float
#     method : {"nearest", "linear", "cubic"}

#     Returns
#     -------
#     grid_lon, grid_lat, grid_aod
#     """

#     # mask = np.isfinite(aod)

# #     mask = (
# #     np.isfinite(lon) &
# #     np.isfinite(lat) &
# #     np.isfinite(aod)
# # )

#     mask = (
#         np.isfinite(lon) &
#         np.isfinite(lat) &
#         np.isfinite(aod)
#     )

#     if mask.sum() == 0:
#         raise ValueError("Nenhum ponto válido para interpolação.")    

#     print("Pontos válidos:", mask.sum())

#     points = np.column_stack((lon[mask], lat[mask]))
#     values = aod[mask]

#     xi = np.arange(lon.min(), lon.max() + resolution, resolution)
#     yi = np.arange(lat.min(), lat.max() + resolution, resolution)

#     grid_lon, grid_lat = np.meshgrid(xi, yi)

#     grid_aod = griddata(
#         points,
#         values,
#         (grid_lon, grid_lat),
#         method=method,
#     )

#     return grid_lon, grid_lat, grid_aod