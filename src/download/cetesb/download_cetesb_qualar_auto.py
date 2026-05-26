# Gera listagem json saída com lat/lon da estação CETESB
# Executa todo o processo automaticamente.

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=============================================================
DOWNLOAD CETESB QUALAR
=============================================================

FUNCIONALIDADES
-------------------------------------------------------------
1) Login automático usando .env
2) Geração automática da lista de estações
3) Download automático dos dados
4) Exporta CSV / TXT / JSON
5) Suporta:
   - uma estação
   - todas as estações
6) Selenium somente para obter lista estações
7) Requests para download rápido dos dados

=============================================================
EXEMPLOS
=============================================================

# Gerar lista estações
python download_cetesb_qualar_auto.py \
--list-stations

# Baixar UMA estação
python download_cetesb_qualar_auto.py \
--station 106 \
--start 15/08/2024 \
--end 25/08/2024

# Baixar TODAS
python download_cetesb_qualar_auto.py \
--station all \
--start 15/08/2024 \
--end 25/08/2024

=============================================================
.ARQUIVO .ENV
=============================================================

CETESB_USER=seu_email
CETESB_PASS=sua_senha

=============================================================
"""

import os
import json
import time
import argparse
from io import StringIO

import pandas as pd
import requests

from pyproj import Transformer

from bs4 import BeautifulSoup
from dotenv import load_dotenv

# =========================================================
# SELENIUM
# =========================================================

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    UnexpectedAlertPresentException,
    TimeoutException
)

# =========================================================
# ENV
# =========================================================

load_dotenv()

USERNAME = os.getenv("CETESB_USER")
PASSWORD = os.getenv("CETESB_PASS")

if not USERNAME or not PASSWORD:

    raise Exception(
        "Variáveis CETESB_USER e CETESB_PASS não encontradas."
    )

# =========================================================
# ARGUMENTOS
# =========================================================

parser = argparse.ArgumentParser()

parser.add_argument(
    "--station",
    default="all",
    help="Código estação ou all"
)

parser.add_argument(
    "--start",
    default="15/08/2024",
    help="Data inicial"
)

parser.add_argument(
    "--end",
    default="25/08/2024",
    help="Data final"
)

parser.add_argument(
    "--output",
    default="../cipc_data/cetesb",
    help="Diretório saída"
)

parser.add_argument(
    "--format",
    default="csv",
    choices=["csv", "txt", "json"]
)

parser.add_argument(
    "--list-stations",
    action="store_true"
)

args = parser.parse_args()

OUTPUT_DIR = args.output
OUTPUT_FORMAT = args.format.lower()

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

# =========================================================
# POLUENTES
# =========================================================

POLUENTES = {
    "SO2": 13,
    "NO2": 15,
    "CO": 16,
    "MP10": 12,
    "MP25": 57,
    "O3": 63
}

# =========================================================
# URLS
# =========================================================

HOME_URL = (
    "https://qualar.cetesb.sp.gov.br/"
    "qualar/home.do"
)

LOGIN_URL = (
    "https://qualar.cetesb.sp.gov.br/"
    "qualar/autenticador"
)

QUERY_URL = (
    "https://qualar.cetesb.sp.gov.br/"
    "qualar/exportaDados.do"
)

EXPORT_URL = (
    "https://qualar.cetesb.sp.gov.br/"
    "qualar/exportaDados.do?method=filtrarParametros"
)

# =========================================================
# HEADERS
# =========================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64)"
    )
}

# =========================================================
# LOGIN REQUESTS
# =========================================================

print("\n================================================")
print("LOGIN REQUESTS")
print("================================================")

session = requests.Session()

session.get(
    HOME_URL,
    headers=HEADERS
)

payload_login = {
    "cetesb_login": USERNAME,
    "cetesb_password": PASSWORD,
    "enviar": "OK"
}

r_login = session.post(
    LOGIN_URL,
    data=payload_login,
    headers=HEADERS,
    allow_redirects=True
)

texto_login = BeautifulSoup(
    r_login.text,
    "html.parser"
).get_text(
    separator=" ",
    strip=True
)

if (
    "Login:" in texto_login
    or "Senha:" in texto_login
    or "Não sou Cadastrado" in texto_login
):

    raise Exception("LOGIN FALHOU")

print("LOGIN OK")

# =========================================================
# SELENIUM FIREFOX
# =========================================================

print("\n================================================")
print("ABRINDO FIREFOX")
print("================================================")

options = Options()

options.binary_location = (
    "/snap/firefox/current/usr/lib/firefox/firefox"
)

service = Service(
    "/snap/bin/geckodriver"
)

driver = webdriver.Firefox(
    service=service,
    options=options
)

# =========================================================
# ABRE QUALAR
# =========================================================

driver.get(EXPORT_URL)
time.sleep(3)

# =========================================================
# LOGIN AUTOMÁTICO SELENIUM
# =========================================================

print("FAZENDO LOGIN SELENIUM...")

try:

    campo_user = driver.find_element(
        By.NAME,
        "cetesb_login"
    )

    campo_pass = driver.find_element(
        By.NAME,
        "cetesb_password"
    )

    campo_user.send_keys(USERNAME)
    campo_pass.send_keys(PASSWORD)

    botao = driver.find_element(
        By.NAME,
        "enviar"
    )

    botao.click()

    time.sleep(5)

except Exception as e:

    print("Login Selenium:", e)

# =========================================================
# FECHA ALERT
# =========================================================

try:

    alert = driver.switch_to.alert

    print("ALERT:", alert.text)

    alert.accept()

    time.sleep(2)

except:
    pass


# =========================================================
# FUNÇÃO ABRIR EXPORTAÇÃO
# =========================================================

def abrir_exportacao():

    tentativas = 5

    for i in range(tentativas):

        print(f"\nTentativa abrir exportação: {i+1}")

        try:

            driver.get(EXPORT_URL)

            time.sleep(4)

            # fecha popup se existir
            try:

                alert = driver.switch_to.alert

                print("ALERT:", alert.text)

                alert.accept()

                time.sleep(2)

            except:
                pass

            # espera select estação
            WebDriverWait(driver, 15).until(

                EC.presence_of_element_located(
                    (
                        By.NAME,
                        "estacaoVO.nestcaMonto"
                    )
                )
            )

            print("Página exportação OK")

            return True

        except UnexpectedAlertPresentException:

            try:

                alert = driver.switch_to.alert

                print("ALERT:", alert.text)

                alert.accept()

            except:
                pass

        except TimeoutException:

            print("Timeout carregando página.")

        except Exception as e:

            print("ERRO:", e)

        time.sleep(5)

    return False

# =========================================================
# ABRIR EXPORTAÇÃO
# =========================================================

ok = abrir_exportacao()

if not ok:

    print("\nNão conseguiu abrir exportação.")

    driver.save_screenshot("erro_qualar.png")

    with open(
        "erro_qualar.html",
        "w",
        encoding="utf-8"
    ) as f:

        f.write(driver.page_source)

    driver.quit()

    exit()


# =========================================================
# PREENCHE CAMPOS
# =========================================================

print("CONFIGURANDO FORMULÁRIO...")

try:

    # tipo rede automática
    rede = Select(
        driver.find_element(
            By.NAME,
            "irede"
        )
    )

    rede.select_by_value("A")

except:
    pass

time.sleep(1)


# =========================================================
# PREENCHIMENTO INICIAL
# =========================================================

print("\nPreenchendo formulário inicial...")

try:

    # =====================================================
    # TIPO REDE AUTOMÁTICA
    # =====================================================

    radios = driver.find_elements(
        By.NAME,
        "irede"
    )

    print("RADIOS REDE:", len(radios))

    for r in radios:

        valor = r.get_attribute("value")

        print("RADIO:", valor)

        if valor == "A":

            driver.execute_script(
                "arguments[0].click();",
                r
            )

            print("Rede automática selecionada.")

            break

    time.sleep(5)

    # =====================================================
    # DATAS
    # =====================================================

    campo_inicio = driver.find_element(
        By.NAME,
        "dataInicialStr"
    )

    campo_inicio.clear()

    campo_inicio.send_keys(
        "15/08/2024"
    )

    campo_fim = driver.find_element(
        By.NAME,
        "dataFinalStr"
    )

    campo_fim.clear()

    campo_fim.send_keys(
        "25/08/2024"
    )

    print("Datas OK")

    time.sleep(2)

    # =====================================================
    # DEBUG HTML
    # =====================================================

    with open(
        "debug_combo.html",
        "w",
        encoding="utf-8"
    ) as f:

        f.write(driver.page_source)

    print("HTML salvo debug_combo.html")

    # =====================================================
    # ESPERA ESTAÇÕES
    # =====================================================

    print("Aguardando combo estações...")

    time.sleep(10)

    select_estacao = Select(

        driver.find_element(
            By.NAME,
            "estacaoVO.nestcaMonto"
        )
    )

    options_tmp = select_estacao.options

    print(
        "TOTAL OPTIONS ESTAÇÃO:",
        len(options_tmp)
    )

    for op in options_tmp[:10]:

        print(
            op.get_attribute("value"),
            "=",
            op.text
        )

    # =====================================================
    # SELECIONA AMERICANA
    # =====================================================

    encontrou = False

    for op in options_tmp:

        txt = op.text.strip().lower()

        if "americana" in txt:

            valor = op.get_attribute("value")

            print(
                "Americana encontrada:",
                valor
            )

            select_estacao.select_by_value(
                valor
            )

            encontrou = True

            break

    if not encontrou:

        raise Exception(
            "Americana não encontrada."
        )

    time.sleep(5)

    # =====================================================
    # PARAMETRO
    # =====================================================

    select_param = Select(
        driver.find_element(
            By.NAME,
            "parametroVO.nparmt"
        )
    )

    options_param = select_param.options

    print(
        "TOTAL PARAM:",
        len(options_param)
    )

    encontrou_o3 = False

    for op in options_param:

        txt = op.text.strip().upper()

        if "O3" in txt:

            valor = op.get_attribute("value")

            print("O3 =", valor)

            select_param.select_by_value(
                valor
            )

            encontrou_o3 = True

            break

    if not encontrou_o3:

        raise Exception(
            "O3 não encontrado."
        )

    time.sleep(3)

    # =====================================================
    # PESQUISAR
    # =====================================================

    print("Executando pesquisa...")

    botao = driver.find_element(
        By.XPATH,
        "//input[@value='Pesquisar']"
    )

    driver.execute_script(
        "arguments[0].click();",
        botao
    )

    time.sleep(10)

    # =====================================================
    # ALERT
    # =====================================================

    try:

        alert = driver.switch_to.alert

        print("ALERT:", alert.text)

        alert.accept()

    except:
        pass

    print("Pesquisa OK")

except Exception as e:

    print("\nERRO:")
    print(e)

# =========================================================
# GERA LISTA ESTAÇÕES
# =========================================================

print("\n================================================")
print("GERANDO LISTA ESTAÇÕES")
print("================================================")

select_estacao = Select(
    driver.find_element(
        By.NAME,
        "estacaoVO.nestcaMonto"
    )
)

options_estacoes = select_estacao.options

stations = []

# =========================================================
# API ARCGIS CETESB
# =========================================================

print("\nConsultando API ArcGIS CETESB...")

try:

    from pyproj import Transformer

    URL_ARCGIS = (
        "https://arcgis.cetesb.sp.gov.br/"
        "server/rest/services/"
        "ESTA%C3%87%C3%95ES_QUALIDADE_DO_AR_2023/"
        "MapServer/0/query"
    )

    PARAMS_ARCGIS = {
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": "true",
        "f": "json"
    }

    r_arcgis = requests.get(
        URL_ARCGIS,
        params=PARAMS_ARCGIS,
        timeout=60
    )

    arcgis_json = r_arcgis.json()

    features = arcgis_json.get(
        "features",
        []
    )

    print(
        f"Features ArcGIS: {len(features)}"
    )

    transformer = Transformer.from_crs(
        "EPSG:31983",
        "EPSG:4326",
        always_xy=True
    )

    # =====================================================
    # DICIONÁRIO ESTAÇÕES
    # =====================================================

    mapa_coords = {}

    for feat in features:

        attr = feat.get(
            "attributes",
            {}
        )

        nome_arcgis = str(
            attr.get("Município", "")
        ).strip()

        tipo = attr.get("TIPO")

        x_utm = attr.get("LONGITUDE")
        y_utm = attr.get("LATITUDE")

        latitude = None
        longitude = None

        if x_utm and y_utm:

            try:

                lon, lat = transformer.transform(
                    x_utm,
                    y_utm
                )

                latitude = round(lat, 6)
                longitude = round(lon, 6)

            except:
                pass

        mapa_coords[
            nome_arcgis.lower()
        ] = {

            "latitude": latitude,
            "longitude": longitude,
            "tipo": tipo
        }

except Exception as e:

    print(
        "\nErro API ArcGIS:",
        e
    )

    mapa_coords = {}

# =========================================================
# LOOP ESTAÇÕES QUALAR
# =========================================================

for op in options_estacoes:

    nome = op.text.strip()

    codigo = op.get_attribute("value")

    if not codigo:
        continue

    if codigo == "-1":
        continue

    latitude = None
    longitude = None
    tipo = None

    # =====================================================
    # PROCURA MATCH
    # =====================================================

    chave = nome.lower()

    if chave in mapa_coords:

        latitude = mapa_coords[chave][
            "latitude"
        ]

        longitude = mapa_coords[chave][
            "longitude"
        ]

        tipo = mapa_coords[chave][
            "tipo"
        ]

    else:

        # tentativa parcial
        for k, v in mapa_coords.items():

            if (
                nome.lower() in k
                or k in nome.lower()
            ):

                latitude = v["latitude"]

                longitude = v["longitude"]

                tipo = v["tipo"]

                break

    item = {

        "codigo": codigo,

        "nome": nome,

        "tipo": tipo,

        "latitude": latitude,

        "longitude": longitude
    }

    stations.append(item)

    print(
        codigo,
        nome,
        latitude,
        longitude
    )

# =========================================================
# SAVE LISTA
# =========================================================

stations_json = os.path.join(
    OUTPUT_DIR,
    "lista_estacoes.json"
)

with open(
    stations_json,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        stations,
        f,
        ensure_ascii=False,
        indent=4
    )

print("\nLISTA SALVA:")
print(stations_json)

# =========================================================
# SOMENTE LISTA
# =========================================================

if args.list_stations:

    print("\nModo somente lista.")
    driver.quit()
    exit()

# =========================================================
# ESTAÇÕES SELECIONADAS
# =========================================================

if args.station.lower() == "all":

    estacoes = stations

else:

    estacoes = []

    for st in stations:

        if st["codigo"] == str(args.station):

            estacoes.append(st)

# =========================================================
# DOWNLOAD DADOS
# =========================================================

todos = []

for est in estacoes:

    cod_estacao = est["codigo"]
    nome_estacao = est["nome"]

    print("\n================================================")
    print(cod_estacao, "-", nome_estacao)
    print("================================================")

    for nome_pol, codigo_pol in POLUENTES.items():

        print("\nPOLUENTE:", nome_pol)

        payload = {

            "method": "pesquisar",

            "irede": "A",

            "dataInicialStr": args.start,

            "dataFinalStr": args.end,

            "iTipoDado": "P",

            "estacaoVO.nestcaMonto": cod_estacao,

            "parametroVO.nparmt": str(codigo_pol),

            "tipoRelatorio": "1",

            "exibeCabecalho": "true"
        }

        response = session.post(
            QUERY_URL,
            data=payload,
            headers=HEADERS
        )

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        tabelas = soup.find_all("table")

        encontrou = False

        for tabela in tabelas:

            try:

                html_table = StringIO(
                    str(tabela)
                )

                dfs = pd.read_html(
                    html_table
                )

                if len(dfs) == 0:
                    continue

                df = dfs[0]

                if df.shape[0] < 3:
                    continue

                encontrou = True

                df["poluente"] = nome_pol

                df["estacao_codigo"] = cod_estacao

                df["estacao_nome"] = nome_estacao

                todos.append(df)

                nome_base = (
                    f"{cod_estacao}_{nome_pol}"
                )

                output_file = os.path.join(
                    OUTPUT_DIR,
                    f"{nome_base}.{OUTPUT_FORMAT}"
                )

                # CSV
                if OUTPUT_FORMAT == "csv":

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

                # JSON
                elif OUTPUT_FORMAT == "json":

                    df.to_json(
                        output_file,
                        orient="records",
                        force_ascii=False,
                        indent=2
                    )

                print("SALVO:")
                print(output_file)

                break

            except Exception:
                pass

        if not encontrou:

            print("Sem dados.")

# =========================================================
# FINAL CONCATENADO
# =========================================================

if len(todos) > 0:

    final = pd.concat(
        todos,
        ignore_index=True
    )

    output_final = os.path.join(
        OUTPUT_DIR,
        f"cetesb_qualidade_ar.{OUTPUT_FORMAT}"
    )

    if OUTPUT_FORMAT == "csv":

        final.to_csv(
            output_final,
            sep=";",
            index=False,
            encoding="utf-8"
        )

    elif OUTPUT_FORMAT == "txt":

        final.to_csv(
            output_final,
            sep="\t",
            index=False,
            encoding="utf-8"
        )

    elif OUTPUT_FORMAT == "json":

        final.to_json(
            output_final,
            orient="records",
            force_ascii=False,
            indent=2
        )

    print("\n================================================")
    print("ARQUIVO FINAL")
    print(output_final)
    print("================================================")

else:

    print("\nNenhum dado baixado.")

driver.quit()

