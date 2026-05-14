#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import glob
import argparse

import pandas as pd
import matplotlib.pyplot as plt

""" Exemplo

Ler os CSVs baixados do QUALAR
Ler a lista de estações JSON
Plotar:
    1 estação (--station 65)
    várias estações (--station all)
Filtrar por:
    período
    poluente
Gerar PNG
Opcionalmente gerar um CSV tratado

*** Plota vários poluentes disponíveis em um gráfico

python plot_cetesb_timeseries.py \
--input ../cipc_data/cetesb \
--stations-file ../cipc_data/cetesb/lista_estacoes.json \
--station 65 \
--pollutant all \
--start 15/08/2024 \
--end 25/08/2024


*** Plota somente 1 poluente
python plot_cetesb_timeseries.py \
--input ../cipc_data/cetesb \
--stations-file ../cipc_data/cetesb/lista_estacoes.json \
--station 65 \
--pollutant O3 \
--start 15/08/2024 \
--end 25/08/2024

ou:

python plot_cetesb_timeseries.py \
--input ../cipc_data/cetesb \
--stations-file ../cipc_data/cetesb/lista_estacoes.json \
--station all \
--pollutant PM25 \
--start 15/08/2024 \
--end 25/08/2024

Resultado:

múltiplos eixos Y
cores por poluente
O3 azul
NO2 laranja
SO2 verde
CO vermelho
PM10 roxo
PM25 marrom

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
    help="""
Poluente:
O3
MP25
MP10
NO2
SO2
CO
ou all
"""
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
    "--output",
    default="../cipc_output/figures/cetesb",
    help="Diretório saída"
)

args = parser.parse_args()

INPUT_DIR = args.input
OUTPUT_DIR = args.output

POLUENTES_VALIDOS = [
    "O3",
    "MP25",
    "MP10",
    "NO2",
    "SO2",
    "CO"
]

# =========================================================
# POLUENTES ESCOLHIDOS
# =========================================================

if args.pollutant.lower() == "all":

    poluentes = POLUENTES_VALIDOS

else:

    poluentes = [args.pollutant]


os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# =========================================================
# DATAS
# =========================================================

DATA_INICIO = pd.to_datetime(
    args.start,
    dayfirst=True
)

DATA_FIM = pd.to_datetime(
    args.end,
    dayfirst=True
)

# =========================================================
# ESTAÇÕES
# =========================================================

df_st = pd.read_json(
    args.stations_file
)

if args.station.lower() == "all":

    estacoes = (
        df_st["codigo"]
        .astype(str)
        .tolist()
    )

else:

    estacoes = [str(args.station)]

# =========================================================
# LEITURA CSVs
# =========================================================

todos = []

for estacao in estacoes:

    for poluente in poluentes:

        arquivo = os.path.join(
            INPUT_DIR,
            f"{estacao}_{poluente}.csv"
        )

        if not os.path.exists(arquivo):

            print(f"Arquivo não encontrado: {arquivo}")
            continue

        print(f"Lendo: {arquivo}")

        try:

            df = pd.read_csv(
                arquivo,
                sep=";",
                skiprows=[0]
            )

        except Exception as e:

            print("Erro leitura:", e)
            continue

        # =====================================================
        # LIMPA COLUNAS
        # =====================================================

        df.columns = [
            str(c).strip()
            for c in df.columns
        ]

        # =====================================================
        # REMOVE VAZIOS
        # =====================================================

        df = df[
            df["Data"].notna()
        ]

        # =====================================================
        # DATETIME
        # =====================================================

        df["datetime"] = pd.to_datetime(
            df["Data"] + " " + df["Hora"],
            dayfirst=True,
            errors="coerce"
        )

        # =====================================================
        # FILTRA DATAS
        # =====================================================

        df = df[
            (df["datetime"] >= DATA_INICIO)
            &
            (df["datetime"] <= DATA_FIM)
        ]

        # =====================================================
        # CONCENTRAÇÃO
        # =====================================================

        df["Média Horária"] = pd.to_numeric(
            df["Média Horária"],
            errors="coerce"
        )

        # =====================================================
        # ESTAÇÃO
        # =====================================================

        nome_est = (
            df["Nome Estação"]
            .dropna()
            .iloc[0]
        )

        df["station_name"] = nome_est

        df["pollutant"] = poluente

        todos.append(df)



# =========================================================
# CONCATENA
# =========================================================

if len(todos) == 0:

    raise Exception(
        "Nenhum dado encontrado."
    )

final = pd.concat(
    todos,
    ignore_index=True
)

# =========================================================
# PLOT
# =========================================================
# =========================================================
# CORES
# =========================================================

CORES = {
    "O3": "blue",
    "NO2": "orange",
    "SO2": "green",
    "CO": "red",
    "MP10": "purple",
    "MP25": "brown"
}

UNIDADES = {
    "O3": "µg/m³",
    "NO2": "µg/m³",
    "SO2": "µg/m³",
    "CO": "ppm",
    "MP10": "µg/m³",
    "MP25": "µg/m³"
}

# =========================================================
# FIGURA
# =========================================================

fig, ax = plt.subplots(
    figsize=(16,7)
)

axes = [ax]

# =========================================================
# POLUENTE PRINCIPAL
# =========================================================

pol0 = poluentes[0]

sub0 = final[
    final["pollutant"] == pol0
]

ax.plot(
    sub0["datetime"],
    sub0["Média Horária"],
    color=CORES[pol0],
    label=pol0,
    linewidth=1.5
)

ax.set_ylabel(
    f"{pol0} ({UNIDADES[pol0]})",
    color=CORES[pol0],
    fontsize=12,
    fontweight="bold"
)

ax.tick_params(
    axis="y",
    colors=CORES[pol0]
)

# =========================================================
# OUTROS POLUENTES
# =========================================================

offset = 0

for pol in poluentes[1:]:

    offset += 0.07

    ax_new = ax.twinx()

    ax_new.spines["right"].set_position(
        ("axes", 1 + offset)
    )

    sub = final[
        final["pollutant"] == pol
    ]

    ax_new.plot(
        sub["datetime"],
        sub["Média Horária"],
        color=CORES[pol],
        label=pol,
        linewidth=1.5
    )

    ax_new.set_ylabel(
        f"{pol} ({UNIDADES[pol]})",
        color=CORES[pol],
        fontsize=12,
        fontweight="bold"
    )

    ax_new.tick_params(
        axis="y",
        colors=CORES[pol]
    )

    axes.append(ax_new)

# =========================================================
# TÍTULO
# =========================================================

nome_estacao = (
    final["station_name"]
    .iloc[0]
)

plt.title(
    "Qualidade do Ar - Vários Poluentes\n"
    f"Estação: {args.station} - {nome_estacao}\n"
    f"Período: {args.start} a {args.end}",
    fontsize=16,
    fontweight="bold"
)

# =========================================================
# GRID
# =========================================================

ax.grid(
    True,
    linestyle="--",
    alpha=0.4
)

# =========================================================
# LEGENDA
# =========================================================

lines = []
labels = []

for a in axes:

    lns = a.get_lines()

    for ln in lns:

        lines.append(ln)
        labels.append(ln.get_label())

ax.legend(
    lines,
    labels,
    loc="upper left"
)

plt.xlabel("Data/Hora")


# =========================================================
# SAVE
# =========================================================

output_png = os.path.join(
    OUTPUT_DIR,
    f"{args.station}_{args.pollutant}_timeseries.png"
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
