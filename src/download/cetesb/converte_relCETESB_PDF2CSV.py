#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Converte PDF CETESB -> CSV

Cada página do PDF gera 1 CSV.

Agora:
- usa lista_estacoes.json
- inclui código da estação
- inclui unidade_medida
- salva:
  <codigo>_<nome_estacao>_<poluente>.csv

Ex:
72_Parque_DPedro_MP10.csv

==================================================
USO
==================================================

python pdf_cetesb_to_csv.py \
    --pdf relatorio.pdf \
    --output ./csvs \
    --list-stations /home/jurandir/cipc_data/cetesb/lista_estacoes.json

python src/download/cetesb/converte_relCETESB_PDF2CSV.py \
    --pdf /home/jurandir/cipc_data/cetesb/relatorio_geral_15a25ago2024_all.pdf \
    --output ./csvs \ 
    --list-stations /home/jurandir/cipc_data/cetesb/lista_estacoes.json

==================================================
DEPENDÊNCIAS
==================================================

pip install pdfplumber pandas
"""

import os
import re
import json
import argparse

import pdfplumber
import pandas as pd


# =========================================================
# ARGUMENTOS
# =========================================================

parser = argparse.ArgumentParser()

parser.add_argument(
    "--pdf",
    required=True,
    help="Arquivo PDF"
)

parser.add_argument(
    "--output",
    default="./csvs",
    help="Diretório saída"
)

parser.add_argument(
    "--list-stations",
    required=True,
    help="JSON lista estações"
)

args = parser.parse_args()

PDF_FILE = args.pdf
OUTPUT_DIR = args.output
STATIONS_JSON = args.list_stations

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

# =========================================================
# MAPA POLUENTES
# =========================================================

POL_MAP = {

    "MP10": "MP10",
    "MP2.5": "MP25",
    "MP2,5": "MP25",

    "SO2": "SO2",

    "NO": "NO",
    "NO2": "NO2",
    "NOX": "NOx",
    "NOx": "NOx",

    "CO": "CO",
    "O3": "O3",

    "BEN": "BEN",
    "TOL": "TOL",

    "PRESS": "PRESS",
    "RADG": "RADG",
    "RADUV": "RADUV",

    "TEMP": "TEMP",
    "UR": "UR",
    "VV": "VV",

    "ERT": "ERT"
}

# =========================================================
# LOAD ESTAÇÕES
# =========================================================

print("\nCarregando lista estações...")

with open(
    STATIONS_JSON,
    "r",
    encoding="utf-8"
) as f:

    stations_data = json.load(f)

stations_lookup = {}

for st in stations_data:

    nome = st["nome"].strip().lower()

    stations_lookup[nome] = {

        "codigo": str(st["codigo"]),
        "nome": st["nome"]
    }

print(
    f"Estações carregadas: "
    f"{len(stations_lookup)}"
)

# =========================================================
# LIMPA NOME
# =========================================================

def sanitize_filename(text):

    if text is None:
        return "UNKNOWN"

    text = str(text)

    replace_map = {

        "á": "a",
        "à": "a",
        "ã": "a",
        "â": "a",

        "é": "e",
        "ê": "e",

        "í": "i",

        "ó": "o",
        "ô": "o",
        "õ": "o",

        "ú": "u",

        "ç": "c",

        "Á": "A",
        "À": "A",
        "Ã": "A",
        "Â": "A",

        "É": "E",
        "Ê": "E",

        "Í": "I",

        "Ó": "O",
        "Ô": "O",
        "Õ": "O",

        "Ú": "U",

        "Ç": "C"
    }

    for k, v in replace_map.items():

        text = text.replace(k, v)

    text = text.replace(".", "")
    text = text.replace("-", "_")
    text = text.replace("/", "_")
    text = text.replace("\\", "_")

    text = re.sub(
        r"\s+",
        "_",
        text
    )

    text = re.sub(
        r"[^a-zA-Z0-9_]",
        "",
        text
    )

    text = re.sub(
        r"_+",
        "_",
        text
    )

    return text.strip("_")

# =========================================================
# METADADOS
# =========================================================

def extract_metadata(text):

    meta = {}

    # -----------------------------------------------------
    # ESTAÇÃO
    # -----------------------------------------------------

    m = re.search(
        r"Estação:\s*(.+)",
        text,
        re.IGNORECASE
    )

    if m:

        station_name = (
            m.group(1)
            .strip()
        )

    else:

        station_name = "UNKNOWN"

    meta["station_name"] = station_name

    # -----------------------------------------------------
    # CÓDIGO ESTAÇÃO
    # -----------------------------------------------------

    station_key = station_name.lower()

    if station_key in stations_lookup:

        meta["station_code"] = (
            stations_lookup[station_key]["codigo"]
        )

    else:

        meta["station_code"] = "000"

    # -----------------------------------------------------
    # UNIDADE
    # -----------------------------------------------------

    m = re.search(
        r"Unidade de Medida:\s*(.+?)\s+PQAR",
        text,
        re.IGNORECASE
    )

    if m:

        unidade = (
            m.group(1)
            .strip()
        )

    else:

        unidade = ""

    meta["unidade_medida"] = unidade

    # -----------------------------------------------------
    # PARÂMETRO
    # -----------------------------------------------------

    m = re.search(

        r"Parâmetro:\s*"
        r"(\d+)\s*-\s*"
        r"([A-Za-z0-9\.,]+)",

        text,
        re.IGNORECASE
    )

    if m:

        pollutant_code = m.group(1)

        pollutant = (
            m.group(2)
            .strip()
        )

        pollutant = POL_MAP.get(
            pollutant,
            pollutant
        )

    else:

        pollutant_code = ""
        pollutant = "UNKNOWN"

    meta["pollutant"] = pollutant
    meta["pollutant_code"] = pollutant_code

    return meta

# =========================================================
# EXTRAI TABELA
# =========================================================

def extract_table(page):

    tables = page.extract_tables()

    if not tables:
        return None

    best_table = None
    best_rows = 0

    for table in tables:

        if table is None:
            continue

        if len(table) > best_rows:

            best_rows = len(table)
            best_table = table

    if best_table is None:
        return None

    if len(best_table) < 2:
        return None

    header = best_table[0]

    rows = best_table[1:]

    header = [

        str(h).replace("\n", " ").strip()

        if h is not None else ""

        for h in header
    ]

    df = pd.DataFrame(
        rows,
        columns=header
    )

    return df

# =========================================================
# PROCESSAMENTO
# =========================================================

print("\n================================")
print("PDF:", PDF_FILE)
print("================================")

total_csv = 0

with pdfplumber.open(PDF_FILE) as pdf:

    total_pages = len(pdf.pages)

    print(
        f"\nTOTAL PÁGINAS: {total_pages}"
    )

    for idx, page in enumerate(pdf.pages):

        page_num = idx + 1

        print("\n--------------------------------")
        print(
            f"Página {page_num}/{total_pages}"
        )
        print("--------------------------------")

        try:

            text = page.extract_text()

            if not text:

                print("Sem texto.")
                continue

            # =================================================
            # METADADOS
            # =================================================

            meta = extract_metadata(text)

            station_name = meta["station_name"]

            station_code = meta["station_code"]

            pollutant = meta["pollutant"]

            pollutant_code = (
                meta["pollutant_code"]
            )

            unidade_medida = (
                meta["unidade_medida"]
            )

            print("Estação:", station_name)

            print("Código:", station_code)

            print("Poluente:", pollutant)

            print("Unidade:", unidade_medida)

            # =================================================
            # TABELA
            # =================================================

            df = extract_table(page)

            if df is None:

                print("Tabela não encontrada.")
                continue

            if df.shape[0] == 0:

                print("Tabela vazia.")
                continue

            # =================================================
            # REMOVE RESUMO
            # =================================================

            primeira_coluna = df.columns[0]

            df = df[
                ~df[primeira_coluna]
                .astype(str)
                .str.contains(
                    "Média|Mínima|Máxima|N. dias|Total",
                    case=False,
                    na=False
                )
            ]

            # =================================================
            # CAMPOS EXTRA
            # =================================================

            df["poluente"] = pollutant

            df["poluente_codigo"] = pollutant_code

            df["estacao_codigo"] = station_code

            df["estacao_nome"] = station_name

            df["unidade_medida"] = unidade_medida

            # =================================================
            # CSV
            # =================================================

            station_clean = sanitize_filename(
                station_name
            )

            pollutant_clean = sanitize_filename(
                pollutant
            )

            # csv_name = (
            #     f"{station_code}_"
            #     f"{station_clean}_"
            #     f"{pollutant_clean}.csv"
            # )

            csv_name = (
                f"{station_code}_"
                f"{pollutant_clean}_"
                f"{station_clean}.csv"
            )


            csv_path = os.path.join(
                OUTPUT_DIR,
                csv_name
            )

            df.to_csv(
                csv_path,
                sep=";",
                index=False,
                encoding="utf-8-sig"
            )

            print(
                f"CSV salvo: {csv_name}"
            )

            total_csv += 1

        except Exception as e:

            print("ERRO:", e)

# =========================================================
# FINAL
# =========================================================

print("\n================================")
print("FINALIZADO")
print("================================")

print("CSV gerados:", total_csv)

print("Saída:", OUTPUT_DIR)

print("================================")


# *** - Funcionando bem.... Falta unidade e código da estação
# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-

# """
# Converte PDF CETESB -> CSV

# Cada página do PDF gera 1 CSV.

# Nome saída:
# <ESTACAO>_<POLUENTE>.csv

# Ex:
# Parque_DPedro_MP10.csv
# SJose_Campos_O3.csv

# ==================================================
# USO
# ==================================================

# python pdf_cetesb_to_csv.py \
#     --pdf relatorio.pdf \
#     --output ./csvs

# ==================================================
# DEPENDÊNCIAS
# ==================================================

# pip install pdfplumber pandas
# """

# import os
# import re
# import argparse
# import pdfplumber
# import pandas as pd


# # =========================================================
# # ARGUMENTOS
# # =========================================================

# parser = argparse.ArgumentParser()

# parser.add_argument(
#     "--pdf",
#     required=True,
#     help="Arquivo PDF"
# )

# parser.add_argument(
#     "--output",
#     default="./csvs",
#     help="Diretório saída"
# )

# args = parser.parse_args()

# PDF_FILE = args.pdf
# OUTPUT_DIR = args.output

# os.makedirs(
#     OUTPUT_DIR,
#     exist_ok=True
# )

# # =========================================================
# # POLUENTES
# # =========================================================

# POL_MAP = {

#     "MP10": "MP10",
#     "MP2.5": "MP25",
#     "MP2,5": "MP25",

#     "SO2": "SO2",

#     "NO": "NO",
#     "NO2": "NO2",
#     "NOX": "NOx",
#     "NOx": "NOx",

#     "CO": "CO",
#     "O3": "O3",

#     "BEN": "BEN",
#     "TOL": "TOL",

#     "PRESS": "PRESS",
#     "RADG": "RADG",
#     "RADUV": "RADUV",

#     "TEMP": "TEMP",
#     "UR": "UR",
#     "VV": "VV",

#     "ERT": "ERT"
# }

# # =========================================================
# # LIMPA TEXTO
# # =========================================================

# def sanitize_filename(text):

#     if text is None:
#         return "UNKNOWN"

#     text = str(text)

#     # remove acentos simples
#     replace_map = {

#         "á": "a",
#         "à": "a",
#         "ã": "a",
#         "â": "a",

#         "é": "e",
#         "ê": "e",

#         "í": "i",

#         "ó": "o",
#         "ô": "o",
#         "õ": "o",

#         "ú": "u",

#         "ç": "c",

#         "Á": "A",
#         "À": "A",
#         "Ã": "A",
#         "Â": "A",

#         "É": "E",
#         "Ê": "E",

#         "Í": "I",

#         "Ó": "O",
#         "Ô": "O",
#         "Õ": "O",

#         "Ú": "U",

#         "Ç": "C"
#     }

#     for k, v in replace_map.items():
#         text = text.replace(k, v)

#     # remove caracteres especiais
#     text = text.replace(".", "")
#     text = text.replace("-", "_")
#     text = text.replace("/", "_")
#     text = text.replace("\\", "_")

#     # espaços -> underline
#     text = re.sub(r"\s+", "_", text)

#     # remove caracteres inválidos
#     text = re.sub(
#         r"[^a-zA-Z0-9_]",
#         "",
#         text
#     )

#     # remove underscores duplicados
#     text = re.sub(
#         r"_+",
#         "_",
#         text
#     )

#     return text.strip("_")


# # =========================================================
# # EXTRAI METADADOS
# # =========================================================

# def extract_metadata(text):

#     meta = {}

#     # -----------------------------------------------------
#     # ESTAÇÃO
#     # -----------------------------------------------------

#     m = re.search(
#         r"Estação:\s*(.+)",
#         text,
#         re.IGNORECASE
#     )

#     if m:

#         station = (
#             m.group(1)
#             .strip()
#         )

#         meta["station_name"] = station

#     else:

#         meta["station_name"] = "UNKNOWN"

#     # -----------------------------------------------------
#     # PARÂMETRO
#     # -----------------------------------------------------

#     m = re.search(

#         r"Parâmetro:\s*"
#         r"(\d+)\s*-\s*"
#         r"([A-Za-z0-9\.,]+)",

#         text,
#         re.IGNORECASE
#     )

#     if m:

#         pol_code = m.group(1)

#         pol_name = (
#             m.group(2)
#             .strip()
#         )

#         pol_name = POL_MAP.get(
#             pol_name,
#             pol_name
#         )

#         meta["pollutant_code"] = pol_code
#         meta["pollutant"] = pol_name

#     else:

#         meta["pollutant_code"] = ""
#         meta["pollutant"] = "UNKNOWN"

#     return meta


# # =========================================================
# # EXTRAI TABELA
# # =========================================================

# def extract_table(page):

#     tables = page.extract_tables()

#     if not tables:
#         return None

#     best_table = None
#     best_rows = 0

#     for table in tables:

#         if table is None:
#             continue

#         if len(table) > best_rows:

#             best_rows = len(table)
#             best_table = table

#     if best_table is None:
#         return None

#     if len(best_table) < 2:
#         return None

#     header = best_table[0]
#     rows = best_table[1:]

#     # limpa header
#     header = [

#         str(h).replace("\n", " ").strip()

#         if h is not None else ""

#         for h in header
#     ]

#     df = pd.DataFrame(
#         rows,
#         columns=header
#     )

#     return df


# # =========================================================
# # PROCESSAMENTO
# # =========================================================

# print("\n================================")
# print("PDF:", PDF_FILE)
# print("================================")

# total_csv = 0

# with pdfplumber.open(PDF_FILE) as pdf:

#     total_pages = len(pdf.pages)

#     print(
#         f"\nTOTAL PÁGINAS: {total_pages}"
#     )

#     for idx, page in enumerate(pdf.pages):

#         page_num = idx + 1

#         print("\n--------------------------------")
#         print(
#             f"Página {page_num}/{total_pages}"
#         )
#         print("--------------------------------")

#         try:

#             text = page.extract_text()

#             if not text:

#                 print("Sem texto.")
#                 continue

#             # =================================================
#             # METADADOS
#             # =================================================

#             meta = extract_metadata(text)

#             station_name = meta["station_name"]

#             pollutant = meta["pollutant"]

#             pollutant_code = (
#                 meta["pollutant_code"]
#             )

#             print("Estação:", station_name)

#             print("Poluente:", pollutant)

#             # =================================================
#             # TABELA
#             # =================================================

#             df = extract_table(page)

#             if df is None:

#                 print("Tabela não encontrada.")
#                 continue

#             if df.shape[0] == 0:

#                 print("Tabela vazia.")
#                 continue

#             # =================================================
#             # REMOVE RESUMO
#             # =================================================

#             # remove linhas:
#             # Média Aritmética
#             # Mínima
#             # Máxima

#             primeira_coluna = df.columns[0]

#             df = df[
#                 ~df[primeira_coluna]
#                 .astype(str)
#                 .str.contains(
#                     "Média|Mínima|Máxima|N. dias|Total",
#                     case=False,
#                     na=False
#                 )
#             ]

#             # =================================================
#             # CAMPOS EXTRA
#             # =================================================

#             df["poluente"] = pollutant

#             df["poluente_codigo"] = pollutant_code

#             df["estacao_nome"] = station_name

#             # =================================================
#             # NOME CSV
#             # =================================================

#             station_clean = sanitize_filename(
#                 station_name
#             )

#             pol_clean = sanitize_filename(
#                 pollutant
#             )

#             csv_name = (
#                 f"{station_clean}"
#                 f"_{pol_clean}.csv"
#             )

#             csv_path = os.path.join(
#                 OUTPUT_DIR,
#                 csv_name
#             )

#             # =================================================
#             # SALVA CSV
#             # =================================================

#             df.to_csv(
#                 csv_path,
#                 sep=";",
#                 index=False,
#                 encoding="utf-8-sig"
#             )

#             print(
#                 f"CSV salvo: {csv_name}"
#             )

#             total_csv += 1

#         except Exception as e:

#             print("ERRO:", e)

# # =========================================================
# # FINAL
# # =========================================================

# print("\n================================")
# print("FINALIZADO")
# print("================================")

# print("CSV gerados:", total_csv)

# print("Saída:", OUTPUT_DIR)

# print("================================")

