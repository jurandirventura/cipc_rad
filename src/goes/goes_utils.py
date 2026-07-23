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

        # info = parse_goes_filename(file.name)

        # print(file.name)
        # print(info["datetime"])
        # print(start_date)
        # print(end_date)        

        # # if start_date <= info["datetime"] <= end_date:
        # #     arquivos.append(file)

        # if start_date.date() <= info["start"].date() <= end_date.date():
        #     arquivos.append(file)            

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

# def parse_goes_filename(filename):
#     """
#     Extrai informações do nome do arquivo GOES.

#     Parameters
#     ----------
#     filename : str

#     Returns
#     -------
#     dict
#     """

#     # regex = re.compile(
#     #     r"OR_ABI-L2-(?P<product>[A-Z0-9]+)-.*?"
#     #     r"_(?P<satellite>G\d{2})"
#     #     r"_s(?P<year>\d{4})(?P<julian>\d{3})"
#     #     r"(?P<hour>\d{2})(?P<minute>\d{2})(?P<second>\d{2})"
#     # )

#     # regex = re.compile(
#     #     r"OR_ABI-L2-(?P<product>[A-Z0-9]+)-.*?"
#     #     r"_(?P<satellite>G\d{2})"
#     #     r"_s(?P<start>\d{13})"
#     #     r"_e(?P<end>\d{13})"
#     #     r"_c(?P<created>\d{13})"
#     # )    

#     regex = re.compile(
#         r"^OR_ABI-L2-"
#         r"(?P<product>[A-Z0-9]+)"
#         r"-M\d+_"
#         r"(?P<satellite>G\d{2})"
#         r"_s(?P<start>\d{13})"
#         r"_e(?P<end>\d{13})"
#         r"_c(?P<created>\d{13})"
#         r"\.nc$"
#     )

#     # m = regex.search(filename)

#     m = regex.match(filename)

#     if m is None:

#         raise ValueError(
#             f"Nome inválido:\n{filename}"
#         )

#     start = goes_time_to_datetime(
#         m.group("start")
#     )

#     end = goes_time_to_datetime(
#         m.group("end")
#     )

#     created = goes_time_to_datetime(
#         m.group("created")
#     )


#     return {

#         "product": m.group("product"),

#         "satellite": m.group("satellite"),

#         "start": start,

#         "end": end,

#         "created": created,

#         "year": start.year,

#         "julian": start.timetuple().tm_yday
#     }



