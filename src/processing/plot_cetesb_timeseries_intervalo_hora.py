#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import argparse
import glob

import pandas as pd
import matplotlib.pyplot as plt

"""
Plota séries temporais CETESB
(Média Horária)

Compatível com CSVs:

279_O3.csv
279_NO2.csv
etc

=========================================================
EXEMPLOS
=========================================================

1 estação:

python plot_cetesb_timeseries.py \
--input ../cipc_data/cetesb \
--stations-file ../cipc_data/cetesb/lista_estacoes.json \
--station 279 \
--pollutant all \
--start 15/08/2024 \
--end 25/08/2024 \
--hour-start 06:00 \
--hour-end 18:00

Todas estações:

python plot_cetesb_timeseries.py \
--input ../cipc_data/cetesb \
--stations-file ../cipc_data/cetesb/lista_estacoes.json \
--station all \
--pollutant O3 \
--start 15/08/2024 \
--end 25/08/2024 \
--hour-start 08:00 \
--hour-end 08:00

"""

# =========================================================
# ARGUMENTOS
# =========================================================

parser = argparse.ArgumentParser()

parser.add_argument(
    "--input",
    required=True,
    help="Diretório CSVs"
)

parser.add_argument(
    "--stations-file",
    required=True,
    help="Arquivo lista_estacoes.json"
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

# =========================================================
# NOVOS ARGUMENTOS HORÁRIO
# =========================================================

parser.add_argument(
    "--hour-start",
    default="00:00",
    help="Hora inicial HH:MM"
)

parser.add_argument(
    "--hour-end",
    default="23:59",
    help="Hora final HH:MM"
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
    "NO",
    "NOx"
]

if args.pollutant.lower() == "all":

    poluentes = POLUENTES_VALIDOS

else:

    poluentes = [args.pollutant.upper()]

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
# INTERVALO HORÁRIO
# =========================================================

try:

    HORA_INICIO = pd.to_datetime(
        args.hour_start,
        format="%H:%M"
    ).time()

    HORA_FIM = pd.to_datetime(
        args.hour_end,
        format="%H:%M"
    ).time()

except Exception:

    raise Exception(
        "Formato horário inválido. Use HH:MM"
    )

# =========================================================
# VALIDA INTERVALO
# =========================================================

if HORA_FIM < HORA_INICIO:

    raise Exception(
        "--hour-end não pode ser menor que --hour-start"
    )

print("\nINTERVALO HORÁRIO:")
print(
    f"{args.hour_start} -> {args.hour_end}"
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
# CORES
# =========================================================

CORES = {
    "O3": "blue",
    "NO2": "orange",
    "SO2": "green",
    "CO": "red",
    "MP10": "purple",
    "MP25": "brown",
    "NO": "gray",
    "NOx": "black"
}

UNIDADES = {
    "O3": "µg/m³",
    "NO2": "µg/m³",
    "SO2": "µg/m³",
    "CO": "ppm",
    "MP10": "µg/m³",
    "MP25": "µg/m³",
    "NO": "µg/m³",
    "NOx": "µg/m³"
}

# =========================================================
# LOOP ESTAÇÕES
# =========================================================

for estacao in estacoes:

    print("\n===================================")
    print("PLOTANDO ESTAÇÃO:", estacao)
    print("===================================")

    todos = []

    # =====================================================
    # LOOP POLUENTES
    # =====================================================

    for poluente in poluentes:

        pattern = os.path.join(
            INPUT_DIR,
            f"{estacao}_{poluente}*.csv"
        )

        arquivos = glob.glob(pattern)

        if len(arquivos) == 0:

            print(f"Nenhum arquivo: {pattern}")
            continue

        for arquivo in arquivos:

            print("Lendo:", arquivo)

            try:

                df = pd.read_csv(
                    arquivo,
                    sep=";",
                    header=[0, 1]
                )

            except Exception as e:

                print("Erro leitura:", e)
                continue

            # =================================================
            # ACHATA MULTIINDEX
            # =================================================

            novas_colunas = []

            for c1, c2 in df.columns:

                if (
                    "Unnamed" in str(c2)
                    or str(c2).strip() == ""
                ):

                    novas_colunas.append(
                        str(c1).strip()
                    )

                else:

                    novas_colunas.append(
                        str(c2).strip()
                    )

            df.columns = novas_colunas

            # remove duplicadas
            df = df.loc[
                :,
                ~pd.Index(df.columns).duplicated()
            ]

            print("COLUNAS:")
            print(df.columns.tolist())

            # =================================================
            # DATA
            # =================================================

            if "Data" not in df.columns:

                print("Coluna Data não encontrada.")
                continue

            df = df[
                df["Data"].notna()
            ]

            if df.empty:

                print("CSV vazio.")
                continue

            # =================================================
            # HORA
            # =================================================

            if "Hora" not in df.columns:

                df["Hora"] = "00:00"

            df["Hora"] = (
                df["Hora"]
                .astype(str)
                .str.strip()
            )

            # trata 24:00
            mask_24 = (
                df["Hora"] == "24:00"
            )

            df.loc[
                mask_24,
                "Hora"
            ] = "00:00"

            # =================================================
            # DATETIME
            # =================================================

            df["datetime"] = pd.to_datetime(
                df["Data"].astype(str)
                + " "
                + df["Hora"].astype(str),
                format="%d/%m/%Y %H:%M",
                errors="coerce"
            )

            # soma +1 dia para 24:00
            df.loc[
                mask_24,
                "datetime"
            ] = (
                df.loc[
                    mask_24,
                    "datetime"
                ]
                + pd.Timedelta(days=1)
            )

            df = df[
                df["datetime"].notna()
            ]

            if df.empty:

                print("Sem datetime válido.")
                continue

            # =================================================
            # FILTRA PERÍODO
            # =================================================

            df = df[
                (df["datetime"] >= DATA_INICIO)
                &
                (df["datetime"] <= DATA_FIM)
            ]

            if df.empty:

                print("Sem dados no período.")
                continue

            # =================================================
            # FILTRA HORÁRIO
            # =================================================

            df["hora_plot"] = (
                df["datetime"]
                .dt.time
            )

            df = df[
                (df["hora_plot"] >= HORA_INICIO)
                &
                (df["hora_plot"] <= HORA_FIM)
            ]

            if df.empty:

                print("Sem dados no intervalo horário.")
                continue

            # =================================================
            # VALOR
            # =================================================

            coluna_valor = None

            if "Média Horária" in df.columns:

                coluna_valor = "Média Horária"

            elif "Valor Diário" in df.columns:

                coluna_valor = "Valor Diário"

            elif "Concentração" in df.columns:

                coluna_valor = "Concentração"

            else:

                print("Nenhuma coluna valor encontrada.")
                continue

            df[coluna_valor] = (
                df[coluna_valor]
                .astype(str)
                .str.replace(",", ".", regex=False)
            )

            df[coluna_valor] = pd.to_numeric(
                df[coluna_valor],
                errors="coerce"
            )

            df = df[
                df[coluna_valor].notna()
            ]

            if df.empty:

                print("Sem valores numéricos.")
                continue

            # =================================================
            # ESTAÇÃO
            # =================================================

            if "Nome Estação" in df.columns:

                nome_estacao = (
                    df["Nome Estação"]
                    .dropna()
                    .iloc[0]
                )

            else:

                nome_estacao = estacao

            df["station_name"] = nome_estacao

            # =================================================
            # CÓDIGO ESTAÇÃO
            # =================================================

            if "Código Estação" in df.columns:

                df["estacao_codigo"] = (
                    df["Código Estação"]
                    .astype(str)
                    .str.strip()
                )

            else:

                df["estacao_codigo"] = str(estacao)

            # =================================================
            # POLUENTE
            # =================================================

            df["pollutant"] = poluente

            # =================================================
            # PADRONIZA VALOR
            # =================================================

            df["valor"] = df[coluna_valor]

            todos.append(df)

    # =====================================================
    # SEM DADOS
    # =====================================================

    if len(todos) == 0:

        print("Nenhum dado encontrado.")
        continue

    # =====================================================
    # CONCATENA
    # =====================================================

    final = pd.concat(
        todos,
        ignore_index=True
    )

    print("\nPOLUENTES ENCONTRADOS:")
    print(final["pollutant"].unique())

    # =====================================================
    # FIGURA
    # =====================================================

    fig, ax = plt.subplots(
        figsize=(16, 7)
    )

    axes = [ax]

    # =====================================================
    # PRIMEIRO POLUENTE
    # =====================================================

    pol0 = poluentes[0]

    sub0 = final[
        final["pollutant"] == pol0
    ]

    if not sub0.empty:

        ax.plot(
            sub0["datetime"],
            sub0["valor"],
            color=CORES.get(pol0, "blue"),
            label=pol0,
            linewidth=1.2
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
    # OUTROS POLUENTES
    # =====================================================

    offset = 0

    for pol in poluentes[1:]:

        sub = final[
            final["pollutant"] == pol
        ]

        if sub.empty:
            continue

        offset += 0.07

        ax_new = ax.twinx()

        ax_new.spines["right"].set_position(
            ("axes", 1 + offset)
        )

        ax_new.plot(
            sub["datetime"],
            sub["valor"],
            color=CORES.get(pol, "black"),
            label=pol,
            linewidth=1.2
        )

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
    # TÍTULO
    # =====================================================

    nome_estacao = (
        final["station_name"]
        .iloc[0]
    )

    plt.title(
        "Qualidade do Ar - Média Horária\n"
        f"Estação: {estacao} - {nome_estacao}\n"
        f"Período: {args.start} a {args.end}\n"
        f"Horário: {args.hour_start} -> {args.hour_end}",
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

    lines = []
    labels = []

    for a in axes:

        for ln in a.get_lines():

            lines.append(ln)
            labels.append(ln.get_label())

    ax.legend(
        lines,
        labels,
        loc="upper left"
    )

    plt.xlabel("Data/Hora")

    # =====================================================
    # SAVE
    # =====================================================

    hora_ini_nome = (
        args.hour_start
        .replace(":", "")
    )

    hora_fim_nome = (
        args.hour_end
        .replace(":", "")
    )

    output_png = os.path.join(
        OUTPUT_DIR,
        f"{estacao}_{args.pollutant}"
        f"_{hora_ini_nome}_{hora_fim_nome}"
        f"_timeseries_MediaHoraria.png"
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