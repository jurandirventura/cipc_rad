"""
export_geotiff.py

Exportação de dados GOES para GeoTIFF.
"""

from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin


def export_geotiff(
    output_file,
    grid_lon,
    grid_lat,
    grid_data,
    metadata=None,
    nodata=np.nan,
):
    """
    Exporta uma grade regular para GeoTIFF.

    Parameters
    ----------
    output_file : str | Path
        Nome do arquivo de saída.

    grid_lon : ndarray
        Grade de longitude (meshgrid).

    grid_lat : ndarray
        Grade de latitude (meshgrid).

    grid_data : ndarray
        Dados interpolados.

    metadata : dict, optional
        Metadados do produto GOES.

    nodata : float
        Valor NoData.
    """

    output_file = Path(output_file)
    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    xres = float(grid_lon[0, 1] - grid_lon[0, 0])
    yres = float(grid_lat[1, 0] - grid_lat[0, 0])

    transform = from_origin(
        west=float(grid_lon.min()),
        north=float(grid_lat.max()),
        xsize=xres,
        ysize=abs(yres),
    )

    data = np.flipud(grid_data.astype(np.float32))

    with rasterio.open(
        output_file,
        "w",
        driver="GTiff",
        height=data.shape[0],
        width=data.shape[1],
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=transform,
        compress="deflate",
        nodata=nodata,
    ) as dst:

        dst.write(data, 1)

        if metadata:

            dst.update_tags(**metadata)

    print(f"GeoTIFF salvo: {output_file}")