
# Plota dados da CETESB - Médias Diárias 
# O3, MP2.5, MP10, CO, NO2, SO2
# e dados do satélite Sentinel-5P para os gases 
# O3, AI, CO, NO2, SO2 e CH4   

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import glob
import argparse

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import rasterio
import re

# Import das funções
from satellite.indexer import build_satellite_index
from satellite.timeseries import get_satellite_series
from satellite.raster_reader import get_satellite_mean

from plotting.plots import plot_satellite_product

from plotting.colors import CORES, UNIDADES

from config import create_sat_config

from cetesb.stations import load_stations

from plotting.legends import build_legend

from cetesb.csv_reader import load_cetesb_data

"""
Plota séries temporais CETESB
(Médias Diárias)

+ Dados de satélite GeoTIFF
(O3 inicialmente)

=========================================================
EXEMPLO
=========================================================

python plot_cetesb_timeseries_mediaDiaria.py \
--input csvs \
--stations-file ../cipc_data/cetesb/lista_estacoes.json \
--station 58 \
--pollutant all \
--start 15/08/2024 \
--end 25/08/2024 \
--sat-dir /home/jurandir/cipc_output/geotiff/ozone_total_vertical_column/2024

*** Incluso O3, CO, AI-354:388
python src/processing/plot_sentinel_cetesb.py \
--input ./csvs \
--stations-file ../cipc_data/cetesb/lista_estacoes.json \
--station 288 \
--pollutant all \
--start 15/08/2024 \
--end 25/08/2024 \
--sat-dir-o3 /home/jurandir/cipc_output/geotiff/ozone_total_vertical_column/2024 \
--sat-dir-co /home/jurandir/cipc_output/geotiff/carbonmonoxide_total_column/2024 \
--sat-dir-ai /home/jurandir/cipc_output/geotiff/aerosol_index_354_388/2024 \
--output /home/jurandir/cipc_output/figures/cetesb/compara_sentinel5p_cetesb/

Sat O3, CO, AI, NO2, SO2
python src/processing/plot_sentinel_cetesb.py \
--input ./csvs \
--stations-file ../cipc_data/cetesb/lista_estacoes.json \
--station all \
--pollutant all \
--start 15/08/2024 \
--end 25/08/2024 \
--sat-dir-o3 /home/jurandir/cipc_output/geotiff/ozone_total_vertical_column/2024 \
--sat-dir-co /home/jurandir/cipc_output/geotiff/carbonmonoxide_total_column/2024 \
--sat-dir-ai /home/jurandir/cipc_output/geotiff/aerosol_index_354_388/2024 \
--sat-dir-no2 /home/jurandir/cipc_output/geotiff/nitrogendioxide_tropospheric_column/2024 \
--sat-dir-so2 /home/jurandir/cipc_output/geotiff/sulfurdioxide_total_vertical_column/2024  \
--sat-dir-ch4 /home/jurandir/cipc_output/geotiff/methane_mixing_ratio/2024 \
--output /home/jurandir/cipc_output/figures/cetesb/compara_sentinel5p_cetesb/

"""

# =========================================================
# ARGUMENTOS
# =========================================================

parser = argparse.ArgumentParser()

parser.add_argument(
    "--input",
    required=True,
    help="Diretório dos CSVs"
)

parser.add_argument(
    "--stations-file",
    required=True,
    help="Arquivo JSON lista_estacoes.json"
)

parser.add_argument(
    "--station",
    required=True,
    help="Código estação ou all"
)

parser.add_argument(
    "--pollutant",
    required=True,
    help="Poluente ou all"
)

parser.add_argument(
    "--start",
    required=True,
    help="Data inicial dd/mm/yyyy"
)

parser.add_argument(
    "--end",
    required=True,
    help="Data final dd/mm/yyyy"
)

parser.add_argument(
    "--sat-dir-o3",
    default="/home/jurandir/cipc_output/geotiff/ozone_total_vertical_column/2024",
    help="Diretório GeoTIFF O3 satélite"
)

parser.add_argument(
    "--sat-dir-co",
    default="/home/jurandir/cipc_output/geotiff/carbonmonoxide_total_column/2024",
    help="Diretório GeoTIFF CO satélite"
)

parser.add_argument(
    "--sat-dir-ai",
    default="/home/jurandir/cipc_output/geotiff/aerosol_index_354_388/2024",
    help="Diretório GeoTIFF Aerosol Index satélite"
)

parser.add_argument(
    "--sat-dir-no2",
    default="/home/jurandir/cipc_output/geotiff/nitrogendioxide_tropospheric_column/2024",
    help="Diretório GeoTIFF NO2 satélite"
)

parser.add_argument(
    "--sat-dir-so2",
    default="/home/jurandir/cipc_output/geotiff/sulfurdioxide_total_vertical_column/2024",
    help="Diretório GeoTIFF SO2 satélite"
)

parser.add_argument(
    "--sat-dir-ch4",
    default="/home/jurandir/cipc_output/geotiff/methane_mixing_ratio/2024",
    help="Diretório GeoTIFF CH4 satélite"
)

parser.add_argument(
    "--sat-delta",
    type=float,
    default=0.5,
    help="Janela espacial em graus"
)

parser.add_argument(
    "--output",
    default="../cipc_output/figures/cetesb",
    help="Diretório saída"
)

args = parser.parse_args()


INPUT_DIR = args.input
OUTPUT_DIR = args.output

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

#==========================================================
# Índice para função satélite
#==========================================================
SAT_INDEX = {
    "O3": build_satellite_index(args.sat_dir_o3),
    "CO": build_satellite_index(args.sat_dir_co),
    "AI": build_satellite_index(args.sat_dir_ai),
    "NO2": build_satellite_index(args.sat_dir_no2),
    "SO2": build_satellite_index(args.sat_dir_so2),
    "CH4": build_satellite_index(args.sat_dir_ch4)
}


# =========================================================
# POLUENTES
# =========================================================

POLUENTES_VALIDOS = [
    "O3",
    "MP25",
    "MP10",
    "NO2",
    "SO2",
    "CO",
#    "NO",
#    "NOx"
]

if args.pollutant.lower() == "all":

    poluentes = POLUENTES_VALIDOS

else:

    poluentes = [args.pollutant]

# =========================================================
# DATAS
# =========================================================

DATA_INICIO = pd.to_datetime(
    args.start,
    dayfirst=True
)

DATA_FIM = (
    pd.to_datetime(
        args.end,
        dayfirst=True
    )
    + pd.Timedelta(days=1)
)

# =========================================================
# ESTAÇÕES
# =========================================================

df_st, stations_dict = load_stations(
    args.stations_file
)

print(f"{len(stations_dict)} estações carregadas.")

if args.station.lower() == "all":

    estacoes = (
        df_st["codigo"]
        .astype(str)
        .tolist()
    )

else:

    estacoes = [str(args.station)]


print("Estações solicitadas:", estacoes)

# =========================================================
# LEITURA CSVs
# =========================================================
final = load_cetesb_data(
    input_dir=INPUT_DIR,
    estacoes=estacoes,
    poluentes=poluentes,
    data_inicio=DATA_INICIO,
    data_fim=DATA_FIM
)

ESTACOES_GRUPO = {
    codigo: grupo
    for codigo, grupo in
    final.groupby("estacao_codigo")
}

# =========================================================
# CORES
# =========================================================

# CORES = {
#     "O3": "blue",
#     "CO": "red",
#     "MP10": "purple",
#     "MP25": "brown",
#     "NO2": "orange",
#     "SO2": "green",
# #    "NO": "gray",
# #    "NOx": "black"
# }

# UNIDADES = {
#     "O3": "µg/m³",
#     "NO2": "µg/m³",
#     "SO2": "µg/m³",
#     "CO": "ppm",
#     "MP10": "µg/m³",
#     "MP25": "µg/m³",
# #    "NO": "µg/m³",
# #    "NOx": "µg/m³"
# }

# =================================================
# SATÉLITE - CONFIGURAÇÃO DE CADA PRODUTO
# =================================================

SAT_CONFIG = create_sat_config(
    SAT_INDEX
)

print("\nPOLUENTES ENCONTRADOS:")
print(final["pollutant"].unique())


# =========================================================
# LOOP ESTAÇÕES
# =========================================================

for estacao in estacoes:

    print("\n===================================")
    print("PLOTANDO ESTAÇÃO:", estacao)
    print("===================================")

    # estacoes_grupo = {
    #     codigo: grupo
    #     for codigo, grupo in
    #     final.groupby("estacao_codigo")
    # }

    sub_est = ESTACOES_GRUPO.get(estacao)

    if sub_est is None:
        continue

    if sub_est.empty:

        print("Sem dados para estação.")
        continue

    nome_estacao = (
        sub_est["station_name"]
        .iloc[0]
    )

    # =====================================================
    # LAT/LON
    # =====================================================

    codigo_estacao = int(estacao)

    if codigo_estacao not in stations_dict:

        print(
            f"Estação {estacao} não encontrada em lista_estacoes.json"
        )
        continue

    st_info = stations_dict[codigo_estacao]

    lat_station = float(st_info["latitude"])
    lon_station = float(st_info["longitude"])

    print("LAT:", lat_station)
    print("LON:", lon_station)

    datas_plot = pd.date_range(
        DATA_INICIO,
        DATA_FIM - pd.Timedelta(days=1),
        freq="D"
    )

    fig, ax = plt.subplots(
        figsize=(22, 8)
    )


    axes = [ax]

    # =====================================================
    # PRIMEIRO POLUENTE
    # =====================================================

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

        # =====================================================
        # CONVERSÃO SATÉLITE - Não utilizado
        # =====================================================
        # ALTURA_CAMADA = 35000.0  # metros
        # MASSA_MOLAR = {
        #     "O3": 48.0,
        #     "CO": 28.01
        # }


        # =================================================
        # SATÉLITE O3
        # =================================================
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
                SAT_CONFIG["O3"],
                args.sat_delta
            )


    # =====================================================
    # DEMAIS POLUENTES
    # =====================================================

    AXIS_SPACING = 0.08

    for pol in poluentes[1:]:


        sub = sub_est[
            sub_est["pollutant"] == pol
        ]

        if sub.empty:
            continue

        num_axes = len(axes)

        ax_new = ax.twinx()

        ax_new.spines["right"].set_position(
            ("axes", 1 + AXIS_SPACING * num_axes)
        )

        sub = sub_est[
            sub_est["pollutant"] == pol
        ]

        if sub.empty:
            continue

        # =================================================
        # SATÉLITE CO
        # =================================================
        if pol == "CO":

            datas_unicas = (
                sub["datetime"]
                .dt.normalize()
                .unique()
            )

            plot_satellite_product(
                ax_new,
                "CO",
                datas_unicas,
                lat_station,
                lon_station,
                SAT_CONFIG["CO"],
                args.sat_delta
            )

        if pol in ["MP10", "MP25"]:

            datas_unicas = (
                sub["datetime"]
                .dt.normalize()
                .unique()
            )

            plot_satellite_product(
                ax_new,
                "AI",
                datas_unicas,
                lat_station,
                lon_station,
                SAT_CONFIG["AI"],
                args.sat_delta
            )


        # =================================================
        # SATÉLITE NO2
        # =================================================
        if pol == "NO2":

            datas_unicas = (
                sub["datetime"]
                .dt.normalize()
                .unique()
            )

            plot_satellite_product(
                ax_new,
                "NO2",
                datas_unicas,
                lat_station,
                lon_station,
                SAT_CONFIG["NO2"],
                args.sat_delta
            )        

        # =================================================
        # SATÉLITE SO2
        # =================================================
        if pol == "SO2":

            datas_unicas = (
                sub["datetime"]
                .dt.normalize()
                .unique()
            )

            plot_satellite_product(
                ax_new,
                "SO2",
                datas_unicas,
                lat_station,
                lon_station,
                SAT_CONFIG["SO2"],
                args.sat_delta
            )

        # =================================================
        # ESTAÇÃO
        # =================================================

        ax_new.plot(
            sub["datetime"],
            sub["Valor Diário"],
            color=CORES.get(pol, "black"),
            label=pol,
            linewidth=1.5,
            marker="o"
        )

        # =================================================
        # CO SATÉLITE
        # =================================================
        ax_new.set_ylabel(
            f"{pol} ({UNIDADES.get(pol,'')})",
            color=CORES.get(pol, "black"),
            fontsize=12,
            fontweight="bold"
        )

        ax_new.tick_params(
            axis="y",
            colors=CORES.get(pol, "black")
        )

        axes.append(ax_new)


    # =====================================================
    # CH4 SATÉLITE SEM CETESB
    # =====================================================

    datas_unicas = final["datetime"].dt.normalize().unique()

    sat_dates_ch4, sat_values_ch4 = get_satellite_series(
        SAT_INDEX["CH4"],
        datas_plot,
        lat_station,
        lon_station,
        args.sat_delta,
        scale=1.0
    )

    if sat_dates_ch4:

        ax_ch4 = ax.twinx()

        ax_ch4.spines["right"].set_position(
            ("axes", 1 + AXIS_SPACING * len(axes))
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


    # =====================================================
    # TÍTULO
    # =====================================================

    plt.title(
        "Qualidade do Ar - Médias Diárias\n"
        f"Estação: {estacao} - {nome_estacao}\n"
        f"Período: {args.start} a {args.end}",
        fontsize=16,
        fontweight="bold"
    )

    # =====================================================
    # GRID
    # =====================================================

    ax.grid(
        True,
        linestyle="--",
        alpha=0.4
    )


    # =====================================================
    # LEGENDA
    # =====================================================

    build_legend(
        ax,
        axes
    )


    # =====================================================
    # SAVE
    # =====================================================

    output_png = os.path.join(
        OUTPUT_DIR,
        f"{estacao}_{args.pollutant}_timeseries_MediaDiaria_compara.png"
    )

    plt.savefig(
        output_png,
        dpi=150,
        bbox_inches="tight"
    )

    print("\n===================================")
    print("FIGURA GERADA")
    print(output_png)
    print("===================================")

    plt.close()






# # Versão que funcionou bem com os módulos de satélite
# # Plota dados da CETESB - Médias Diárias 
# # O3, MP2.5, MP10, CO, NO2, SO2
# # e dados do satélite Sentinel-5P para os gases 
# # O3, AI, CO, NO2, SO2 e CH4   

# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-
# import os
# import glob
# import argparse

# import numpy as np
# import pandas as pd
# import matplotlib.pyplot as plt
# import rasterio
# import re

# # Import das funções
# from satellite.indexer import build_satellite_index
# from satellite.timeseries import get_satellite_series
# from satellite.raster_reader import get_satellite_mean

# from plotting.plots import plot_satellite_product

# from plotting.colors import CORES, UNIDADES

# """
# Plota séries temporais CETESB
# (Médias Diárias)

# + Dados de satélite GeoTIFF
# (O3 inicialmente)

# =========================================================
# EXEMPLO
# =========================================================

# python plot_cetesb_timeseries_mediaDiaria.py \
# --input csvs \
# --stations-file ../cipc_data/cetesb/lista_estacoes.json \
# --station 58 \
# --pollutant all \
# --start 15/08/2024 \
# --end 25/08/2024 \
# --sat-dir /home/jurandir/cipc_output/geotiff/ozone_total_vertical_column/2024

# *** Incluso O3, CO, AI-354:388
# python src/processing/plot_sentinel_cetesb.py \
# --input ./csvs \
# --stations-file ../cipc_data/cetesb/lista_estacoes.json \
# --station 288 \
# --pollutant all \
# --start 15/08/2024 \
# --end 25/08/2024 \
# --sat-dir-o3 /home/jurandir/cipc_output/geotiff/ozone_total_vertical_column/2024 \
# --sat-dir-co /home/jurandir/cipc_output/geotiff/carbonmonoxide_total_column/2024 \
# --sat-dir-ai /home/jurandir/cipc_output/geotiff/aerosol_index_354_388/2024 \
# --output /home/jurandir/cipc_output/figures/cetesb/compara_sentinel5p_cetesb/

# Sat O3, CO, AI, NO2, SO2
# python src/processing/plot_sentinel_cetesb.py \
# --input ./csvs \
# --stations-file ../cipc_data/cetesb/lista_estacoes.json \
# --station all \
# --pollutant all \
# --start 15/08/2024 \
# --end 25/08/2024 \
# --sat-dir-o3 /home/jurandir/cipc_output/geotiff/ozone_total_vertical_column/2024 \
# --sat-dir-co /home/jurandir/cipc_output/geotiff/carbonmonoxide_total_column/2024 \
# --sat-dir-ai /home/jurandir/cipc_output/geotiff/aerosol_index_354_388/2024 \
# --sat-dir-no2 /home/jurandir/cipc_output/geotiff/nitrogendioxide_tropospheric_column/2024 \
# --sat-dir-so2 /home/jurandir/cipc_output/geotiff/sulfurdioxide_total_vertical_column/2024  \
# --sat-dir-ch4 /home/jurandir/cipc_output/geotiff/methane_mixing_ratio/2024 \
# --output /home/jurandir/cipc_output/figures/cetesb/compara_sentinel5p_cetesb/

# """

# # =========================================================
# # ARGUMENTOS
# # =========================================================

# parser = argparse.ArgumentParser()

# parser.add_argument(
#     "--input",
#     required=True,
#     help="Diretório dos CSVs"
# )

# parser.add_argument(
#     "--stations-file",
#     required=True,
#     help="Arquivo JSON lista_estacoes.json"
# )

# parser.add_argument(
#     "--station",
#     required=True,
#     help="Código estação ou all"
# )

# parser.add_argument(
#     "--pollutant",
#     required=True,
#     help="Poluente ou all"
# )

# parser.add_argument(
#     "--start",
#     required=True,
#     help="Data inicial dd/mm/yyyy"
# )

# parser.add_argument(
#     "--end",
#     required=True,
#     help="Data final dd/mm/yyyy"
# )

# parser.add_argument(
#     "--sat-dir-o3",
#     default="/home/jurandir/cipc_output/geotiff/ozone_total_vertical_column/2024",
#     help="Diretório GeoTIFF O3 satélite"
# )

# parser.add_argument(
#     "--sat-dir-co",
#     default="/home/jurandir/cipc_output/geotiff/carbonmonoxide_total_column/2024",
#     help="Diretório GeoTIFF CO satélite"
# )

# parser.add_argument(
#     "--sat-dir-ai",
#     default="/home/jurandir/cipc_output/geotiff/aerosol_index_354_388/2024",
#     help="Diretório GeoTIFF Aerosol Index satélite"
# )

# parser.add_argument(
#     "--sat-dir-no2",
#     default="/home/jurandir/cipc_output/geotiff/nitrogendioxide_tropospheric_column/2024",
#     help="Diretório GeoTIFF NO2 satélite"
# )

# parser.add_argument(
#     "--sat-dir-so2",
#     default="/home/jurandir/cipc_output/geotiff/sulfurdioxide_total_vertical_column/2024",
#     help="Diretório GeoTIFF SO2 satélite"
# )

# parser.add_argument(
#     "--sat-dir-ch4",
#     default="/home/jurandir/cipc_output/geotiff/methane_mixing_ratio/2024",
#     help="Diretório GeoTIFF CH4 satélite"
# )

# parser.add_argument(
#     "--sat-delta",
#     type=float,
#     default=0.5,
#     help="Janela espacial em graus"
# )

# parser.add_argument(
#     "--output",
#     default="../cipc_output/figures/cetesb",
#     help="Diretório saída"
# )

# args = parser.parse_args()


# INPUT_DIR = args.input
# OUTPUT_DIR = args.output

# os.makedirs(
#     OUTPUT_DIR,
#     exist_ok=True
# )

# #==========================================================
# # Índice para função satélite
# #==========================================================
# SAT_INDEX = {
#     "O3": build_satellite_index(args.sat_dir_o3),
#     "CO": build_satellite_index(args.sat_dir_co),
#     "AI": build_satellite_index(args.sat_dir_ai),
#     "NO2": build_satellite_index(args.sat_dir_no2),
#     "SO2": build_satellite_index(args.sat_dir_so2),
#     "CH4": build_satellite_index(args.sat_dir_ch4)
# }


# # =========================================================
# # POLUENTES
# # =========================================================

# POLUENTES_VALIDOS = [
#     "O3",
#     "MP25",
#     "MP10",
#     "NO2",
#     "SO2",
#     "CO",
# #    "NO",
# #    "NOx"
# ]

# if args.pollutant.lower() == "all":

#     poluentes = POLUENTES_VALIDOS

# else:

#     poluentes = [args.pollutant]

# # =========================================================
# # DATAS
# # =========================================================

# DATA_INICIO = pd.to_datetime(
#     args.start,
#     dayfirst=True
# )

# DATA_FIM = (
#     pd.to_datetime(
#         args.end,
#         dayfirst=True
#     )
#     + pd.Timedelta(days=1)
# )

# # =========================================================
# # ESTAÇÕES
# # =========================================================

# df_st = pd.read_json(
#     args.stations_file
# )

# # =========================================================
# # Índice das estações
# # =========================================================

# df_st["codigo"] = pd.to_numeric(
#     df_st["codigo"],
#     errors="coerce"
# )

# stations_dict = (
#     df_st
#     .set_index("codigo")
#     .to_dict("index")
# )

# print(f"{len(stations_dict)} estações carregadas.")

# if args.station.lower() == "all":

#     estacoes = (
#         df_st["codigo"]
#         .astype(str)
#         .tolist()
#     )

# else:

#     estacoes = [str(args.station)]


# print("Estações solicitadas:", estacoes)

# # =========================================================
# # LEITURA CSVs
# # =========================================================

# todos = []

# for estacao in estacoes:

#     for poluente in poluentes:

#         pattern = os.path.join(
#             INPUT_DIR,
#             f"{estacao}_{poluente}_*.csv"
#         )

#         arquivos = glob.glob(pattern)

#         if len(arquivos) == 0:

#             print(f"Nenhum arquivo encontrado: {pattern}")
#             continue

#         for arquivo in arquivos:

#             print(f"Lendo: {arquivo}")

#             try:

#                 df = pd.read_csv(
#                     arquivo,
#                     sep=";"
#                 )

#             except Exception as e:

#                 print("Erro leitura:", e)
#                 continue

#             df.columns = [
#                 str(c).strip()
#                 for c in df.columns
#             ]

#             if "Data" not in df.columns:
#                 continue

#             df = df[
#                 df["Data"].notna()
#             ]

#             if df.empty:
#                 continue

#             if "Hora" not in df.columns:
#                 df["Hora"] = "00:00"

#             df["Hora"] = (
#                 df["Hora"]
#                 .astype(str)
#                 .str.strip()
#             )

#             df.loc[
#                 (df["Hora"] == "")
#                 |
#                 (df["Hora"].str.lower() == "nan"),
#                 "Hora"
#             ] = "00:00"

#             df["Hora"] = df["Hora"].str[:5]

#             mask_24 = (
#                 df["Hora"] == "24:00"
#             )

#             df.loc[
#                 mask_24,
#                 "Hora"
#             ] = "00:00"

#             df["datetime"] = pd.to_datetime(
#                 df["Data"].astype(str)
#                 + " "
#                 + df["Hora"].astype(str),
#                 format="%d/%m/%Y %H:%M",
#                 errors="coerce"
#             )

#             df.loc[
#                 mask_24,
#                 "datetime"
#             ] = (
#                 df.loc[
#                     mask_24,
#                     "datetime"
#                 ]
#                 + pd.Timedelta(days=1)
#             )

#             df = df[
#                 df["datetime"].notna()
#             ]

#             if df.empty:
#                 continue

#             df = df[
#                 (df["datetime"] >= DATA_INICIO)
#                 &
#                 (df["datetime"] <= DATA_FIM)
#             ]

#             if df.empty:
#                 continue

#             if "Valor Diário" not in df.columns:
#                 continue

#             df["Valor Diário"] = (
#                 df["Valor Diário"]
#                 .astype(str)
#                 .str.replace(",", ".", regex=False)
#             )

#             df["Valor Diário"] = pd.to_numeric(
#                 df["Valor Diário"],
#                 errors="coerce"
#             )

#             df = df[
#                 df["Valor Diário"].notna()
#             ]

#             if df.empty:
#                 continue

#             if "estacao_nome" in df.columns:

#                 nomes_validos = (
#                     df["estacao_nome"]
#                     .dropna()
#                 )

#                 if len(nomes_validos) > 0:

#                     nome_est = nomes_validos.iloc[0]

#                 else:

#                     nome_est = str(estacao)

#             else:

#                 nome_est = str(estacao)

#             df["station_name"] = nome_est

#             if "poluente" in df.columns:

#                 df["pollutant"] = (
#                     df["poluente"]
#                     .astype(str)
#                     .str.strip()
#                     .str.upper()
#                 )

#                 df["pollutant"] = (
#                     df["pollutant"]
#                     .replace({
#                         "MP2.5": "MP25",
#                         "MP2,5": "MP25",
#                         "PM25": "MP25",
#                         "PM10": "MP10",
# #                        "NOX": "NOx"
#                     })
#                 )

#             else:

#                 df["pollutant"] = poluente

#             todos.append(df)

# # =========================================================
# # CONCATENA
# # =========================================================

# if len(todos) == 0:

#     raise Exception(
#         "Nenhum dado encontrado."
#     )

# final = pd.concat(
#     todos,
#     ignore_index=True
# )

# final["estacao_codigo"] = (
#     final["estacao_codigo"]
#     .astype(str)
# )        

# ESTACOES_GRUPO = {
#     codigo: grupo
#     for codigo, grupo in
#     final.groupby("estacao_codigo")
# }

# # =========================================================
# # CORES
# # =========================================================

# # CORES = {
# #     "O3": "blue",
# #     "CO": "red",
# #     "MP10": "purple",
# #     "MP25": "brown",
# #     "NO2": "orange",
# #     "SO2": "green",
# # #    "NO": "gray",
# # #    "NOx": "black"
# # }

# # UNIDADES = {
# #     "O3": "µg/m³",
# #     "NO2": "µg/m³",
# #     "SO2": "µg/m³",
# #     "CO": "ppm",
# #     "MP10": "µg/m³",
# #     "MP25": "µg/m³",
# # #    "NO": "µg/m³",
# # #    "NOx": "µg/m³"
# # }

# # =================================================
# # SATÉLITE - CONFIGURAÇÃO DE CADA PRODUTO
# # =================================================

# SAT_CONFIG = {

#     "O3": {
#         "index": SAT_INDEX["O3"],
#         "scale": 1000.0,
#         "color": "cyan",
#         "marker": "*",
#         "label": "O3_SAT*1000"
#     },

#     "CO": {
#         "index": SAT_INDEX["CO"],
#         "scale": 100.0,
#         "color": "magenta",
#         "marker": "*",
#         "label": "CO_SAT*100"
#     },

#     "NO2": {
#         "index": SAT_INDEX["NO2"],
#         "scale": 1e6,
#         "color": "gold",
#         "marker": "^",
#         "label": "NO2_SAT*1e6"
#     },

#     "SO2": {
#         "index": SAT_INDEX["SO2"],
#         "scale": 1e6,
#         "color": "limegreen",
#         "marker": "D",
#         "label": "SO2_SAT*1e6"
#     },

#     "AI": {
#         "index": SAT_INDEX["AI"],
#         "scale": 100.0,
#         "color": "darkviolet",
#         "marker": "s",
#         "label": "AI_SAT*100"
#     },

#     "CH4": {
#         "index": SAT_INDEX["CH4"],
#         "scale": 1.0,
#         "color": "olive",
#         "marker": "P",
#         "label": "CH4_SAT"
#     }
# }


# print("\nPOLUENTES ENCONTRADOS:")
# print(final["pollutant"].unique())


# # =========================================================
# # LOOP ESTAÇÕES
# # =========================================================

# for estacao in estacoes:

#     print("\n===================================")
#     print("PLOTANDO ESTAÇÃO:", estacao)
#     print("===================================")

#     # estacoes_grupo = {
#     #     codigo: grupo
#     #     for codigo, grupo in
#     #     final.groupby("estacao_codigo")
#     # }

#     sub_est = ESTACOES_GRUPO.get(estacao)

#     if sub_est is None:
#         continue

#     if sub_est.empty:

#         print("Sem dados para estação.")
#         continue

#     nome_estacao = (
#         sub_est["station_name"]
#         .iloc[0]
#     )

#     # =====================================================
#     # LAT/LON
#     # =====================================================

#     codigo_estacao = int(estacao)

#     if codigo_estacao not in stations_dict:

#         print(
#             f"Estação {estacao} não encontrada em lista_estacoes.json"
#         )
#         continue

#     st_info = stations_dict[codigo_estacao]

#     lat_station = float(st_info["latitude"])
#     lon_station = float(st_info["longitude"])

#     print("LAT:", lat_station)
#     print("LON:", lon_station)

#     datas_plot = pd.date_range(
#         DATA_INICIO,
#         DATA_FIM - pd.Timedelta(days=1),
#         freq="D"
#     )

#     fig, ax = plt.subplots(
#         figsize=(22, 8)
#     )


#     axes = [ax]

#     # =====================================================
#     # PRIMEIRO POLUENTE
#     # =====================================================

#     pol0 = poluentes[0]

#     sub0 = sub_est[
#         sub_est["pollutant"] == pol0
#     ]

#     if not sub0.empty:

#         ax.plot(
#             sub0["datetime"],
#             sub0["Valor Diário"],
#             color=CORES.get(pol0, "blue"),
#             label=pol0,
#             linewidth=1.5,
#             marker="o"
#         )
#         ax.set_ylabel(
#             f"{pol0} ({UNIDADES.get(pol0,'')})",
#             color=CORES.get(pol0, "blue"),
#             fontsize=12,
#             fontweight="bold"
#         )

#         ax.tick_params(
#             axis="y",
#             colors=CORES.get(pol0, "blue")
#         )

#         # =====================================================
#         # CONVERSÃO SATÉLITE - Não utilizado
#         # =====================================================
#         # ALTURA_CAMADA = 35000.0  # metros
#         # MASSA_MOLAR = {
#         #     "O3": 48.0,
#         #     "CO": 28.01
#         # }


#         # =================================================
#         # SATÉLITE O3
#         # =================================================
#         if pol0 == "O3":

#             datas_unicas = (
#                 sub0["datetime"]
#                 .dt.normalize()
#                 .unique()
#             )

#             plot_satellite_product(
#                 ax,
#                 "O3",
#                 datas_unicas,
#                 lat_station,
#                 lon_station,
#                 SAT_CONFIG["O3"],
#                 args.sat_delta
#             )


#     # =====================================================
#     # DEMAIS POLUENTES
#     # =====================================================

#     AXIS_SPACING = 0.08

#     for pol in poluentes[1:]:


#         sub = sub_est[
#             sub_est["pollutant"] == pol
#         ]

#         if sub.empty:
#             continue

#         num_axes = len(axes)

#         ax_new = ax.twinx()

#         ax_new.spines["right"].set_position(
#             ("axes", 1 + AXIS_SPACING * num_axes)
#         )

#         sub = sub_est[
#             sub_est["pollutant"] == pol
#         ]

#         if sub.empty:
#             continue

#         # =================================================
#         # SATÉLITE CO
#         # =================================================
#         if pol == "CO":

#             datas_unicas = (
#                 sub["datetime"]
#                 .dt.normalize()
#                 .unique()
#             )

#             plot_satellite_product(
#                 ax_new,
#                 "CO",
#                 datas_unicas,
#                 lat_station,
#                 lon_station,
#                 SAT_CONFIG["CO"],
#                 args.sat_delta
#             )

#         if pol in ["MP10", "MP25"]:

#             datas_unicas = (
#                 sub["datetime"]
#                 .dt.normalize()
#                 .unique()
#             )

#             plot_satellite_product(
#                 ax_new,
#                 "AI",
#                 datas_unicas,
#                 lat_station,
#                 lon_station,
#                 SAT_CONFIG["AI"],
#                 args.sat_delta
#             )


#         # =================================================
#         # SATÉLITE NO2
#         # =================================================
#         if pol == "NO2":

#             datas_unicas = (
#                 sub["datetime"]
#                 .dt.normalize()
#                 .unique()
#             )

#             plot_satellite_product(
#                 ax_new,
#                 "NO2",
#                 datas_unicas,
#                 lat_station,
#                 lon_station,
#                 SAT_CONFIG["NO2"],
#                 args.sat_delta
#             )        

#         # =================================================
#         # SATÉLITE SO2
#         # =================================================
#         if pol == "SO2":

#             datas_unicas = (
#                 sub["datetime"]
#                 .dt.normalize()
#                 .unique()
#             )

#             plot_satellite_product(
#                 ax_new,
#                 "SO2",
#                 datas_unicas,
#                 lat_station,
#                 lon_station,
#                 SAT_CONFIG["SO2"],
#                 args.sat_delta
#             )

#         # =================================================
#         # ESTAÇÃO
#         # =================================================

#         ax_new.plot(
#             sub["datetime"],
#             sub["Valor Diário"],
#             color=CORES.get(pol, "black"),
#             label=pol,
#             linewidth=1.5,
#             marker="o"
#         )

#         # =================================================
#         # CO SATÉLITE
#         # =================================================
#         ax_new.set_ylabel(
#             f"{pol} ({UNIDADES.get(pol,'')})",
#             color=CORES.get(pol, "black"),
#             fontsize=12,
#             fontweight="bold"
#         )

#         ax_new.tick_params(
#             axis="y",
#             colors=CORES.get(pol, "black")
#         )

#         axes.append(ax_new)


#     # =====================================================
#     # CH4 SATÉLITE SEM CETESB
#     # =====================================================

#     datas_unicas = final["datetime"].dt.normalize().unique()

#     sat_dates_ch4, sat_values_ch4 = get_satellite_series(
#         SAT_INDEX["CH4"],
#         datas_plot,
#         lat_station,
#         lon_station,
#         args.sat_delta,
#         scale=1.0
#     )

#     if sat_dates_ch4:

#         ax_ch4 = ax.twinx()

#         ax_ch4.spines["right"].set_position(
#             ("axes", 1 + AXIS_SPACING * len(axes))
#         )

#         ax_ch4.plot(
#             sat_dates_ch4,
#             sat_values_ch4,
#             color="olive",
#             linestyle="--",
#             marker="P",
#             linewidth=2,
#             markersize=8,
#             label="CH4_SAT"
#         )

#         ax_ch4.set_ylabel(
#             "CH4 SAT (ppb)",
#             color="olive"
#         )

#         ax_ch4.tick_params(
#             axis="y",
#             colors="olive"
#         )

#         axes.append(ax_ch4)


#     # =====================================================
#     # TÍTULO
#     # =====================================================

#     plt.title(
#         "Qualidade do Ar - Médias Diárias\n"
#         f"Estação: {estacao} - {nome_estacao}\n"
#         f"Período: {args.start} a {args.end}",
#         fontsize=16,
#         fontweight="bold"
#     )

#     # =====================================================
#     # GRID
#     # =====================================================

#     ax.grid(
#         True,
#         linestyle="--",
#         alpha=0.4
#     )


#     # =====================================================
#     # LEGENDA
#     # =====================================================
#     legend_dict = {}

#     for a in axes:

#         for ln in a.get_lines():

#             label = ln.get_label()

#             if label.startswith("_"):
#                 continue

#             #legend_dict[label] = ln    
#             legend_dict.setdefault(label, ln)

#     legend_order = [
#         "O3",
#         "O3_SAT*1000",

#         "MP25",
#         "MP10",
#         "AI_SAT*100",

#         "NO2",
#         "NO2_SAT*1e6",

#         "SO2",
#         "SO2_SAT*1e6",

#         "CO",
#         "CO_SAT*100",

#         "CH4_SAT"
#     ]

#     # Monta Legenda
#     lines = []
#     labels = []

#     for label in legend_order:

#         if label in legend_dict:

#             lines.append(legend_dict[label])
#             labels.append(label)

#     ax.legend(
#         lines,
#         labels,
#         loc="upper left",
#         fontsize=9
#     )

#     # =====================================================
#     # SAVE
#     # =====================================================

#     output_png = os.path.join(
#         OUTPUT_DIR,
#         f"{estacao}_{args.pollutant}_timeseries_MediaDiaria_compara.png"
#     )

#     plt.savefig(
#         output_png,
#         dpi=150,
#         bbox_inches="tight"
#     )

#     print("\n===================================")
#     print("FIGURA GERADA")
#     print(output_png)
#     print("===================================")

#     plt.close()
