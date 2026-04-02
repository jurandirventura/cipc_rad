# Com qa_value mas plotando apenas valores maiores que -1
# Inclui também as subdivisões de mapa para Estados...

import sys
import os
import re
import glob

import xarray as xr
import numpy as np
import matplotlib.pyplot as plt

import cartopy.crs as ccrs
import cartopy.feature as cfeature
from cartopy.feature import NaturalEarthFeature

from matplotlib.colors import Normalize

from src.processing.colormap_loader import load_colormap
from src.config.settings import OUTPUT_DIR

from osgeo import gdal

import subprocess

from scipy.interpolate import griddata
from scipy.spatial import cKDTree


import xarray as xr
import netCDF4

def open_netcdf_smart(file, group=None):
    """
    Abre NetCDF com ou sem group automaticamente
    """

    try:
        # Abre via netCDF4 para inspecionar
        nc = netCDF4.Dataset(file)

        # Lista grupos disponíveis
        groups = list(nc.groups.keys())

        nc.close()

        # Caso tenha grupos (ex: Sentinel-5P)
        if groups:
            if group:
                print(f"[INFO] Abrindo com group: {group}")
                return xr.open_dataset(file, group=group)
            else:
                # fallback padrão Sentinel
                print("[INFO] Group não informado, usando '/PRODUCT'")
                return xr.open_dataset(file, group="/PRODUCT")

        # Caso NÃO tenha grupos (ex: risco de fogo)
        else:
            print("[INFO] Arquivo sem group (raiz)")
            return xr.open_dataset(file)

    except Exception as e:
        print(f"[ERRO] Falha ao abrir arquivo: {e}")
        raise



# =========================
# ARGUMENTOS
# =========================

if len(sys.argv) < 7:
    print("\nUso:")
    print("python read_plot_S5p.py FILE1 [FILE2 ... ou máscara*] GROUP VAR_PRODUCT TITLE LABEL EXT(png|jpeg)\n")
    sys.exit(1)

GROUP = sys.argv[-5]
VAR_PRODUCT = sys.argv[-4]
TITLE = sys.argv[-3]
LABEL = sys.argv[-2]
EXT = sys.argv[-1].lower().replace(".", "")
INPUTS = sys.argv[1:-5]

if EXT not in ["png", "jpeg", "jpg"]:
    print("Extensão deve ser png ou jpeg")
    sys.exit(1)


# =========================
# EXPANDIR MÁSCARAS
# =========================

FILES = []

for item in INPUTS:
    expanded = glob.glob(item)
    if expanded:
        FILES.extend(expanded)
    else:
        print(f"Aviso: {item} não encontrou arquivos.")

FILES = sorted(list(set(FILES)))

if len(FILES) == 0:
    print("Nenhum arquivo encontrado.")
    sys.exit(1)

print(f"{len(FILES)} arquivo(s) encontrado(s).")


# =========================
# AGRUPAR POR DATA
# =========================

groups = {}

for f in FILES:

    name = os.path.basename(f)

    # tenta padrão Sentinel (com T)
    m = re.search(r'_(\d{8})T', name)

    if m:
        date = m.group(1)
    else:
        # tenta padrão INPE (sem T)
        m = re.search(r'(\d{8})', name)
        if m:
            date = m.group(1)
        else:
            date = "unknown"


    if date not in groups:
        groups[date] = []

    groups[date].append(f)

print("\nDatas encontradas:")
for d in groups:
    print(d, len(groups[d]), "arquivos")


# =========================
# DIRETÓRIO DE SAÍDA
# =========================

figures_dir = OUTPUT_DIR / "figures" / VAR_PRODUCT
geotiff_dir = OUTPUT_DIR / "geotiff" / VAR_PRODUCT
cog_dir = OUTPUT_DIR / "cog" / VAR_PRODUCT
tiles_dir = OUTPUT_DIR / "tiles" / VAR_PRODUCT


os.makedirs(figures_dir, exist_ok=True)
os.makedirs(geotiff_dir, exist_ok=True)
os.makedirs(cog_dir, exist_ok=True)
os.makedirs(tiles_dir, exist_ok=True)

# =========================
# COLORMAP
# =========================

try:

    cmap, norm, vmin, vmax, ticks = load_colormap(VAR_PRODUCT)

    print(f"Colormap carregado para {VAR_PRODUCT}")

except Exception:

    print("Colormap não encontrado, usando padrão matplotlib")

    cmap = plt.cm.viridis
    norm = None
    ticks = None
    vmin = None
    vmax = None

# =========================
# LOOP POR DATA
# =========================

for date_part, day_files in groups.items():

    all_lon = []
    all_lat = []
    all_values = []   
    all_data = [] 

    print("\nProcessando data:", date_part)

    # -------------------------
    # extrair ano
    # -------------------------

    if date_part != "unknown":
        year = date_part[:4]
    else:
        year = "unknown"

    # -------------------------
    # diretório por ano
    # -------------------------

    year_fig_dir = figures_dir / year
    year_tif_dir = geotiff_dir / year
    year_cog_dir = cog_dir / year
    date_tiles_dir = tiles_dir / year / date_part
    
    os.makedirs(year_fig_dir, exist_ok=True)
    os.makedirs(year_tif_dir, exist_ok=True)
    os.makedirs(year_cog_dir, exist_ok=True)
    os.makedirs(date_tiles_dir, exist_ok=True)



    fig = plt.figure(figsize=(12, 8))

    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([-85, -30, -60, 15], crs=ccrs.PlateCarree())

    last_mesh = None

    for FILE in day_files:


        print("Lendo:", FILE)

        try:

            # 🔥 NOVO: usa função inteligente
            ds = open_netcdf_smart(FILE, GROUP)

        except Exception as e:

            print("Erro abrindo", FILE)
            print(e)
            continue


        # =========================
        # VARIÁVEL
        # =========================

        var = ds[VAR_PRODUCT]

        # 🔥 remove dimensão de tempo corretamente
        if "time" in var.dims:
            var = var.isel(time=0)

        data = var.astype(float).values


        # =========================
        # LAT / LON
        # =========================

        if "latitude" in ds:
            lat = ds["latitude"]
            lon = ds["longitude"]
        elif "lat" in ds:
            lat = ds["lat"]
            lon = ds["lon"]
        else:
            raise Exception("Variáveis de latitude/longitude não encontradas")

        lat = lat.values
        lon = lon.values

        # =========================
        # FILL VALUE
        # =========================

        fill_value = var.attrs.get("_FillValue")

        if fill_value is not None:
            data[data == fill_value] = np.nan


        # =========================
        # QA FILTER
        # =========================

        if "qa_value" in ds.variables:

            qa = ds["qa_value"]

            if "time" in qa.dims:
                qa = qa.isel(time=0)

            qa = qa.values

            # 🔥 remove dimensões extras
            qa = np.squeeze(qa)

            # 🔥 garante mesmo shape do data
            if qa.shape != data.shape:
                try:
                    qa = np.broadcast_to(qa, data.shape)
                except:
                    print("⚠️ QA shape incompatível:", qa.shape, "vs", data.shape)
                    qa = None

            if qa is not None:
               data[qa < 0.75] = np.nan
               #data[qa < 0.50] = np.nan
               #data[qa < 0] = np.nan

        # # =========================
        # # INTERPOLAR PARA GRADE REGULAR
        # # =========================

        valid = np.isfinite(data)

        # garante que data é 2D
        if data.ndim == 2:

            # caso lat/lon 1D → cria grade
            if lat.ndim == 1 and lon.ndim == 1:
                lon2d, lat2d = np.meshgrid(lon, lat)

            # caso lat/lon 2D → usa direto
            elif lat.ndim == 2 and lon.ndim == 2:
                lat2d = lat
                lon2d = lon

            # 🔥 CASO PROBLEMÁTICO (Sentinel com dimensão extra)
            else:
                lat2d = np.squeeze(lat)
                lon2d = np.squeeze(lon)

                if lat2d.ndim == 1 and lon2d.ndim == 1:
                    lon2d, lat2d = np.meshgrid(lon2d, lat2d)

            # 🔥 AGORA GARANTE COMPATIBILIDADE
            if lat2d.shape != data.shape:
                print("⚠️ Ajustando shape lat/lon para bater com data")

                lat2d = np.broadcast_to(lat2d, data.shape)
                lon2d = np.broadcast_to(lon2d, data.shape)

            all_lon.append(lon2d[valid])
            all_lat.append(lat2d[valid])
            all_values.append(data[valid])        


        # =========================
        # FILTRO
        # =========================

        ###data[(data < -1) | (data > 5)] = np.nan

        if np.all(np.isnan(data)):

            print("Sem dados válidos.")
            ds.close()
            continue


        # =========================
        # NORMALIZE
        # =========================

        if norm is None:

            vmin = np.nanmin(data)
            vmax = np.nanmax(data)

            norm = Normalize(vmin=vmin, vmax=vmax)


        # # =========================
        # # PLOT
        # # =========================

        # last_mesh = ax.pcolormesh(
        #     lon,
        #     lat,
        #     data,
        #     cmap=cmap,
        #     norm=norm,
        #     shading="auto",
        #     transform=ccrs.PlateCarree()
        # )

        ds.close()

    if len(all_values) == 0 or all(len(v) == 0 for v in all_values):        
        print("Sem dados válidos.")
        continue

    # =========================
    # GRID LEVEL-3 BINNING
    # =========================

    lon_all = np.concatenate(all_lon)
    lat_all = np.concatenate(all_lat)
    values_all = np.concatenate(all_values)

    # resolução da grade
    res = 0.05   # ~5 km

    lon_min = -85
    lon_max = -30
    lat_min = -60
    lat_max = 15

    lon_bins = np.arange(lon_min, lon_max + res, res)
    lat_bins = np.arange(lat_min, lat_max + res, res)

    # índices das células
    lon_idx = np.digitize(lon_all, lon_bins) - 1
    lat_idx = np.digitize(lat_all, lat_bins) - 1

    grid_sum = np.zeros((len(lat_bins), len(lon_bins)))
    grid_count = np.zeros((len(lat_bins), len(lon_bins)))

    for i in range(len(values_all)):

        x = lon_idx[i]
        y = lat_idx[i]

        if 0 <= x < len(lon_bins) and 0 <= y < len(lat_bins):

            grid_sum[y, x] += values_all[i]
            grid_count[y, x] += 1

    grid_data = np.zeros_like(grid_sum)

    np.divide(
        grid_sum,
        grid_count,
        out=grid_data,
        where=grid_count > 0
    )

    grid_data[grid_count == 0] = np.nan

    lon2, lat2 = np.meshgrid(lon_bins, lat_bins)

    data = grid_data
    lon = lon2
    lat = lat2

    last_mesh = ax.pcolormesh(
        lon,
        lat,
        data,
        cmap=cmap,
        norm=norm,
        shading="auto",
        transform=ccrs.PlateCarree()
    )


    if last_mesh is None:
        print("Sem dados válidos para", date_part)
        plt.close()
        continue


    # =========================
    # COLORBAR
    # =========================

    cbar = plt.colorbar(last_mesh, ax=ax, orientation="vertical", pad=0.02)
    cbar.set_label(LABEL)

    if ticks is not None:
        cbar.set_ticks(ticks)
    else:
        cbar.set_ticks(np.linspace(vmin, vmax, 6))


    # =========================
    # MAPA
    # =========================

    ax.coastlines(resolution="10m")
    ax.add_feature(cfeature.BORDERS, linewidth=0.6)
    ax.add_feature(cfeature.LAND, facecolor="lightgray")

    states = NaturalEarthFeature(
        category="cultural",
        name="admin_1_states_provinces_lines",
        scale="10m",
        facecolor="none"
    )

    ax.add_feature(states, edgecolor="black", linewidth=0.4)

    plt.title(f"{TITLE} {date_part}")


    # =========================
    # SALVAR
    # =========================

    output_name = f"{VAR_PRODUCT}_{date_part}_overlay.{EXT}"

    output_path = year_fig_dir / output_name

    plt.savefig(output_path, dpi=300, bbox_inches="tight")


    # =========================
    # GERAR GEOTIFF
    # =========================

    tif_name = f"{VAR_PRODUCT}_{date_part}_overlay.tif"
    tif_path = year_tif_dir / tif_name

    xmin = -85
    xmax = -30
    ymin = -60
    ymax = 15

    nrows, ncols = data.shape

    xres = (xmax - xmin) / (ncols - 1)
    yres = (ymax - ymin) / (nrows - 1)

    driver = gdal.GetDriverByName("GTiff")

    dataset = driver.Create(
        str(tif_path),
        ncols,
        nrows,
        1,
        gdal.GDT_Float32
    )

    dataset.SetGeoTransform((xmin, xres, 0, ymax, 0, -yres))

    srs = gdal.osr.SpatialReference()
    srs.ImportFromEPSG(4326)

    dataset.SetProjection(srs.ExportToWkt())

    band = dataset.GetRasterBand(1)

    data_out = np.flipud(data)
    data_out[np.isnan(data_out)] = -9999

    band.WriteArray(data_out)
    band.SetNoDataValue(-9999)

    # data_out = np.flipud(data)
    # band.WriteArray(data_out)

    #band.SetNoDataValue(np.nan)
    band.SetNoDataValue(-9999)

    dataset.FlushCache()
    dataset = None

    print("[OK] GeoTIFF salvo:")
    print(tif_path)


    # =========================
    # GERAR COG
    # =========================

    cog_name = f"{VAR_PRODUCT}_{date_part}_overlay_cog.tif"
    cog_path = year_cog_dir / cog_name

    gdal.Translate(
        str(cog_path),
        str(tif_path),
        format="COG",
        creationOptions=[
            "COMPRESS=DEFLATE",
            "LEVEL=9"
        ]
    )

    print("[OK] COG salvo:")
    print(cog_path)


    # =========================
    # GERAR TILES XYZ
    # =========================

    print("[INFO] Preparando raster 8-bit para tiles...")

    vrt_path = year_cog_dir / f"{VAR_PRODUCT}_{date_part}_tiles.vrt"

    subprocess.run([
        "gdal_translate",
        "-of", "VRT",
        "-ot", "Byte",
        "-scale",
        "-a_nodata", "0",
        str(cog_path),
        str(vrt_path)
    ], check=True)


    print("[INFO] Gerando tiles...")

    cmd = [
        "gdal2tiles.py",
        "--processes=4",
        "-z", "0-6",
        "-w", "none",
        str(vrt_path),
        str(date_tiles_dir)
    ]


    subprocess.run(cmd, check=True)

    print("[OK] Tiles gerados em:")
    print(date_tiles_dir)



    print("\n[OK] Imagem salva em:")
    print(output_path)

    plt.close()




