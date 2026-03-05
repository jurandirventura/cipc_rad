import json
from matplotlib.colors import LinearSegmentedColormap, Normalize

from src.config.settings import CONFIG_DIR


def load_colormap(var_name):

    json_file = CONFIG_DIR / "colormaps.json"

    with open(json_file) as f:
        colormaps = json.load(f)

    # case insensitive
    key_map = {k.lower(): k for k in colormaps.keys()}

    if var_name.lower() not in key_map:
        raise ValueError(f"Colormap '{var_name}' não encontrado no JSON.")

    config = colormaps[key_map[var_name.lower()]]

    colors = config["colors"]
    vmin = config["vmin"]
    vmax = config["vmax"]
    ticks = config.get("ticks", None)

    cmap = LinearSegmentedColormap.from_list(var_name, colors)
    norm = Normalize(vmin=vmin, vmax=vmax)

    print(f"[DEBUG] JSON carregado: vmin={vmin}, vmax={vmax}")
    print(f"[DEBUG] ticks={ticks}")

    return cmap, norm, vmin, vmax, ticks

# Colormaps aceita os TICKS
# import json
# from matplotlib.colors import LinearSegmentedColormap, Normalize

# def load_colormap(var_name, json_file="colormaps.json"):

#     with open(json_file) as f:
#         colormaps = json.load(f)

#     # case insensitive
#     key_map = {k.lower(): k for k in colormaps.keys()}

#     if var_name.lower() not in key_map:
#         raise ValueError(f"Colormap '{var_name}' não encontrado no JSON.")

#     config = colormaps[key_map[var_name.lower()]]

#     colors = config["colors"]
#     vmin = config["vmin"]
#     vmax = config["vmax"]
#     ticks = config.get("ticks", None)

#     cmap = LinearSegmentedColormap.from_list(var_name, colors)
#     norm = Normalize(vmin=vmin, vmax=vmax)

#     print(f"[DEBUG] JSON carregado: vmin={vmin}, vmax={vmax}")
#     print(f"[DEBUG] ticks={ticks}")

#     return cmap, norm, vmin, vmax, ticks

