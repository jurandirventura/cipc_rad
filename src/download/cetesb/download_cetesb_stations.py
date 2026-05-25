from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

import json
import time

# ======================================================
# FIREFOX
# ======================================================

options = Options()

options.binary_location = (
    "/snap/firefox/current/usr/lib/firefox/firefox"
)

service = Service("/snap/bin/geckodriver")

driver = webdriver.Firefox(
    service=service,
    options=options
)

# ======================================================
# URL
# ======================================================

url = (
    "https://qualar.cetesb.sp.gov.br/qualar/"
    "exportaDados.do?method=filtrarParametros"
)

driver.get(url)

print("\nFaça login manualmente.")
print("Depois pressione ENTER.\n")

input()

time.sleep(3)

# ======================================================
# SELECT ESTAÇÕES
# ======================================================

select_estacao = Select(
    driver.find_element(By.NAME, "estacaoVO.nestcaMonto")
)

options_estacoes = select_estacao.options

stations = []

# ======================================================
# LOOP
# ======================================================

for op in options_estacoes:

    nome = op.text.strip()
    valor = op.get_attribute("value")

    if not valor or valor == "-1":
        continue

    item = {
        "codigo": valor,
        "nome": nome
    }

    stations.append(item)

    print(valor, "=", nome)

# ======================================================
# SAVE
# ======================================================

with open(
    "stations_cetesb.json",
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        stations,
        f,
        ensure_ascii=False,
        indent=4
    )

print("\nTOTAL:", len(stations))

driver.quit()





# # FUNCIONOU LISTANDO NA TELA MAS NÃO SALVOU ARQUIVO
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import Select
# from selenium.webdriver.firefox.options import Options
# from selenium.webdriver.firefox.service import Service

# from bs4 import BeautifulSoup

# import json
# import time
# import random

# # =========================================================
# # FIREFOX / GECKODRIVER
# # =========================================================

# options = Options()

# options.binary_location = (
#     "/snap/firefox/current/usr/lib/firefox/firefox"
# )

# service = Service("/snap/bin/geckodriver")

# driver = webdriver.Firefox(
#     service=service,
#     options=options
# )

# # =========================================================
# # URL
# # =========================================================

# url = (
#     "https://qualar.cetesb.sp.gov.br/qualar/"
#     "exportaDados.do?method=filtrarParametros"
# )

# driver.get(url)

# print("\nAbra o login manualmente no navegador.")
# print("Depois que entrar no QUALAR, pressione ENTER aqui.\n")

# input()

# time.sleep(3)

# # =========================================================
# # SELECT ESTAÇÕES
# # =========================================================

# select_estacao = Select(
#     driver.find_element(By.NAME, "estacaoVO.nestcaMonto")
# )

# options_estacoes = select_estacao.options

# stations = []

# # =========================================================
# # LOOP ESTAÇÕES
# # =========================================================

# for i in range(len(options_estacoes)):

#     try:

#         # recarrega select SEMPRE
#         select_estacao = Select(
#             driver.find_element(By.NAME, "estacaoVO.nestcaMonto")
#         )

#         options_estacoes = select_estacao.options

#         op = options_estacoes[i]

#         nome_select = op.text.strip()
#         valor = op.get_attribute("value")

#         # ignora vazio / selecione
#         if not valor or valor == "-1":

#             print(f"[{i}] IGNORANDO:", nome_select, valor)
#             continue

#         print("\n================================================")
#         print(f"[{i}] TESTANDO ESTAÇÃO")
#         print("NOME SELECT:", nome_select)
#         print("VALUE:", valor)

#         # seleciona estação
#         select_estacao.select_by_value(valor)

#         time.sleep(2)

#         # botão pesquisar
#         botao = driver.find_element(
#             By.XPATH,
#             "//input[@value='Pesquisar']"
#         )

#         botao.click()

#         # aguarda carregar
#         espera = random.uniform(4, 8)

#         print(f"Aguardando {espera:.1f} segundos...")

#         time.sleep(espera)

#         # trata alert
#         try:

#             alert = driver.switch_to.alert

#             print("ALERT:", alert.text)

#             alert.accept()

#             time.sleep(2)

#             continue

#         except:
#             pass

#         html = driver.page_source

#         # salva html debug
#         with open(
#             f"debug_station_{valor}.html",
#             "w",
#             encoding="utf-8"
#         ) as f:

#             f.write(html)

#         soup = BeautifulSoup(html, "html.parser")

#         # =================================================
#         # EXTRAI CÓDIGO / NOME
#         # =================================================

#         codigo_real = None
#         nome_real = None

#         tabelas = soup.find_all("table")

#         for tabela in tabelas:

#             linhas = tabela.find_all("tr")

#             for linha in linhas:

#                 cols = linha.find_all("td")

#                 if len(cols) >= 7:

#                     try:

#                         codigo_tmp = cols[5].get_text(strip=True)
#                         nome_tmp = cols[6].get_text(strip=True)

#                         if codigo_tmp.isdigit():

#                             codigo_real = codigo_tmp
#                             nome_real = nome_tmp

#                             break

#                     except:
#                         pass

#             if codigo_real:
#                 break

#         # =================================================
#         # RESULTADO
#         # =================================================

#         if codigo_real:

#             print("OK")
#             print("CÓDIGO:", codigo_real)
#             print("NOME:", nome_real)

#             item = {
#                 "codigo": codigo_real,
#                 "nome": nome_real,
#                 "valor_select": valor
#             }

#             if item not in stations:
#                 stations.append(item)

#         else:

#             print("SEM DADOS")

#         # volta
#         driver.back()

#         time.sleep(random.uniform(3, 6))

#     except Exception as e:

#         print("ERRO:", e)

#         try:
#             driver.back()
#             time.sleep(5)
#         except:
#             pass

# # =========================================================
# # SALVA JSON
# # =========================================================

# with open(
#     "stations_cetesb.json",
#     "w",
#     encoding="utf-8"
# ) as f:

#     json.dump(
#         stations,
#         f,
#         ensure_ascii=False,
#         indent=4
#     )

# print("\n================================================")
# print("TOTAL ESTAÇÕES:", len(stations))
# print("Arquivo salvo: stations_cetesb.json")

# driver.quit()


# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-

# import requests
# from bs4 import BeautifulSoup
# import json
# import argparse
# from pathlib import Path

# """
# python src/download/cetesb/download_cetesb_stations.py \
#   --user SEU_LOGIN \
#   --password SUA_SENHA \
#   --output ../cipc_data/cetesb/ \
#   --format json
# """

# # =========================================================
# # ARGUMENTOS
# # =========================================================

# parser = argparse.ArgumentParser(
#     description="Download lista de estações CETESB QUALAR"
# )

# parser.add_argument(
#     "--user",
#     required=True,
#     help="Login CETESB"
# )

# parser.add_argument(
#     "--password",
#     required=True,
#     help="Senha CETESB"
# )

# parser.add_argument(
#     "--output",
#     default="../cipc_data/cetesb/",
#     help="Diretório de saída"
# )

# parser.add_argument(
#     "--format",
#     choices=["json", "csv"],
#     default="json",
#     help="Formato de saída"
# )

# args = parser.parse_args()

# USER = args.user
# PASSWORD = args.password

# output_dir = Path(args.output)
# output_dir.mkdir(parents=True, exist_ok=True)

# # =========================================================
# # SESSION
# # =========================================================

# session = requests.Session()

# headers = {
#     "User-Agent": (
#         "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:150.0) "
#         "Gecko/20100101 Firefox/150.0"
#     )
# }

# # =========================================================
# # 1) GET INICIAL
# # =========================================================

# url_login = "https://qualar.cetesb.sp.gov.br/qualar/"

# r0 = session.get(url_login, headers=headers)

# print("GET INICIAL:", r0.status_code)

# # =========================================================
# # 2) LOGIN
# # =========================================================

# payload = {
#     "cetesb_login": USER,
#     "cetesb_password": PASSWORD
# }

# login_url = "https://qualar.cetesb.sp.gov.br/qualar/autenticador"

# r1 = session.post(
#     login_url,
#     data=payload,
#     headers={
#         **headers,
#         "Referer": url_login,
#         "Origin": "https://qualar.cetesb.sp.gov.br"
#     },
#     allow_redirects=True
# )

# print("LOGIN STATUS:", r1.status_code)
# print("LOGIN URL FINAL:", r1.url)

# print("\nCOOKIES:")
# print(session.cookies.get_dict())

# # =========================================================
# # 3) EXPORTA DADOS
# # =========================================================

# export_url = (
#     "https://qualar.cetesb.sp.gov.br/qualar/exportaDados.do"
#     "?method=filtrarParametros"
# )

# r2 = session.get(
#     export_url,
#     headers={
#         **headers,
#         "Referer": "https://qualar.cetesb.sp.gov.br/qualar/"
#     }
# )

# print("\nEXPORT STATUS:", r2.status_code)
# print("EXPORT URL:", r2.url)

# # =========================================================
# # DEBUG HTML
# # =========================================================

# debug_file = output_dir / "debug_exporta.html"

# with open(debug_file, "w", encoding="utf-8") as f:
#     f.write(r2.text)

# print(f"\nHTML salvo em: {debug_file}")

# # =========================================================
# # PARSE HTML
# # =========================================================

# soup = BeautifulSoup(r2.text, "html.parser")

# selects = soup.find_all("select")

# print("\nSELECTS ENCONTRADOS:", len(selects))

# for s in selects:
#     print("ID:", s.get("id"))
#     print("NAME:", s.get("name"))
#     print("-" * 40)

# # =========================================================
# # DROPDOWN ESTAÇÕES
# # =========================================================

# station_select = soup.find(
#     "select",
#     {"name": "estacaoVO.nestcaMonto"}
# )

# if not station_select:
#     raise Exception("Dropdown estações não encontrado")

# # =========================================================
# # LISTA ESTAÇÕES
# # =========================================================

# stations = []

# options = station_select.find_all("option")

# print("\nESTAÇÕES ENCONTRADAS:\n")

# for opt in options:

#     value = opt.get("value", "").strip()
#     text = opt.text.strip()

#     if value:

#         print(f"{value} -> {text}")

#         stations.append({
#             "id": value,
#             "nome": text
#         })

# print(f"\nTOTAL ESTAÇÕES: {len(stations)}")

# # =========================================================
# # SALVAR JSON
# # =========================================================

# if args.format == "json":

#     output_file = output_dir / "stations.json"

#     with open(output_file, "w", encoding="utf-8") as f:
#         json.dump(
#             stations,
#             f,
#             ensure_ascii=False,
#             indent=2
#         )

# # =========================================================
# # SALVAR CSV
# # =========================================================

# elif args.format == "csv":

#     import csv

#     output_file = output_dir / "stations.csv"

#     with open(output_file, "w", newline="", encoding="utf-8") as f:

#         writer = csv.writer(f)

#         writer.writerow(["id", "nome"])

#         for s in stations:
#             writer.writerow([s["id"], s["nome"]])

# print(f"\nArquivo salvo: {output_file}")



# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-

# import os
# import argparse
# import requests
# import pandas as pd

# from bs4 import BeautifulSoup

# """
# download_cetesb_stations.py

# Baixa estações CETESB
# via ArcGIS REST API.

# Saída:
# - json (default)
# - csv
# - txt


# Exemplo de uso:

# python src/download/cetesb/download_cetesb_stations.py

# ou

# python src/download/cetesb/download_cetesb_stations.py \
# --format csv

# ou

# python src/download/cetesb/download_cetesb_stations.py \
# --output ../dados \
# --format json
# """ 

# # =========================================================
# # ARGUMENTOS
# # =========================================================

# parser = argparse.ArgumentParser()

# parser.add_argument(
#     "--output",
#     default="../cipc_data/cetesb",
#     help="Diretório saída"
# )

# parser.add_argument(
#     "--format",
#     default="json",
#     choices=["json", "csv", "txt"],
# )

# args = parser.parse_args()

# OUTPUT_DIR = args.output
# OUTPUT_FORMAT = args.format.lower()

# os.makedirs(
#     OUTPUT_DIR,
#     exist_ok=True
# )

# # =========================================================
# # URL QUALAR
# # =========================================================

# URL = (
#     "https://qualar.cetesb.sp.gov.br/"
#     "qualar/exportaDados.do?method=filtrarParametros"
# )

# # =========================================================
# # SESSION
# # =========================================================

# session = requests.Session()

# headers = {
#     "User-Agent":
#         "Mozilla/5.0 (X11; Ubuntu; Linux x86_64)"
# }

# print("\nAcessando QUALAR...")

# r = session.get(
#     URL,
#     headers=headers,
#     timeout=60
# )

# print("STATUS:", r.status_code)

# print("\nTAMANHO HTML:", len(r.text))

# with open("debug_qualar.html", "w", encoding="utf-8") as f:
#     f.write(r.text)

# print("\nHTML salvo: debug_qualar.html")

# if r.status_code != 200:
#     raise Exception("Erro acesso QUALAR")

# # =========================================================
# # PARSE HTML
# # =========================================================

# soup = BeautifulSoup(
#     r.text,
#     "html.parser"
# )

# # =========================================================
# # DEBUG
# # =========================================================

# print("\nSELECTS ENCONTRADOS:\n")

# for s in soup.find_all("select"):

#     print(
#         "NAME:",
#         s.get("name"),
#         "ID:",
#         s.get("id")
#     )

# # =========================================================
# # TENTA ENCONTRAR SELECT ESTAÇÕES
# # =========================================================

# select_estacoes = None

# for s in soup.find_all("select"):

#     texto = str(s).lower()

#     if (
#         "estacao" in texto
#         or "estação" in texto
#     ):

#         select_estacoes = s
#         break

# if select_estacoes is None:

#     raise Exception(
#         "Dropdown estações não encontrado"
#     )

# # =========================================================
# # EXTRAI OPTIONS
# # =========================================================

# lista = []

# options = select_estacoes.find_all("option")

# print(f"\nTotal options: {len(options)}")

# for opt in options:

#     codigo = (
#         opt.get("value", "")
#         .strip()
#     )

#     nome = (
#         opt.text
#         .strip()
#     )

#     if not codigo:
#         continue

#     if nome == "":
#         continue

#     registro = {
#         "codigo_qualar": codigo,
#         "nome": nome
#     }

#     lista.append(registro)

# # =========================================================
# # DATAFRAME
# # =========================================================

# df = pd.DataFrame(lista)

# # remove duplicados
# df = df.drop_duplicates()

# # ordena
# df = df.sort_values(
#     by="nome"
# )

# # =========================================================
# # OUTPUT
# # =========================================================

# output_file = os.path.join(
#     OUTPUT_DIR,
#     f"lista_estacoes_qualar.{OUTPUT_FORMAT}"
# )

# if OUTPUT_FORMAT == "json":

#     df.to_json(
#         output_file,
#         orient="records",
#         force_ascii=False,
#         indent=2
#     )

# elif OUTPUT_FORMAT == "csv":

#     df.to_csv(
#         output_file,
#         sep=";",
#         index=False,
#         encoding="utf-8"
#     )

# elif OUTPUT_FORMAT == "txt":

#     df.to_csv(
#         output_file,
#         sep="\t",
#         index=False,
#         encoding="utf-8"
#     )

# # =========================================================
# # FINAL
# # =========================================================

# print("\n================================")
# print("ARQUIVO GERADO")
# print(output_file)
# print("================================")

# print("\nEXEMPLO:\n")

# print(
#     df.head(20).to_string(index=False)
# )


# ***- Número de estação Arcgis - Não corresponde com 
#      as opções Consultar/Exportar ou Exportar avançado
# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-

# """
# download_cetesb_stations.py

# Baixa estações CETESB
# via ArcGIS REST API.

# Saída:
# - json (default)
# - csv
# - txt


# Exemplo de uso:

# python src/download/cetesb/download_cetesb_stations.py

# ou

# python src/download/cetesb/download_cetesb_stations.py \
# --format csv

# ou

# python src/download/cetesb/download_cetesb_stations.py \
# --output ../dados \
# --format json
# """ 


# import os
# import argparse
# import requests
# import pandas as pd

# from pyproj import Transformer

# # =========================================================
# # ARGUMENTOS
# # =========================================================

# parser = argparse.ArgumentParser()

# parser.add_argument(
#     "--output",
#     default="../cipc_data/cetesb",
#     help="Diretório saída"
# )

# parser.add_argument(
#     "--format",
#     default="json",
#     choices=["json", "csv", "txt"],
#     help="Formato saída"
# )

# args = parser.parse_args()

# OUTPUT_DIR = args.output
# OUTPUT_FORMAT = args.format.lower()

# os.makedirs(
#     OUTPUT_DIR,
#     exist_ok=True
# )

# # =========================================================
# # URL ESTAÇÕES CETESB
# # =========================================================

# URL = (
#     "https://arcgis.cetesb.sp.gov.br/"
#     "server/rest/services/"
#     "ESTA%C3%87%C3%95ES_QUALIDADE_DO_AR_2023/"
#     "MapServer/0/query"
# )

# PARAMS = {
#     "where": "1=1",
#     "outFields": "*",
#     "returnGeometry": "true",
#     "f": "json"
# }

# # =========================================================
# # DOWNLOAD
# # =========================================================

# print("\nBaixando estações CETESB...")

# response = requests.get(
#     URL,
#     params=PARAMS,
#     timeout=60
# )

# print("STATUS:", response.status_code)

# if response.status_code != 200:

#     raise Exception(
#         "Erro acesso API ArcGIS CETESB"
#     )

# data = response.json()

# if "features" not in data:

#     raise Exception(
#         "Nenhuma feature encontrada"
#     )

# features = data["features"]

# print(f"Total features: {len(features)}")

# if len(features) == 0:

#     raise Exception(
#         "API retornou 0 features"
#     )

# # =========================================================
# # DEBUG PRIMEIRA FEATURE
# # =========================================================

# print("\nPRIMEIRA FEATURE:\n")

# print(features[0])

# # =========================================================
# # CONVERSOR UTM -> LAT/LON
# # =========================================================
# #
# # Dados CETESB:
# # EPSG:31983
# # SIRGAS 2000 / UTM zone 23S
# #
# # Conversão para:
# # EPSG:4326 (WGS84)
# #
# # =========================================================

# transformer = Transformer.from_crs(
#     "EPSG:31983",
#     "EPSG:4326",
#     always_xy=True
# )

# # =========================================================
# # PARSE
# # =========================================================

# lista = []

# for feat in features:

#     attr = feat.get("attributes", {})

#     # =====================================================
#     # COORDENADAS UTM
#     # =====================================================

#     x_utm = attr.get("LONGITUDE")
#     y_utm = attr.get("LATITUDE")

#     latitude = None
#     longitude = None

#     # =====================================================
#     # CONVERTE PARA GRAUS DECIMAIS
#     # =====================================================

#     if x_utm and y_utm:

#         try:

#             lon, lat = transformer.transform(
#                 x_utm,
#                 y_utm
#             )

#             latitude = round(lat, 6)
#             longitude = round(lon, 6)

#         except Exception as e:

#             print(
#                 "Erro conversão coordenadas:",
#                 e
#             )

#     # =====================================================
#     # REGISTRO
#     # =====================================================

#     registro = {

#         # código interno
#         "codigo":
#             attr.get("FID"),

#         # município
#         "nome":
#             attr.get("Município"),

#         # automática/manual
#         "tipo":
#             attr.get("TIPO"),

#         # coordenadas convertidas
#         "latitude":
#             latitude,

#         "longitude":
#             longitude,

#         # não disponível
#         "altitude":
#             None,

#         # links úteis
#         "link_qualar":
#             attr.get("Link"),

#         "link_mapa":
#             attr.get("Link2")
#     }

#     lista.append(registro)

# # =========================================================
# # DATAFRAME
# # =========================================================

# df = pd.DataFrame(lista)

# # remove totalmente vazios
# df = df.dropna(
#     how="all"
# )

# # =========================================================
# # OUTPUT
# # =========================================================

# output_file = os.path.join(
#     OUTPUT_DIR,
#     f"lista_estacoes.{OUTPUT_FORMAT}"
# )

# # JSON
# if OUTPUT_FORMAT == "json":

#     df.to_json(
#         output_file,
#         orient="records",
#         force_ascii=False,
#         indent=2
#     )

# # CSV
# elif OUTPUT_FORMAT == "csv":

#     df.to_csv(
#         output_file,
#         sep=";",
#         index=False,
#         encoding="utf-8"
#     )

# # TXT
# elif OUTPUT_FORMAT == "txt":

#     df.to_csv(
#         output_file,
#         sep="\t",
#         index=False,
#         encoding="utf-8"
#     )

# # =========================================================
# # FINAL
# # =========================================================

# print("\n===================================")
# print("ARQUIVO GERADO")
# print(output_file)
# print("===================================")

# print("\nEXEMPLO:\n")

# print(
#     df.head(10).to_string(index=False)
# )