# plotting/station_plot.py

import os

import pandas as pd
import matplotlib.pyplot as plt

from plotting.colors import CORES, UNIDADES
from plotting.legends import build_legend
from plotting.plots import plot_satellite_product

from satellite.timeseries import get_satellite_series


def plot_station(
    estacao,
    sub_est,
    stations_dict,
    poluentes,
    sat_index,
    sat_config,
    data_inicio,
    data_fim,
    output_dir,
    sat_delta,
    output_pollutant,
    start_str,
    end_str
):

    print("\n===================================")
    print("PLOTANDO ESTAÇÃO:", estacao)
    print("===================================")

    if sub_est is None:
        return

    if sub_est.empty:
        print("Sem dados para estação.")
        return

    nome_estacao = sub_est["station_name"].iloc[0]

    codigo_estacao = int(estacao)

    if codigo_estacao not in stations_dict:

        print(
            f"Estação {estacao} não encontrada."
        )
        return

    st_info = stations_dict[codigo_estacao]

    lat_station = float(
        st_info["latitude"]
    )

    lon_station = float(
        st_info["longitude"]
    )

    print("LAT:", lat_station)
    print("LON:", lon_station)

    datas_plot = pd.date_range(
        data_inicio,
        data_fim - pd.Timedelta(days=1),
        freq="D"
    )

    fig, ax = plt.subplots(
        figsize=(22, 8)
    )

    axes = [ax]

    # ==================================================
    # PRIMEIRO POLUENTE
    # ==================================================

    pol0 = poluentes[0]

    sub0 = sub_est[
        sub_est["pollutant"] == pol0
    ]

    if not sub0.empty:

        ax.plot(
            sub0["datetime"],
            sub0["Valor Diário"],
            color=CORES.get(pol0, "blue"),
            label=pol0,
            linewidth=1.5,
            marker="o"
        )

        ax.set_ylabel(
            f"{pol0} ({UNIDADES.get(pol0,'')})",
            color=CORES.get(pol0, "blue"),
            fontsize=12,
            fontweight="bold"
        )

        ax.tick_params(
            axis="y",
            colors=CORES.get(pol0, "blue")
        )

        if pol0 == "O3":

            datas_unicas = (
                sub0["datetime"]
                .dt.normalize()
                .unique()
            )

            plot_satellite_product(
                ax,
                "O3",
                datas_unicas,
                lat_station,
                lon_station,
                sat_config["O3"],
                sat_delta
            )

    # ==================================================
    # DEMAIS POLUENTES
    # ==================================================

    AXIS_SPACING = 0.08

    for pol in poluentes[1:]:

        sub = sub_est[
            sub_est["pollutant"] == pol
        ]

        if sub.empty:
            continue

        ax_new = ax.twinx()

        ax_new.spines["right"].set_position(
            ("axes",
             1 + AXIS_SPACING * len(axes))
        )

        datas_unicas = (
            sub["datetime"]
            .dt.normalize()
            .unique()
        )

        if pol == "CO":

            plot_satellite_product(
                ax_new,
                "CO",
                datas_unicas,
                lat_station,
                lon_station,
                sat_config["CO"],
                sat_delta
            )

        elif pol in ["MP10", "MP25"]:

            plot_satellite_product(
                ax_new,
                "AI",
                datas_unicas,
                lat_station,
                lon_station,
                sat_config["AI"],
                sat_delta
            )

        elif pol == "NO2":

            plot_satellite_product(
                ax_new,
                "NO2",
                datas_unicas,
                lat_station,
                lon_station,
                sat_config["NO2"],
                sat_delta
            )

        elif pol == "SO2":

            plot_satellite_product(
                ax_new,
                "SO2",
                datas_unicas,
                lat_station,
                lon_station,
                sat_config["SO2"],
                sat_delta
            )

        ax_new.plot(
            sub["datetime"],
            sub["Valor Diário"],
            color=CORES.get(pol, "black"),
            label=pol,
            linewidth=1.5,
            marker="o"
        )

        ax_new.set_ylabel(
            f"{pol} ({UNIDADES.get(pol,'')})",
            color=CORES.get(pol, "black")
        )

        ax_new.tick_params(
            axis="y",
            colors=CORES.get(pol, "black")
        )

        axes.append(ax_new)

    # ==================================================
    # CH4 SATÉLITE
    # ==================================================

    sat_dates_ch4, sat_values_ch4 = (
        get_satellite_series(
            sat_index["CH4"],
            datas_plot,
            lat_station,
            lon_station,
            sat_delta,
            scale=1.0
        )
    )

    if sat_dates_ch4:

        ax_ch4 = ax.twinx()

        ax_ch4.spines["right"].set_position(
            ("axes",
             1 + AXIS_SPACING * len(axes))
        )

        ax_ch4.plot(
            sat_dates_ch4,
            sat_values_ch4,
            color="olive",
            linestyle="--",
            marker="P",
            linewidth=2,
            markersize=8,
            label="CH4_SAT"
        )

        ax_ch4.set_ylabel(
            "CH4 SAT (ppb)",
            color="olive"
        )

        ax_ch4.tick_params(
            axis="y",
            colors="olive"
        )

        axes.append(ax_ch4)

    # ==================================================
    # FINALIZAÇÃO
    # ==================================================

    plt.title(
        "Qualidade do Ar - Médias Diárias\n"
        f"Estação: {estacao} - {nome_estacao}\n"
        f"Período: {start_str} a {end_str}",
        fontsize=16,
        fontweight="bold"
    )

    ax.grid(
        True,
        linestyle="--",
        alpha=0.4
    )

    build_legend(
        ax,
        axes
    )

    output_png = os.path.join(
        output_dir,
        f"{estacao}_{output_pollutant}"
        "_timeseries_MediaDiaria_compara.png"
    )

    plt.savefig(
        output_png,
        dpi=150,
        bbox_inches="tight"
    )

    plt.close()

    print("FIGURA GERADA:", output_png)