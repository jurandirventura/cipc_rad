# Funciona bem mas usa lista de estação como dado de entrada
import os
import argparse
from io import StringIO

import pandas as pd
import requests

from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Exemplo
"""
 python download_cetesb_qualar.py \
--station all \
--start 15/08/2024 \
--end 25/08/2024 \
--format json

python download_cetesb_qualar.py \
--station 63 \
--start 15/08/2024 \
--end 25/08/2024 \
--format txt

python download_cetesb_qualar.py \
--station 63 \
--start 15/08/2024 \
--end 25/08/2024 \
--format csv  

*** TODAS AS ESTAÇÕES DA LISTAGEM *** 
python download_cetesb_qualar.py \
--station all \
--stations-file ../cipc_data/cetesb/lista_estacoes.json \
--start 15/08/2024 \
--end 25/08/2024


"""


# =========================================================
# ENV
# =========================================================

load_dotenv()

USERNAME = os.getenv("CETESB_USER")
PASSWORD = os.getenv("CETESB_PASS")

if not USERNAME or not PASSWORD:
    raise Exception(
        "Variáveis CETESB_USER e CETESB_PASS não encontradas no .env"
    )

# =========================================================
# ARGUMENTOS
# =========================================================

parser = argparse.ArgumentParser()

parser.add_argument(
    "--station",
    required=True,
    help="ID da estação ou all/todos"
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
    default="../cipc_data/cetesb",
    help="Diretório de saída"
)

parser.add_argument(
    "--format",
    default="csv",
    choices=["csv", "txt", "json"],
    help="Formato de saída"
)

parser.add_argument(
    "--list-stations",
    action="store_true",
    help="Gerar lista de estações"
)

parser.add_argument(
    "--stations-file",
    help=(
        "Arquivo JSON com lista de estações "
        "(usado quando --station all)"
    )
)


args = parser.parse_args()

DATA_INICIO = args.start
DATA_FIM = args.end
OUTPUT_DIR = args.output
OUTPUT_FORMAT = args.format.lower()

os.makedirs(OUTPUT_DIR, exist_ok=True)

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

QUERY_URL = (
    "https://qualar.cetesb.sp.gov.br/"
    "qualar/exportaDados.do"
)

LOGIN_URL = (
    "https://qualar.cetesb.sp.gov.br/"
    "qualar/autenticador"
)

# =========================================================
# HEADERS
# =========================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/139 Safari/537.36"
    ),
    "Content-Type": "application/x-www-form-urlencoded",
    "Referer": HOME_URL
}

# =========================================================
# SESSION
# =========================================================

session = requests.Session()

# =========================================================
# LOGIN PAGE
# =========================================================

print("\nAbrindo tela login...")

r_login = session.get(
    HOME_URL,
    headers=HEADERS
)

print("STATUS LOGIN PAGE:", r_login.status_code)

# =========================================================
# LOGIN
# =========================================================

login_payload = {
    "cetesb_login": USERNAME,
    "cetesb_password": PASSWORD,
    "enviar": "OK"
}

print("\nFAZENDO LOGIN...")

r_auth = session.post(
    LOGIN_URL,
    data=login_payload,
    headers=HEADERS,
    allow_redirects=True
)

texto_login = BeautifulSoup(
    r_auth.text,
    "html.parser"
).get_text(
    separator="\n",
    strip=True
)

if (
    "Login:" in texto_login
    or "Senha:" in texto_login
    or "Não sou Cadastrado" in texto_login
    or "HTTP Status 500" in texto_login
    or "NullPointerException" in texto_login
):
    raise Exception("LOGIN FALHOU")

print("\nLOGIN OK")



# =========================================================
# LISTA ESTAÇÕES
# =========================================================

if args.list_stations:

    print("\nGerando lista de estações...")

    r_est = session.get(
        HOME_URL,
        headers=HEADERS
    )

    print("STATUS:", r_est.status_code)

    with open(
        "debug_estacoes.html",
        "w",
        encoding="utf-8"
    ) as f:
        f.write(r_est.text)

    soup_est = BeautifulSoup(
        r_est.text,
        "html.parser"
    )

    selects = soup_est.find_all("select")

    print("\nSELECTS ENCONTRADOS:")

    for s in selects:

        print(
            "name =",
            s.get("name"),
            "| id =",
            s.get("id")
        )

    select_estacao = None

    for s in selects:

        nome = str(s.get("name")).lower()

        if "estacao" in nome:

            select_estacao = s
            break

    if select_estacao is None:

        print("\nNenhum select de estação encontrado.")
        print("Veja debug_estacoes.html")
        exit()

    lista_estacoes = []

    for option in select_estacao.find_all("option"):

        codigo = option.get("value")
        nome = option.text.strip()

        if not codigo:
            continue

        if not codigo.isdigit():
            continue

        lista_estacoes.append({
            "codigo": codigo,
            "nome": nome
        })

    df_est = pd.DataFrame(lista_estacoes)

    output_est = os.path.join(
        OUTPUT_DIR,
        "lista_estacoes.json"
    )

    df_est.to_json(
        output_est,
        orient="records",
        force_ascii=False,
        indent=2
    )

    print("\n===================================")
    print("LISTA DE ESTAÇÕES GERADA")
    print(output_est)
    print("===================================")

    exit()


# # =========================================================
# # ABRE HOME
# # =========================================================

r = session.get(
    HOME_URL,
    headers=HEADERS
)

soup_home = BeautifulSoup(
    r.text,
    "html.parser"
)


# =========================================================
# ESTAÇÕES
# =========================================================

print("\nConfigurando estações...")

# =========================================================
# MODO ALL
# =========================================================

if args.station.lower() in ["all", "todos"]:

    if not args.stations_file:

        raise Exception(
            """
Para usar ALL informe:

--stations-file lista_estacoes.json
"""
        )

    if not os.path.exists(args.stations_file):

        raise Exception(
            f"Arquivo não encontrado: "
            f"{args.stations_file}"
        )

    print("\nLendo arquivo estações:")
    print(args.stations_file)

    df_est = pd.read_json(
        args.stations_file
    )

    estacoes_selecionadas = {}

    for _, row in df_est.iterrows():

        codigo = str(row["codigo"])

        nome = row.get(
            "nome",
            f"ESTACAO_{codigo}"
        )

        estacoes_selecionadas[codigo] = nome

# =========================================================
# MODO UMA ESTAÇÃO
# =========================================================

else:

    estacoes_selecionadas = {
        str(args.station):
        f"ESTACAO_{args.station}"
    }

# =========================================================
# DEBUG
# =========================================================

print("\nEstações selecionadas:")

for k, v in estacoes_selecionadas.items():

    print(k, "-", v)



# # =========================================================
# # ESTAÇÕES
# # =========================================================

# print("\nConfigurando estações...")

# # modo ALL ainda não implementado
# if args.station.lower() in ["all", "todos"]:

#     raise Exception(
#         """
# Modo ALL ainda não implementado.

# Use por enquanto:

# --station 63
# """
#     )

# # usa somente a estação informada
# estacoes_selecionadas = {
#     args.station: f"ESTACAO_{args.station}"
# }

# print("Estações selecionadas:")
# print(estacoes_selecionadas)

# =========================================================
# DOWNLOAD
# =========================================================


todos = []

# for cod_estacao, nome_estacao in estacoes_selecionadas.items():

for cod_estacao, nome_estacao in estacoes_selecionadas.items():

    print("\n=================================================")
    print(f"ESTAÇÃO: {cod_estacao} - {nome_estacao}")
    print("=================================================")

    for nome_pol, codigo_pol in POLUENTES.items():

        print(f"\nBaixando: {nome_pol}")

        payload = {
            "method": "pesquisar",
            "irede": "A",
            "dataInicialStr": DATA_INICIO,
            "dataFinalStr": DATA_FIM,
            "iTipoDado": "P",
            "estacaoVO.nestcaMonto": str(cod_estacao),
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

                html_table = StringIO(str(tabela))

                dfs = pd.read_html(
                    html_table,
                    decimal=",",
                    thousands="."
                )

                if len(dfs) == 0:
                    continue

                df = dfs[0]

                if df.shape[0] < 5:
                    continue

                texto_df = df.astype(str).to_string()

                if (
                    "Login:" in texto_df
                    or "Senha:" in texto_df
                    or "Digite os Dados" in texto_df
                ):
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

            print("Nenhum dado encontrado.")

# =========================================================
# CONCATENADO FINAL
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

    print("\n===================================")
    print("ARQUIVO FINAL GERADO")
    print(output_final)
    print("===================================")

else:

    print("\nNenhum dado baixado.")

