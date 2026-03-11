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

    m = re.search(r'_(\d{8})T', name)

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

            ds = xr.open_dataset(
                FILE,
                group=GROUP,
                engine="netcdf4",
                decode_cf=False
            )

        except Exception as e:

            print("Erro abrindo", FILE)
            print(e)
            continue


        var = ds[VAR_PRODUCT][0]
        lat = ds["latitude"][0]
        lon = ds["longitude"][0]

        data = var.astype(float).values
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

            qa = ds["qa_value"][0].values
            data[qa < 0.75] = np.nan


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


        # =========================
        # PLOT
        # =========================

        last_mesh = ax.pcolormesh(
            lon,
            lat,
            data,
            cmap=cmap,
            norm=norm,
            shading="auto",
            transform=ccrs.PlateCarree()
        )

        ds.close()


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

    xmin, xmax = lon.min(), lon.max()
    ymin, ymax = lat.min(), lat.max()

    nrows, ncols = data.shape

    xres = (xmax - xmin) / float(ncols)
    yres = (ymax - ymin) / float(nrows)

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
    band.WriteArray(data)

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

    # vrt_path = year_cog_dir / f"{VAR_PRODUCT}_{date_part}_tiles.vrt"

    # # converter para 8-bit
    # subprocess.run([
    #     "gdal_translate",
    #     "-of", "VRT",
    #     "-ot", "Byte",
    #     "-scale",
    #     str(cog_path),
    #     str(vrt_path)
    # ], check=True)

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

    
    # Jurandir - Caso o de baixo funcione bem, pode remover este.
    # cmd = [
    #     "gdal2tiles.py",
    #     "-z", "0-6",
    #     "-w", "none",
    #     str(vrt_path),
    #     str(date_tiles_dir)
    # ]

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





# Versão até 11mar2026 (sem geotiff)
# import sys
# import os
# import re
# import glob

# import xarray as xr
# import numpy as np
# import matplotlib.pyplot as plt

# import cartopy.crs as ccrs
# import cartopy.feature as cfeature
# from cartopy.feature import NaturalEarthFeature

# from matplotlib.colors import Normalize

# from src.processing.colormap_loader import load_colormap
# from src.config.settings import OUTPUT_DIR


# # =========================
# # ARGUMENTOS
# # =========================

# if len(sys.argv) < 7:
#     print("\nUso:")
#     print("python read_plot_S5p.py FILE1 [FILE2 ... ou máscara*] GROUP VAR_PRODUCT TITLE LABEL EXT(png|jpeg)\n")
#     sys.exit(1)

# GROUP = sys.argv[-5]
# VAR_PRODUCT = sys.argv[-4]
# TITLE = sys.argv[-3]
# LABEL = sys.argv[-2]
# EXT = sys.argv[-1].lower().replace(".", "")
# INPUTS = sys.argv[1:-5]

# if EXT not in ["png", "jpeg", "jpg"]:
#     print("Extensão deve ser png ou jpeg")
#     sys.exit(1)


# # =========================
# # EXPANDIR MÁSCARAS
# # =========================

# FILES = []

# for item in INPUTS:
#     expanded = glob.glob(item)
#     if expanded:
#         FILES.extend(expanded)
#     else:
#         print(f"Aviso: {item} não encontrou arquivos.")

# FILES = sorted(list(set(FILES)))

# if len(FILES) == 0:
#     print("Nenhum arquivo encontrado.")
#     sys.exit(1)

# print(f"{len(FILES)} arquivo(s) encontrado(s).")


# # =========================
# # AGRUPAR POR DATA
# # =========================

# groups = {}

# for f in FILES:

#     name = os.path.basename(f)

#     m = re.search(r'_(\d{8})T', name)

#     if m:
#         date = m.group(1)
#     else:
#         date = "unknown"

#     if date not in groups:
#         groups[date] = []

#     groups[date].append(f)

# print("\nDatas encontradas:")
# for d in groups:
#     print(d, len(groups[d]), "arquivos")


# # =========================
# # DIRETÓRIO DE SAÍDA
# # =========================

# output_dir = OUTPUT_DIR / "figures" / VAR_PRODUCT
# os.makedirs(output_dir, exist_ok=True)


# # =========================
# # COLORMAP
# # =========================

# try:

#     cmap, norm, vmin, vmax, ticks = load_colormap(VAR_PRODUCT)

#     print(f"Colormap carregado para {VAR_PRODUCT}")

# except Exception:

#     print("Colormap não encontrado, usando padrão matplotlib")

#     cmap = plt.cm.viridis
#     norm = None
#     ticks = None
#     vmin = None
#     vmax = None


# # =========================
# # LOOP POR DATA
# # =========================

# for date_part, day_files in groups.items():

#     print("\nProcessando data:", date_part)

#     # -------------------------
#     # extrair ano
#     # -------------------------

#     if date_part != "unknown":
#         year = date_part[:4]
#     else:
#         year = "unknown"

#     # -------------------------
#     # diretório por ano
#     # -------------------------

#     year_dir = output_dir / year
#     os.makedirs(year_dir, exist_ok=True)

#     fig = plt.figure(figsize=(12, 8))

#     ax = plt.axes(projection=ccrs.PlateCarree())
#     ax.set_extent([-85, -30, -60, 15], crs=ccrs.PlateCarree())

#     last_mesh = None

#     for FILE in day_files:

#         print("Lendo:", FILE)

#         try:

#             ds = xr.open_dataset(
#                 FILE,
#                 group=GROUP,
#                 engine="netcdf4",
#                 decode_cf=False
#             )

#         except Exception as e:

#             print("Erro abrindo", FILE)
#             print(e)
#             continue


#         var = ds[VAR_PRODUCT][0]
#         lat = ds["latitude"][0]
#         lon = ds["longitude"][0]

#         data = var.astype(float).values
#         lat = lat.values
#         lon = lon.values


#         # =========================
#         # FILL VALUE
#         # =========================

#         fill_value = var.attrs.get("_FillValue")

#         if fill_value is not None:
#             data[data == fill_value] = np.nan


#         # =========================
#         # QA FILTER
#         # =========================

#         if "qa_value" in ds.variables:

#             qa = ds["qa_value"][0].values
#             data[qa < 0.75] = np.nan


#         # =========================
#         # FILTRO
#         # =========================

#         ###data[(data < -1) | (data > 5)] = np.nan

#         if np.all(np.isnan(data)):

#             print("Sem dados válidos.")
#             ds.close()
#             continue


#         # =========================
#         # NORMALIZE
#         # =========================

#         if norm is None:

#             vmin = np.nanmin(data)
#             vmax = np.nanmax(data)

#             norm = Normalize(vmin=vmin, vmax=vmax)


#         # =========================
#         # PLOT
#         # =========================

#         last_mesh = ax.pcolormesh(
#             lon,
#             lat,
#             data,
#             cmap=cmap,
#             norm=norm,
#             shading="auto",
#             transform=ccrs.PlateCarree()
#         )

#         ds.close()


#     if last_mesh is None:
#         print("Sem dados válidos para", date_part)
#         plt.close()
#         continue


#     # =========================
#     # COLORBAR
#     # =========================

#     cbar = plt.colorbar(last_mesh, ax=ax, orientation="vertical", pad=0.02)
#     cbar.set_label(LABEL)

#     if ticks is not None:
#         cbar.set_ticks(ticks)
#     else:
#         cbar.set_ticks(np.linspace(vmin, vmax, 6))


#     # =========================
#     # MAPA
#     # =========================

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

#     plt.title(f"{TITLE} {date_part}")


#     # =========================
#     # SALVAR
#     # =========================

#     output_name = f"{VAR_PRODUCT}_{date_part}_overlay.{EXT}"

#     output_path = year_dir / output_name

#     plt.savefig(output_path, dpi=300, bbox_inches="tight")

#     print("\n[OK] Imagem salva em:")
#     print(output_path)

#     plt.close()




