#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import glob
import argparse

import pandas as pd
import matplotlib.pyplot as plt

"""
Plota séries temporais CETESB
(Médias Diárias)

Compatível com CSVs no formato:

58_O3_Ribeirao_Preto.csv

Estrutura:

Tipo de Rede;Tipo de Monitoramento;Tipo;Data;Hora;
Código Estação;Nome Estação;Nome Parâmetro;
Unidade de Medida;Valor Diário;...

=========================================================
EXEMPLOS
=========================================================

python plot_cetesb_timeseries_mediaDiaria.py \
--input csvs \
--stations-file ../cipc_data/cetesb/lista_estacoes.json \
--station 58 \
--pollutant all \
--start 15/08/2024 \
--end 25/08/2024

python plot_cetesb_timeseries_mediaDiaria.py \
--input csvs \
--stations-file ../cipc_data/cetesb/lista_estacoes.json \
--station 58 \
--pollutant O3 \
--start 15/08/2024 \
--end 25/08/2024
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

        pattern = os.path.join(
            INPUT_DIR,
            f"{estacao}_{poluente}_*.csv"
        )

        arquivos = glob.glob(pattern)

        if len(arquivos) == 0:

            print(f"Nenhum arquivo encontrado: {pattern}")
            continue

        for arquivo in arquivos:

            print(f"Lendo: {arquivo}")

            try:

                df = pd.read_csv(
                    arquivo,
                    sep=";"
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
            # REMOVE LINHAS SEM DATA
            # =====================================================

            if "Data" not in df.columns:

                print("Coluna Data não encontrada.")
                continue

            df = df[
                df["Data"].notna()
            ]

            if df.empty:

                print("CSV vazio.")
                continue

            # =====================================================
            # HORA
            # =====================================================

            if "Hora" not in df.columns:

                df["Hora"] = "00:00"

            df["Hora"] = (
                df["Hora"]
                .astype(str)
                .str.strip()
            )

            # substitui vazios
            df.loc[
                (df["Hora"] == "")
                |
                (df["Hora"].str.lower() == "nan"),
                "Hora"
            ] = "00:00"

            # garante HH:MM
            df["Hora"] = df["Hora"].str[:5]

            # =====================================================
            # DATETIME
            # =====================================================

            if "Hora" not in df.columns:

                df["Hora"] = "00:00"

            # limpa strings

            df["Hora"] = (
                df["Hora"]
                .astype(str)
                .str.strip()
            )

            # =====================================================
            # TRATA 24:00
            # =====================================================

            mask_24 = df["Hora"] == "24:00"

            # troca por 00:00

            df.loc[mask_24, "Hora"] = "00:00"

            # cria datetime normal

            df["datetime"] = pd.to_datetime(
                df["Data"].astype(str)
                + " "
                + df["Hora"].astype(str),
                format="%d/%m/%Y %H:%M",
                errors="coerce"
            )

            # soma 1 dia onde era 24:00

            df.loc[mask_24, "datetime"] = (
                df.loc[mask_24, "datetime"]
                + pd.Timedelta(days=1)
            )


            # =====================================================
            # REMOVE DATAS INVÁLIDAS
            # =====================================================

            df = df[
                df["datetime"].notna()
            ]

            if df.empty:

                print("Sem datetime válido.")
                continue

            # =====================================================
            # FILTRA PERÍODO
            # =====================================================

            df = df[
                (df["datetime"] >= DATA_INICIO)
                &
                (df["datetime"] <= DATA_FIM)
            ]

            if df.empty:

                print("Sem dados no período.")
                continue

            # =====================================================
            # VALOR DIÁRIO
            # =====================================================

            if "Valor Diário" not in df.columns:

                print("Coluna Valor Diário não encontrada.")
                continue

            df["Valor Diário"] = (
                df["Valor Diário"]
                .astype(str)
                .str.replace(",", ".", regex=False)
            )

            df["Valor Diário"] = pd.to_numeric(
                df["Valor Diário"],
                errors="coerce"
            )

            df = df[
                df["Valor Diário"].notna()
            ]

            if df.empty:

                print("Sem valores numéricos.")
                continue

            # =====================================================
            # ESTAÇÃO
            # =====================================================

            if "estacao_nome" in df.columns:

                nomes_validos = (
                    df["estacao_nome"]
                    .dropna()
                )

                if len(nomes_validos) > 0:

                    nome_est = nomes_validos.iloc[0]

                else:

                    nome_est = str(estacao)

            else:

                nome_est = str(estacao)

            df["station_name"] = nome_est

            # =====================================================
            # POLUENTE
            # =====================================================

            if "poluente" in df.columns:

                df["pollutant"] = (
                    df["poluente"]
                    .astype(str)
                    .str.strip()
                    .str.upper()
                )

                # =========================================
                # NORMALIZA NOMES
                # =========================================

                df["pollutant"] = (
                    df["pollutant"]
                    .replace({
                        "MP2.5": "MP25",
                        "MP2,5": "MP25",
                        "PM25": "MP25",
                        "PM10": "MP10",
#                        "NOX": "NOx"
                    })
                )

            else:

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
# CORES
# =========================================================

CORES = {
    "O3": "blue",
    "NO2": "orange",
    "SO2": "green",
    "CO": "red",
    "MP10": "purple",
    "MP25": "brown",
#    "NO": "gray",
#    "NOx": "black"
}

UNIDADES = {
    "O3": "µg/m³",
    "NO2": "µg/m³",
    "SO2": "µg/m³",
    "CO": "ppm",
    "MP10": "µg/m³",
    "MP25": "µg/m³",
#    "NO": "µg/m³",
#    "NOx": "µg/m³"
}

print("\nPOLUENTES ENCONTRADOS:")
print(final["pollutant"].unique())

# =========================================================
# LOOP ESTAÇÕES
# =========================================================

for estacao in estacoes:

    print("\n===================================")
    print("PLOTANDO ESTAÇÃO:", estacao)
    print("===================================")

    sub_est = final[
        final["estacao_codigo"].astype(str)
        == str(estacao)
    ]

    if sub_est.empty:

        print("Sem dados para estação.")
        continue

    nome_estacao = (
        sub_est["station_name"]
        .iloc[0]
    )

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
    # DEMAIS POLUENTES
    # =====================================================

    offset = 0

    for pol in poluentes[1:]:

        sub = sub_est[
            sub_est["pollutant"] == pol
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
            sub["Valor Diário"],
            color=CORES.get(pol, "black"),
            label=pol,
            linewidth=1.5,
            marker="o"
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

    plt.xlabel("Data")

    # =====================================================
    # SAVE
    # =====================================================

    output_png = os.path.join(
        OUTPUT_DIR,
        f"{estacao}_{args.pollutant}_timeseries_MediaDiaria.png"
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





# - Argumento all das estações imprime tudo junto e não 
#   para todas estações 
# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-

# import os
# import glob
# import argparse

# import pandas as pd
# import matplotlib.pyplot as plt

# """
# Plota séries temporais CETESB
# (Médias Diárias)

# Compatível com CSVs no formato:

# 58_O3_Ribeirao_Preto.csv

# Estrutura:

# Tipo de Rede;Tipo de Monitoramento;Tipo;Data;Hora;
# Código Estação;Nome Estação;Nome Parâmetro;
# Unidade de Medida;Valor Diário;...

# =========================================================
# EXEMPLOS
# =========================================================

# python plot_cetesb_timeseries_mediaDiaria.py \
# --input csvs \
# --stations-file ../cipc_data/cetesb/lista_estacoes.json \
# --station 58 \
# --pollutant all \
# --start 15/08/2024 \
# --end 25/08/2024

# python plot_cetesb_timeseries_mediaDiaria.py \
# --input csvs \
# --stations-file ../cipc_data/cetesb/lista_estacoes.json \
# --station 58 \
# --pollutant O3 \
# --start 15/08/2024 \
# --end 25/08/2024
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
#     "NO",
#     "NOx"
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

# if args.station.lower() == "all":

#     estacoes = (
#         df_st["codigo"]
#         .astype(str)
#         .tolist()
#     )

# else:

#     estacoes = [str(args.station)]

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

#             # =====================================================
#             # LIMPA COLUNAS
#             # =====================================================

#             df.columns = [
#                 str(c).strip()
#                 for c in df.columns
#             ]

#             # =====================================================
#             # REMOVE LINHAS SEM DATA
#             # =====================================================

#             if "Data" not in df.columns:

#                 print("Coluna Data não encontrada.")
#                 continue

#             df = df[
#                 df["Data"].notna()
#             ]

#             if df.empty:

#                 print("CSV vazio.")
#                 continue

#             # =====================================================
#             # HORA
#             # =====================================================

#             if "Hora" not in df.columns:

#                 df["Hora"] = "00:00"

#             df["Hora"] = (
#                 df["Hora"]
#                 .astype(str)
#                 .str.strip()
#             )

#             # substitui vazios
#             df.loc[
#                 (df["Hora"] == "")
#                 |
#                 (df["Hora"].str.lower() == "nan"),
#                 "Hora"
#             ] = "00:00"

#             # garante HH:MM
#             df["Hora"] = df["Hora"].str[:5]

#             # =====================================================
#             # DATETIME
#             # =====================================================

#             if "Hora" not in df.columns:

#                 df["Hora"] = "00:00"

#             # limpa strings

#             df["Hora"] = (
#                 df["Hora"]
#                 .astype(str)
#                 .str.strip()
#             )

#             # =====================================================
#             # TRATA 24:00
#             # =====================================================

#             mask_24 = df["Hora"] == "24:00"

#             # troca por 00:00

#             df.loc[mask_24, "Hora"] = "00:00"

#             # cria datetime normal

#             df["datetime"] = pd.to_datetime(
#                 df["Data"].astype(str)
#                 + " "
#                 + df["Hora"].astype(str),
#                 format="%d/%m/%Y %H:%M",
#                 errors="coerce"
#             )

#             # soma 1 dia onde era 24:00

#             df.loc[mask_24, "datetime"] = (
#                 df.loc[mask_24, "datetime"]
#                 + pd.Timedelta(days=1)
#             )


#             # =====================================================
#             # REMOVE DATAS INVÁLIDAS
#             # =====================================================

#             df = df[
#                 df["datetime"].notna()
#             ]

#             if df.empty:

#                 print("Sem datetime válido.")
#                 continue

#             # =====================================================
#             # FILTRA PERÍODO
#             # =====================================================

#             df = df[
#                 (df["datetime"] >= DATA_INICIO)
#                 &
#                 (df["datetime"] <= DATA_FIM)
#             ]

#             if df.empty:

#                 print("Sem dados no período.")
#                 continue

#             # =====================================================
#             # VALOR DIÁRIO
#             # =====================================================

#             if "Valor Diário" not in df.columns:

#                 print("Coluna Valor Diário não encontrada.")
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

#                 print("Sem valores numéricos.")
#                 continue

#             # =====================================================
#             # ESTAÇÃO
#             # =====================================================

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

#             # =====================================================
#             # POLUENTE
#             # =====================================================

#             if "poluente" in df.columns:

#                 df["pollutant"] = (
#                     df["poluente"]
#                     .astype(str)
#                     .str.strip()
#                     .str.upper()
#                 )

#                 # =========================================
#                 # NORMALIZA NOMES
#                 # =========================================

#                 df["pollutant"] = (
#                     df["pollutant"]
#                     .replace({
#                         "MP2.5": "MP25",
#                         "MP2,5": "MP25",
#                         "PM25": "MP25",
#                         "PM10": "MP10",
#                         "NOX": "NOx"
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

# # =========================================================
# # CORES
# # =========================================================

# CORES = {
#     "O3": "blue",
#     "NO2": "orange",
#     "SO2": "green",
#     "CO": "red",
#     "MP10": "purple",
#     "MP25": "brown",
#     "NO": "gray",
#     "NOx": "black"
# }

# UNIDADES = {
#     "O3": "µg/m³",
#     "NO2": "µg/m³",
#     "SO2": "µg/m³",
#     "CO": "ppm",
#     "MP10": "µg/m³",
#     "MP25": "µg/m³",
#     "NO": "µg/m³",
#     "NOx": "µg/m³"
# }

# print("\nPOLUENTES ENCONTRADOS:")
# print(final["pollutant"].unique())

# # =========================================================
# # FIGURA
# # =========================================================

# fig, ax = plt.subplots(
#     figsize=(16, 7)
# )

# axes = [ax]

# # =========================================================
# # POLUENTE PRINCIPAL
# # =========================================================

# pol0 = poluentes[0]

# sub0 = final[
#     final["pollutant"] == pol0
# ]

# if not sub0.empty:

#     ax.plot(
#         sub0["datetime"],
#         sub0["Valor Diário"],
#         color=CORES.get(pol0, "blue"),
#         label=pol0,
#         linewidth=1.5,
#         marker="o"
#     )

#     ax.set_ylabel(
#         f"{pol0} ({UNIDADES.get(pol0,'')})",
#         color=CORES.get(pol0, "blue"),
#         fontsize=12,
#         fontweight="bold"
#     )

#     ax.tick_params(
#         axis="y",
#         colors=CORES.get(pol0, "blue")
#     )

# # =========================================================
# # OUTROS POLUENTES
# # =========================================================

# offset = 0

# for pol in poluentes[1:]:

#     sub = final[
#         final["pollutant"] == pol
#     ]

#     if sub.empty:
#         continue

#     offset += 0.07

#     ax_new = ax.twinx()

#     ax_new.spines["right"].set_position(
#         ("axes", 1 + offset)
#     )

#     ax_new.plot(
#         sub["datetime"],
#         sub["Valor Diário"],
#         color=CORES.get(pol, "black"),
#         label=pol,
#         linewidth=1.5,
#         marker="o"
#     )

#     ax_new.set_ylabel(
#         f"{pol} ({UNIDADES.get(pol,'')})",
#         color=CORES.get(pol, "black"),
#         fontsize=12,
#         fontweight="bold"
#     )

#     ax_new.tick_params(
#         axis="y",
#         colors=CORES.get(pol, "black")
#     )

#     axes.append(ax_new)

# # =========================================================
# # TÍTULO
# # =========================================================

# nome_estacao = (
#     final["station_name"]
#     .iloc[0]
# )

# plt.title(
#     "Qualidade do Ar - Médias Diárias\n"
#     f"Estação: {args.station} - {nome_estacao}\n"
#     f"Período: {args.start} a {args.end}",
#     fontsize=16,
#     fontweight="bold"
# )

# # =========================================================
# # GRID
# # =========================================================

# ax.grid(
#     True,
#     linestyle="--",
#     alpha=0.4
# )

# # =========================================================
# # LEGENDA
# # =========================================================

# lines = []
# labels = []

# for a in axes:

#     for ln in a.get_lines():

#         lines.append(ln)
#         labels.append(ln.get_label())

# ax.legend(
#     lines,
#     labels,
#     loc="upper left"
# )

# plt.xlabel("Data")

# # =========================================================
# # SAVE
# # =========================================================

# output_png = os.path.join(
#     OUTPUT_DIR,
#     f"{args.station}_{args.pollutant}_timeseries_MediaDiaria.png"
# )

# plt.savefig(
#     output_png,
#     dpi=150,
#     bbox_inches="tight"
# )

# print("\n===================================")
# print("FIGURA GERADA")
# print(output_png)
# print("===================================")

# plt.close()



# *** Funcionando mas falta plotar MP10 e MP25
# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-

# import os
# import glob
# import argparse

# import pandas as pd
# import matplotlib.pyplot as plt

# """ Exemplo

# Ler os CSVs baixados do QUALAR
# Ler a lista de estações JSON
# Plotar:
#     1 estação (--station 65)
#     várias estações (--station all)
# Filtrar por:
#     período
#     poluente
# Gerar PNG
# Opcionalmente gerar um CSV tratado

# *** Plota vários poluentes disponíveis em um gráfico

# python plot_cetesb_timeseries.py \
# --input ../cipc_data/cetesb \
# --stations-file ../cipc_data/cetesb/lista_estacoes.json \
# --station 65 \
# --pollutant all \
# --start 15/08/2024 \
# --end 25/08/2024


# *** Plota somente 1 poluente
# python plot_cetesb_timeseries.py \
# --input ../cipc_data/cetesb \
# --stations-file ../cipc_data/cetesb/lista_estacoes.json \
# --station 65 \
# --pollutant O3 \
# --start 15/08/2024 \
# --end 25/08/2024

# ou:

# python plot_cetesb_timeseries.py \
# --input ../cipc_data/cetesb \
# --stations-file ../cipc_data/cetesb/lista_estacoes.json \
# --station all \
# --pollutant PM25 \
# --start 15/08/2024 \
# --end 25/08/2024

# Resultado:

# múltiplos eixos Y
# cores por poluente
# O3 azul
# NO2 laranja
# SO2 verde
# CO vermelho
# PM10 roxo
# PM25 marrom

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
#     help="""
# Poluente:
# O3
# MP25
# MP10
# NO2
# SO2
# CO
# ou all
# """
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
#     "--output",
#     default="../cipc_output/figures/cetesb",
#     help="Diretório saída"
# )

# args = parser.parse_args()

# INPUT_DIR = args.input
# OUTPUT_DIR = args.output

# POLUENTES_VALIDOS = [
#     "O3",
#     "MP25",
#     "MP10",
#     "NO2",
#     "SO2",
#     "CO"
# ]

# # =========================================================
# # POLUENTES ESCOLHIDOS
# # =========================================================

# if args.pollutant.lower() == "all":

#     poluentes = POLUENTES_VALIDOS

# else:

#     poluentes = [args.pollutant]


# os.makedirs(
#     OUTPUT_DIR,
#     exist_ok=True
# )


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

# if args.station.lower() == "all":

#     estacoes = (
#         df_st["codigo"]
#         .astype(str)
#         .tolist()
#     )

# else:

#     estacoes = [str(args.station)]

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

#         # =====================================================
#         # LIMPA COLUNAS
#         # =====================================================

#         df.columns = [
#             str(c).strip()
#             for c in df.columns
#         ]

#         # =====================================================
#         # REMOVE VAZIOS
#         # =====================================================

#         df = df[
#             df["Data"].notna()
#         ]

#         # =====================================================
#         # DATETIME
#         # =====================================================

#         df["datetime"] = pd.to_datetime(
#             df["Data"].astype(str) + " " + df["Hora"].astype(str),
#             format="%d/%m/%Y %H:%M",
#             errors="coerce"
#         )

#         # =====================================================
#         # FILTRA DATAS
#         # =====================================================

#         df = df[
#             (df["datetime"] >= DATA_INICIO)
#             &
#             (df["datetime"] <= DATA_FIM)
#         ]

#         if df.empty:
#             print("Sem dados no período.")
#             continue

#         # =====================================================
#         # CONCENTRAÇÃO
#         # =====================================================

#         df["Valor Diário"] = (
#             df["Valor Diário"]
#             .astype(str)
#             .str.replace(",", ".", regex=False)
#         )

#         df["Valor Diário"] = pd.to_numeric(
#             df["Valor Diário"],
#             errors="coerce"
#         )


#         # =====================================================
#         # ESTAÇÃO
#         # =====================================================

#         if "estacao_nome" in df.columns:

#             nomes_validos = df["estacao_nome"].dropna()

#             if len(nomes_validos) > 0:

#                 nome_est = nomes_validos.iloc[0]

#             else:

#                 nome_est = str(estacao)

#         else:

#             nome_est = str(estacao) 



#         df["station_name"] = nome_est

#         df["pollutant"] = (
#             df["poluente"]
#             .astype(str)
#             .str.strip()
#         )        

#         todos.append(df)



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

# # =========================================================
# # PLOT
# # =========================================================
# # =========================================================
# # CORES
# # =========================================================

# CORES = {
#     "O3": "blue",
#     "NO2": "orange",
#     "SO2": "green",
#     "CO": "red",
#     "MP10": "purple",
#     "MP25": "brown"
# }

# UNIDADES = {
#     "O3": "µg/m³",
#     "NO2": "µg/m³",
#     "SO2": "µg/m³",
#     "CO": "ppm",
#     "MP10": "µg/m³",
#     "MP25": "µg/m³"
# }

# # =========================================================
# # FIGURA
# # =========================================================

# fig, ax = plt.subplots(
#     figsize=(16,7)
# )

# axes = [ax]

# # =========================================================
# # POLUENTE PRINCIPAL
# # =========================================================

# pol0 = poluentes[0]

# sub0 = final[
#     final["pollutant"] == pol0
# ]

# ax.plot(
#     sub0["datetime"],
#     sub0["Valor Diário"],
#     color=CORES[pol0],
#     label=pol0,
#     linewidth=1.5,
#     marker="o"
# )

# ax.set_ylabel(
#     f"{pol0} ({UNIDADES[pol0]})",
#     color=CORES[pol0],
#     fontsize=12,
#     fontweight="bold"
# )

# ax.tick_params(
#     axis="y",
#     colors=CORES[pol0]
# )

# # =========================================================
# # OUTROS POLUENTES
# # =========================================================

# offset = 0

# for pol in poluentes[1:]:

#     offset += 0.07

#     ax_new = ax.twinx()

#     ax_new.spines["right"].set_position(
#         ("axes", 1 + offset)
#     )

#     sub = final[
#         final["pollutant"] == pol
#     ]

#     ax_new.plot(
#         sub["datetime"],
#         sub["Valor Diário"],
#         color=CORES[pol],
#         label=pol,
#         linewidth=1.5
#     )

#     ax_new.set_ylabel(
#         f"{pol} ({UNIDADES[pol]})",
#         color=CORES[pol],
#         fontsize=12,
#         fontweight="bold"
#     )

#     ax_new.tick_params(
#         axis="y",
#         colors=CORES[pol]
#     )

#     axes.append(ax_new)

# # =========================================================
# # TÍTULO
# # =========================================================

# nome_estacao = (
#     final["station_name"]
#     .iloc[0]
# )

# plt.title(
#     "Qualidade do Ar - Médias Diárias\n"
#     f"Estação: {args.station} - {nome_estacao}\n"
#     f"Período: {args.start} a {args.end}",
#     fontsize=16,
#     fontweight="bold"
# )

# # =========================================================
# # GRID
# # =========================================================

# ax.grid(
#     True,
#     linestyle="--",
#     alpha=0.4
# )

# # =========================================================
# # LEGENDA
# # =========================================================

# lines = []
# labels = []

# for a in axes:

#     lns = a.get_lines()

#     for ln in lns:

#         lines.append(ln)
#         labels.append(ln.get_label())

# ax.legend(
#     lines,
#     labels,
#     loc="upper left"
# )

# plt.xlabel("Data")


# # =========================================================
# # SAVE
# # =========================================================

# output_png = os.path.join(
#     OUTPUT_DIR,
#     f"{args.station}_{args.pollutant}_timeseries_MediaDiaria.png"
# )

# plt.savefig(
#     output_png,
#     dpi=150,
#     bbox_inches="tight"
# )

# print("\n===================================")
# print("FIGURA GERADA")
# print(output_png)
# print("===================================")

# plt.close()





# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-

# """
# Plot CETESB - Série Temporal Média Diária

# Compatível com os CSVs novos:
# 58_O3_Ribeirao_Preto.csv

# ==================================================
# USO
# ==================================================

# python src/processing/plot_cetesb_timeseries_mediaDiaria.py \
#     --input /home/jurandir/cipc_rad/csvs/58_O3_Ribeirao_Preto.csv

# python src/processing/plot_cetesb_timeseries_mediaDiaria.py \
#     --input /home/jurandir/cipc_rad/csvs/58_O3_Ribeirao_Preto.csv \
#     --output ./figures

# ==================================================
# DEPENDÊNCIAS
# ==================================================

# pip install pandas matplotlib
# """

# import os
# import argparse

# import pandas as pd
# import matplotlib.pyplot as plt


# # =========================================================
# # ARGUMENTOS
# # =========================================================

# parser = argparse.ArgumentParser()

# parser.add_argument(
#     "--input",
#     required=True,
#     help="Arquivo CSV CETESB"
# )

# parser.add_argument(
#     "--output",
#     default="./figures",
#     help="Diretório saída"
# )

# args = parser.parse_args()

# INPUT_FILE = args.input
# OUTPUT_DIR = args.output

# os.makedirs(
#     OUTPUT_DIR,
#     exist_ok=True
# )

# # =========================================================
# # LEITURA CSV
# # =========================================================

# print("\n================================")
# print("LENDO CSV")
# print("================================")

# print(INPUT_FILE)

# df = pd.read_csv(
#     INPUT_FILE,
#     sep=";",
#     encoding="utf-8-sig"
# )

# print(df.head())

# # =========================================================
# # VERIFICA CAMPOS
# # =========================================================

# required_cols = [

#     "Data",
#     "Valor Diário",
#     "Nome Estação",
#     "poluente",
#     "Unidade de Medida"
# ]

# for col in required_cols:

#     if col not in df.columns:

#         raise Exception(
#             f"Coluna não encontrada: {col}"
#         )

# # =========================================================
# # CONVERTE DATA
# # =========================================================

# df["datetime"] = pd.to_datetime(
#     df["Data"],
#     format="%d/%m/%Y",
#     errors="coerce"
# )

# # remove inválidos
# df = df.dropna(
#     subset=["datetime"]
# )

# # =========================================================
# # CONVERTE VALORES
# # =========================================================

# df["Valor Diário"] = pd.to_numeric(
#     df["Valor Diário"],
#     errors="coerce"
# )

# df = df.dropna(
#     subset=["Valor Diário"]
# )

# # =========================================================
# # ORDENA
# # =========================================================

# df = df.sort_values(
#     "datetime"
# )

# # =========================================================
# # METADADOS
# # =========================================================

# station_name = (
#     str(df["Nome Estação"].iloc[0])
# )

# pollutant = (
#     str(df["poluente"].iloc[0])
# )

# unit = (
#     str(df["Unidade de Medida"].iloc[0])
# )

# station_code = (
#     str(df["estacao_codigo"].iloc[0])
# )

# # =========================================================
# # PLOT
# # =========================================================

# print("\n================================")
# print("GERANDO FIGURA")
# print("================================")

# fig = plt.figure(
#     figsize=(14, 6)
# )

# ax = fig.add_subplot(111)

# ax.plot(

#     df["datetime"],
#     df["Valor Diário"],

#     linewidth=2,
#     marker="o"
# )

# # =========================================================
# # LABELS
# # =========================================================

# title = (

#     f"CETESB - Média Diária\n"
#     f"{station_name} ({station_code}) - {pollutant}"
# )

# ax.set_title(
#     title,
#     fontsize=14,
#     fontweight="bold"
# )

# ax.set_xlabel(
#     "Data",
#     fontsize=12
# )

# ax.set_ylabel(
#     f"{pollutant} ({unit})",
#     fontsize=12
# )

# # =========================================================
# # GRID
# # =========================================================

# ax.grid(
#     True,
#     linestyle="--",
#     alpha=0.5
# )

# # =========================================================
# # AJUSTES EIXO X
# # =========================================================

# fig.autofmt_xdate()

# # =========================================================
# # OUTPUT
# # =========================================================

# output_name = os.path.basename(
#     INPUT_FILE
# ).replace(".csv", ".png")

# output_path = os.path.join(
#     OUTPUT_DIR,
#     output_name
# )

# plt.tight_layout()

# plt.savefig(
#     output_path,
#     dpi=200,
#     bbox_inches="tight"
# )

# plt.close()

# # =========================================================
# # FINAL
# # =========================================================

# print("\n================================")
# print("FINALIZADO")
# print("================================")

# print("Figura salva:")

# print(output_path)

# print("================================")