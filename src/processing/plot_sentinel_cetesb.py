
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

from plotting.station_plot import plot_station

"""
Plota séries temporais CETESB
(Médias Diárias)

+ Dados de satélite GeoTIFF
(O3 inicialmente)

=========================================================
EXEMPLO
=========================================================

python plot_cetesb_timeseries_mediaDiaria.py \
--input /home/jurandir/cipc_output/cetesb/media_diaria_csvs \
--stations-file ../cipc_data/cetesb/lista_estacoes.json \
--station 58 \
--pollutant all \
--start 15/08/2024 \
--end 25/08/2024 \
--sat-dir /home/jurandir/cipc_output/geotiff/ozone_total_vertical_column/2024

*** Incluso O3, CO, AI-354:388
python src/processing/plot_sentinel_cetesb.py \
--input /home/jurandir/cipc_output/cetesb/media_diaria_csvs \
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
--input /home/jurandir/cipc_output/cetesb/media_diaria_csvs \
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
    sub_est = ESTACOES_GRUPO.get(estacao)

    plot_station(
        estacao=estacao,
        sub_est=sub_est,
        stations_dict=stations_dict,
        poluentes=poluentes,
        sat_index=SAT_INDEX,
        sat_config=SAT_CONFIG,
        data_inicio=DATA_INICIO,
        data_fim=DATA_FIM,
        output_dir=OUTPUT_DIR,
        sat_delta=args.sat_delta,
        output_pollutant=args.pollutant,
        start_str=args.start,
        end_str=args.end
    )

