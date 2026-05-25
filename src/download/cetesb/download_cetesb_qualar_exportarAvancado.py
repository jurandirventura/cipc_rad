import os
import argparse
from io import StringIO

import pandas as pd
import requests

from bs4 import BeautifulSoup
from dotenv import load_dotenv


# =========================================================
# EXEMPLOS
# =========================================================

"""
python download_cetesb_qualar.py \
--station all \
--stations-file ../cipc_data/cetesb/lista_estacoes.json \
--start 15/08/2024 \
--end 25/08/2024 \
--format csv

python download_cetesb_qualar.py \
--station 110 \
--start 15/08/2024 \
--end 25/08/2024 \
--format csv

python download_cetesb_qualar.py \
--station 110 \
--start 15/08/2024 \
--end 25/08/2024 \
--format json

python download_cetesb_qualar.py \
--station 110 \
--start 15/08/2024 \
--end 25/08/2024 \
--format txt
"""


# =========================================================
# ENV
# =========================================================

load_dotenv()

USERNAME = os.getenv("CETESB_USER")
PASSWORD = os.getenv("CETESB_PASS")

if not USERNAME or not PASSWORD:

    raise Exception(
        "Variáveis CETESB_USER e CETESB_PASS "
        "não encontradas no .env"
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

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# =========================================================
# POLUENTES
# =========================================================

POLUENTES = [
    "SO2",
    "NO2",
    "CO",
    "MP10",
    "MP25",
    "O3"
]


# =========================================================
# URLS
# =========================================================

BASE_URL = (
    "https://qualar.cetesb.sp.gov.br/qualar/"
)

HOME_URL = (
    BASE_URL + "home.do"
)

LOGIN_URL = (
    BASE_URL + "autenticador"
)

EXPORT_PAGE_URL = (
    BASE_URL
    + "exportaDadosAvanc.do?method=filtrarParametros"
)

QUERY_URL = (
    BASE_URL
    + "exportaDadosAvanc.do?method=exportar"
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

    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,*/*;q=0.8"
    ),

    "Content-Type": (
        "application/x-www-form-urlencoded"
    ),

    "Origin": (
        "https://qualar.cetesb.sp.gov.br"
    ),

    "Referer": EXPORT_PAGE_URL
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

print(
    "STATUS LOGIN PAGE:",
    r_login.status_code
)


# =========================================================
# LOGIN
# =========================================================

login_payload = {

    "cetesb_login":
    USERNAME,

    "cetesb_password":
    PASSWORD,

    "enviar":
    "OK"
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

    raise Exception(
        "LOGIN FALHOU"
    )

print("\nLOGIN OK")


# =========================================================
# ABRE PÁGINA EXPORTAÇÃO
# =========================================================

print("\nAbrindo página exportação...")

r_export = session.get(
    EXPORT_PAGE_URL,
    headers=HEADERS
)

print(
    "STATUS EXPORT PAGE:",
    r_export.status_code
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

    if not os.path.exists(
        args.stations_file
    ):

        raise Exception(
            f"Arquivo não encontrado: "
            f"{args.stations_file}"
        )

    print(
        "\nLendo arquivo estações:"
    )

    print(
        args.stations_file
    )

    df_est = pd.read_json(
        args.stations_file
    )

    estacoes_selecionadas = {}

    for _, row in df_est.iterrows():

        codigo = str(
            row["codigo"]
        )

        nome = row.get(
            "nome",
            f"ESTACAO_{codigo}"
        )

        estacoes_selecionadas[
            codigo
        ] = nome


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


# =========================================================
# LIMPA NOME
# =========================================================

def limpar_nome(texto):

    texto = (
        texto
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace("(", "")
        .replace(")", "")
        .replace("-", "_")
        .replace("ã", "a")
        .replace("á", "a")
        .replace("à", "a")
        .replace("â", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("õ", "o")
        .replace("ú", "u")
        .replace("ç", "c")
    )

    return texto

def extrair_parametros_disponiveis(html):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    parametros = {}

    inputs = soup.find_all(
        "input",
        {
            "name":
            "nparmtsSelecionados"
        }
    )

    for inp in inputs:

        valor = inp.get("value")

        if not valor:
            continue

        valor = str(valor)

        texto = ""

        td = inp.find_parent("td")

        if td:

            prox = td.find_next_sibling("td")

            if prox:

                texto = prox.get_text(
                    " ",
                    strip=True
                )

        texto_upper = texto.upper()

        if "SO2" in texto_upper:

            parametros["SO2"] = valor

        elif "NO2" in texto_upper:

            parametros["NO2"] = valor

        elif (
            " CO" in texto_upper
            or texto_upper.startswith("CO")
        ):

            parametros["CO"] = valor

        elif "MP10" in texto_upper:

            parametros["MP10"] = valor

        elif (
            "MP2" in texto_upper
            or "MP25" in texto_upper
        ):

            parametros["MP25"] = valor

        elif "O3" in texto_upper:

            parametros["O3"] = valor

    return parametros


# =========================================================
# DOWNLOAD
# =========================================================

def baixar_dados(
    estacao_codigo,
    estacao_nome,
    poluente_nome
):

    print("\n===================================")
    print("ESTAÇÃO :", estacao_codigo)
    print("NOME    :", estacao_nome)
    print("POLUENTE:", poluente_nome)
    print("===================================")

    # =====================================================
    # PRIMEIRO FILTRA PARÂMETROS
    # =====================================================

    filtro_payload = {

        "method":
        "filtrarParametros",

        "tipoRede":
        "A",

        "dataInicialStr":
        DATA_INICIO,

        "dataFinalStr":
        DATA_FIM,

        "estacaoVO.nestcaMonto":
        estacao_codigo
    }

    r_filtro = session.post(
        EXPORT_PAGE_URL,
        data=filtro_payload,
        headers=HEADERS
    )

    html_filtrado = r_filtro.text

    debug_html = os.path.join(
        OUTPUT_DIR,
        f"debug_filtro_{estacao_codigo}_{poluente_nome}.html"
    )

    with open(
        debug_html,
        "w",
        encoding="utf-8",
        errors="ignore"
    ) as f:

        f.write(html_filtrado)

    # =====================================================
    # EXTRAI PARÂMETROS
    # =====================================================

    parametros_disponiveis = (
        extrair_parametros_disponiveis(
            html_filtrado
        )
    )

    print("\nPARÂMETROS ENCONTRADOS:")

    for k, v in parametros_disponiveis.items():

        print(k, "=>", v)

    # =====================================================
    # NÃO DISPONÍVEL
    # =====================================================

    if poluente_nome not in parametros_disponiveis:

        print(
            f"\n{poluente_nome} não disponível "
            f"na estação {estacao_codigo}"
        )

        return

    # =====================================================
    # CÓDIGO REAL
    # =====================================================

    codigo_parametro = (
        parametros_disponiveis[
            poluente_nome
        ]
    )

    print(
        "\nCÓDIGO PARAMETRO:",
        codigo_parametro
    )

    # =====================================================
    # PAYLOAD EXPORTAÇÃO
    # =====================================================

    payload = {

        "method":
        "exportar",

        "tipoRede":
        "A",

        "dataInicialStr":
        DATA_INICIO,

        "dataFinalStr":
        DATA_FIM,

        "estacaoVO.nestcaMonto":
        estacao_codigo,

        "nparmtsSelecionados":
        codigo_parametro
    }

    print("\nPAYLOAD EXPORT:")

    for k, v in payload.items():

        print(k, "=", v)

    # =====================================================
    # EXPORTA
    # =====================================================

    r = session.post(
        QUERY_URL,
        data=payload,
        headers=HEADERS,
        allow_redirects=True
    )

    print(
        "\nSTATUS DOWNLOAD:",
        r.status_code
    )

    content_type = r.headers.get(
        "content-type",
        ""
    ).lower()

    print(
        "CONTENT-TYPE:",
        content_type
    )

    # =====================================================
    # DEBUG EXPORT
    # =====================================================

    debug_file = os.path.join(
        OUTPUT_DIR,
        f"debug_export_{estacao_codigo}_{poluente_nome}.html"
    )

    with open(
        debug_file,
        "w",
        encoding="utf-8",
        errors="ignore"
    ) as f:

        f.write(r.text)

    # =====================================================
    # VERIFICA CSV
    # =====================================================

    if "text/csv" not in content_type:

        print(
            "\nNÃO RETORNOU CSV"
        )

        print(
            "\nVeja:",
            debug_file
        )

        return

    # =====================================================
    # TEXTO CSV
    # =====================================================

    texto_csv = r.content.decode(
        "cp1252",
        errors="ignore"
    )

    if len(texto_csv.strip()) < 50:

        print(
            "\nCSV vazio."
        )

        return

    # =====================================================
    # NOME
    # =====================================================

    estacao_nome_limpo = limpar_nome(
        estacao_nome
    )

    nome_saida = (
        f"{estacao_codigo}_"
        f"{estacao_nome_limpo}_"
        f"{poluente_nome}_"
        f"{DATA_INICIO.replace('/','')}_"
        f"{DATA_FIM.replace('/','')}"
    )

    # =====================================================
    # CSV
    # =====================================================

    if OUTPUT_FORMAT == "csv":

        output_file = os.path.join(
            OUTPUT_DIR,
            nome_saida + ".csv"
        )

        with open(
            output_file,
            "wb"
        ) as f:

            f.write(r.content)

    # =====================================================
    # TXT
    # =====================================================

    elif OUTPUT_FORMAT == "txt":

        output_file = os.path.join(
            OUTPUT_DIR,
            nome_saida + ".txt"
        )

        with open(
            output_file,
            "w",
            encoding="cp1252",
            errors="ignore"
        ) as f:

            f.write(texto_csv)

    # =====================================================
    # JSON
    # =====================================================

    elif OUTPUT_FORMAT == "json":

        try:

            df = pd.read_csv(
                StringIO(texto_csv),
                sep=";",
                engine="python",
                skiprows=5
            )

        except Exception as e:

            print("\nERRO CSV:")
            print(e)
            return

        output_file = os.path.join(
            OUTPUT_DIR,
            nome_saida + ".json"
        )

        df.to_json(
            output_file,
            orient="records",
            force_ascii=False,
            indent=2
        )

    print("\nARQUIVO SALVO:")
    print(output_file)


# =========================================================
# LOOP DOWNLOAD
# =========================================================

for (
    estacao_codigo,
    estacao_nome
) in estacoes_selecionadas.items():

    for pol_nome in POLUENTES:

        try:

            baixar_dados(
                estacao_codigo,
                estacao_nome,
                pol_nome
            )

        except Exception as e:

            print("\nERRO:")

            print(
                estacao_codigo,
                pol_nome,
                e
            )

print("\nFINALIZADO")




# #*** versão com list_estações mas não está trazendo todas, somente 8
# import os
# import argparse
# from io import StringIO

# import pandas as pd
# import requests

# from bs4 import BeautifulSoup
# from dotenv import load_dotenv


# # =========================================================
# # EXEMPLOS
# # =========================================================

# """
# python download_cetesb_qualar.py \
# --station all \
# --stations-file ../cipc_data/cetesb/lista_estacoes.json \
# --start 15/08/2024 \
# --end 25/08/2024 \
# --format csv

# python download_cetesb_qualar.py \
# --station 63 \
# --start 15/08/2024 \
# --end 25/08/2024 \
# --format csv

# python download_cetesb_qualar.py \
# --station 63 \
# --start 15/08/2024 \
# --end 25/08/2024 \
# --format json

# python download_cetesb_qualar.py \
# --station 63 \
# --start 15/08/2024 \
# --end 25/08/2024 \
# --format txt
# """


# # =========================================================
# # ENV
# # =========================================================

# load_dotenv()

# USERNAME = os.getenv("CETESB_USER")
# PASSWORD = os.getenv("CETESB_PASS")

# if not USERNAME or not PASSWORD:

#     raise Exception(
#         "Variáveis CETESB_USER e CETESB_PASS "
#         "não encontradas no .env"
#     )


# # =========================================================
# # ARGUMENTOS
# # =========================================================

# parser = argparse.ArgumentParser()

# parser.add_argument(
#     "--station",
#     required=True,
#     help="ID da estação ou all/todos"
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
#     default="../cipc_data/cetesb",
#     help="Diretório de saída"
# )

# parser.add_argument(
#     "--format",
#     default="csv",
#     choices=["csv", "txt", "json"],
#     help="Formato de saída"
# )

# parser.add_argument(
#     "--list-stations",
#     action="store_true",
#     help="Gerar lista de estações"
# )

# parser.add_argument(
#     "--stations-file",
#     help=(
#         "Arquivo JSON com lista de estações "
#         "(usado quando --station all)"
#     )
# )

# args = parser.parse_args()

# DATA_INICIO = args.start
# DATA_FIM = args.end
# OUTPUT_DIR = args.output
# OUTPUT_FORMAT = args.format.lower()

# os.makedirs(
#     OUTPUT_DIR,
#     exist_ok=True
# )


# # =========================================================
# # POLUENTES
# # =========================================================

# POLUENTES = {
#     "SO2": 13,
#     "NO2": 15,
#     "CO": 16,
#     "MP10": 12,
#     "MP25": 57,
#     "O3": 63
# }


# # =========================================================
# # URLS
# # =========================================================

# BASE_URL = (
#     "https://qualar.cetesb.sp.gov.br/qualar/"
# )

# HOME_URL = (
#     BASE_URL + "home.do"
# )

# LOGIN_URL = (
#     BASE_URL + "autenticador"
# )

# EXPORT_PAGE_URL = (
#     BASE_URL
#     + "exportaDadosAvanc.do?method=filtrarParametros"
# )

# QUERY_URL = (
#     BASE_URL
#     + "exportaDadosAvanc.do?method=exportar"
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
#     "Accept": (
#         "text/html,application/xhtml+xml,"
#         "application/xml;q=0.9,*/*;q=0.8"
#     ),
#     "Content-Type": (
#         "application/x-www-form-urlencoded"
#     ),
#     "Origin": (
#         "https://qualar.cetesb.sp.gov.br"
#     ),
#     "Referer": EXPORT_PAGE_URL
# }


# # =========================================================
# # SESSION
# # =========================================================

# session = requests.Session()


# # =========================================================
# # LOGIN PAGE
# # =========================================================

# print("\nAbrindo tela login...")

# r_login = session.get(
#     HOME_URL,
#     headers=HEADERS
# )

# print(
#     "STATUS LOGIN PAGE:",
#     r_login.status_code
# )


# # =========================================================
# # LOGIN
# # =========================================================

# login_payload = {
#     "cetesb_login": USERNAME,
#     "cetesb_password": PASSWORD,
#     "enviar": "OK"
# }

# print("\nFAZENDO LOGIN...")

# r_auth = session.post(
#     LOGIN_URL,
#     data=login_payload,
#     headers=HEADERS,
#     allow_redirects=True
# )

# texto_login = BeautifulSoup(
#     r_auth.text,
#     "html.parser"
# ).get_text(
#     separator="\n",
#     strip=True
# )

# if (
#     "Login:" in texto_login
#     or "Senha:" in texto_login
#     or "Não sou Cadastrado" in texto_login
#     or "HTTP Status 500" in texto_login
#     or "NullPointerException" in texto_login
# ):

#     raise Exception(
#         "LOGIN FALHOU"
#     )

# print("\nLOGIN OK")


# # =========================================================
# # ABRE PÁGINA EXPORTAÇÃO
# # =========================================================

# print("\nAbrindo página exportação...")

# r_export = session.get(
#     EXPORT_PAGE_URL,
#     headers=HEADERS
# )

# print(
#     "STATUS EXPORT PAGE:",
#     r_export.status_code
# )


# # =========================================================
# # LISTA ESTAÇÕES
# # =========================================================

# if args.list_stations:

#     print(
#         "\nGerando lista de estações..."
#     )

#     soup_est = BeautifulSoup(
#         r_export.text,
#         "html.parser"
#     )

#     selects = soup_est.find_all("select")

#     print("\nSELECTS ENCONTRADOS:")

#     for s in selects:

#         print(
#             "name =",
#             s.get("name"),
#             "| id =",
#             s.get("id")
#         )

#     select_estacao = None

#     for s in selects:

#         nome = str(
#             s.get("name")
#         ).lower()

#         if "estacao" in nome:

#             select_estacao = s
#             break

#     if select_estacao is None:

#         with open(
#             "debug_estacoes.html",
#             "w",
#             encoding="utf-8"
#         ) as f:

#             f.write(r_export.text)

#         print(
#             "\nNenhum select de estação encontrado."
#         )

#         print(
#             "Veja debug_estacoes.html"
#         )

#         exit()

#     lista_estacoes = []

#     for option in select_estacao.find_all("option"):

#         codigo = option.get("value")
#         nome = option.text.strip()

#         if not codigo:
#             continue

#         if not codigo.isdigit():
#             continue

#         lista_estacoes.append({
#             "codigo": codigo,
#             "nome": nome
#         })

#     df_est = pd.DataFrame(
#         lista_estacoes
#     )

#     output_est = os.path.join(
#         OUTPUT_DIR,
#         "lista_estacoes.json"
#     )

#     df_est.to_json(
#         output_est,
#         orient="records",
#         force_ascii=False,
#         indent=2
#     )

#     print("\n===================================")
#     print("LISTA DE ESTAÇÕES GERADA")
#     print(output_est)
#     print("===================================")

#     exit()


# # =========================================================
# # ESTAÇÕES
# # =========================================================

# print("\nConfigurando estações...")


# # =========================================================
# # MODO ALL
# # =========================================================

# if args.station.lower() in ["all", "todos"]:

#     if not args.stations_file:

#         raise Exception(
#             """
# Para usar ALL informe:

# --stations-file lista_estacoes.json
# """
#         )

#     if not os.path.exists(
#         args.stations_file
#     ):

#         raise Exception(
#             f"Arquivo não encontrado: "
#             f"{args.stations_file}"
#         )

#     print(
#         "\nLendo arquivo estações:"
#     )

#     print(
#         args.stations_file
#     )

#     df_est = pd.read_json(
#         args.stations_file
#     )

#     estacoes_selecionadas = {}

#     for _, row in df_est.iterrows():

#         codigo = str(
#             row["codigo"]
#         )

#         nome = row.get(
#             "nome",
#             f"ESTACAO_{codigo}"
#         )

#         estacoes_selecionadas[
#             codigo
#         ] = nome


# # =========================================================
# # MODO UMA ESTAÇÃO
# # =========================================================

# else:

#     estacoes_selecionadas = {

#         str(args.station):
#         f"ESTACAO_{args.station}"

#     }


# # =========================================================
# # DEBUG
# # =========================================================

# print("\nEstações selecionadas:")

# for k, v in estacoes_selecionadas.items():

#     print(k, "-", v)


# # =========================================================
# # FILTRA PARÂMETROS DA ESTAÇÃO
# # =========================================================

# def filtrar_parametros_estacao(estacao_codigo):

#     payload = {

#         "dataInicialStr":
#         DATA_INICIO,

#         "dataFinalStr":
#         DATA_FIM,

#         "estacaoVO.nestcaMonto":
#         estacao_codigo
#     }

#     r = session.post(

#         EXPORT_PAGE_URL,
#         data=payload,
#         headers=HEADERS

#     )

#     return r.text

# # =========================================================
# # VERIFICA SE PARÂMETRO EXISTE
# # =========================================================

# def parametro_disponivel(html, parametro_codigo):

#     soup = BeautifulSoup(
#         html,
#         "html.parser"
#     )

#     inputs = soup.find_all(
#         "input",
#         {
#             "name":
#             "nparmtsSelecionados"
#         }
#     )

#     parametros_validos = []

#     for inp in inputs:

#         valor = inp.get("value")

#         if valor:

#             parametros_validos.append(
#                 str(valor)
#             )

#     return str(parametro_codigo) in parametros_validos

# # =========================================================
# # FUNÇÃO DOWNLOAD
# # =========================================================

# def baixar_dados(
#     estacao_codigo,
#     estacao_nome,
#     poluente_nome,
#     poluente_codigo
# ):

#     print("\n===================================")
#     print("ESTAÇÃO :", estacao_codigo)
#     print("NOME    :", estacao_nome)
#     print("POLUENTE:", poluente_nome)
#     print("===================================")

#     # =====================================================
#     # 1) FILTRA PARÂMETROS DA ESTAÇÃO
#     # =====================================================

#     html_filtrado = filtrar_parametros_estacao(
#         estacao_codigo
#     )

#     # =====================================================
#     # 2) VERIFICA SE POLUENTE EXISTE
#     # =====================================================

#     if not parametro_disponivel(
#         html_filtrado,
#         poluente_codigo
#     ):

#         print(
#             f"Parâmetro "
#             f"{poluente_nome} "
#             f"não disponível "
#             f"para estação "
#             f"{estacao_codigo}"
#         )

#         return

#     # =====================================================
#     # 3) PAYLOAD EXPORTAÇÃO
#     # =====================================================

#     payload = {

#         "dataInicialStr":
#         DATA_INICIO,

#         "dataFinalStr":
#         DATA_FIM,

#         "estacaoVO.nestcaMonto":
#         estacao_codigo,

#         "nparmtsSelecionados":
#         poluente_codigo
#     }

#     # =====================================================
#     # 4) EXPORTA
#     # =====================================================

#     r = session.post(
#         QUERY_URL,
#         data=payload,
#         headers=HEADERS,
#         allow_redirects=True
#     )

#     print(
#         "STATUS DOWNLOAD:",
#         r.status_code
#     )

#     content_type = r.headers.get(
#         "content-type",
#         ""
#     )

#     print(
#         "CONTENT-TYPE:",
#         content_type
#     )

#     # =====================================================
#     # DEBUG HTML
#     # =====================================================

#     debug_file = os.path.join(
#         OUTPUT_DIR,
#         "debug_exportacao.html"
#     )

#     with open(
#         debug_file,
#         "w",
#         encoding="utf-8"
#     ) as f:

#         f.write(r.text)

#     # =====================================================
#     # NÃO RETORNOU CSV
#     # =====================================================

#     if "text/csv" not in content_type:

#         print("\nNão retornou CSV.")

#         print("\nVeja:")
#         print(debug_file)

#         print("\nPrimeiros caracteres:")
#         print(r.text[:1000])

#         return

#     # =====================================================
#     # LIMPA NOME ESTAÇÃO
#     # =====================================================

#     estacao_nome_limpo = (
#         estacao_nome
#         .replace(" ", "_")
#         .replace("/", "_")
#         .replace("\\", "_")
#         .replace("(", "")
#         .replace(")", "")
#         .replace("-", "_")
#     )

#     # =====================================================
#     # NOME SAÍDA
#     # =====================================================

#     nome_saida = (
#         f"{estacao_codigo}_"
#         f"{estacao_nome_limpo}_"
#         f"{poluente_nome}_"
#         f"{DATA_INICIO.replace('/','')}_"
#         f"{DATA_FIM.replace('/','')}"
#     )

#     # =====================================================
#     # CSV
#     # =====================================================

#     if OUTPUT_FORMAT == "csv":

#         output_file = os.path.join(
#             OUTPUT_DIR,
#             nome_saida + ".csv"
#         )

#         with open(
#             output_file,
#             "wb"
#         ) as f:

#             f.write(r.content)

#     # =====================================================
#     # TXT
#     # =====================================================

#     elif OUTPUT_FORMAT == "txt":

#         output_file = os.path.join(
#             OUTPUT_DIR,
#             nome_saida + ".txt"
#         )

#         with open(
#             output_file,
#             "w",
#             encoding="cp1252",
#             errors="ignore"
#         ) as f:

#             f.write(r.text)

#     # =====================================================
#     # JSON
#     # =====================================================

#     elif OUTPUT_FORMAT == "json":

#         csv_text = r.content.decode(
#             "cp1252",
#             errors="ignore"
#         )

#         try:

#             df = pd.read_csv(
#                 StringIO(csv_text),
#                 sep=";",
#                 engine="python"
#             )

#         except Exception as e:

#             print(
#                 "ERRO LENDO CSV:"
#             )

#             print(e)

#             return

#         output_file = os.path.join(
#             OUTPUT_DIR,
#             nome_saida + ".json"
#         )

#         df.to_json(
#             output_file,
#             orient="records",
#             force_ascii=False,
#             indent=2
#         )

#     print("\nARQUIVO SALVO:")
#     print(output_file)


# # =========================================================
# # LOOP DOWNLOAD
# # =========================================================

# for (
#     estacao_codigo,
#     estacao_nome
# ) in estacoes_selecionadas.items():

#     for (
#         pol_nome,
#         pol_cod
#     ) in POLUENTES.items():

#         try:

#             baixar_dados(
#                 estacao_codigo,
#                 estacao_nome,
#                 pol_nome,
#                 pol_cod
#             )

#         except Exception as e:

#             print(
#                 "\nERRO:"
#             )

#             print(
#                 estacao_codigo,
#                 pol_nome,
#                 e
#             )

# print("\nFINALIZADO")