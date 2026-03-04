# Com qa_value mas plotando apneas valores maiores que -1 
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
import cartopy.io.shapereader as shpreader
from cartopy.feature import NaturalEarthFeature

from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.colors import Normalize

from colormap_loader import load_colormap

# =========================
# PARÂMETROS
# =========================

if len(sys.argv) < 7:
    print("\nUso:")
    print("python read_plot_S5p.py FILE1 [FILE2 ... ou máscara*] GROUP VAR_PRODUCT TITLE LABEL EXT(png|jpeg)\n")
    sys.exit(1)

GROUP = sys.argv[-5]
VAR_PRODUCT = sys.argv[-4]
TITLE = sys.argv[-3]
LABEL = sys.argv[-2]
EXT = sys.argv[-1].lower()
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
# PLOT
# =========================

fig = plt.figure(figsize=(12, 8))
ax = plt.axes(projection=ccrs.PlateCarree())
ax.set_extent([-85, -30, -60, 15], crs=ccrs.PlateCarree())

last_mesh = None

for FILE in FILES:

    print(f"Lendo arquivo: {FILE}")
    ds = xr.open_dataset(FILE, group=GROUP)

    var = ds[VAR_PRODUCT][0, :, :]
    lat = ds["latitude"][0, :, :]
    lon = ds["longitude"][0, :, :]

    data = var.values.astype(float)
    lat = lat.values
    lon = lon.values

    # =========================
    # REMOVER FILLVALUE
    # =========================
    fill_value = var.attrs.get("_FillValue")

    if fill_value is not None:
        data[data == fill_value] = np.nan

    # =========================
    # APLICAR QA VALUE
    # =========================
    if "qa_value" in ds.variables:
        qa = ds["qa_value"][0, :, :].values
        
       # Descomentar a linha para considerar qa_value < 0.75 (threshold)
       ### data[qa < 0.75] = np.nan

    # # =========================
    # # MANTER APENAS VALORES >= 0
    # # =========================
    # data[data < 0] = np.nan
    #data[data < -1.0] = np.nan


    # =========================
    # MANTER APENAS VALORES > 0 ou descartar valores abaixo de 0 e acima de 0.5
    # =========================
    #data[data <= 0 ] = np.nan
    #data[(data < 0) | (data > 0.5)] = np.nan

    # Se todo o arquivo for inválido, pula
    if np.all(np.isnan(data)):
        print("Arquivo sem valores positivos válidos, pulando...")
        ds.close()
        continue        

    # UTILIZANDO ESCALA DE CORES INDEPENDENTE COM ARQUIVOS JSON
    try:
        cmap, norm, vmin, vmax, ticks = load_colormap(VAR_PRODUCT)
        print(f"Colormap carregado para {VAR_PRODUCT}")
    except Exception:
        print(f"Aviso: colormap não encontrado para {VAR_PRODUCT}")
        print("Usando escala padrão matplotlib...")
        vmin = np.nanmin(data)
        vmax = np.nanmax(data)
        cmap = plt.cm.viridis
        norm = Normalize(vmin=vmin, vmax=vmax)
        ticks = None   # ← ESSENCIAL


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


### Inserido fora do laço porque estava gerando barra de cores igual ao número de arquivos
### Se tem 4 arquivos, gera 4 barras
cbar = plt.colorbar(last_mesh, ax=ax, orientation="vertical", pad=0.02)
cbar.set_label(LABEL)

if ticks is not None:
    cbar.set_ticks(ticks)
else:
    cbar.set_ticks(np.linspace(vmin, vmax, 6))


# ax.coastlines()
# ax.add_feature(cfeature.BORDERS, linewidth=0.5)
# ax.add_feature(cfeature.LAND, facecolor="lightgray")


ax.coastlines(resolution='10m')
ax.add_feature(cfeature.BORDERS, linewidth=0.6)
ax.add_feature(cfeature.LAND, facecolor="lightgray")

# Estados / províncias (admin level 1)
states = NaturalEarthFeature(
    category='cultural',
    name='admin_1_states_provinces_lines',
    scale='10m',
    facecolor='none'
)

ax.add_feature(states, edgecolor='black', linewidth=0.4)
# mais elegante ax.add_feature(states, edgecolor='gray', linewidth=0.3, alpha=0.6)

# # =========================
# # ESTADOS / PROVÍNCIAS (Admin 1)
# # =========================

# states_shp = shpreader.natural_earth(
#     resolution='10m',
#     category='cultural',
#     name='admin_1_states_provinces_lines'
# )

# reader = shpreader.Reader(states_shp)

# for state in reader.records():
#     ax.add_geometries(
#         [state.geometry],
#         ccrs.PlateCarree(),
#         edgecolor='black',
#         facecolor='none',
#         linewidth=0.4
    
#         # edgecolor='dimgray'
#         # linewidth=0.5
#         # alpha=0.7
#     )



plt.title(TITLE)

# =========================
# DATA DO PRIMEIRO ARQUIVO
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

output_name = f"{VAR_PRODUCT}_{date_part}_{time_part}_overlay.{EXT}"
plt.savefig(output_name, dpi=300, bbox_inches="tight")

print(f"[OK] Imagem salva como: {output_name}")
plt.close()





# Com qa_value mas plotando apenas valores maiores que -1
# Pode-se alterar para outros testes 

# import sys
# import os
# import re
# import glob
# import xarray as xr
# import numpy as np
# import matplotlib.pyplot as plt
# import cartopy.crs as ccrs
# import cartopy.feature as cfeature

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
#        ### data[qa < 0.75] = np.nan

#     # # =========================
#     # # MANTER APENAS VALORES >= 0
#     # # =========================
#     # data[data < 0] = np.nan
#     #data[data < -1.0] = np.nan


#     # =========================
#     # MANTER APENAS VALORES > 0 ou descartar valores abaixo de 0 e acima de 0.5
#     # =========================
#     #data[data <= 0 ] = np.nan
#     #data[(data < 0) | (data > 0.5)] = np.nan

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


# ax.coastlines()
# ax.add_feature(cfeature.BORDERS, linewidth=0.5)
# ax.add_feature(cfeature.LAND, facecolor="lightgray")

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



    # =========================
    # ESCALA PADRÃO AOD (MODIS/CAMS)  usado depois do if np.all(np.isnan(data))...
    # =========================
    # bounds = [0.0, 0.1, 0.3, 0.5, 1.0, 5.0]

    # colors = [
    #     "#ffffcc",  # muito claro (0–0.1) Atmosfera limpa, visibilidade máxima
    #     "#ffeda0",  # amarelo (0.1–0.3)   Níveis baixo a moderados de aerossol
    #     "#feb24c",  # laranja (0.3–0.5)   níveis moderados a altos, indica haze (névoa seca ou poluição moderada)
    #     "#f03b20",  # vermelho (0.5–1.0)  Níveis muito altos de concentração de aerossóis, típicos de queimadas,
    #                   #                     poeira intensa ou poluição urbana severa.
    #     "#7f2704"   # marrom (>1.0)       O mesmo do anterior
    # ]

    ### Utilizando o Azul
    # #--------------------------------------------------------------- funciona
    # bounds = [-2, -1, -0.5, 0, 0.5, 1, 2, 5]
    # colors = [
    #     "#08306b",  # azul escuro
    #     "#2171b5",  # azul
    #     "#6baed6",  # azul claro
    # #    "#ffffcc",  # amarelo claro
    #     "#f7f7f2",  # branco - claro
    #     "#fd8d3c",  # laranja
    #     "#e31a1c",  # vermelho
    #     "#7f0000"   # marrom escuro
    # ]

    # cmap = ListedColormap(colors)
    # norm = BoundaryNorm(bounds, cmap.N)

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
    # #--------------------------------------------------------------- funciona


 # # # Utilizando uma escala Absorbing aerosol index (354/388 nm)
    # Usado depois de if np.all(np.isnan(data))....
    # # # TROPOMI - KNM/ESA
    # # COLORMAP PERSONALIZADA (igual à imagem) KNM/ESA
    # # ==================================================================
    # colors = [
    #     "#dddddd",  # cinza claro (~1.0)
    #     "#d7b5d8",  # rosa/lilás
    #     "#b2abd2",  # roxo claro
    #     "#80b1d3",  # azul
    #     "#66c2a5",  # ciano
    #     "#4daf4a",  # verde
    #     "#a6d854",  # verde claro
    #     "#ffff33",  # amarelo
    #     "#fdae61",  # laranja
    #     "#ff7f00"   # laranja forte (~3.0)
    # ]

    # cmap = LinearSegmentedColormap.from_list("ai_custom", colors, N=256)
    # norm = Normalize(vmin=1.0, vmax=3.0)

    # last_mesh = ax.pcolormesh(
    #     lon,
    #     lat,
    #     data,
    #     cmap=cmap,
    #     norm=norm,
    #     shading="auto",
    #     transform=ccrs.PlateCarree()
    # )

    # cbar = plt.colorbar(
    #     last_mesh,
    #     ax=ax,
    #     orientation="horizontal",
    #     pad=0.05,
    #     extend="max"
    # )

    # cbar.set_label(LABEL)
    # cbar.set_ticks([1.0, 1.5, 2.0, 2.5, 3.0])
    # # ==================================================================