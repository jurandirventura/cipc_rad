import matplotlib.pyplot as plt

from satellite.timeseries import get_satellite_series

# =========================================================
# Função para Plot dos produtos de satélite
# =========================================================
def plot_satellite_product(
    ax,
    produto,
    datas_unicas,
    lat_station,
    lon_station,
    sat_config,
    delta
):

    sat_dates, sat_values = get_satellite_series(
        sat_config["index"],
        datas_unicas,
        lat_station,
        lon_station,
        delta,
        scale=sat_config["scale"]
    )

    if len(sat_dates) == 0:
        return

    ax.plot(
        sat_dates,
        sat_values,
        color=sat_config["color"],
        linestyle="--",
        linewidth=1.5,
        marker=sat_config["marker"],
        markersize=8,
        label=sat_config["label"]
    )
