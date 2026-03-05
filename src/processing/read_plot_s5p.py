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
# DIRETÓRIO DE SAÍDA
# =========================

output_dir = OUTPUT_DIR / "figures" / VAR_PRODUCT
os.makedirs(output_dir, exist_ok=True)


# =========================
# COLORMAP (carrega 1 vez)
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
# FIGURA
# =========================

fig = plt.figure(figsize=(12, 8))

ax = plt.axes(projection=ccrs.PlateCarree())
ax.set_extent([-85, -30, -60, 15], crs=ccrs.PlateCarree())

last_mesh = None


# =========================
# LOOP DOS ARQUIVOS
# =========================

for FILE in FILES:

    print(f"Lendo: {FILE}")

    try:

        ds = xr.open_dataset(
            FILE,
            group=GROUP,
            engine="netcdf4",
            decode_cf=False
        )

    except Exception as e:

        print(f"Erro abrindo {FILE}")
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

    data[(data < -1) | (data > 0.5)] = np.nan

    if np.all(np.isnan(data)):

        print("Sem dados válidos.")
        ds.close()
        continue


    # =========================
    # NORMALIZE (fallback)
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

plt.title(TITLE)


# =========================
# DATA
# =========================

filename = os.path.basename(FILES[0])

match = re.search(r'(\d{8}T\d{6})', filename)

if match:

    datetime_str = match.group(1)
    date_part = datetime_str[:8]
    time_part = datetime_str[9:]

else:

    date_part = "composite"
    time_part = ""


# =========================
# SALVAR
# =========================

output_name = f"{VAR_PRODUCT}_{date_part}_{time_part}_overlay.{EXT}"

output_path = output_dir / output_name

plt.savefig(output_path, dpi=300, bbox_inches="tight")

print("\n[OK] Imagem salva em:")
print(output_path)

plt.close()




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

# # imports do projeto
# from src.processing.colormap_loader import load_colormap
# from src.config.settings import OUTPUT_DIR

# # =========================
# # PARÂMETROS
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
# # DIRETÓRIO DE SAÍDA
# # =========================

# output_dir = OUTPUT_DIR / "figures" / VAR_PRODUCT
# os.makedirs(output_dir, exist_ok=True)

# # =========================
# # PLOT
# # =========================

# fig = plt.figure(figsize=(12, 8))
# ax = plt.axes(projection=ccrs.PlateCarree())
# ax.set_extent([-85, -30, -60, 15], crs=ccrs.PlateCarree())

# last_mesh = None

# for FILE in FILES:

#     print(f"Lendo arquivo: {FILE}")

#     ### remover ds = xr.open_dataset(FILE, group=GROUP)
#     ds = xr.open_dataset(FILE, group=GROUP, engine="netcdf4")

#     var = ds[VAR_PRODUCT][0, :, :]
#     lat = ds["latitude"][0, :, :]
#     lon = ds["longitude"][0, :, :]

#     data = var.values.astype(float)
#     lat = lat.values
#     lon = lon.values

#     # =========================
#     # REMOVER FILLVALUE
#     # =========================

#     fill_value = var.attrs.get("_FillValue")

#     if fill_value is not None:
#         data[data == fill_value] = np.nan

#     # =========================
#     # APLICAR QA VALUE
#     # =========================

#     if "qa_value" in ds.variables:

#         qa = ds["qa_value"][0, :, :].values

#         # threshold recomendado Sentinel-5P
#         data[qa < 0.75] = np.nan

#     # =========================
#     # FILTRO DE VALORES
#     # =========================

#     data[(data < -1) | (data > 0.5)] = np.nan

#     if np.all(np.isnan(data)):
#         print("Arquivo sem valores válidos, pulando...")
#         ds.close()
#         continue

#     # =========================
#     # COLORMAP
#     # =========================

#     try:
#         cmap, norm, vmin, vmax, ticks = load_colormap(VAR_PRODUCT)
#         print(f"Colormap carregado para {VAR_PRODUCT}")

#     except Exception:

#         print(f"Aviso: colormap não encontrado para {VAR_PRODUCT}")
#         print("Usando escala padrão matplotlib...")

#         vmin = np.nanmin(data)
#         vmax = np.nanmax(data)

#         cmap = plt.cm.viridis
#         norm = Normalize(vmin=vmin, vmax=vmax)
#         ticks = None

#     last_mesh = ax.pcolormesh(
#         lon,
#         lat,
#         data,
#         cmap=cmap,
#         norm=norm,
#         shading="auto",
#         transform=ccrs.PlateCarree()
#     )

#     ds.close()

# # =========================
# # COLORBAR
# # =========================

# cbar = plt.colorbar(last_mesh, ax=ax, orientation="vertical", pad=0.02)
# cbar.set_label(LABEL)

# if ticks is not None:
#     cbar.set_ticks(ticks)
# else:
#     cbar.set_ticks(np.linspace(vmin, vmax, 6))

# # =========================
# # MAPA
# # =========================

# ax.coastlines(resolution='10m')
# ax.add_feature(cfeature.BORDERS, linewidth=0.6)
# ax.add_feature(cfeature.LAND, facecolor="lightgray")

# states = NaturalEarthFeature(
#     category='cultural',
#     name='admin_1_states_provinces_lines',
#     scale='10m',
#     facecolor='none'
# )

# ax.add_feature(states, edgecolor='black', linewidth=0.4)

# plt.title(TITLE)

# # =========================
# # DATA DO PRIMEIRO ARQUIVO
# # =========================

# filename = os.path.basename(FILES[0])

# match = re.search(r'(\d{8}T\d{6})', filename)

# if match:

#     datetime_str = match.group(1)
#     date_part = datetime_str[:8]
#     time_part = datetime_str[9:]

# else:

#     date_part = "composite"
#     time_part = ""

# output_name = f"{VAR_PRODUCT}_{date_part}_{time_part}_overlay.{EXT}"

# output_path = output_dir / output_name

# plt.savefig(output_path, dpi=300, bbox_inches="tight")

# print(f"[OK] Imagem salva em:")
# print(output_path)

# plt.close()






# # Com qa_value mas plotando apneas valores maiores que -1 
# # Inclui também as subdivisões de mapa para Estados...

# import sys
# import os
# import re
# import glob
# import xarray as xr
# import numpy as np
# import matplotlib.pyplot as plt
# import cartopy.crs as ccrs
# import cartopy.feature as cfeature
# import cartopy.io.shapereader as shpreader
# from cartopy.feature import NaturalEarthFeature

# from matplotlib.colors import ListedColormap, BoundaryNorm
# from matplotlib.colors import LinearSegmentedColormap, Normalize
# from matplotlib.colors import Normalize

# from colormap_loader import load_colormap

# # =========================
# # PARÂMETROS
# # =========================

# if len(sys.argv) < 7:
#     print("\nUso:")
#     print("python read_plot_S5p.py FILE1 [FILE2 ... ou máscara*] GROUP VAR_PRODUCT TITLE LABEL EXT(png|jpeg)\n")
#     sys.exit(1)

# GROUP = sys.argv[-5]
# VAR_PRODUCT = sys.argv[-4]
# TITLE = sys.argv[-3]
# LABEL = sys.argv[-2]
# EXT = sys.argv[-1].lower()
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
# # PLOT
# # =========================

# fig = plt.figure(figsize=(12, 8))
# ax = plt.axes(projection=ccrs.PlateCarree())
# ax.set_extent([-85, -30, -60, 15], crs=ccrs.PlateCarree())

# last_mesh = None

# for FILE in FILES:

#     print(f"Lendo arquivo: {FILE}")
#     ds = xr.open_dataset(FILE, group=GROUP)

#     var = ds[VAR_PRODUCT][0, :, :]
#     lat = ds["latitude"][0, :, :]
#     lon = ds["longitude"][0, :, :]

#     data = var.values.astype(float)
#     lat = lat.values
#     lon = lon.values

#     # =========================
#     # REMOVER FILLVALUE
#     # =========================
#     fill_value = var.attrs.get("_FillValue")

#     if fill_value is not None:
#         data[data == fill_value] = np.nan

#     # =========================
#     # APLICAR QA VALUE
#     # =========================
#     if "qa_value" in ds.variables:
#         qa = ds["qa_value"][0, :, :].values
        
#        # Descomentar a linha para considerar qa_value < 0.75 (threshold)
#        data[qa < 0.75] = np.nan

#     # =========================
#     # MANTER APENAS VALORES > 0 ou descartar valores abaixo de 0 e acima de 0.5
#     # =========================
#     data[(data < -1) | (data > 0.5)] = np.nan

#     # Se todo o arquivo for inválido, pula
#     if np.all(np.isnan(data)):
#         print("Arquivo sem valores positivos válidos, pulando...")
#         ds.close()
#         continue        

#     # UTILIZANDO ESCALA DE CORES INDEPENDENTE COM ARQUIVOS JSON
#     try:
#         cmap, norm, vmin, vmax, ticks = load_colormap(VAR_PRODUCT)
#         print(f"Colormap carregado para {VAR_PRODUCT}")
#     except Exception:
#         print(f"Aviso: colormap não encontrado para {VAR_PRODUCT}")
#         print("Usando escala padrão matplotlib...")
#         vmin = np.nanmin(data)
#         vmax = np.nanmax(data)
#         cmap = plt.cm.viridis
#         norm = Normalize(vmin=vmin, vmax=vmax)
#         ticks = None   # ← ESSENCIAL


#     last_mesh = ax.pcolormesh(
#         lon,
#         lat,
#         data,
#         cmap=cmap,
#         norm=norm,
#         shading="auto",
#         transform=ccrs.PlateCarree()
#     )

#     ds.close()


# ### Inserido fora do laço porque estava gerando barra de cores igual ao número de arquivos
# ### Se tem 4 arquivos, gera 4 barras
# cbar = plt.colorbar(last_mesh, ax=ax, orientation="vertical", pad=0.02)
# cbar.set_label(LABEL)

# if ticks is not None:
#     cbar.set_ticks(ticks)
# else:
#     cbar.set_ticks(np.linspace(vmin, vmax, 6))

# ax.coastlines(resolution='10m')
# ax.add_feature(cfeature.BORDERS, linewidth=0.6)
# ax.add_feature(cfeature.LAND, facecolor="lightgray")

# # Estados / províncias (admin level 1)
# states = NaturalEarthFeature(
#     category='cultural',
#     name='admin_1_states_provinces_lines',
#     scale='10m',
#     facecolor='none'
# )

# ax.add_feature(states, edgecolor='black', linewidth=0.4)

# plt.title(TITLE)

# # =========================
# # DATA DO PRIMEIRO ARQUIVO
# # =========================

# filename = os.path.basename(FILES[0])
# match = re.search(r'(\d{8}T\d{6})', filename)

# if match:
#     datetime_str = match.group(1)
#     date_part = datetime_str[:8]
#     time_part = datetime_str[9:]
# else:
#     date_part = "composite"
#     time_part = ""

# output_name = f"{VAR_PRODUCT}_{date_part}_{time_part}_overlay.{EXT}"
# plt.savefig(output_name, dpi=300, bbox_inches="tight")

# print(f"[OK] Imagem salva como: {output_name}")
# plt.close()
