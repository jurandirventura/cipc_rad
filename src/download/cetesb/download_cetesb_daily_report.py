#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import argparse
import requests
import pandas as pd

from bs4 import BeautifulSoup
from dotenv import load_dotenv

# =========================================================
# EXEMPLOS
# =========================================================

"""
python src/download/cetesb/download_cetesb_daily_report.py \
--station 280 \
--pollutant O3 \
--start 15/08/2024 \
--end 25/08/2024

python src/download/cetesb/download_cetesb_daily_report.py \
--station all \
--pollutant MP10 \
--start 01/01/2025 \
--end 05/01/2025
"""

# =========================================================
# ENV
# =========================================================

load_dotenv()

USERNAME = os.getenv("CETESB_USER")
PASSWORD = os.getenv("CETESB_PASS")

if not USERNAME or not PASSWORD:

    raise Exception(
        "Defina CETESB_USER e CETESB_PASS"
    )

# =========================================================
# ARGUMENTOS
# =========================================================

parser = argparse.ArgumentParser()

parser.add_argument("--station", required=True)

parser.add_argument(
    "--pollutant",
    required=True,
    choices=[
        "MP10",
        "MP25",
        "O3",
        "NO2",
        "SO2",
        "CO"
    ]
)

parser.add_argument("--start", required=True)
parser.add_argument("--end", required=True)

parser.add_argument(
    "--output",
    default="../cipc_data/cetesb/daily_reports"
)

parser.add_argument(
    "--stations-file",
    default="../cipc_data/cetesb/lista_estacoes.json"
)

args = parser.parse_args()

# =========================================================
# OUTPUT
# =========================================================

OUTPUT_DIR = args.output

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

# =========================================================
# POLUENTES
# =========================================================

POLUENTES = {

    "MP10": 12,
    "SO2": 13,
    "NO2": 15,
    "CO": 16,
    "MP25": 57,
    "O3": 63
}

COD_POL = POLUENTES[args.pollutant]

# =========================================================
# URLS
# =========================================================

BASE_URL = "https://qualar.cetesb.sp.gov.br/qualar"

HOME_URL = f"{BASE_URL}/home.do"

LOGIN_URL = f"{BASE_URL}/autenticador"

REPORT_PAGE_URL = (
    f"{BASE_URL}/relValoresDiarios.do"
)

REPORT_URL = (
    f"{BASE_URL}/relValoresDiarios.do?method=gerarRelatorio"
)

# =========================================================
# HEADERS
# =========================================================

HEADERS = {

    "User-Agent": (
        "Mozilla/5.0 "
        "(X11; Ubuntu; Linux x86_64; rv:150.0) "
        "Gecko/20100101 Firefox/150.0"
    ),

    "Referer": REPORT_PAGE_URL,

    "Origin": "https://qualar.cetesb.sp.gov.br"
}

# =========================================================
# SESSION
# =========================================================

session = requests.Session()

# =========================================================
# HOME
# =========================================================

print("\nAbrindo HOME...")

r = session.get(
    HOME_URL,
    headers=HEADERS,
    timeout=120
)

print("STATUS:", r.status_code)

# =========================================================
# LOGIN
# =========================================================

print("\nFazendo LOGIN...")

payload_login = {

    "cetesb_login": USERNAME,
    "cetesb_password": PASSWORD,
    "enviar": "OK"
}

r_login = session.post(
    LOGIN_URL,
    data=payload_login,
    headers=HEADERS,
    allow_redirects=True,
    timeout=120
)

texto = BeautifulSoup(
    r_login.text,
    "html.parser"
).get_text(
    separator="\n",
    strip=True
)

if (
    "Login:" in texto
    or "Senha:" in texto
    or "Não sou Cadastrado" in texto
):

    raise Exception(
        "LOGIN FALHOU"
    )

print("LOGIN OK")

# =========================================================
# ABRE PÁGINA RELATÓRIO
# =========================================================

print("\nAbrindo página relatório...")

r_rel = session.get(
    REPORT_PAGE_URL,
    headers=HEADERS,
    timeout=120
)

print("STATUS:", r_rel.status_code)

# =========================================================
# ESTAÇÕES
# =========================================================

if args.station.lower() == "all":

    df_st = pd.read_json(
        args.stations_file
    )

    estacoes = (
        df_st["codigo"]
        .astype(str)
        .tolist()
    )

else:

    estacoes = [str(args.station)]

print("\nESTAÇÕES:")
print(estacoes)

# =========================================================
# LOOP
# =========================================================

todos = []

for estacao in estacoes:

    print("\n================================")
    print(f"ESTAÇÃO: {estacao}")
    print("================================")

    payload = {

        "irede": "A",

        "ainiclStr": args.start,
        "afinalStr": args.end,

        "nugrhi": "-1",

        "nparmt": str(COD_POL),

        "srealizarRepresentatividade": "N",

        "sutilizarMaiorMediaMovelDia": "N",

        "nestcasMontoSelecionadas": str(estacao)
    }

    response = None

    MAX_RETRY = 5

    for tentativa in range(MAX_RETRY):

        try:

            print(
                f"\nTentativa "
                f"{tentativa+1}/{MAX_RETRY}"
            )

            response = session.post(
                REPORT_URL,
                data=payload,
                headers=HEADERS,
                timeout=300
            )

            print(
                "STATUS:",
                response.status_code
            )

            if response.status_code == 200:

                break

        except Exception as e:

            print("ERRO:", e)

        time.sleep(5)

    if response is None:

        print("Falha request.")
        continue

    # =====================================================
    # DEBUG
    # =====================================================

    debug_file = os.path.join(
        OUTPUT_DIR,
        f"debug_{estacao}.html"
    )

    with open(
        debug_file,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(response.text)

    # =====================================================
    # CONTENT TYPE
    # =====================================================

    content_type = response.headers.get(
        "Content-Type",
        ""
    )

    print("\nCONTENT-TYPE:")
    print(content_type)

    # =====================================================
    # PDF
    # =====================================================

    if "application/pdf" in content_type:

        pdf_file = os.path.join(
            OUTPUT_DIR,
            f"{estacao}_{args.pollutant}.pdf"
        )

        with open(
            pdf_file,
            "wb"
        ) as f:

            f.write(response.content)

        print("\nPDF SALVO:")
        print(pdf_file)

        continue

    # =====================================================
    # HTML
    # =====================================================

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    tabelas = soup.find_all("table")

    print(f"\nTABELAS ENCONTRADAS: {len(tabelas)}")

    encontrou = False

    for tabela in tabelas:

        try:

            dfs = pd.read_html(
                str(tabela),
                decimal=",",
                thousands="."
            )

            if len(dfs) == 0:
                continue

            df = dfs[0]

            if df.shape[0] < 1:
                continue

            # ignora tabela de layout
            if df.shape[1] < 2:
                continue

            encontrou = True

            json_file = os.path.join(
                OUTPUT_DIR,
                f"{estacao}_{args.pollutant}.json"
            )

            df.to_json(
                json_file,
                orient="records",
                force_ascii=False,
                indent=2
            )

            print("\nJSON SALVO:")
            print(json_file)

            todos.append(df)

            break

        except Exception:
            pass

    if not encontrou:

        print("\nNenhum dado encontrado.")

    time.sleep(3)

# =========================================================
# FINAL
# =========================================================

if len(todos) == 0:

    print("\nNenhum dado baixado.")

else:

    final = pd.concat(
        todos,
        ignore_index=True
    )

    output_final = os.path.join(
        OUTPUT_DIR,
        "daily_reports_all.json"
    )

    final.to_json(
        output_final,
        orient="records",
        force_ascii=False,
        indent=2
    )

    print("\n================================")
    print("ARQUIVO FINAL")
    print(output_final)
    print("================================")











# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-

# import os
# import time
# import argparse
# import requests
# import pandas as pd

# from bs4 import BeautifulSoup
# from dotenv import load_dotenv

# """
# python src/download/cetesb/download_cetesb_daily_report.py \
# --station 58 \
# --pollutant MP10 \
# --start 15/05/2026 \
# --end 15/05/2026

# python src/download/cetesb/download_cetesb_daily_report.py \
# --station 280 \
# --pollutant O3 \
# --start 15/08/2024 \
# --end 25/08/2024
# """



# # =========================================================
# # ENV
# # =========================================================

# load_dotenv()

# USERNAME = os.getenv("CETESB_USER")
# PASSWORD = os.getenv("CETESB_PASS")

# if not USERNAME or not PASSWORD:

#     raise Exception(
#         "Defina CETESB_USER e CETESB_PASS"
#     )

# # =========================================================
# # ARGUMENTOS
# # =========================================================

# parser = argparse.ArgumentParser()

# parser.add_argument("--station", required=True)
# parser.add_argument("--pollutant", required=True)

# parser.add_argument("--start", required=True)
# parser.add_argument("--end", required=True)

# parser.add_argument(
#     "--output",
#     default="../cipc_data/cetesb/daily_reports"
# )

# parser.add_argument(
#     "--stations-file",
#     default="../cipc_data/cetesb/lista_estacoes.json"
# )

# args = parser.parse_args()

# # =========================================================
# # OUTPUT
# # =========================================================

# OUTPUT_DIR = args.output

# os.makedirs(
#     OUTPUT_DIR,
#     exist_ok=True
# )

# # =========================================================
# # POLUENTES
# # =========================================================

# POLUENTES = {

#     "MP10": 12,
#     "SO2": 13,
#     "NO2": 15,
#     "CO": 16,
#     "MP25": 57,
#     "O3": 63
# }

# COD_POL = POLUENTES[args.pollutant]

# # =========================================================
# # URLS
# # =========================================================

# BASE_URL = "https://qualar.cetesb.sp.gov.br/qualar"

# HOME_URL = f"{BASE_URL}/home.do"

# LOGIN_URL = f"{BASE_URL}/autenticador"

# REPORT_URL = (
#     f"{BASE_URL}/relValoresDiarios.do"
# )

# FILTER_URL = (
#     f"{BASE_URL}/relValoresDiarios.do?method=filtrarListas"
# )

# # =========================================================
# # HEADERS
# # =========================================================

# HEADERS = {

#     "User-Agent": (
#         "Mozilla/5.0 "
#         "(X11; Ubuntu; Linux x86_64; rv:150.0) "
#         "Gecko/20100101 Firefox/150.0"
#     ),

#     "Origin": BASE_URL,

#     "Referer": (
#         f"{BASE_URL}/relValoresDiarios.do"
#         "?method=gerarRelatorio"
#     ),

#     "Content-Type": (
#         "application/x-www-form-urlencoded"
#     )
# }

# # =========================================================
# # SESSION
# # =========================================================

# session = requests.Session()

# # =========================================================
# # ABRE HOME
# # =========================================================

# print("\nAbrindo home...")

# r = session.get(
#     HOME_URL,
#     headers=HEADERS,
#     timeout=120
# )

# print("STATUS:", r.status_code)

# # =========================================================
# # LOGIN
# # =========================================================

# print("\nFazendo login...")

# payload_login = {

#     "cetesb_login": USERNAME,
#     "cetesb_password": PASSWORD,
#     "enviar": "OK"
# }

# r_login = session.post(
#     LOGIN_URL,
#     data=payload_login,
#     headers=HEADERS,
#     allow_redirects=True,
#     timeout=120
# )

# texto = BeautifulSoup(
#     r_login.text,
#     "html.parser"
# ).get_text(
#     separator="\n",
#     strip=True
# )

# if (
#     "Login:" in texto
#     or "Senha:" in texto
# ):

#     raise Exception(
#         "LOGIN FALHOU"
#     )

# print("LOGIN OK")

# # =========================================================
# # ESTAÇÕES
# # =========================================================

# if args.station.lower() == "all":

#     df_st = pd.read_json(
#         args.stations_file
#     )

#     estacoes = (
#         df_st["codigo"]
#         .astype(str)
#         .tolist()
#     )

# else:

#     estacoes = [str(args.station)]

# print("\nEstações:")
# print(estacoes)

# # =========================================================
# # LOOP ESTAÇÕES
# # =========================================================

# todos = []

# for estacao in estacoes:

#     print("\n================================")
#     print(f"ESTAÇÃO: {estacao}")
#     print("================================")

#     # =====================================================
#     # FILTRAR LISTAS
#     # =====================================================

#     payload_filter = {

#         "irede": "A",

#         "ainiclStr": args.start,
#         "afinalStr": args.end,

#         "nugrhi": "-1",

#         "nparmt": str(COD_POL),

#         "chkAll": "N",

#         "nestcasMontoSelecionadas": estacao
#     }

#     try:

#         print("\nAtualizando listas...")

#         rf = session.post(
#             FILTER_URL,
#             data=payload_filter,
#             headers=HEADERS,
#             timeout=180
#         )

#         print(
#             "FILTER STATUS:",
#             rf.status_code
#         )

#         time.sleep(3)

#     except Exception as e:

#         print("Erro filtro:", e)
#         continue

#     # =====================================================
#     # GERAR RELATÓRIO
#     # =====================================================

#     payload_report = {

#         "irede": "A",

#         "ainiclStr": args.start,
#         "afinalStr": args.end,

#         "nugrhi": "-1",

#         "nparmt": str(COD_POL),

#         "chkAll": "N",

#         "nestcasMontoSelecionadas": estacao
#     }

#     response = None

#     MAX_RETRY = 5

#     for tentativa in range(MAX_RETRY):

#         try:

#             print(
#                 f"\nTentativa "
#                 f"{tentativa+1}/{MAX_RETRY}"
#             )

#             response = session.post(
#                 REPORT_URL +
#                 "?method=gerarRelatorio",
#                 data=payload_report,
#                 headers=HEADERS,
#                 timeout=300
#             )

#             print(
#                 "STATUS:",
#                 response.status_code
#             )

#             if response.status_code == 200:

#                 break

#             time.sleep(10)

#         except Exception as e:

#             print("ERRO:", e)

#             time.sleep(10)

#     if response is None:

#         continue

#     # =====================================================
#     # DEBUG HTML
#     # =====================================================

#     debug_file = os.path.join(
#         OUTPUT_DIR,
#         f"debug_{estacao}.html"
#     )

#     with open(
#         debug_file,
#         "w",
#         encoding="utf-8"
#     ) as f:

#         f.write(response.text)

#     # =====================================================
#     # CONTENT TYPE
#     # =====================================================

#     content_type = response.headers.get(
#         "Content-Type",
#         ""
#     )

#     print("\nCONTENT-TYPE:")
#     print(content_type)

#     # =====================================================
#     # PDF
#     # =====================================================

#     if "application/pdf" in content_type:

#         pdf_file = os.path.join(
#             OUTPUT_DIR,
#             f"{estacao}_{args.pollutant}.pdf"
#         )

#         with open(
#             pdf_file,
#             "wb"
#         ) as f:

#             f.write(response.content)

#         print("\nPDF SALVO:")
#         print(pdf_file)

#         continue

#     # =====================================================
#     # HTML
#     # =====================================================

#     soup = BeautifulSoup(
#         response.text,
#         "html.parser"
#     )

#     tabelas = soup.find_all("table")

#     if len(tabelas) == 0:

#         print("\nNenhuma tabela.")
#         continue

#     encontrou = False

#     for tabela in tabelas:

#         try:

#             dfs = pd.read_html(
#                 str(tabela),
#                 decimal=",",
#                 thousands="."
#             )

#             if len(dfs) == 0:
#                 continue

#             df = dfs[0]

#             if df.shape[0] < 1:
#                 continue

#             encontrou = True

#             # =============================================
#             # SALVA JSON
#             # =============================================

#             json_file = os.path.join(
#                 OUTPUT_DIR,
#                 f"{estacao}_{args.pollutant}.json"
#             )

#             df.to_json(
#                 json_file,
#                 orient="records",
#                 force_ascii=False,
#                 indent=2
#             )

#             print("\nJSON SALVO:")
#             print(json_file)

#             todos.append(df)

#             break

#         except Exception:
#             pass

#     if not encontrou:

#         print("\nNenhum dado encontrado.")

#     # =====================================================
#     # DELAY
#     # =====================================================

#     time.sleep(5)

# # =========================================================
# # FINAL
# # =========================================================

# if len(todos) == 0:

#     print("\nNenhum dado baixado.")

# else:

#     final = pd.concat(
#         todos,
#         ignore_index=True
#     )

#     output_final = os.path.join(
#         OUTPUT_DIR,
#         "daily_reports_all.json"
#     )

#     final.to_json(
#         output_final,
#         orient="records",
#         force_ascii=False,
#         indent=2
#     )

#     print("\n================================")
#     print("ARQUIVO FINAL")
#     print(output_final)
#     print("================================")




# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-

# """
# download_cetesb_daily_report.py

# Baixa relatórios diários QUALAR CETESB
# em:
# - PDF
# - JSON

# Suporta:
# - 1 estação
# - várias estações via lista JSON

# Exemplos:

# # 1 estação
# python download_cetesb_daily_report.py \
# --station 72 \
# --pollutant MP10 \
# --start 15/08/2024 \
# --end 25/08/2024

# # todas estações da lista
# python download_cetesb_daily_report.py \
# --station all \
# --stations-file ../cipc_data/cetesb/lista_estacoes.json \
# --pollutant MP10 \
# --start 15/08/2024 \
# --end 25/08/2024

# """

# import os
# import re
# import json
# import argparse
# from io import StringIO

# import pandas as pd
# import requests

# from bs4 import BeautifulSoup
# from dotenv import load_dotenv

# # =========================================================
# # ENV
# # =========================================================

# load_dotenv()

# USERNAME = os.getenv("CETESB_USER")
# PASSWORD = os.getenv("CETESB_PASS")

# if not USERNAME or not PASSWORD:

#     raise Exception(
#         "CETESB_USER / CETESB_PASS não encontrados"
#     )

# # =========================================================
# # ARGUMENTOS
# # =========================================================

# parser = argparse.ArgumentParser()

# parser.add_argument(
#     "--station",
#     required=True,
#     help="Código estação ou all"
# )

# parser.add_argument(
#     "--stations-file",
#     help="lista_estacoes.json"
# )

# parser.add_argument(
#     "--pollutant",
#     required=True,
#     choices=[
#         "MP10",
#         "MP25",
#         "O3",
#         "NO2",
#         "SO2",
#         "CO"
#     ]
# )

# parser.add_argument(
#     "--start",
#     required=True
# )

# parser.add_argument(
#     "--end",
#     required=True
# )

# parser.add_argument(
#     "--output",
#     default="../cipc_data/cetesb/daily_reports"
# )

# parser.add_argument(
#     "--save-pdf",
#     action="store_true",
#     help="Salvar PDF"
# )

# args = parser.parse_args()

# # =========================================================
# # OUTPUT
# # =========================================================

# OUTPUT_DIR = args.output

# os.makedirs(
#     OUTPUT_DIR,
#     exist_ok=True
# )

# # =========================================================
# # POLUENTES
# # =========================================================

# POLUENTES = {
#     "MP10": 12,
#     "SO2": 13,
#     "NO2": 15,
#     "CO": 16,
#     "O3": 63,
#     "MP25": 57
# }

# COD_POL = POLUENTES[args.pollutant]

# # =========================================================
# # URLS
# # =========================================================

# HOME_URL = (
#     "https://qualar.cetesb.sp.gov.br/"
#     "qualar/home.do"
# )

# LOGIN_URL = (
#     "https://qualar.cetesb.sp.gov.br/"
#     "qualar/autenticador"
# )

# REPORT_URL = (
#     "https://qualar.cetesb.sp.gov.br/"
#     "qualar/relValoresDiarios.do"
# )

# # =========================================================
# # HEADERS
# # =========================================================

# HEADERS = {

#     "User-Agent": (
#         "Mozilla/5.0 (X11; Linux x86_64) "
#         "Gecko/20100101 Firefox/150.0"
#     ),

#     "Referer": (
#         "https://qualar.cetesb.sp.gov.br/"
#         "qualar/relValoresDiarios.do"
#     )
# }

# # =========================================================
# # SESSION
# # =========================================================

# session = requests.Session()

# # =========================================================
# # LOGIN PAGE
# # =========================================================

# print("\nAbrindo login...")

# r = session.get(
#     HOME_URL,
#     headers=HEADERS
# )

# print("STATUS:", r.status_code)

# # =========================================================
# # LOGIN
# # =========================================================

# payload_login = {

#     "cetesb_login": USERNAME,
#     "cetesb_password": PASSWORD,
#     "enviar": "OK"
# }

# print("\nFazendo login...")

# r_login = session.post(
#     LOGIN_URL,
#     data=payload_login,
#     headers=HEADERS,
#     allow_redirects=True
# )

# texto = BeautifulSoup(
#     r_login.text,
#     "html.parser"
# ).get_text()

# if "Login:" in texto:

#     raise Exception("LOGIN FALHOU")

# print("LOGIN OK")

# # =========================================================
# # ESTAÇÕES
# # =========================================================

# if args.station.lower() == "all":

#     if not args.stations_file:

#         raise Exception(
#             "--stations-file obrigatório"
#         )

#     df_st = pd.read_json(
#         args.stations_file
#     )

#     estacoes = (
#         df_st["codigo"]
#         .astype(str)
#         .tolist()
#     )

# else:

#     estacoes = [str(args.station)]

# print("\nEstações:")
# print(estacoes)

# # =========================================================
# # LOOP ESTAÇÕES
# # =========================================================

# todos = []

# for estacao in estacoes:

#     print("\n================================")
#     print("ESTAÇÃO:", estacao)
#     print("================================")

#     # =====================================================
#     # PAYLOAD
#     # =====================================================

#     payload = {

#         "method": "gerarRelatorio",

#         "irede": "A",

#         "dataInicialStr": args.start,
#         "dataFinalStr": args.end,

#         "parametroVO.nparmt": str(COD_POL),

#         "estacaoVO.nestcaMonto": str(estacao),

#         "tipoRelatorio": "1",

#         "exibeCabecalho": "true"
#     }

#     # =====================================================
#     # REQUEST
#     # =====================================================

#     r = session.post(
#         REPORT_URL,
#         data=payload,
#         headers=HEADERS
#     )

#     print("STATUS:", r.status_code)

#     # =====================================================
#     # SAVE HTML DEBUG
#     # =====================================================

#     debug_html = os.path.join(
#         OUTPUT_DIR,
#         f"debug_{estacao}.html"
#     )

#     with open(
#         debug_html,
#         "w",
#         encoding="utf-8"
#     ) as f:

#         f.write(r.text)

#     # =====================================================
#     # PDF
#     # =====================================================

#     content_type = r.headers.get(
#         "Content-Type",
#         ""
#     )

#     if "pdf" in content_type.lower():

#         pdf_file = os.path.join(
#             OUTPUT_DIR,
#             f"{estacao}_{args.pollutant}.pdf"
#         )

#         with open(pdf_file, "wb") as f:

#             f.write(r.content)

#         print("PDF salvo:")
#         print(pdf_file)

#         continue

#     # =====================================================
#     # HTML
#     # =====================================================

#     soup = BeautifulSoup(
#         r.text,
#         "html.parser"
#     )

#     tabelas = soup.find_all("table")

#     if len(tabelas) == 0:

#         print("Nenhuma tabela.")
#         continue

#     encontrou = False

#     for tabela in tabelas:

#         try:

#             html_table = StringIO(
#                 str(tabela)
#             )

#             dfs = pd.read_html(
#                 html_table,
#                 decimal=",",
#                 thousands="."
#             )

#             if len(dfs) == 0:
#                 continue

#             df = dfs[0]

#             # tenta localizar tabela correta
#             cols = [
#                 str(c)
#                 for c in df.columns
#             ]

#             texto_cols = " ".join(cols)

#             if (
#                 "Valor Diário" not in texto_cols
#                 and
#                 "Qualidade do Ar" not in texto_cols
#             ):
#                 continue

#             encontrou = True

#             # =============================================
#             # LIMPA
#             # =============================================

#             df.columns = [
#                 str(c).replace("\n", " ")
#                 for c in df.columns
#             ]

#             df["estacao_codigo"] = estacao
#             df["poluente"] = args.pollutant

#             todos.append(df)

#             # =============================================
#             # JSON
#             # =============================================

#             json_file = os.path.join(
#                 OUTPUT_DIR,
#                 f"{estacao}_{args.pollutant}.json"
#             )

#             df.to_json(
#                 json_file,
#                 orient="records",
#                 force_ascii=False,
#                 indent=2
#             )

#             print("JSON salvo:")
#             print(json_file)

#             break

#         except Exception as e:

#             print("Erro tabela:", e)

#     if not encontrou:

#         print("Tabela diária não encontrada.")

# # =========================================================
# # CONCATENADO FINAL
# # =========================================================

# if len(todos) > 0:

#     final = pd.concat(
#         todos,
#         ignore_index=True
#     )

#     output_final = os.path.join(
#         OUTPUT_DIR,
#         f"daily_{args.pollutant}.json"
#     )

#     final.to_json(
#         output_final,
#         orient="records",
#         force_ascii=False,
#         indent=2
#     )

#     print("\n================================")
#     print("ARQUIVO FINAL")
#     print(output_final)
#     print("================================")

# else:

#     print("\nNenhum dado baixado.")