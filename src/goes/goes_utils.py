"""
goes_utils.py

Funções auxiliares para leitura e processamento dos produtos
GOES-16 ABI L2 AOD.
"""

from pathlib import Path
import numpy as np
import re
from datetime import datetime
import xarray as xr
from scipy.interpolate import griddata

# ==========================================================
# Verifica se o Dataset possui as variáveis necessárias
# ==========================================================
def check_dataset(ds):

    required = [
        "AOD",
        "DQF",
        "goes_imager_projection"
    ]

    for var in required:

        if var not in ds:

            raise RuntimeError(
                f"Variável '{var}' não encontrada no arquivo GOES."
            )


# ==========================================================
# Abre arquivo NetCDF do GOES
# ==========================================================
def open_dataset(nc_file):
    """
    Abre um produto GOES ABI-L2-AODF.

    Parameters
    ----------
    nc_file : str | Path
        Caminho para o arquivo NetCDF.

    Returns
    -------
    xarray.Dataset
    """

    nc_file = Path(nc_file)

    if not nc_file.exists():

        raise FileNotFoundError(
            f"Arquivo inexistente:\n{nc_file}"
        )

    try:

        ds = xr.open_dataset(
            nc_file,
            engine="netcdf4",
            mask_and_scale=True,
            decode_times=True
        )

    except Exception as e:

        raise RuntimeError(
            f"Erro abrindo arquivo GOES:\n{nc_file}\n{e}"
        )

    # Valida o conteúdo do NetCDF
    check_dataset(ds)

    return ds


# ==========================================================
# Lê o produto AOD
# ==========================================================
def read_aod(ds):
    """
    Lê a variável AOD do produto GOES.

    Parameters
    ----------
    ds : xarray.Dataset

    Returns
    -------
    aod : numpy.ndarray
        Matriz 2D contendo os valores de AOD.

    attrs : dict
        Metadados da variável AOD.
    """

    if "AOD" not in ds:

        raise RuntimeError(
            "Variável 'AOD' não encontrada no Dataset."
        )

    var = ds["AOD"]

    aod = var.values.astype(np.float32)

    attrs = dict(var.attrs)

    aod = np.where(
        np.isfinite(aod),
        aod,
        np.nan
    )

    attrs = dict(var.attrs)

    return aod,attrs


def read_projection(ds):
    ...

def goes_xy_to_latlon(ds):
    ...

import numpy as np


# ==========================================================
# Lê a variável DQF (Data Quality Flag)
# ==========================================================
def read_quality_flag(ds):
    """
    Lê a variável DQF do produto GOES.

    Parameters
    ----------
    ds : xarray.Dataset

    Returns
    -------
    dqf : numpy.ndarray
        Matriz contendo os valores da Data Quality Flag.

    attrs : dict
        Metadados da variável DQF.
    """

    if "DQF" not in ds:

        raise RuntimeError(
            "Variável 'DQF' não encontrada no Dataset."
        )

    var = ds["DQF"]

    # dqf = var.values.astype(np.uint8)
    dqf = np.nan_to_num(
    var.values,
    nan=255
    ).astype(np.uint8)

    attrs = dict(var.attrs)

    return dqf, attrs

# ==========================================================
# Aplica máscara de qualidade ao AOD
# ==========================================================
def apply_quality_mask(aod, dqf, max_dqf=1):
    """
    Remove pixels de baixa qualidade.

    Parameters
    ----------
    aod : ndarray
    dqf : ndarray
    max_dqf : int

    Returns
    -------
    ndarray
    """

    aod = aod.copy()

    aod[dqf > max_dqf] = np.nan

    return aod


# ==========================================================
# Substitui valores inválidos por NaN
# ==========================================================
def replace_fill_values(data):
    """
    Substitui valores inválidos.

    Parameters
    ----------
    data : ndarray

    Returns
    -------
    ndarray
    """

    data = data.astype(np.float32)

    data[~np.isfinite(data)] = np.nan

    data[data < -9000] = np.nan

    return data



# ==========================================================
# Recorta área de interesse
# ==========================================================
def crop_bbox(lon, lat, data, bbox):
    """
    bbox = (
        lon_min,
        lat_min,
        lon_max,
        lat_max
    )
    """

    lon_min, lat_min, lon_max, lat_max = bbox

    mask = (
        (lon >= lon_min) &
        (lon <= lon_max) &
        (lat >= lat_min) &
        (lat <= lat_max)
    )

    return (
        lon[mask],
        lat[mask],
        data[mask]
    )


# ==========================================================
# Nome do arquivo de saída - Padronização
# ==========================================================
# def create_output_filename(
#     input_file,
#     output_dir
# ):

#     info = parse_goes_filename(
#         Path(input_file).name
#     )

#     data = info["start"].strftime(
#         "%Y%m%d"
#     )

#     output_dir = Path(output_dir)

#     output_dir.mkdir(
#         parents=True,
#         exist_ok=True
#     )

#     return output_dir / (
#         f"aod_goes16_{data}_overlay.tif"
#     )


def create_output_filename(
    metadata,
    output_dir,
    prefix="aod"
):
    data = datetime.fromisoformat(
        metadata["time_coverage_start"].replace("Z", "")
    )

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    return output_dir / (
        f"{prefix}_goes16_{data:%Y%m%d_%H%M%S}.tif"
    )



# ==========================================================
# Extrai metadados
# ==========================================================
def get_metadata(ds):

    meta = {}

    meta["platform"] = ds.attrs.get(
        "platform_ID",
        "G16"
    )

    meta["instrument"] = ds.attrs.get(
        "instrument_type",
        "ABI"
    )

    meta["title"] = ds.attrs.get(
        "title",
        ""
    )

    meta["time_coverage_start"] = ds.attrs.get(
        "time_coverage_start",
        ""
    )

    meta["time_coverage_end"] = ds.attrs.get(
        "time_coverage_end",
        ""
    )

    return meta



def list_goes_files(
    directory,
    start_date,
    end_date
):

    arquivos = []

    # for file in sorted(Path(directory).glob("*.nc")):
    for file in Path(directory).rglob("*.nc"):
        info = parse_goes_filename(
            file.name
        )

        print(file.name)
        print(info["start"])
        print(start_date)
        print(end_date)          

        if start_date.date() <= info["start"].date() <= end_date.date():
            arquivos.append(file)


    return arquivos


def goes_time_to_datetime(timestr):
    """
    Converte tempo GOES (YYYYJJJHHMMSS)
    para datetime.
    """

    year = int(timestr[0:4])
    julian = int(timestr[4:7])
    hour = int(timestr[7:9])
    minute = int(timestr[9:11])
    second = int(timestr[11:13])

    dt = datetime.strptime(
        f"{year} {julian}",
        "%Y %j"
    )

    return dt.replace(
        hour=hour,
        minute=minute,
        second=second
    )


# ==========================================================
# Extrai informações do nome do arquivo GOES
# ==========================================================
from pathlib import Path

def parse_goes_filename(filename):
    """
    Extrai informações do nome do arquivo GOES.

    Exemplo:
    OR_ABI-L2-AODF-M6_G16_s20242361640205_e20242361649513_c20242361654253.nc
    """

    nome = Path(filename).stem

    partes = nome.split("_")

    # ['OR', 'ABI-L2-AODF-M6', 'G16',
    #  's20242361640205',
    #  'e20242361649513',
    #  'c20242361654253']

    produto = partes[1].split("-")[2]      # AODF

    satelite = partes[2]                   # G16

    start = goes_time_to_datetime(
        partes[3][1:]                      # remove o 's'
    )

    end = goes_time_to_datetime(
        partes[4][1:]                      # remove o 'e'
    )

    created = goes_time_to_datetime(
        partes[5][1:]                      # remove o 'c'
    )

    return {

        "product": produto,

        "satellite": satelite,

        "start": start,

        "end": end,

        "created": created,

        "year": start.year,

        "julian": start.timetuple().tm_yday
    }



# ==========================================================
# Lê os parâmetros da projeção GOES
# ==========================================================
def read_projection(ds):
    """
    Lê as informações da projeção geostacionária.

    Returns
    -------
    dict
    """

    proj = ds["goes_imager_projection"]

    return {

        "x": ds["x"].values.astype(np.float64),

        "y": ds["y"].values.astype(np.float64),

        "H": (
            proj.perspective_point_height +
            proj.semi_major_axis
        ),

        "lon0": np.deg2rad(
            proj.longitude_of_projection_origin
        ),

        "a": proj.semi_major_axis,

        "b": proj.semi_minor_axis,

        "sweep": proj.sweep_angle_axis
    }



# ==========================================================
# Converte coordenadas GOES para Latitude/Longitude
# ==========================================================
def goes_xy_to_latlon(proj):
    """
    Converte coordenadas do GOES em latitude e longitude.

    Parameters
    ----------
    proj : dict

    Returns
    -------
    lon, lat
    """

    x = proj["x"]
    y = proj["y"]

    xx, yy = np.meshgrid(x, y)

    H = proj["H"]
    a = proj["a"]
    b = proj["b"]
    lon0 = proj["lon0"]

    cosx = np.cos(xx)
    sinx = np.sin(xx)

    cosy = np.cos(yy)
    siny = np.sin(yy)

    req2 = a**2
    rpol2 = b**2

    A = (
        sinx**2 +
        cosx**2 *
        (cosy**2 + req2/rpol2 * siny**2)
    )

    B = -2 * H * cosx * cosy

    C = H**2 - req2

    rs = (-B - np.sqrt(B**2 - 4*A*C)) / (2*A)

    sx = rs * cosx * cosy

    sy = -rs * sinx

    sz = rs * cosx * siny

    lat = np.rad2deg(
        np.arctan(
            req2/rpol2 *
            sz /
            np.sqrt((H-sx)**2 + sy**2)
        )
    )

    lon = np.rad2deg(
        lon0 -
        np.arctan(
            sy /
            (H-sx)
        )
    )

    return lon, lat


"""
interpolate_goes.py

Interpola os pixels do GOES para uma grade regular
(latitude/longitude - EPSG:4326).
"""
# ==========================================================
# Interpolação dos dados GOES
# ==========================================================
def interpolate_grid(
    lon,
    lat,
    data,
    resolution=0.05,
    method="linear"
):
    """
    Interpola os dados GOES para uma grade regular.

    Parameters
    ----------
    lon : ndarray
        Longitude (2D ou 1D).

    lat : ndarray
        Latitude (2D ou 1D).

    data : ndarray
        Valores do produto (AOD).

    resolution : float
        Resolução da grade em graus.

    method : str
        nearest | linear | cubic

    Returns
    -------
    grid_lon : ndarray

    grid_lat : ndarray

    grid_data : ndarray
    """

    # ------------------------------------------------------
    # Vetoriza as matrizes
    # ------------------------------------------------------

    lon = lon.ravel()

    lat = lat.ravel()

    data = data.ravel()

    # ------------------------------------------------------
    # Remove pixels inválidos
    # ------------------------------------------------------

    mask = (
        np.isfinite(lon) &
        np.isfinite(lat) &
        np.isfinite(data)
    )

    lon = lon[mask]

    lat = lat[mask]

    data = data[mask]

    # ------------------------------------------------------
    # Limites da área
    # ------------------------------------------------------

    xmin = lon.min()

    xmax = lon.max()

    ymin = lat.min()

    ymax = lat.max()

    # ------------------------------------------------------
    # Grade regular
    # ------------------------------------------------------

    grid_lon = np.arange(
        xmin,
        xmax + resolution,
        resolution
    )

    grid_lat = np.arange(
        ymax,
        ymin - resolution,
        -resolution
    )

    grid_lon, grid_lat = np.meshgrid(
        grid_lon,
        grid_lat
    )

    # ------------------------------------------------------
    # Interpolação
    # ------------------------------------------------------

    grid_data = griddata(
        (lon, lat),
        data,
        (grid_lon, grid_lat),
        method=method
    )

    return (
        grid_lon,
        grid_lat,
        grid_data
    )