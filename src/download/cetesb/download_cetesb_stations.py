#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
download_cetesb_stations.py

Baixa estações CETESB
via ArcGIS REST API.

Saída:
- json (default)
- csv
- txt


Exemplo de uso:

python src/download/cetesb/download_cetesb_stations.py

ou

python src/download/cetesb/download_cetesb_stations.py \
--format csv

ou

python src/download/cetesb/download_cetesb_stations.py \
--output ../dados \
--format json
""" 


import os
import argparse
import requests
import pandas as pd

from pyproj import Transformer

# =========================================================
# ARGUMENTOS
# =========================================================

parser = argparse.ArgumentParser()

parser.add_argument(
    "--output",
    default="../cipc_data/cetesb",
    help="Diretório saída"
)

parser.add_argument(
    "--format",
    default="json",
    choices=["json", "csv", "txt"],
    help="Formato saída"
)

args = parser.parse_args()

OUTPUT_DIR = args.output
OUTPUT_FORMAT = args.format.lower()

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

# =========================================================
# URL ESTAÇÕES CETESB
# =========================================================

URL = (
    "https://arcgis.cetesb.sp.gov.br/"
    "server/rest/services/"
    "ESTA%C3%87%C3%95ES_QUALIDADE_DO_AR_2023/"
    "MapServer/0/query"
)

PARAMS = {
    "where": "1=1",
    "outFields": "*",
    "returnGeometry": "true",
    "f": "json"
}

# =========================================================
# DOWNLOAD
# =========================================================

print("\nBaixando estações CETESB...")

response = requests.get(
    URL,
    params=PARAMS,
    timeout=60
)

print("STATUS:", response.status_code)

if response.status_code != 200:

    raise Exception(
        "Erro acesso API ArcGIS CETESB"
    )

data = response.json()

if "features" not in data:

    raise Exception(
        "Nenhuma feature encontrada"
    )

features = data["features"]

print(f"Total features: {len(features)}")

if len(features) == 0:

    raise Exception(
        "API retornou 0 features"
    )

# =========================================================
# DEBUG PRIMEIRA FEATURE
# =========================================================

print("\nPRIMEIRA FEATURE:\n")

print(features[0])

# =========================================================
# CONVERSOR UTM -> LAT/LON
# =========================================================
#
# Dados CETESB:
# EPSG:31983
# SIRGAS 2000 / UTM zone 23S
#
# Conversão para:
# EPSG:4326 (WGS84)
#
# =========================================================

transformer = Transformer.from_crs(
    "EPSG:31983",
    "EPSG:4326",
    always_xy=True
)

# =========================================================
# PARSE
# =========================================================

lista = []

for feat in features:

    attr = feat.get("attributes", {})

    # =====================================================
    # COORDENADAS UTM
    # =====================================================

    x_utm = attr.get("LONGITUDE")
    y_utm = attr.get("LATITUDE")

    latitude = None
    longitude = None

    # =====================================================
    # CONVERTE PARA GRAUS DECIMAIS
    # =====================================================

    if x_utm and y_utm:

        try:

            lon, lat = transformer.transform(
                x_utm,
                y_utm
            )

            latitude = round(lat, 6)
            longitude = round(lon, 6)

        except Exception as e:

            print(
                "Erro conversão coordenadas:",
                e
            )

    # =====================================================
    # REGISTRO
    # =====================================================

    registro = {

        # código interno
        "codigo":
            attr.get("FID"),

        # município
        "nome":
            attr.get("Município"),

        # automática/manual
        "tipo":
            attr.get("TIPO"),

        # coordenadas convertidas
        "latitude":
            latitude,

        "longitude":
            longitude,

        # não disponível
        "altitude":
            None,

        # links úteis
        "link_qualar":
            attr.get("Link"),

        "link_mapa":
            attr.get("Link2")
    }

    lista.append(registro)

# =========================================================
# DATAFRAME
# =========================================================

df = pd.DataFrame(lista)

# remove totalmente vazios
df = df.dropna(
    how="all"
)

# =========================================================
# OUTPUT
# =========================================================

output_file = os.path.join(
    OUTPUT_DIR,
    f"lista_estacoes.{OUTPUT_FORMAT}"
)

# JSON
if OUTPUT_FORMAT == "json":

    df.to_json(
        output_file,
        orient="records",
        force_ascii=False,
        indent=2
    )

# CSV
elif OUTPUT_FORMAT == "csv":

    df.to_csv(
        output_file,
        sep=";",
        index=False,
        encoding="utf-8"
    )

# TXT
elif OUTPUT_FORMAT == "txt":

    df.to_csv(
        output_file,
        sep="\t",
        index=False,
        encoding="utf-8"
    )

# =========================================================
# FINAL
# =========================================================

print("\n===================================")
print("ARQUIVO GERADO")
print(output_file)
print("===================================")

print("\nEXEMPLO:\n")

print(
    df.head(10).to_string(index=False)
)