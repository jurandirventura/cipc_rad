
#!/usr/bin/env python3

"""
Sentinel-3A + Sentinel-3B SLSTR L2 AOD
    -> passagens
    -> overlay diário
    -> GeoTIFF
    -> COG
    -> tiles XYZ

Coleção EUMETSAT:
    EO:EUM:DAT:0416

Produtos:
    S3A_AOD
    S3B_AOD

O processamento combina os dados dos dois satélites
em um único overlay diário.

Exemplo:

python read_plot_s3b.py \
    20240815 \
    20240826 \
    AOD_550_Merged_OceanLand \
    "Sentinel-3 A+B AOD 550 nm" \
    "AOD 550" \
    png

DATA_FINAL é EXCLUSIVA.

Exemplo:
    20240815 -> 20240826

processa:
    15/08/2024
    ...
    25/08/2024
"""

import sys
import os
import re
import glob
import subprocess
import zipfile
import tempfile

from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

import xarray as xr
import numpy as np

import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

from cartopy.feature import NaturalEarthFeature
from matplotlib.colors import Normalize

from osgeo import gdal, osr

from src.processing.colormap_loader import load_colormap
from src.config.settings import OUTPUT_DIR


# ============================================================
# AMÉRICA DO SUL
# ============================================================

LON_MIN, LON_MAX = -86.17, -30.12
LAT_MIN, LAT_MAX = -59.01, 11.60


# ============================================================
# PARÂMETROS
# ============================================================

# Granules da mesma passagem são separados por ~5 min.
# Gap maior que este valor inicia nova passagem.
PASSAGE_GAP_MINUTES = 20

# Resolução do grid Level-3
GRID_RESOLUTION = 0.05


# ============================================================
# ARGUMENTOS
# ============================================================

if len(sys.argv) < 7:

    print()
    print("Uso:")
    print(
        "python read_plot_s3b.py "
        "DATA_INICIAL DATA_FINAL "
        "VAR_PRODUCT TITLE LABEL EXT"
    )

    print()

    print("DATA_FINAL é exclusiva.")

    print()

    print(
        "Exemplo:"
    )

    print(
        "python read_plot_s3b.py "
        "20240815 20240826 "
        "AOD_550_Merged_OceanLand "
        "'Sentinel-3 A+B AOD 550 nm' "
        "'AOD 550' png"
    )

    print()

    sys.exit(1)


DATE_START = datetime.strptime(
    sys.argv[1],
    "%Y%m%d"
).date()

DATE_END = datetime.strptime(
    sys.argv[2],
    "%Y%m%d"
).date()

VAR_PRODUCT = sys.argv[3]

TITLE = sys.argv[4]

LABEL = sys.argv[5]

EXT = sys.argv[6].lower().replace(".", "")


if DATE_END <= DATE_START:

    raise ValueError(
        "DATA_FINAL deve ser posterior à DATA_INICIAL."
    )


if EXT not in ("png", "jpg", "jpeg"):

    raise ValueError(
        "EXT deve ser png, jpg ou jpeg"
    )


# ============================================================
# DIRETÓRIO DOS DADOS
# ============================================================

L2_ROOT = Path(
    "/home/jurandir/cipc_data/L2"
)


# ============================================================
# SATÉLITES
# ============================================================

SATELLITE_DIRS = {
    "S3A": L2_ROOT / "S3A_AOD",
    "S3B": L2_ROOT / "S3B_AOD",
}

for satellite, satellite_root in SATELLITE_DIRS.items():
    if not satellite_root.exists():
        print(
            f"[WARN] Diretório {satellite} não existe: "
            f"{satellite_root}"
        )


# ============================================================
# LOCALIZAÇÃO DOS PRODUTOS
# ============================================================

FILES = []


current_date = DATE_START

while current_date < DATE_END:

    year = current_date.strftime("%Y")

    day = current_date.strftime("%Y%m%d")


    for satellite, satellite_root in SATELLITE_DIRS.items():

        day_dir = satellite_root / year


        # ----------------------------------------------------
        # Arquivos ZIP
        # ----------------------------------------------------

        pattern = (
            day_dir
            / f"{satellite}_SL_2_AOD____{day}*.SEN3.zip"
        )

        matches = glob.glob(
            str(pattern)
        )


        for filename in matches:

            FILES.append(
                (
                    satellite,
                    filename
                )
            )


        # ----------------------------------------------------
        # NRT_AOD.nc já extraídos
        # ----------------------------------------------------

        nc_matches = []

        if day_dir.exists():

            nc_matches = [
                filename
                for filename in day_dir.glob(
                    f"{satellite}_SL_2_AOD____{day}*/**/NRT_AOD.nc"
                )
                if filename.is_file()
            ]

            for filename in nc_matches:
                FILES.append(
                    (
                        satellite,
                        str(filename)
                    )
                )

        print(
            f"[INFO] {day} {satellite}: "
            f"{len(matches)} produto(s) .SEN3.zip encontrado(s)."
        )

        if nc_matches:
            print(
                f"[INFO] {day} {satellite}: "
                f"{len(nc_matches)} NRT_AOD.nc extraído(s) encontrado(s)."
            )


    current_date += timedelta(days=1)


# ============================================================
# REMOVER DUPLICIDADES
# ============================================================

FILES = sorted(
    set(FILES),
    key=lambda x: x[1]
)


if not FILES:

    raise SystemExit(
        f"Nenhum produto S3A/S3B encontrado entre "
        f"{DATE_START:%Y%m%d} e {DATE_END:%Y%m%d}."
    )


print()

print(
    f"[INFO] {len(FILES)} arquivo(s) encontrado(s)."
)


print()

for satellite in ("S3A", "S3B"):

    count = sum(
        1
        for sat, _ in FILES
        if sat == satellite
    )

    print(
        f"[INFO] {satellite}: {count} arquivo(s)"
    )


# ============================================================
# ABRIR NRT_AOD.nc DENTRO DO ZIP
# ============================================================

def abrir_netcdf_do_zip(zip_path):

    """
    Abre NRT_AOD.nc dentro do .SEN3.zip.

    O arquivo é extraído somente para um diretório
    temporário e removido ao final.
    """

    tmpdir = tempfile.TemporaryDirectory()

    try:

        with zipfile.ZipFile(
            zip_path,
            "r"
        ) as z:

            candidatos = [
                name
                for name in z.namelist()
                if (
                    name.endswith("/NRT_AOD.nc")
                    or name == "NRT_AOD.nc"
                )
            ]


            if not candidatos:

                raise FileNotFoundError(
                    f"NRT_AOD.nc não encontrado em {zip_path}"
                )


            nc_name = candidatos[0]

            nc_path = (
                Path(tmpdir.name)
                / "NRT_AOD.nc"
            )


            with z.open(nc_name) as src:

                with open(
                    nc_path,
                    "wb"
                ) as dst:

                    while True:

                        chunk = src.read(
                            1024 * 1024
                        )

                        if not chunk:
                            break

                        dst.write(chunk)


        ds = xr.open_dataset(
            nc_path,
            decode_cf=True,
            mask_and_scale=True
        )


        return ds, tmpdir


    except Exception:

        tmpdir.cleanup()

        raise


# ============================================================
# DATA/HORA DO PRODUTO
# ============================================================

def extract_datetime(filename):

    """
    Extrai YYYYMMDDThhmmss do nome do produto.
    """

    m = re.search(
        r"(\d{8})T(\d{6})",
        filename
    )


    if not m:

        return None


    return datetime.strptime(
        m.group(1) + m.group(2),
        "%Y%m%d%H%M%S"
    )


# ============================================================
# LEITURA DO DATASET
# ============================================================

def read_aod_dataset(ds):

    if VAR_PRODUCT not in ds.variables:

        aod_vars = [
            x
            for x in ds.variables
            if "AOD" in x.upper()
        ]


        raise KeyError(
            f"Variável '{VAR_PRODUCT}' não encontrada. "
            f"Variáveis AOD encontradas: {aod_vars}"
        )


    data = (
        ds[VAR_PRODUCT]
        .squeeze()
        .astype(np.float64)
        .values
    )


    lat = (
        ds["latitude"]
        .squeeze()
        .astype(np.float64)
        .values
    )


    lon = (
        ds["longitude"]
        .squeeze()
        .astype(np.float64)
        .values
    )


    if lat.ndim == 1 and lon.ndim == 1:

        lon, lat = np.meshgrid(
            lon,
            lat
        )


    if data.shape != lat.shape:

        lat = np.broadcast_to(
            lat,
            data.shape
        )

        lon = np.broadcast_to(
            lon,
            data.shape
        )


    data[~np.isfinite(data)] = np.nan

    data[data < 0] = np.nan


    valid = (

        np.isfinite(data)

        & np.isfinite(lat)

        & np.isfinite(lon)

        & (lat >= LAT_MIN)

        & (lat <= LAT_MAX)

        & (lon >= LON_MIN)

        & (lon <= LON_MAX)
    )


    return (
        lat[valid],
        lon[valid],
        data[valid]
    )


# ============================================================
# LER NRT_AOD.nc
# ============================================================

def read_aod_nc(filename):

    with xr.open_dataset(
        filename,
        decode_cf=True,
        mask_and_scale=True
    ) as ds:

        return read_aod_dataset(ds)


# ============================================================
# LER PRODUTO
# ============================================================

def read_aod(filename):

    filename = Path(filename)


    # --------------------------------------------------------
    # ZIP
    # --------------------------------------------------------

    if filename.name.endswith(".SEN3.zip"):

        ds, tmpdir = abrir_netcdf_do_zip(
            filename
        )


        try:

            return read_aod_dataset(ds)


        finally:

            ds.close()

            tmpdir.cleanup()


    # --------------------------------------------------------
    # NRT_AOD.nc
    # --------------------------------------------------------

    return read_aod_nc(
        filename
    )


# ============================================================
# GRID LEVEL-3
# ============================================================

def make_grid(
    lon,
    lat,
    values
):

    """
    Level-3 binning:
    média em células de 0.05°.
    """

    lon_bins = np.arange(
        LON_MIN,
        LON_MAX + GRID_RESOLUTION,
        GRID_RESOLUTION
    )


    lat_bins = np.arange(
        LAT_MIN,
        LAT_MAX + GRID_RESOLUTION,
        GRID_RESOLUTION
    )


    ix = np.digitize(
        lon,
        lon_bins
    ) - 1


    iy = np.digitize(
        lat,
        lat_bins
    ) - 1


    ok = (

        (ix >= 0)

        & (ix < len(lon_bins))

        & (iy >= 0)

        & (iy < len(lat_bins))

        & np.isfinite(values)
    )


    ix = ix[ok]

    iy = iy[ok]

    values = values[ok]


    total = np.zeros(
        (
            len(lat_bins),
            len(lon_bins)
        ),
        dtype=np.float64
    )


    count = np.zeros_like(
        total
    )


    np.add.at(
        total,
        (iy, ix),
        values
    )


    np.add.at(
        count,
        (iy, ix),
        1
    )


    grid = np.full(
        total.shape,
        np.nan,
        dtype=np.float32
    )


    np.divide(
        total,
        count,
        out=grid,
        where=count > 0
    )


    lon2d, lat2d = np.meshgrid(
        lon_bins,
        lat_bins
    )


    return (
        lon2d,
        lat2d,
        grid
    )


# ============================================================
# IDENTIFICAR PASSAGENS
# ============================================================

"""
IMPORTANTE:

As passagens são identificadas separadamente para S3A e S3B.

Não devemos juntar um granule S3A com um S3B apenas porque
os horários estão próximos.

Depois as passagens dos dois satélites serão combinadas
somente no overlay diário.
"""


dated_by_satellite = {
    "S3A": [],
    "S3B": []
}


for satellite, filename in FILES:

    dt = extract_datetime(
        filename
    )


    if dt is None:

        print(
            f"[WARN] Data/hora não encontrada: "
            f"{filename}"
        )

        continue


    dated_by_satellite[
        satellite
    ].append(
        (
            dt,
            filename
        )
    )


for satellite in dated_by_satellite:

    dated_by_satellite[
        satellite
    ].sort(
        key=lambda x: x[0]
    )


# ============================================================
# AGRUPAR PASSAGENS POR SATÉLITE
# ============================================================

passages_by_satellite = {
    "S3A": [],
    "S3B": []
}


for satellite in (
    "S3A",
    "S3B"
):

    dated = dated_by_satellite[
        satellite
    ]


    current = []


    for item in dated:

        if not current:

            current = [
                item
            ]

            continue


        gap = (
            item[0]
            - current[-1][0]
        ).total_seconds() / 60.0


        if gap <= PASSAGE_GAP_MINUTES:

            current.append(
                item
            )

        else:

            passages_by_satellite[
                satellite
            ].append(
                current
            )

            current = [
                item
            ]


    if current:

        passages_by_satellite[
            satellite
        ].append(
            current
        )


# ============================================================
# MOSTRAR PASSAGENS
# ============================================================

print()

print(
    "[INFO] Passagens identificadas:"
)


for satellite in (
    "S3A",
    "S3B"
):

    passages = passages_by_satellite[
        satellite
    ]


    print()

    print(
        f"  {satellite}: "
        f"{len(passages)} passagem(ns)"
    )


    for i, passage in enumerate(
        passages,
        1
    ):

        print(

            f"    {satellite} "
            f"Passagem {i:02d}: "

            f"{passage[0][0]:%Y-%m-%d %H:%M:%S}"

            f" -> "

            f"{passage[-1][0]:%H:%M:%S}"

            f" "
            f"({len(passage)} granules)"
        )


# ============================================================
# SAÍDAS
# ============================================================

figures_dir = (
    OUTPUT_DIR
    / "figures"
    / VAR_PRODUCT
)


geotiff_dir = (
    OUTPUT_DIR
    / "geotiff"
    / VAR_PRODUCT
)


cog_dir = (
    OUTPUT_DIR
    / "cog"
    / VAR_PRODUCT
)


tiles_dir = (
    OUTPUT_DIR
    / "tiles"
    / VAR_PRODUCT
)


for d in (
    figures_dir,
    geotiff_dir,
    cog_dir,
    tiles_dir
):

    d.mkdir(
        parents=True,
        exist_ok=True
    )


# ============================================================
# COLORMAP
# ============================================================

try:

    cmap, norm, vmin, vmax, ticks = (
        load_colormap(
            VAR_PRODUCT
        )
    )


except Exception:

    cmap = plt.cm.viridis

    norm = None

    vmin = None

    vmax = None

    ticks = None


# ============================================================
# AGRUPAR PASSAGENS POR DIA
# ============================================================

passages_by_day = defaultdict(
    list
)


for satellite in (
    "S3A",
    "S3B"
):

    for passage in passages_by_satellite[
        satellite
    ]:

        passage_day = (
            passage[0][0].date()
        )


        if (
            DATE_START
            <= passage_day
            < DATE_END
        ):

            passages_by_day[
                passage_day
            ].append(
                (
                    satellite,
                    passage
                )
            )


print()

print(
    "[INFO] Passagens por dia:"
)


for day in sorted(
    passages_by_day
):

    day_passages = (
        passages_by_day[day]
    )


    print()

    print(
        f"  {day:%Y-%m-%d}: "
        f"{len(day_passages)} passagem(ns)"
    )


    for satellite, passage in day_passages:

        print(

            f"      {satellite}: "
            f"{passage[0][0]:%H:%M:%S}"
            f" -> "
            f"{passage[-1][0]:%H:%M:%S}"
            f" "
            f"({len(passage)} granules)"
        )


# ============================================================
# PROCESSAR OVERLAY DIÁRIO
# ============================================================

for day in sorted(
    passages_by_day
):

    day_passages = (
        passages_by_day[day]
    )


    year = day.strftime(
        "%Y"
    )


    date = day.strftime(
        "%Y%m%d"
    )


    print()

    print(
        "=" * 70
    )

    print(
        f"OVERLAY DIÁRIO S3A + S3B: {date}"
    )

    print(
        f"Passagens: {len(day_passages)}"
    )

    print(
        "=" * 70
    )


    # --------------------------------------------------------
    # Pixels de todos os satélites/passagens
    # --------------------------------------------------------

    lats = []

    lons = []

    vals = []


    # Contadores individuais
    pixels_by_satellite = {
        "S3A": 0,
        "S3B": 0
    }


    for number, (
        satellite,
        passage
    ) in enumerate(
        day_passages,
        1
    ):

        start_dt = passage[0][0]

        end_dt = passage[-1][0]


        print()

        print(

            f"[PASSAGEM {number:02d}] "
            f"{satellite} "
            f"{start_dt:%H:%M:%S} "
            f"-> "
            f"{end_dt:%H:%M:%S} "
            f"({len(passage)} granules)"
        )


        for dt, filename in passage:

            print(
                f"[READ] "
                f"{satellite} "
                f"{dt:%H:%M:%S} "
                f"{Path(filename).name}"
            )


            try:

                lat, lon, value = (
                    read_aod(
                        filename
                    )
                )


            except Exception as e:

                print(
                    f"[ERRO] {e}"
                )

                continue


            if len(value):

                lats.append(
                    lat
                )

                lons.append(
                    lon
                )

                vals.append(
                    value
                )


                pixels_by_satellite[
                    satellite
                ] += len(value)


                print(

                    f"       pixels válidos: "
                    f"{len(value)}"
                )


            else:

                print(
                    "       pixels válidos: 0"
                )


    # --------------------------------------------------------
    # Nenhum dado
    # --------------------------------------------------------

    if not vals:

        print(
            f"[WARN] {date}: "
            f"nenhuma passagem possui dados válidos."
        )

        continue


    # --------------------------------------------------------
    # Juntar S3A + S3B
    # --------------------------------------------------------

    lat = np.concatenate(
        lats
    )


    lon = np.concatenate(
        lons
    )


    value = np.concatenate(
        vals
    )


    print()

    print(
        f"[INFO] {date}: "
        f"{len(value)} pixels válidos "
        f"antes do binning."
    )


    print(
        f"[INFO] {date}: "
        f"S3A = "
        f"{pixels_by_satellite['S3A']} pixels"
    )


    print(
        f"[INFO] {date}: "
        f"S3B = "
        f"{pixels_by_satellite['S3B']} pixels"
    )


    # --------------------------------------------------------
    # Level-3 binning
    # --------------------------------------------------------

    lon2d, lat2d, data = make_grid(
        lon,
        lat,
        value
    )


    if not np.any(
        np.isfinite(data)
    ):

        print(
            f"[WARN] {date}: grade vazia."
        )

        continue


    print(

        f"[INFO] {date}: "
        f"{np.count_nonzero(np.isfinite(data))} "
        f"células válidas no grid diário."
    )


    # --------------------------------------------------------
    # Normalização
    # --------------------------------------------------------

    local_norm = norm


    if local_norm is None:

        lo = np.nanpercentile(
            data,
            1
        )


        hi = np.nanpercentile(
            data,
            99
        )


        if lo == hi:

            hi = lo + 1


        local_norm = Normalize(
            lo,
            hi
        )


    # ========================================================
    # DIRETÓRIOS
    # ========================================================

    fig_dir = (
        figures_dir
        / year
    )


    tif_dir = (
        geotiff_dir
        / year
    )


    cog_year_dir = (
        cog_dir
        / year
    )


    tile_dir = (
        tiles_dir
        / year
        / date
        / "overlay"
    )


    for d in (
        fig_dir,
        tif_dir,
        cog_year_dir,
        tile_dir
    ):

        d.mkdir(
            parents=True,
            exist_ok=True
        )


    # --------------------------------------------------------
    # Nome
    # --------------------------------------------------------

    base_name = (
        f"s3ab_aod_{date}_overlay"
    )


    # ========================================================
    # FIGURA
    # ========================================================

    fig = plt.figure(
        figsize=(12, 8)
    )


    ax = plt.axes(
        projection=ccrs.PlateCarree()
    )


    ax.set_extent(
        [
            LON_MIN,
            LON_MAX,
            LAT_MIN,
            LAT_MAX
        ],
        crs=ccrs.PlateCarree()
    )


    mesh = ax.pcolormesh(

        lon2d,
        lat2d,
        data,

        cmap=cmap,
        norm=local_norm,

        shading="auto",

        transform=ccrs.PlateCarree()
    )


    cbar = plt.colorbar(
        mesh,
        ax=ax,
        pad=0.02
    )


    cbar.set_label(
        LABEL
    )


    if ticks is not None:

        cbar.set_ticks(
            ticks
        )


    ax.coastlines(
        resolution="10m"
    )


    ax.add_feature(
        cfeature.BORDERS,
        linewidth=0.6
    )


    ax.add_feature(
        cfeature.LAND,
        facecolor="lightgray"
    )


    states = NaturalEarthFeature(

        category="cultural",

        name="admin_1_states_provinces_lines",

        scale="10m",

        facecolor="none"
    )


    ax.add_feature(
        states,
        edgecolor="black",
        linewidth=0.4
    )


    ax.set_title(

        f"{TITLE} - "
        f"{day:%Y-%m-%d} UTC - "
        f"Overlay S3A + S3B"
    )


    fig_path = (
        fig_dir
        / f"{base_name}.{EXT}"
    )


    plt.savefig(
        fig_path,
        dpi=300,
        bbox_inches="tight"
    )


    plt.close(
        fig
    )


    print(
        f"[OK] Figura: {fig_path}"
    )


    # ========================================================
    # GEOTIFF
    # ========================================================

    tif_path = (
        tif_dir
        / f"{base_name}.tif"
    )


    nrows, ncols = (
        data.shape
    )


    xres = (
        LON_MAX - LON_MIN
    ) / (
        ncols - 1
    )


    yres = (
        LAT_MAX - LAT_MIN
    ) / (
        nrows - 1
    )


    driver = gdal.GetDriverByName(
        "GTiff"
    )


    ds = driver.Create(

        str(tif_path),

        ncols,
        nrows,

        1,

        gdal.GDT_Float32
    )


    ds.SetGeoTransform(
        (
            LON_MIN,
            xres,
            0,
            LAT_MAX,
            0,
            -yres
        )
    )


    srs = osr.SpatialReference()

    srs.ImportFromEPSG(
        4326
    )


    ds.SetProjection(
        srs.ExportToWkt()
    )


    band = (
        ds.GetRasterBand(1)
    )


    out = np.flipud(
        data
    ).astype(
        np.float32
    )


    out[
        ~np.isfinite(out)
    ] = -9999


    band.WriteArray(
        out
    )


    band.SetNoDataValue(
        -9999
    )


    band.SetDescription(
        "Sentinel-3A + Sentinel-3B "
        "SLSTR AOD 550 nm - daily overlay"
    )


    ds.FlushCache()

    ds = None


    print(
        f"[OK] GeoTIFF: {tif_path}"
    )


    # ========================================================
    # COG
    # ========================================================

    cog_path = (
        cog_year_dir
        / f"{base_name}_cog.tif"
    )


    gdal.Translate(

        str(cog_path),

        str(tif_path),

        format="COG",

        creationOptions=[
            "COMPRESS=DEFLATE",
            "LEVEL=9"
        ]
    )


    print(
        f"[OK] COG: {cog_path}"
    )


    # ========================================================
    # TILES XYZ
    # ========================================================

    vrt_path = (
        cog_year_dir
        / f"{base_name}_tiles.vrt"
    )


    subprocess.run(

        [
            "gdal_translate",

            "-of",
            "VRT",

            "-ot",
            "Byte",

            "-scale",

            "-a_nodata",
            "0",

            str(cog_path),

            str(vrt_path)
        ],

        check=True
    )


    subprocess.run(

        [
            "gdal2tiles.py",

            "--processes=4",

            "-z",
            "0-6",

            "-w",
            "none",

            str(vrt_path),

            str(tile_dir)
        ],

        check=True
    )


    print(
        f"[OK] Tiles: {tile_dir}"
    )


# ============================================================
# FIM
# ============================================================

print()

print(
    "[OK] Processamento Sentinel-3A + "
    "Sentinel-3B concluído."
)



### COM ERRO.....###
# #!/usr/bin/env python3

# """
# Sentinel-3A + Sentinel-3B SLSTR L2 AOD
#     -> passagens
#     -> overlay diário
#     -> GeoTIFF
#     -> COG
#     -> tiles XYZ

# Coleção EUMETSAT:
#     EO:EUM:DAT:0416

# Produtos:
#     S3A_AOD
#     S3B_AOD

# O processamento combina os dados dos dois satélites
# em um único overlay diário.

# Exemplo:

# python read_plot_s3b.py \
#     20240815 \
#     20240826 \
#     AOD_550_Merged_OceanLand \
#     "Sentinel-3 A+B AOD 550 nm" \
#     "AOD 550" \
#     png

# DATA_FINAL é EXCLUSIVA.

# Exemplo:
#     20240815 -> 20240826

# processa:
#     15/08/2024
#     ...
#     25/08/2024
# """

# import sys
# import os
# import re
# import glob
# import subprocess
# import zipfile
# import tempfile

# from pathlib import Path
# from datetime import datetime, timedelta
# from collections import defaultdict

# import xarray as xr
# import numpy as np

# import matplotlib.pyplot as plt
# import cartopy.crs as ccrs
# import cartopy.feature as cfeature

# from cartopy.feature import NaturalEarthFeature
# from matplotlib.colors import Normalize

# from osgeo import gdal, osr

# from src.processing.colormap_loader import load_colormap
# from src.config.settings import OUTPUT_DIR


# # ============================================================
# # AMÉRICA DO SUL
# # ============================================================

# LON_MIN, LON_MAX = -86.17, -30.12
# LAT_MIN, LAT_MAX = -59.01, 11.60


# # ============================================================
# # PARÂMETROS
# # ============================================================

# # Granules da mesma passagem são separados por ~5 min.
# # Gap maior que este valor inicia nova passagem.
# PASSAGE_GAP_MINUTES = 20

# # Resolução do grid Level-3
# GRID_RESOLUTION = 0.05


# # ============================================================
# # ARGUMENTOS
# # ============================================================

# if len(sys.argv) < 7:

#     print()
#     print("Uso:")
#     print(
#         "python read_plot_s3b.py "
#         "DATA_INICIAL DATA_FINAL "
#         "VAR_PRODUCT TITLE LABEL EXT"
#     )

#     print()

#     print("DATA_FINAL é exclusiva.")

#     print()

#     print(
#         "Exemplo:"
#     )

#     print(
#         "python read_plot_s3b.py "
#         "20240815 20240826 "
#         "AOD_550_Merged_OceanLand "
#         "'Sentinel-3 A+B AOD 550 nm' "
#         "'AOD 550' png"
#     )

#     print()

#     sys.exit(1)


# DATE_START = datetime.strptime(
#     sys.argv[1],
#     "%Y%m%d"
# ).date()

# DATE_END = datetime.strptime(
#     sys.argv[2],
#     "%Y%m%d"
# ).date()

# VAR_PRODUCT = sys.argv[3]

# TITLE = sys.argv[4]

# LABEL = sys.argv[5]

# EXT = sys.argv[6].lower().replace(".", "")


# if DATE_END <= DATE_START:

#     raise ValueError(
#         "DATA_FINAL deve ser posterior à DATA_INICIAL."
#     )


# if EXT not in ("png", "jpg", "jpeg"):

#     raise ValueError(
#         "EXT deve ser png, jpg ou jpeg"
#     )


# # ============================================================
# # DIRETÓRIO DOS DADOS
# # ============================================================

# L2_ROOT = Path(
#     "/home/jurandir/cipc_data/L2"
# )


# # ============================================================
# # SATÉLITES
# # ============================================================

# SATELLITE_DIRS = {
#     "S3A": L2_ROOT / "S3A_AOD",
#     "S3B": L2_ROOT / "S3B_AOD",
# }


# # ============================================================
# # LOCALIZAÇÃO DOS PRODUTOS
# # ============================================================

# FILES = []


# current_date = DATE_START

# while current_date < DATE_END:

#     year = current_date.strftime("%Y")

#     day = current_date.strftime("%Y%m%d")


#     for satellite, satellite_root in SATELLITE_DIRS.items():

#         day_dir = satellite_root / year


#         # ----------------------------------------------------
#         # Arquivos ZIP
#         # ----------------------------------------------------

#         pattern = (
#             day_dir
#             / f"S{satellite[-1]}_SL_2_AOD____{day}*.SEN3.zip"
#         )

#         matches = glob.glob(
#             str(pattern)
#         )


#         for filename in matches:

#             FILES.append(
#                 (
#                     satellite,
#                     filename
#                 )
#             )


#         # ----------------------------------------------------
#         # NRT_AOD.nc já extraídos
#         # ----------------------------------------------------

#         if day_dir.exists():

#             for filename in day_dir.glob(
#                 f"S{satellite[-1]}_SL_2_AOD____{day}*/**/NRT_AOD.nc"
#             ):

#                 if filename.is_file():

#                     FILES.append(
#                         (
#                             satellite,
#                             str(filename)
#                         )
#                     )


#         print(
#             f"[INFO] {day} "
#             f"{satellite}: "
#             f"{len(matches)} produto(s) .SEN3.zip encontrado(s)."
#         )


#     current_date += timedelta(days=1)


# # ============================================================
# # REMOVER DUPLICIDADES
# # ============================================================

# FILES = sorted(
#     set(FILES),
#     key=lambda x: x[1]
# )


# if not FILES:

#     raise SystemExit(
#         f"Nenhum produto S3A/S3B encontrado entre "
#         f"{DATE_START:%Y%m%d} e {DATE_END:%Y%m%d}."
#     )


# print()

# print(
#     f"[INFO] {len(FILES)} arquivo(s) encontrado(s)."
# )


# print()

# for satellite in ("S3A", "S3B"):

#     count = sum(
#         1
#         for sat, _ in FILES
#         if sat == satellite
#     )

#     print(
#         f"[INFO] {satellite}: {count} arquivo(s)"
#     )


# # ============================================================
# # ABRIR NRT_AOD.nc DENTRO DO ZIP
# # ============================================================

# def abrir_netcdf_do_zip(zip_path):

#     """
#     Abre NRT_AOD.nc dentro do .SEN3.zip.

#     O arquivo é extraído somente para um diretório
#     temporário e removido ao final.
#     """

#     tmpdir = tempfile.TemporaryDirectory()

#     try:

#         with zipfile.ZipFile(
#             zip_path,
#             "r"
#         ) as z:

#             candidatos = [
#                 name
#                 for name in z.namelist()
#                 if (
#                     name.endswith("/NRT_AOD.nc")
#                     or name == "NRT_AOD.nc"
#                 )
#             ]


#             if not candidatos:

#                 raise FileNotFoundError(
#                     f"NRT_AOD.nc não encontrado em {zip_path}"
#                 )


#             nc_name = candidatos[0]

#             nc_path = (
#                 Path(tmpdir.name)
#                 / "NRT_AOD.nc"
#             )


#             with z.open(nc_name) as src:

#                 with open(
#                     nc_path,
#                     "wb"
#                 ) as dst:

#                     while True:

#                         chunk = src.read(
#                             1024 * 1024
#                         )

#                         if not chunk:
#                             break

#                         dst.write(chunk)


#         ds = xr.open_dataset(
#             nc_path,
#             decode_cf=True,
#             mask_and_scale=True
#         )


#         return ds, tmpdir


#     except Exception:

#         tmpdir.cleanup()

#         raise


# # ============================================================
# # DATA/HORA DO PRODUTO
# # ============================================================

# def extract_datetime(filename):

#     """
#     Extrai YYYYMMDDThhmmss do nome do produto.
#     """

#     m = re.search(
#         r"(\d{8})T(\d{6})",
#         filename
#     )


#     if not m:

#         return None


#     return datetime.strptime(
#         m.group(1) + m.group(2),
#         "%Y%m%d%H%M%S"
#     )


# # ============================================================
# # LEITURA DO DATASET
# # ============================================================

# def read_aod_dataset(ds):

#     if VAR_PRODUCT not in ds.variables:

#         aod_vars = [
#             x
#             for x in ds.variables
#             if "AOD" in x.upper()
#         ]


#         raise KeyError(
#             f"Variável '{VAR_PRODUCT}' não encontrada. "
#             f"Variáveis AOD encontradas: {aod_vars}"
#         )


#     data = (
#         ds[VAR_PRODUCT]
#         .squeeze()
#         .astype(np.float64)
#         .values
#     )


#     lat = (
#         ds["latitude"]
#         .squeeze()
#         .astype(np.float64)
#         .values
#     )


#     lon = (
#         ds["longitude"]
#         .squeeze()
#         .astype(np.float64)
#         .values
#     )


#     if lat.ndim == 1 and lon.ndim == 1:

#         lon, lat = np.meshgrid(
#             lon,
#             lat
#         )


#     if data.shape != lat.shape:

#         lat = np.broadcast_to(
#             lat,
#             data.shape
#         )

#         lon = np.broadcast_to(
#             lon,
#             data.shape
#         )


#     data[~np.isfinite(data)] = np.nan

#     data[data < 0] = np.nan


#     valid = (

#         np.isfinite(data)

#         & np.isfinite(lat)

#         & np.isfinite(lon)

#         & (lat >= LAT_MIN)

#         & (lat <= LAT_MAX)

#         & (lon >= LON_MIN)

#         & (lon <= LON_MAX)
#     )


#     return (
#         lat[valid],
#         lon[valid],
#         data[valid]
#     )


# # ============================================================
# # LER NRT_AOD.nc
# # ============================================================

# def read_aod_nc(filename):

#     with xr.open_dataset(
#         filename,
#         decode_cf=True,
#         mask_and_scale=True
#     ) as ds:

#         return read_aod_dataset(ds)


# # ============================================================
# # LER PRODUTO
# # ============================================================

# def read_aod(filename):

#     filename = Path(filename)


#     # --------------------------------------------------------
#     # ZIP
#     # --------------------------------------------------------

#     if filename.name.endswith(".SEN3.zip"):

#         ds, tmpdir = abrir_netcdf_do_zip(
#             filename
#         )


#         try:

#             return read_aod_dataset(ds)


#         finally:

#             ds.close()

#             tmpdir.cleanup()


#     # --------------------------------------------------------
#     # NRT_AOD.nc
#     # --------------------------------------------------------

#     return read_aod_nc(
#         filename
#     )


# # ============================================================
# # GRID LEVEL-3
# # ============================================================

# def make_grid(
#     lon,
#     lat,
#     values
# ):

#     """
#     Level-3 binning:
#     média em células de 0.05°.
#     """

#     lon_bins = np.arange(
#         LON_MIN,
#         LON_MAX + GRID_RESOLUTION,
#         GRID_RESOLUTION
#     )


#     lat_bins = np.arange(
#         LAT_MIN,
#         LAT_MAX + GRID_RESOLUTION,
#         GRID_RESOLUTION
#     )


#     ix = np.digitize(
#         lon,
#         lon_bins
#     ) - 1


#     iy = np.digitize(
#         lat,
#         lat_bins
#     ) - 1


#     ok = (

#         (ix >= 0)

#         & (ix < len(lon_bins))

#         & (iy >= 0)

#         & (iy < len(lat_bins))

#         & np.isfinite(values)
#     )


#     ix = ix[ok]

#     iy = iy[ok]

#     values = values[ok]


#     total = np.zeros(
#         (
#             len(lat_bins),
#             len(lon_bins)
#         ),
#         dtype=np.float64
#     )


#     count = np.zeros_like(
#         total
#     )


#     np.add.at(
#         total,
#         (iy, ix),
#         values
#     )


#     np.add.at(
#         count,
#         (iy, ix),
#         1
#     )


#     grid = np.full(
#         total.shape,
#         np.nan,
#         dtype=np.float32
#     )


#     np.divide(
#         total,
#         count,
#         out=grid,
#         where=count > 0
#     )


#     lon2d, lat2d = np.meshgrid(
#         lon_bins,
#         lat_bins
#     )


#     return (
#         lon2d,
#         lat2d,
#         grid
#     )


# # ============================================================
# # IDENTIFICAR PASSAGENS
# # ============================================================

# """
# IMPORTANTE:

# As passagens são identificadas separadamente para S3A e S3B.

# Não devemos juntar um granule S3A com um S3B apenas porque
# os horários estão próximos.

# Depois as passagens dos dois satélites serão combinadas
# somente no overlay diário.
# """


# dated_by_satellite = {
#     "S3A": [],
#     "S3B": []
# }


# for satellite, filename in FILES:

#     dt = extract_datetime(
#         filename
#     )


#     if dt is None:

#         print(
#             f"[WARN] Data/hora não encontrada: "
#             f"{filename}"
#         )

#         continue


#     dated_by_satellite[
#         satellite
#     ].append(
#         (
#             dt,
#             filename
#         )
#     )


# for satellite in dated_by_satellite:

#     dated_by_satellite[
#         satellite
#     ].sort(
#         key=lambda x: x[0]
#     )


# # ============================================================
# # AGRUPAR PASSAGENS POR SATÉLITE
# # ============================================================

# passages_by_satellite = {
#     "S3A": [],
#     "S3B": []
# }


# for satellite in (
#     "S3A",
#     "S3B"
# ):

#     dated = dated_by_satellite[
#         satellite
#     ]


#     current = []


#     for item in dated:

#         if not current:

#             current = [
#                 item
#             ]

#             continue


#         gap = (
#             item[0]
#             - current[-1][0]
#         ).total_seconds() / 60.0


#         if gap <= PASSAGE_GAP_MINUTES:

#             current.append(
#                 item
#             )

#         else:

#             passages_by_satellite[
#                 satellite
#             ].append(
#                 current
#             )

#             current = [
#                 item
#             ]


#     if current:

#         passages_by_satellite[
#             satellite
#         ].append(
#             current
#         )


# # ============================================================
# # MOSTRAR PASSAGENS
# # ============================================================

# print()

# print(
#     "[INFO] Passagens identificadas:"
# )


# for satellite in (
#     "S3A",
#     "S3B"
# ):

#     passages = passages_by_satellite[
#         satellite
#     ]


#     print()

#     print(
#         f"  {satellite}: "
#         f"{len(passages)} passagem(ns)"
#     )


#     for i, passage in enumerate(
#         passages,
#         1
#     ):

#         print(

#             f"    {satellite} "
#             f"Passagem {i:02d}: "

#             f"{passage[0][0]:%Y-%m-%d %H:%M:%S}"

#             f" -> "

#             f"{passage[-1][0]:%H:%M:%S}"

#             f" "
#             f"({len(passage)} granules)"
#         )


# # ============================================================
# # SAÍDAS
# # ============================================================

# figures_dir = (
#     OUTPUT_DIR
#     / "figures"
#     / VAR_PRODUCT
# )


# geotiff_dir = (
#     OUTPUT_DIR
#     / "geotiff"
#     / VAR_PRODUCT
# )


# cog_dir = (
#     OUTPUT_DIR
#     / "cog"
#     / VAR_PRODUCT
# )


# tiles_dir = (
#     OUTPUT_DIR
#     / "tiles"
#     / VAR_PRODUCT
# )


# for d in (
#     figures_dir,
#     geotiff_dir,
#     cog_dir,
#     tiles_dir
# ):

#     d.mkdir(
#         parents=True,
#         exist_ok=True
#     )


# # ============================================================
# # COLORMAP
# # ============================================================

# try:

#     cmap, norm, vmin, vmax, ticks = (
#         load_colormap(
#             VAR_PRODUCT
#         )
#     )


# except Exception:

#     cmap = plt.cm.viridis

#     norm = None

#     vmin = None

#     vmax = None

#     ticks = None


# # ============================================================
# # AGRUPAR PASSAGENS POR DIA
# # ============================================================

# passages_by_day = defaultdict(
#     list
# )


# for satellite in (
#     "S3A",
#     "S3B"
# ):

#     for passage in passages_by_satellite[
#         satellite
#     ]:

#         passage_day = (
#             passage[0][0].date()
#         )


#         if (
#             DATE_START
#             <= passage_day
#             < DATE_END
#         ):

#             passages_by_day[
#                 passage_day
#             ].append(
#                 (
#                     satellite,
#                     passage
#                 )
#             )


# print()

# print(
#     "[INFO] Passagens por dia:"
# )


# for day in sorted(
#     passages_by_day
# ):

#     day_passages = (
#         passages_by_day[day]
#     )


#     print()

#     print(
#         f"  {day:%Y-%m-%d}: "
#         f"{len(day_passages)} passagem(ns)"
#     )


#     for satellite, passage in day_passages:

#         print(

#             f"      {satellite}: "
#             f"{passage[0][0]:%H:%M:%S}"
#             f" -> "
#             f"{passage[-1][0]:%H:%M:%S}"
#             f" "
#             f"({len(passage)} granules)"
#         )


# # ============================================================
# # PROCESSAR OVERLAY DIÁRIO
# # ============================================================

# for day in sorted(
#     passages_by_day
# ):

#     day_passages = (
#         passages_by_day[day]
#     )


#     year = day.strftime(
#         "%Y"
#     )


#     date = day.strftime(
#         "%Y%m%d"
#     )


#     print()

#     print(
#         "=" * 70
#     )

#     print(
#         f"OVERLAY DIÁRIO S3A + S3B: {date}"
#     )

#     print(
#         f"Passagens: {len(day_passages)}"
#     )

#     print(
#         "=" * 70
#     )


#     # --------------------------------------------------------
#     # Pixels de todos os satélites/passagens
#     # --------------------------------------------------------

#     lats = []

#     lons = []

#     vals = []


#     # Contadores individuais
#     pixels_by_satellite = {
#         "S3A": 0,
#         "S3B": 0
#     }


#     for number, (
#         satellite,
#         passage
#     ) in enumerate(
#         day_passages,
#         1
#     ):

#         start_dt = passage[0][0]

#         end_dt = passage[-1][0]


#         print()

#         print(

#             f"[PASSAGEM {number:02d}] "
#             f"{satellite} "
#             f"{start_dt:%H:%M:%S} "
#             f"-> "
#             f"{end_dt:%H:%M:%S} "
#             f"({len(passage)} granules)"
#         )


#         for dt, filename in passage:

#             print(
#                 f"[READ] "
#                 f"{satellite} "
#                 f"{dt:%H:%M:%S} "
#                 f"{Path(filename).name}"
#             )


#             try:

#                 lat, lon, value = (
#                     read_aod(
#                         filename
#                     )
#                 )


#             except Exception as e:

#                 print(
#                     f"[ERRO] {e}"
#                 )

#                 continue


#             if len(value):

#                 lats.append(
#                     lat
#                 )

#                 lons.append(
#                     lon
#                 )

#                 vals.append(
#                     value
#                 )


#                 pixels_by_satellite[
#                     satellite
#                 ] += len(value)


#                 print(

#                     f"       pixels válidos: "
#                     f"{len(value)}"
#                 )


#             else:

#                 print(
#                     "       pixels válidos: 0"
#                 )


#     # --------------------------------------------------------
#     # Nenhum dado
#     # --------------------------------------------------------

#     if not vals:

#         print(
#             f"[WARN] {date}: "
#             f"nenhuma passagem possui dados válidos."
#         )

#         continue


#     # --------------------------------------------------------
#     # Juntar S3A + S3B
#     # --------------------------------------------------------

#     lat = np.concatenate(
#         lats
#     )


#     lon = np.concatenate(
#         lons
#     )


#     value = np.concatenate(
#         vals
#     )


#     print()

#     print(
#         f"[INFO] {date}: "
#         f"{len(value)} pixels válidos "
#         f"antes do binning."
#     )


#     print(
#         f"[INFO] {date}: "
#         f"S3A = "
#         f"{pixels_by_satellite['S3A']} pixels"
#     )


#     print(
#         f"[INFO] {date}: "
#         f"S3B = "
#         f"{pixels_by_satellite['S3B']} pixels"
#     )


#     # --------------------------------------------------------
#     # Level-3 binning
#     # --------------------------------------------------------

#     lon2d, lat2d, data = make_grid(
#         lon,
#         lat,
#         value
#     )


#     if not np.any(
#         np.isfinite(data)
#     ):

#         print(
#             f"[WARN] {date}: grade vazia."
#         )

#         continue


#     print(

#         f"[INFO] {date}: "
#         f"{np.count_nonzero(np.isfinite(data))} "
#         f"células válidas no grid diário."
#     )


#     # --------------------------------------------------------
#     # Normalização
#     # --------------------------------------------------------

#     local_norm = norm


#     if local_norm is None:

#         lo = np.nanpercentile(
#             data,
#             1
#         )


#         hi = np.nanpercentile(
#             data,
#             99
#         )


#         if lo == hi:

#             hi = lo + 1


#         local_norm = Normalize(
#             lo,
#             hi
#         )


#     # ========================================================
#     # DIRETÓRIOS
#     # ========================================================

#     fig_dir = (
#         figures_dir
#         / year
#     )


#     tif_dir = (
#         geotiff_dir
#         / year
#     )


#     cog_year_dir = (
#         cog_dir
#         / year
#     )


#     tile_dir = (
#         tiles_dir
#         / year
#         / date
#         / "overlay"
#     )


#     for d in (
#         fig_dir,
#         tif_dir,
#         cog_year_dir,
#         tile_dir
#     ):

#         d.mkdir(
#             parents=True,
#             exist_ok=True
#         )


#     # --------------------------------------------------------
#     # Nome
#     # --------------------------------------------------------

#     base_name = (
#         f"s3ab_aod_{date}_overlay"
#     )


#     # ========================================================
#     # FIGURA
#     # ========================================================

#     fig = plt.figure(
#         figsize=(12, 8)
#     )


#     ax = plt.axes(
#         projection=ccrs.PlateCarree()
#     )


#     ax.set_extent(
#         [
#             LON_MIN,
#             LON_MAX,
#             LAT_MIN,
#             LAT_MAX
#         ],
#         crs=ccrs.PlateCarree()
#     )


#     mesh = ax.pcolormesh(

#         lon2d,
#         lat2d,
#         data,

#         cmap=cmap,
#         norm=local_norm,

#         shading="auto",

#         transform=ccrs.PlateCarree()
#     )


#     cbar = plt.colorbar(
#         mesh,
#         ax=ax,
#         pad=0.02
#     )


#     cbar.set_label(
#         LABEL
#     )


#     if ticks is not None:

#         cbar.set_ticks(
#             ticks
#         )


#     ax.coastlines(
#         resolution="10m"
#     )


#     ax.add_feature(
#         cfeature.BORDERS,
#         linewidth=0.6
#     )


#     ax.add_feature(
#         cfeature.LAND,
#         facecolor="lightgray"
#     )


#     states = NaturalEarthFeature(

#         category="cultural",

#         name="admin_1_states_provinces_lines",

#         scale="10m",

#         facecolor="none"
#     )


#     ax.add_feature(
#         states,
#         edgecolor="black",
#         linewidth=0.4
#     )


#     ax.set_title(

#         f"{TITLE} - "
#         f"{day:%Y-%m-%d} UTC - "
#         f"Overlay S3A + S3B"
#     )


#     fig_path = (
#         fig_dir
#         / f"{base_name}.{EXT}"
#     )


#     plt.savefig(
#         fig_path,
#         dpi=300,
#         bbox_inches="tight"
#     )


#     plt.close(
#         fig
#     )


#     print(
#         f"[OK] Figura: {fig_path}"
#     )


#     # ========================================================
#     # GEOTIFF
#     # ========================================================

#     tif_path = (
#         tif_dir
#         / f"{base_name}.tif"
#     )


#     nrows, ncols = (
#         data.shape
#     )


#     xres = (
#         LON_MAX - LON_MIN
#     ) / (
#         ncols - 1
#     )


#     yres = (
#         LAT_MAX - LAT_MIN
#     ) / (
#         nrows - 1
#     )


#     driver = gdal.GetDriverByName(
#         "GTiff"
#     )


#     ds = driver.Create(

#         str(tif_path),

#         ncols,
#         nrows,

#         1,

#         gdal.GDT_Float32
#     )


#     ds.SetGeoTransform(
#         (
#             LON_MIN,
#             xres,
#             0,
#             LAT_MAX,
#             0,
#             -yres
#         )
#     )


#     srs = osr.SpatialReference()

#     srs.ImportFromEPSG(
#         4326
#     )


#     ds.SetProjection(
#         srs.ExportToWkt()
#     )


#     band = (
#         ds.GetRasterBand(1)
#     )


#     out = np.flipud(
#         data
#     ).astype(
#         np.float32
#     )


#     out[
#         ~np.isfinite(out)
#     ] = -9999


#     band.WriteArray(
#         out
#     )


#     band.SetNoDataValue(
#         -9999
#     )


#     band.SetDescription(
#         "Sentinel-3A + Sentinel-3B "
#         "SLSTR AOD 550 nm - daily overlay"
#     )


#     ds.FlushCache()

#     ds = None


#     print(
#         f"[OK] GeoTIFF: {tif_path}"
#     )


#     # ========================================================
#     # COG
#     # ========================================================

#     cog_path = (
#         cog_year_dir
#         / f"{base_name}_cog.tif"
#     )


#     gdal.Translate(

#         str(cog_path),

#         str(tif_path),

#         format="COG",

#         creationOptions=[
#             "COMPRESS=DEFLATE",
#             "LEVEL=9"
#         ]
#     )


#     print(
#         f"[OK] COG: {cog_path}"
#     )


#     # ========================================================
#     # TILES XYZ
#     # ========================================================

#     vrt_path = (
#         cog_year_dir
#         / f"{base_name}_tiles.vrt"
#     )


#     subprocess.run(

#         [
#             "gdal_translate",

#             "-of",
#             "VRT",

#             "-ot",
#             "Byte",

#             "-scale",

#             "-a_nodata",
#             "0",

#             str(cog_path),

#             str(vrt_path)
#         ],

#         check=True
#     )


#     subprocess.run(

#         [
#             "gdal2tiles.py",

#             "--processes=4",

#             "-z",
#             "0-6",

#             "-w",
#             "none",

#             str(vrt_path),

#             str(tile_dir)
#         ],

#         check=True
#     )


#     print(
#         f"[OK] Tiles: {tile_dir}"
#     )


# # ============================================================
# # FIM
# # ============================================================

# print()

# print(
#     "[OK] Processamento Sentinel-3A + "
#     "Sentinel-3B concluído."
# )






### SENTINEL 3B MAS NÃO CONSIDERA O 3A

# #!/usr/bin/env python3
# # Sentinel-3B SLSTR L2 AOD -> passagem -> GeoTIFF/COG/tiles
# #
# # Adaptação da rotina read_plot_S5p.py.
# #
# # Exemplo:
# # python read_plot_s3b.py "/home/jurandir/cipc_data/L2/2024/S3B_SL_2_AOD____20240816*/**/NRT_AOD.nc" AOD_550_Merged_OceanLand "Sentinel-3B AOD 550 nm" "AOD 550" png

# import sys, os, re, glob, subprocess
# from pathlib import Path
# from datetime import datetime, timedelta
# from collections import defaultdict
# import xarray as xr
# import numpy as np
# import matplotlib.pyplot as plt
# import cartopy.crs as ccrs
# import cartopy.feature as cfeature
# from cartopy.feature import NaturalEarthFeature
# from matplotlib.colors import Normalize
# from osgeo import gdal, osr

# import zipfile
# import tempfile

# from src.processing.colormap_loader import load_colormap
# from src.config.settings import OUTPUT_DIR

# # América do Sul
# LON_MIN, LON_MAX = -86.17, -30.12
# LAT_MIN, LAT_MAX = -59.01, 11.60

# # Granules da mesma passagem são separados por ~5 min.
# # Gap maior que este valor inicia nova passagem.
# PASSAGE_GAP_MINUTES = 20
# GRID_RESOLUTION = 0.05


# if len(sys.argv) < 7:
#     print("Uso:")
#     print(
#         "python read_plot_s3b.py DATA_INICIAL DATA_FINAL "
#         "VAR_PRODUCT TITLE LABEL EXT"
#     )
#     print()
#     print("DATA_FINAL é exclusiva.")
#     print("Exemplo: processar 15/08/2024 até 25/08/2024 = 10 dias")
#     print()
#     print(
#         "python read_plot_s3b.py 20240815 20240825 "
#         "AOD_550_Merged_OceanLand "
#         "'Sentinel-3B AOD 550 nm' 'AOD 550' png"
#     )
#     sys.exit(1)

# DATE_START = datetime.strptime(sys.argv[1], "%Y%m%d").date()
# DATE_END = datetime.strptime(sys.argv[2], "%Y%m%d").date()
# VAR_PRODUCT = sys.argv[3]
# TITLE = sys.argv[4]
# LABEL = sys.argv[5]
# EXT = sys.argv[6].lower().replace(".", "")

# if DATE_END <= DATE_START:
#     raise ValueError("DATA_FINAL deve ser posterior à DATA_INICIAL.")

# if EXT not in ("png", "jpg", "jpeg"):
#     raise ValueError("EXT deve ser png, jpg ou jpeg")

# # Diretório padrão dos produtos Sentinel-3B.
# L2_ROOT = Path("/home/jurandir/cipc_data/L2")


# # ------------------------------------------------------------
# # Localizar produtos S3B dentro do período solicitado
# # DATA_START inclusiva / DATA_END exclusiva
# # Localizar NRT_AOD.nc dentro do arquivo zip
# # ------------------------------------------------------------
# FILES = []

# current_date = DATE_START
# while current_date < DATE_END:
#     year = current_date.strftime("%Y")
#     day = current_date.strftime("%Y%m%d")

#     day_dir = L2_ROOT / year
#     pattern = day_dir / f"S3B_SL_2_AOD____{day}*.SEN3.zip"

#     matches = glob.glob(str(pattern))
#     FILES.extend(matches)

#     # Também aceita NRT_AOD.nc já extraído, caso exista.
#     if day_dir.exists():
#         FILES.extend(
#             str(x)
#             for x in day_dir.glob(f"S3B_SL_2_AOD____{day}*/**/NRT_AOD.nc")
#             if x.is_file()
#         )

#     print(
#         f"[INFO] {day}: {len(matches)} produto(s) .SEN3.zip encontrado(s)."
#     )

#     current_date += timedelta(days=1)

# FILES = sorted(set(FILES))

# if not FILES:
#     raise SystemExit(
#         f"Nenhum .SEN3.zip ou NRT_AOD.nc encontrado entre "
#         f"{DATE_START:%Y%m%d} e {DATE_END:%Y%m%d}."
#     )

# print(f"\n[INFO] {len(FILES)} arquivo(s) encontrado(s) no período.")

# zip_files = [f for f in FILES if f.endswith(".SEN3.zip")]
# nc_files = [f for f in FILES if Path(f).name == "NRT_AOD.nc"]

# print(f"[INFO] Produtos .SEN3.zip: {len(zip_files)}")
# print(f"[INFO] NRT_AOD.nc extraídos: {len(nc_files)}")


# def localizar_nrt_aod(zip_path):
#     """
#     Localiza NRT_AOD.nc dentro de um produto Sentinel-3B .SEN3.zip.
#     Extrai somente o NRT_AOD.nc para um diretório temporário.
#     """

#     with zipfile.ZipFile(zip_path, "r") as z:

#         candidatos = [
#             name
#             for name in z.namelist()
#             if name.endswith("/NRT_AOD.nc") or name == "NRT_AOD.nc"
#         ]

#         if not candidatos:
#             raise FileNotFoundError(
#                 f"NRT_AOD.nc não encontrado em {zip_path}"
#             )

#         nc_name = candidatos[0]

#         tmpdir = tempfile.TemporaryDirectory()

#         nc_path = Path(tmpdir.name) / "NRT_AOD.nc"

#         with z.open(nc_name) as src, open(nc_path, "wb") as dst:
#             while True:
#                 chunk = src.read(1024 * 1024)

#                 if not chunk:
#                     break

#                 dst.write(chunk)

#         return tmpdir, nc_path




# def abrir_netcdf_do_zip(zip_path):
#     tmpdir = tempfile.TemporaryDirectory()

#     try:

#         with zipfile.ZipFile(zip_path, "r") as z:

#             candidatos = [
#                 name
#                 for name in z.namelist()
#                 if name.endswith("/NRT_AOD.nc")
#             ]

#             if not candidatos:
#                 raise FileNotFoundError(
#                     f"NRT_AOD.nc não encontrado em {zip_path}"
#                 )

#             nc_name = candidatos[0]

#             nc_path = Path(tmpdir.name) / "NRT_AOD.nc"

#             with z.open(nc_name) as src, open(nc_path, "wb") as dst:

#                 while True:

#                     chunk = src.read(1024 * 1024)

#                     if not chunk:
#                         break

#                     dst.write(chunk)

#         ds = xr.open_dataset(
#             nc_path,
#             decode_cf=True,
#             mask_and_scale=True
#         )

#         return ds, tmpdir

#     except Exception:

#         tmpdir.cleanup()
#         raise

    

# def extract_datetime(filename):
#     m = re.search(r"(\d{8})T(\d{6})", filename)
#     if not m:
#         return None
#     return datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S")


# # ------------------------------------------------------------
# # Ordenar e agrupar granules em passagens
# # ------------------------------------------------------------
# dated = []
# for f in FILES:
#     dt = extract_datetime(f)
#     if dt:
#         dated.append((dt, f))
#     else:
#         print(f"[WARN] Data/hora não encontrada: {f}")

# dated.sort(key=lambda x: x[0])

# passages = []
# current = []

# for item in dated:
#     if not current:
#         current = [item]
#         continue

#     gap = (item[0] - current[-1][0]).total_seconds() / 60.0

#     if gap <= PASSAGE_GAP_MINUTES:
#         current.append(item)
#     else:
#         passages.append(current)
#         current = [item]

# if current:
#     passages.append(current)

# print("\n[INFO] Passagens identificadas:")
# for i, passage in enumerate(passages, 1):
#     print(
#         f"  Passagem {i:02d}: "
#         f"{passage[0][0]:%Y-%m-%d %H:%M:%S} -> "
#         f"{passage[-1][0]:%H:%M:%S} "
#         f"({len(passage)} granules)"
#     )


# # ------------------------------------------------------------
# # Saídas
# # ------------------------------------------------------------
# figures_dir = OUTPUT_DIR / "figures" / VAR_PRODUCT
# geotiff_dir = OUTPUT_DIR / "geotiff" / VAR_PRODUCT
# cog_dir = OUTPUT_DIR / "cog" / VAR_PRODUCT
# tiles_dir = OUTPUT_DIR / "tiles" / VAR_PRODUCT

# for d in (figures_dir, geotiff_dir, cog_dir, tiles_dir):
#     d.mkdir(parents=True, exist_ok=True)

# try:
#     cmap, norm, vmin, vmax, ticks = load_colormap(VAR_PRODUCT)
# except Exception:
#     cmap = plt.cm.viridis
#     norm = None
#     vmin = vmax = ticks = None


# def read_aod_dataset(ds):

#     if VAR_PRODUCT not in ds.variables:
#         aod_vars = [
#             x for x in ds.variables
#             if "AOD" in x.upper()
#         ]

#         raise KeyError(
#             f"Variável '{VAR_PRODUCT}' não encontrada. "
#             f"Variáveis AOD encontradas: {aod_vars}"
#         )

#     data = (
#         ds[VAR_PRODUCT]
#         .squeeze()
#         .astype(np.float64)
#         .values
#     )

#     lat = (
#         ds["latitude"]
#         .squeeze()
#         .astype(np.float64)
#         .values
#     )

#     lon = (
#         ds["longitude"]
#         .squeeze()
#         .astype(np.float64)
#         .values
#     )

#     if lat.ndim == 1 and lon.ndim == 1:
#         lon, lat = np.meshgrid(lon, lat)

#     if data.shape != lat.shape:
#         lat = np.broadcast_to(lat, data.shape)
#         lon = np.broadcast_to(lon, data.shape)

#     data[~np.isfinite(data)] = np.nan
#     data[data < 0] = np.nan

#     valid = (
#         np.isfinite(data)
#         & np.isfinite(lat)
#         & np.isfinite(lon)
#         & (lat >= LAT_MIN)
#         & (lat <= LAT_MAX)
#         & (lon >= LON_MIN)
#         & (lon <= LON_MAX)
#     )

#     return (
#         lat[valid],
#         lon[valid],
#         data[valid]
#     )


# def read_aod_nc(filename):

#     with xr.open_dataset(
#         filename,
#         decode_cf=True,
#         mask_and_scale=True
#     ) as ds:

#         return read_aod_dataset(ds)


# def read_aod(filename):

#     filename = Path(filename)

#     # ------------------------------------------------------------
#     # Se for ZIP, extrai temporariamente o NRT_AOD.nc
#     # ------------------------------------------------------------

#     if filename.suffix.lower() == ".zip":

#         ds, tmpdir = abrir_netcdf_do_zip(filename)

#         try:
#             return read_aod_dataset(ds)

#         finally:
#             ds.close()
#             tmpdir.cleanup()

#     # ------------------------------------------------------------
#     # Se já for NRT_AOD.nc, abre normalmente
#     # ------------------------------------------------------------

#     return read_aod_nc(filename)


# def make_grid(lon, lat, values):
#     """Level-3 binning: média em células de 0.05°."""
#     lon_bins = np.arange(LON_MIN, LON_MAX + GRID_RESOLUTION, GRID_RESOLUTION)
#     lat_bins = np.arange(LAT_MIN, LAT_MAX + GRID_RESOLUTION, GRID_RESOLUTION)

#     ix = np.digitize(lon, lon_bins) - 1
#     iy = np.digitize(lat, lat_bins) - 1

#     ok = (
#         (ix >= 0) & (ix < len(lon_bins)) &
#         (iy >= 0) & (iy < len(lat_bins)) &
#         np.isfinite(values)
#     )

#     ix, iy, values = ix[ok], iy[ok], values[ok]

#     total = np.zeros((len(lat_bins), len(lon_bins)), dtype=np.float64)
#     count = np.zeros_like(total)

#     np.add.at(total, (iy, ix), values)
#     np.add.at(count, (iy, ix), 1)

#     grid = np.full(total.shape, np.nan, dtype=np.float32)
#     np.divide(total, count, out=grid, where=count > 0)

#     lon2d, lat2d = np.meshgrid(lon_bins, lat_bins)
#     return lon2d, lat2d, grid


# # ------------------------------------------------------------
# # Agrupar as passagens por dia
# # ------------------------------------------------------------
# passages_by_day = defaultdict(list)

# for passage in passages:
#     passage_day = passage[0][0].date()

#     # Segurança: somente dias solicitados.
#     if DATE_START <= passage_day < DATE_END:
#         passages_by_day[passage_day].append(passage)

# print("\n[INFO] Passagens por dia:")
# for day in sorted(passages_by_day):
#     print(f"  {day:%Y-%m-%d}: {len(passages_by_day[day])} passagem(ns)")

# # ------------------------------------------------------------
# # Processar um único produto diário por data
# # ------------------------------------------------------------
# for day in sorted(passages_by_day):

#     day_passages = passages_by_day[day]
#     year = day.strftime("%Y")
#     date = day.strftime("%Y%m%d")

#     print("\n" + "=" * 70)
#     print(f"OVERLAY DIÁRIO: {date}")
#     print(f"Passagens: {len(day_passages)}")
#     print("=" * 70)

#     # --------------------------------------------------------
#     # Juntar os pixels de TODAS as passagens do dia
#     # antes do Level-3 binning.
#     # --------------------------------------------------------
#     lats, lons, vals = [], [], []

#     for number, passage in enumerate(day_passages, 1):

#         start_dt = passage[0][0]
#         end_dt = passage[-1][0]

#         print(
#             f"\n[PASSAGEM {number:02d}] "
#             f"{start_dt:%H:%M:%S} -> {end_dt:%H:%M:%S} "
#             f"({len(passage)} granules)"
#         )

#         for dt, filename in passage:
#             print(f"[READ] {dt:%H:%M:%S} {Path(filename).name}")

#             try:
#                 lat, lon, value = read_aod(filename)
#             except Exception as e:
#                 print(f"[ERRO] {e}")
#                 continue

#             if len(value):
#                 lats.append(lat)
#                 lons.append(lon)
#                 vals.append(value)
#                 print(f"       pixels válidos: {len(value)}")
#             else:
#                 print("       pixels válidos: 0")

#     if not vals:
#         print(f"[WARN] {date}: nenhuma passagem possui dados válidos.")
#         continue

#     # Todas as passagens do dia entram no mesmo grid.
#     lat = np.concatenate(lats)
#     lon = np.concatenate(lons)
#     value = np.concatenate(vals)

#     print(f"[INFO] {date}: {len(value)} pixels válidos antes do binning.")

#     lon2d, lat2d, data = make_grid(lon, lat, value)

#     if not np.any(np.isfinite(data)):
#         print(f"[WARN] {date}: grade vazia.")
#         continue

#     print(
#         f"[INFO] {date}: "
#         f"{np.count_nonzero(np.isfinite(data))} células válidas "
#         f"no grid diário."
#     )

#     local_norm = norm
#     if local_norm is None:
#         lo = np.nanpercentile(data, 1)
#         hi = np.nanpercentile(data, 99)
#         if lo == hi:
#             hi = lo + 1
#         local_norm = Normalize(lo, hi)

#     # --------------------------------------------------------
#     # Diretórios
#     # --------------------------------------------------------
#     fig_dir = figures_dir / year
#     tif_dir = geotiff_dir / year
#     cog_year_dir = cog_dir / year
#     tile_dir = tiles_dir / year / date / "overlay"

#     for d in (fig_dir, tif_dir, cog_year_dir, tile_dir):
#         d.mkdir(parents=True, exist_ok=True)

#     base_name = f"s3b_aod_{date}_overlay"

#     # --------------------------------------------------------
#     # Figura diária
#     # --------------------------------------------------------
#     fig = plt.figure(figsize=(12, 8))
#     ax = plt.axes(projection=ccrs.PlateCarree())
#     ax.set_extent(
#         [LON_MIN, LON_MAX, LAT_MIN, LAT_MAX],
#         crs=ccrs.PlateCarree()
#     )

#     mesh = ax.pcolormesh(
#         lon2d, lat2d, data,
#         cmap=cmap, norm=local_norm,
#         shading="auto",
#         transform=ccrs.PlateCarree()
#     )

#     cbar = plt.colorbar(mesh, ax=ax, pad=0.02)
#     cbar.set_label(LABEL)

#     if ticks is not None:
#         cbar.set_ticks(ticks)

#     ax.coastlines(resolution="10m")
#     ax.add_feature(cfeature.BORDERS, linewidth=0.6)
#     ax.add_feature(cfeature.LAND, facecolor="lightgray")

#     states = NaturalEarthFeature(
#         category="cultural",
#         name="admin_1_states_provinces_lines",
#         scale="10m",
#         facecolor="none"
#     )
#     ax.add_feature(states, edgecolor="black", linewidth=0.4)

#     ax.set_title(
#         f"{TITLE} - {day:%Y-%m-%d} UTC - Overlay diário"
#     )

#     fig_path = fig_dir / f"{base_name}.{EXT}"
#     plt.savefig(fig_path, dpi=300, bbox_inches="tight")
#     plt.close(fig)

#     print(f"[OK] Figura: {fig_path}")

#     # --------------------------------------------------------
#     # GeoTIFF diário
#     # --------------------------------------------------------
#     tif_path = tif_dir / f"{base_name}.tif"

#     nrows, ncols = data.shape
#     xres = (LON_MAX - LON_MIN) / (ncols - 1)
#     yres = (LAT_MAX - LAT_MIN) / (nrows - 1)

#     driver = gdal.GetDriverByName("GTiff")
#     ds = driver.Create(
#         str(tif_path), ncols, nrows, 1, gdal.GDT_Float32
#     )

#     ds.SetGeoTransform((LON_MIN, xres, 0, LAT_MAX, 0, -yres))

#     srs = osr.SpatialReference()
#     srs.ImportFromEPSG(4326)
#     ds.SetProjection(srs.ExportToWkt())

#     band = ds.GetRasterBand(1)
#     out = np.flipud(data).astype(np.float32)
#     out[~np.isfinite(out)] = -9999
#     band.WriteArray(out)
#     band.SetNoDataValue(-9999)
#     band.SetDescription("Sentinel-3B SLSTR AOD 550 nm - daily overlay")

#     ds.FlushCache()
#     ds = None

#     print(f"[OK] GeoTIFF: {tif_path}")

#     # --------------------------------------------------------
#     # COG
#     # --------------------------------------------------------
#     cog_path = cog_year_dir / f"{base_name}_cog.tif"

#     gdal.Translate(
#         str(cog_path),
#         str(tif_path),
#         format="COG",
#         creationOptions=["COMPRESS=DEFLATE", "LEVEL=9"]
#     )

#     print(f"[OK] COG: {cog_path}")

#     # --------------------------------------------------------
#     # Tiles XYZ
#     # --------------------------------------------------------
#     vrt_path = cog_year_dir / f"{base_name}_tiles.vrt"

#     subprocess.run([
#         "gdal_translate", "-of", "VRT", "-ot", "Byte",
#         "-scale", "-a_nodata", "0",
#         str(cog_path), str(vrt_path)
#     ], check=True)

#     subprocess.run([
#         "gdal2tiles.py",
#         "--processes=4",
#         "-z", "0-6",
#         "-w", "none",
#         str(vrt_path),
#         str(tile_dir)
#     ], check=True)

#     print(f"[OK] Tiles: {tile_dir}")

# print("\n[OK] Processamento Sentinel-3B concluído.")


##==================================================================
### VERSÃO FUNCIONA PARA MONTAGEM DOS GRÁNULOS EM CADA PASSAGEM ====
### Se tiver 3 passagem, serão 3 arquivos em formato GeoTIFF final==
##================================================================== 
# #!/usr/bin/env python3
# # Sentinel-3B SLSTR L2 AOD -> passagem -> GeoTIFF/COG/tiles
# #
# # Adaptação da rotina read_plot_S5p.py.
# #
# # Exemplo:
# # python read_plot_s3b.py "/home/jurandir/cipc_data/L2/2024/S3B_SL_2_AOD____20240816*/**/NRT_AOD.nc" AOD_550_Merged_OceanLand "Sentinel-3B AOD 550 nm" "AOD 550" png

# import sys, os, re, glob, subprocess
# from pathlib import Path
# from datetime import datetime
# import xarray as xr
# import numpy as np
# import matplotlib.pyplot as plt
# import cartopy.crs as ccrs
# import cartopy.feature as cfeature
# from cartopy.feature import NaturalEarthFeature
# from matplotlib.colors import Normalize
# from osgeo import gdal, osr

# import zipfile
# import tempfile

# from src.processing.colormap_loader import load_colormap
# from src.config.settings import OUTPUT_DIR

# # América do Sul
# LON_MIN, LON_MAX = -86.17, -30.12
# LAT_MIN, LAT_MAX = -59.01, 11.60

# # Granules da mesma passagem são separados por ~5 min.
# # Gap maior que este valor inicia nova passagem.
# PASSAGE_GAP_MINUTES = 20
# GRID_RESOLUTION = 0.05


# if len(sys.argv) < 6:
#     print("Uso:")
#     print("python read_plot_s3b.py FILE1 [FILE2 ... ou máscara*] VAR_PRODUCT TITLE LABEL EXT")
#     print()
#     print("Exemplo:")
#     print("python read_plot_s3b.py '/home/jurandir/cipc_data/L2/2024/S3B_SL_2_AOD____20240816*/**/NRT_AOD.nc' AOD_550_Merged_OceanLand 'Sentinel-3B AOD 550 nm' 'AOD 550' png")
#     sys.exit(1)

# VAR_PRODUCT = sys.argv[-4]
# TITLE = sys.argv[-3]
# LABEL = sys.argv[-2]
# EXT = sys.argv[-1].lower().replace(".", "")
# INPUTS = sys.argv[1:-4]

# if len(sys.argv) < 6:
#     print("\nUso:")
#     print(
#         "python read_plot_s3b.py "
#         "FILE1 [FILE2 ... ou máscara*] "
#         "VAR_PRODUCT TITLE LABEL EXT"
#     )
#     print()
#     print("Exemplo:")
#     print(
#         "python read_plot_s3b.py "
#         "'/home/jurandir/cipc_data/L2/2024/"
#         "S3B_SL_2_AOD____20240816*/**/NRT_AOD.nc' "
#         "AOD_550_Merged_OceanLand "
#         "'Sentinel-3B AOD 550 nm' "
#         "'AOD 550' png"
#     )
#     sys.exit(1)

# VAR_PRODUCT = sys.argv[-4]
# TITLE = sys.argv[-3]
# LABEL = sys.argv[-2]
# EXT = sys.argv[-1].lower().replace(".", "")
# INPUTS = sys.argv[1:-4]

# if EXT not in ("png", "jpg", "jpeg"):
#     raise ValueError("EXT deve ser png, jpg ou jpeg")


# # ------------------------------------------------------------
# # Localizar arquivos S3B
# # ------------------------------------------------------------
# FILES = []

# for item in INPUTS:

#     matches = glob.glob(item, recursive=True)

#     if not matches:
#         print(f"[WARN] Nenhum arquivo encontrado: {item}")
#         continue

#     for path in matches:

#         p = Path(path)

#         # --------------------------------------------------------
#         # Produto ZIP
#         # --------------------------------------------------------
#         if p.is_file() and p.name.endswith(".SEN3.zip"):
#             FILES.append(str(p))

#         # --------------------------------------------------------
#         # NRT_AOD.nc já extraído
#         # --------------------------------------------------------
#         elif p.is_file() and p.name == "NRT_AOD.nc":
#             FILES.append(str(p))

#         # --------------------------------------------------------
#         # Diretório
#         # --------------------------------------------------------
#         elif p.is_dir():

#             # ZIPs Sentinel-3B
#             FILES.extend(
#                 str(x)
#                 for x in p.rglob("*.SEN3.zip")
#                 if x.is_file()
#             )

#             # NRT_AOD.nc já extraídos
#             FILES.extend(
#                 str(x)
#                 for x in p.rglob("NRT_AOD.nc")
#                 if x.is_file()
#             )


# FILES = sorted(set(FILES))

# if not FILES:
#     raise SystemExit(
#         "Nenhum .SEN3.zip ou NRT_AOD.nc encontrado."
#     )

# print(f"\n[INFO] {len(FILES)} arquivo(s) encontrado(s).")

# zip_files = [
#     f for f in FILES
#     if f.endswith(".SEN3.zip")
# ]

# nc_files = [
#     f for f in FILES
#     if Path(f).name == "NRT_AOD.nc"
# ]

# print(f"[INFO] Produtos .SEN3.zip: {len(zip_files)}")
# print(f"[INFO] NRT_AOD.nc extraídos: {len(nc_files)}")

# # # ------------------------------------------------------------
# # # Localizar NRT_AOD.nc
# # # ------------------------------------------------------------
# # FILES = []
# # for item in INPUTS:
# #     matches = glob.glob(item, recursive=True)
# #     if not matches:
# #         print(f"[WARN] Nenhum arquivo encontrado: {item}")
# #         continue

# #     for path in matches:
# #         p = Path(path)
# #         if p.is_file() and p.name == "NRT_AOD.nc":
# #             FILES.append(str(p))
# #         elif p.is_dir():
# #             FILES.extend(str(x) for x in p.rglob("NRT_AOD.nc"))

# # FILES = sorted(set(FILES))

# # if not FILES:
# #     raise SystemExit("Nenhum NRT_AOD.nc encontrado.")

# # print(f"[INFO] {len(FILES)} NRT_AOD.nc encontrado(s).")


# def localizar_nrt_aod(zip_path):
#     """
#     Localiza NRT_AOD.nc dentro de um produto Sentinel-3B .SEN3.zip.
#     Extrai somente o NRT_AOD.nc para um diretório temporário.
#     """

#     with zipfile.ZipFile(zip_path, "r") as z:

#         candidatos = [
#             name
#             for name in z.namelist()
#             if name.endswith("/NRT_AOD.nc") or name == "NRT_AOD.nc"
#         ]

#         if not candidatos:
#             raise FileNotFoundError(
#                 f"NRT_AOD.nc não encontrado em {zip_path}"
#             )

#         nc_name = candidatos[0]

#         tmpdir = tempfile.TemporaryDirectory()

#         nc_path = Path(tmpdir.name) / "NRT_AOD.nc"

#         with z.open(nc_name) as src, open(nc_path, "wb") as dst:
#             while True:
#                 chunk = src.read(1024 * 1024)

#                 if not chunk:
#                     break

#                 dst.write(chunk)

#         return tmpdir, nc_path




# def abrir_netcdf_do_zip(zip_path):
#     tmpdir = tempfile.TemporaryDirectory()

#     try:

#         with zipfile.ZipFile(zip_path, "r") as z:

#             candidatos = [
#                 name
#                 for name in z.namelist()
#                 if name.endswith("/NRT_AOD.nc")
#             ]

#             if not candidatos:
#                 raise FileNotFoundError(
#                     f"NRT_AOD.nc não encontrado em {zip_path}"
#                 )

#             nc_name = candidatos[0]

#             nc_path = Path(tmpdir.name) / "NRT_AOD.nc"

#             with z.open(nc_name) as src, open(nc_path, "wb") as dst:

#                 while True:

#                     chunk = src.read(1024 * 1024)

#                     if not chunk:
#                         break

#                     dst.write(chunk)

#         ds = xr.open_dataset(
#             nc_path,
#             decode_cf=True,
#             mask_and_scale=True
#         )

#         return ds, tmpdir

#     except Exception:

#         tmpdir.cleanup()
#         raise

    

# def extract_datetime(filename):
#     m = re.search(r"(\d{8})T(\d{6})", filename)
#     if not m:
#         return None
#     return datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S")


# # ------------------------------------------------------------
# # Ordenar e agrupar granules em passagens
# # ------------------------------------------------------------
# dated = []
# for f in FILES:
#     dt = extract_datetime(f)
#     if dt:
#         dated.append((dt, f))
#     else:
#         print(f"[WARN] Data/hora não encontrada: {f}")

# dated.sort(key=lambda x: x[0])

# passages = []
# current = []

# for item in dated:
#     if not current:
#         current = [item]
#         continue

#     gap = (item[0] - current[-1][0]).total_seconds() / 60.0

#     if gap <= PASSAGE_GAP_MINUTES:
#         current.append(item)
#     else:
#         passages.append(current)
#         current = [item]

# if current:
#     passages.append(current)

# print("\n[INFO] Passagens identificadas:")
# for i, passage in enumerate(passages, 1):
#     print(
#         f"  Passagem {i:02d}: "
#         f"{passage[0][0]:%Y-%m-%d %H:%M:%S} -> "
#         f"{passage[-1][0]:%H:%M:%S} "
#         f"({len(passage)} granules)"
#     )


# # ------------------------------------------------------------
# # Saídas
# # ------------------------------------------------------------
# figures_dir = OUTPUT_DIR / "figures" / VAR_PRODUCT
# geotiff_dir = OUTPUT_DIR / "geotiff" / VAR_PRODUCT
# cog_dir = OUTPUT_DIR / "cog" / VAR_PRODUCT
# tiles_dir = OUTPUT_DIR / "tiles" / VAR_PRODUCT

# for d in (figures_dir, geotiff_dir, cog_dir, tiles_dir):
#     d.mkdir(parents=True, exist_ok=True)

# try:
#     cmap, norm, vmin, vmax, ticks = load_colormap(VAR_PRODUCT)
# except Exception:
#     cmap = plt.cm.viridis
#     norm = None
#     vmin = vmax = ticks = None


# def read_aod_dataset(ds):

#     if VAR_PRODUCT not in ds.variables:
#         aod_vars = [
#             x for x in ds.variables
#             if "AOD" in x.upper()
#         ]

#         raise KeyError(
#             f"Variável '{VAR_PRODUCT}' não encontrada. "
#             f"Variáveis AOD encontradas: {aod_vars}"
#         )

#     data = (
#         ds[VAR_PRODUCT]
#         .squeeze()
#         .astype(np.float64)
#         .values
#     )

#     lat = (
#         ds["latitude"]
#         .squeeze()
#         .astype(np.float64)
#         .values
#     )

#     lon = (
#         ds["longitude"]
#         .squeeze()
#         .astype(np.float64)
#         .values
#     )

#     if lat.ndim == 1 and lon.ndim == 1:
#         lon, lat = np.meshgrid(lon, lat)

#     if data.shape != lat.shape:
#         lat = np.broadcast_to(lat, data.shape)
#         lon = np.broadcast_to(lon, data.shape)

#     data[~np.isfinite(data)] = np.nan
#     data[data < 0] = np.nan

#     valid = (
#         np.isfinite(data)
#         & np.isfinite(lat)
#         & np.isfinite(lon)
#         & (lat >= LAT_MIN)
#         & (lat <= LAT_MAX)
#         & (lon >= LON_MIN)
#         & (lon <= LON_MAX)
#     )

#     return (
#         lat[valid],
#         lon[valid],
#         data[valid]
#     )


# def read_aod_nc(filename):

#     with xr.open_dataset(
#         filename,
#         decode_cf=True,
#         mask_and_scale=True
#     ) as ds:

#         return read_aod_dataset(ds)


# def read_aod(filename):

#     filename = Path(filename)

#     # ------------------------------------------------------------
#     # Se for ZIP, extrai temporariamente o NRT_AOD.nc
#     # ------------------------------------------------------------

#     if filename.suffix.lower() == ".zip":

#         ds, tmpdir = abrir_netcdf_do_zip(filename)

#         try:
#             return read_aod_dataset(ds)

#         finally:
#             ds.close()
#             tmpdir.cleanup()

#     # ------------------------------------------------------------
#     # Se já for NRT_AOD.nc, abre normalmente
#     # ------------------------------------------------------------

#     return read_aod_nc(filename)


# def make_grid(lon, lat, values):
#     """Level-3 binning: média em células de 0.05°."""
#     lon_bins = np.arange(LON_MIN, LON_MAX + GRID_RESOLUTION, GRID_RESOLUTION)
#     lat_bins = np.arange(LAT_MIN, LAT_MAX + GRID_RESOLUTION, GRID_RESOLUTION)

#     ix = np.digitize(lon, lon_bins) - 1
#     iy = np.digitize(lat, lat_bins) - 1

#     ok = (
#         (ix >= 0) & (ix < len(lon_bins)) &
#         (iy >= 0) & (iy < len(lat_bins)) &
#         np.isfinite(values)
#     )

#     ix, iy, values = ix[ok], iy[ok], values[ok]

#     total = np.zeros((len(lat_bins), len(lon_bins)), dtype=np.float64)
#     count = np.zeros_like(total)

#     np.add.at(total, (iy, ix), values)
#     np.add.at(count, (iy, ix), 1)

#     grid = np.full(total.shape, np.nan, dtype=np.float32)
#     np.divide(total, count, out=grid, where=count > 0)

#     lon2d, lat2d = np.meshgrid(lon_bins, lat_bins)
#     return lon2d, lat2d, grid


# # ------------------------------------------------------------
# # Processar cada passagem
# # ------------------------------------------------------------
# for number, passage in enumerate(passages, 1):

#     start_dt = passage[0][0]
#     end_dt = passage[-1][0]
#     timestamp = start_dt.strftime("%Y%m%d_%H%M%S")
#     year = start_dt.strftime("%Y")
#     date = start_dt.strftime("%Y%m%d")

#     print("\n" + "=" * 70)
#     print(f"PASSAGEM {number:02d}")
#     print(f"{start_dt} -> {end_dt}")
#     print("=" * 70)

#     lats, lons, vals = [], [], []

#     for dt, filename in passage:
#         print(f"[READ] {dt:%H:%M:%S} {Path(filename).parent.name}")

#         try:
#             lat, lon, value = read_aod(filename)
#         except Exception as e:
#             print(f"[ERRO] {e}")
#             continue

#         if len(value):
#             lats.append(lat)
#             lons.append(lon)
#             vals.append(value)
#             print(f"       pixels válidos: {len(value)}")

#     if not vals:
#         print("[WARN] Passagem sem dados válidos.")
#         continue

#     lat = np.concatenate(lats)
#     lon = np.concatenate(lons)
#     value = np.concatenate(vals)

#     lon2d, lat2d, data = make_grid(lon, lat, value)

#     if not np.any(np.isfinite(data)):
#         print("[WARN] Grade vazia.")
#         continue

#     local_norm = norm
#     if local_norm is None:
#         lo = np.nanpercentile(data, 1)
#         hi = np.nanpercentile(data, 99)
#         if lo == hi:
#             hi = lo + 1
#         local_norm = Normalize(lo, hi)

#     # Diretórios anuais
#     fig_dir = figures_dir / year
#     tif_dir = geotiff_dir / year
#     cog_year_dir = cog_dir / year
#     tile_dir = tiles_dir / year / date / timestamp

#     for d in (fig_dir, tif_dir, cog_year_dir, tile_dir):
#         d.mkdir(parents=True, exist_ok=True)

#     # --------------------------------------------------------
#     # Figura
#     # --------------------------------------------------------
#     fig = plt.figure(figsize=(12, 8))
#     ax = plt.axes(projection=ccrs.PlateCarree())
#     ax.set_extent(
#         [LON_MIN, LON_MAX, LAT_MIN, LAT_MAX],
#         crs=ccrs.PlateCarree()
#     )

#     mesh = ax.pcolormesh(
#         lon2d, lat2d, data,
#         cmap=cmap, norm=local_norm,
#         shading="auto",
#         transform=ccrs.PlateCarree()
#     )

#     cbar = plt.colorbar(mesh, ax=ax, pad=0.02)
#     cbar.set_label(LABEL)

#     if ticks is not None:
#         cbar.set_ticks(ticks)

#     ax.coastlines(resolution="10m")
#     ax.add_feature(cfeature.BORDERS, linewidth=0.6)
#     ax.add_feature(cfeature.LAND, facecolor="lightgray")

#     states = NaturalEarthFeature(
#         category="cultural",
#         name="admin_1_states_provinces_lines",
#         scale="10m",
#         facecolor="none"
#     )
#     ax.add_feature(states, edgecolor="black", linewidth=0.4)

#     ax.set_title(
#         f"{TITLE} - {start_dt:%Y-%m-%d %H:%M:%S} UTC"
#     )

#     fig_path = fig_dir / f"s3b_aod_{timestamp}.{EXT}"
#     plt.savefig(fig_path, dpi=300, bbox_inches="tight")
#     plt.close(fig)

#     print(f"[OK] Figura: {fig_path}")

#     # --------------------------------------------------------
#     # GeoTIFF
#     # --------------------------------------------------------
#     tif_path = tif_dir / f"s3b_aod_{timestamp}.tif"

#     nrows, ncols = data.shape
#     xres = (LON_MAX - LON_MIN) / (ncols - 1)
#     yres = (LAT_MAX - LAT_MIN) / (nrows - 1)

#     driver = gdal.GetDriverByName("GTiff")
#     ds = driver.Create(
#         str(tif_path), ncols, nrows, 1, gdal.GDT_Float32
#     )

#     ds.SetGeoTransform((LON_MIN, xres, 0, LAT_MAX, 0, -yres))

#     srs = osr.SpatialReference()
#     srs.ImportFromEPSG(4326)
#     ds.SetProjection(srs.ExportToWkt())

#     band = ds.GetRasterBand(1)
#     out = np.flipud(data).astype(np.float32)
#     out[~np.isfinite(out)] = -9999
#     band.WriteArray(out)
#     band.SetNoDataValue(-9999)
#     band.SetDescription("Sentinel-3B SLSTR AOD 550 nm")

#     ds.FlushCache()
#     ds = None

#     print(f"[OK] GeoTIFF: {tif_path}")

#     # --------------------------------------------------------
#     # COG
#     # --------------------------------------------------------
#     cog_path = cog_year_dir / f"s3b_aod_{timestamp}_cog.tif"

#     gdal.Translate(
#         str(cog_path),
#         str(tif_path),
#         format="COG",
#         creationOptions=["COMPRESS=DEFLATE", "LEVEL=9"]
#     )

#     print(f"[OK] COG: {cog_path}")

#     # --------------------------------------------------------
#     # Tiles XYZ
#     # --------------------------------------------------------
#     vrt_path = cog_year_dir / f"s3b_aod_{timestamp}_tiles.vrt"

#     subprocess.run([
#         "gdal_translate", "-of", "VRT", "-ot", "Byte",
#         "-scale", "-a_nodata", "0",
#         str(cog_path), str(vrt_path)
#     ], check=True)

#     subprocess.run([
#         "gdal2tiles.py",
#         "--processes=4",
#         "-z", "0-6",
#         "-w", "none",
#         str(vrt_path),
#         str(tile_dir)
#     ], check=True)

#     print(f"[OK] Tiles: {tile_dir}")

# print("\n[OK] Processamento Sentinel-3B concluído.")
