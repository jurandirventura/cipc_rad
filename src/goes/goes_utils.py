"""
goes_utils.py

Funções auxiliares para leitura e processamento dos produtos
GOES-16 ABI L2 AOD.
"""

from pathlib import Path
import numpy as np

import xarray as xr


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

    dqf = var.values.astype(np.uint8)

    attrs = dict(var.attrs)

    return dqf, attrs

def apply_quality_mask(ds):
    pass

def replace_fill_values(data):
    pass

def crop_bbox(lon, lat, data, bbox):
    pass

def create_output_filename(input_file, output_dir):
    pass

def get_metadata(ds):
    pass

def list_goes_files(directory):

    directory = Path(directory)

    return sorted(
        directory.glob("*.nc")
    )