"""
interpolate_goes.py

Rotinas de interpolação dos dados GOES.
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
    Interpola os dados GOES para uma grade regular.

    Parameters
    ----------
    lon : ndarray
    lat : ndarray
    aod : ndarray
    resolution : float
    method : {"nearest", "linear", "cubic"}

    Returns
    -------
    grid_lon, grid_lat, grid_aod
    """

    # mask = np.isfinite(aod)

#     mask = (
#     np.isfinite(lon) &
#     np.isfinite(lat) &
#     np.isfinite(aod)
# )

    mask = (
        np.isfinite(lon) &
        np.isfinite(lat) &
        np.isfinite(aod)
    )

    if mask.sum() == 0:
        raise ValueError("Nenhum ponto válido para interpolação.")    

    print("Pontos válidos:", mask.sum())

    points = np.column_stack((lon[mask], lat[mask]))
    values = aod[mask]

    xi = np.arange(lon.min(), lon.max() + resolution, resolution)
    yi = np.arange(lat.min(), lat.max() + resolution, resolution)

    grid_lon, grid_lat = np.meshgrid(xi, yi)

    grid_aod = griddata(
        points,
        values,
        (grid_lon, grid_lat),
        method=method,
    )

    return grid_lon, grid_lat, grid_aod