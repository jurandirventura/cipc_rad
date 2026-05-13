import os
import time
import glob
import pandas as pd

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# ==========================================================
# CONFIGURAÇÕES
# ==========================================================

DOWNLOAD_DIR = os.path.expanduser("~/cetesb_downloads")

DATA_INICIO = "15/08/2024"
DATA_FIM    = "25/08/2024"

POLUENTES = [
    "SO2",
    "NO2",
    "O3",
    "MP2.5",
    "MP10",
    "CO"
]

# ==========================================================
# CHROME
# ==========================================================

# chrome_options.binary_location = "/usr/bin/chromium-browser"

# driver = webdriver.Chrome(
#     service=Service(),
#     options=chrome_options
# )

# chrome_options = Options()

# prefs = {
#     "download.default_directory": DOWNLOAD_DIR,
#     "download.prompt_for_download": False,
#     "download.directory_upgrade": True,
#     "safebrowsing.enabled": True
# }

# chrome_options.add_experimental_option("prefs", prefs)

# chrome_options.add_argument("--headless=new")
# chrome_options.add_argument("--window-size=1920,1080")

# driver = webdriver.Chrome(options=chrome_options)

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

chrome_options = Options()

chrome_options.binary_location = "/usr/bin/chromium"

prefs = {
    "download.default_directory": DOWNLOAD_DIR,
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "safebrowsing.enabled": True
}

chrome_options.add_experimental_option("prefs", prefs)

chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")

driver = webdriver.Chrome(
    service=Service(),
    options=chrome_options
)


# ==========================================================
# ACESSAR QUALAR
# ==========================================================

url = "https://qualar.cetesb.sp.gov.br/qualar/exportaDados.do"

driver.get(url)

time.sleep(5)

# ==========================================================
# LOOP DOS POLUENTES
# ==========================================================

for poluente in POLUENTES:

    print(f"\nBaixando {poluente}")

    # ------------------------------------------------------
    # Seleciona poluente
    # ------------------------------------------------------

    select_pol = Select(
        driver.find_element(By.NAME, "idParametro")
    )

    encontrou = False

    for option in select_pol.options:

        texto = option.text.upper()

        if poluente in texto:

            select_pol.select_by_visible_text(option.text)

            encontrou = True
            break

    if not encontrou:
        print(f"Poluente não encontrado: {poluente}")
        continue

    time.sleep(2)

    # ------------------------------------------------------
    # Datas
    # ------------------------------------------------------

    driver.find_element(By.NAME, "dataInicial").clear()
    driver.find_element(By.NAME, "dataInicial").send_keys(DATA_INICIO)

    driver.find_element(By.NAME, "dataFinal").clear()
    driver.find_element(By.NAME, "dataFinal").send_keys(DATA_FIM)

    # ------------------------------------------------------
    # Média diária
    # ------------------------------------------------------

    select_tempo = Select(
        driver.find_element(By.NAME, "periodo")
    )

    for option in select_tempo.options:

        if "DIÁRIA" in option.text.upper():
            select_tempo.select_by_visible_text(option.text)
            break

    time.sleep(2)

    # ------------------------------------------------------
    # Exportar CSV
    # ------------------------------------------------------

    botoes = driver.find_elements(By.TAG_NAME, "input")

    for botao in botoes:

        value = botao.get_attribute("value")

        if value and "CSV" in value.upper():

            botao.click()
            break

    print("Aguardando download...")

    time.sleep(10)

# ==========================================================
# FECHAR
# ==========================================================

driver.quit()

# ==========================================================
# CONCATENAR CSVs
# ==========================================================

arquivos = glob.glob(
    os.path.join(DOWNLOAD_DIR, "*.csv")
)

dfs = []

for arq in arquivos:

    try:

        df = pd.read_csv(
            arq,
            sep=";",
            encoding="latin1"
        )

        df["arquivo_origem"] = os.path.basename(arq)

        dfs.append(df)

    except Exception as e:

        print(f"Erro lendo {arq}")
        print(e)

# ==========================================================
# CSV FINAL
# ==========================================================

if dfs:

    final = pd.concat(dfs, ignore_index=True)

    output_csv = os.path.join(
        DOWNLOAD_DIR,
        "cetesb_qualidade_ar_20240815_20240825.csv"
    )

    final.to_csv(
        output_csv,
        sep=";",
        index=False,
        encoding="utf-8"
    )

    print("\nArquivo final:")
    print(output_csv)

else:

    print("Nenhum CSV encontrado.")









# Primeira cópia reserver (não funcionou com chromium)

# import os
# import time
# import glob
# import pandas as pd

# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import Select
# from selenium.webdriver.chrome.options import Options

# # ==========================================================
# # CONFIGURAÇÕES
# # ==========================================================

# DOWNLOAD_DIR = os.path.expanduser("~/cetesb_downloads")

# DATA_INICIO = "15/08/2024"
# DATA_FIM    = "25/08/2024"

# POLUENTES = [
#     "SO2",
#     "NO2",
#     "O3",
#     "MP2.5",
#     "MP10",
#     "CO"
# ]

# # ==========================================================
# # CHROME
# # ==========================================================

# chrome_options = Options()

# prefs = {
#     "download.default_directory": DOWNLOAD_DIR,
#     "download.prompt_for_download": False,
#     "download.directory_upgrade": True,
#     "safebrowsing.enabled": True
# }

# chrome_options.add_experimental_option("prefs", prefs)

# chrome_options.add_argument("--headless=new")
# chrome_options.add_argument("--window-size=1920,1080")

# driver = webdriver.Chrome(options=chrome_options)

# # ==========================================================
# # ACESSAR QUALAR
# # ==========================================================

# url = "https://qualar.cetesb.sp.gov.br/qualar/exportaDados.do"

# driver.get(url)

# time.sleep(5)

# # ==========================================================
# # LOOP DOS POLUENTES
# # ==========================================================

# for poluente in POLUENTES:

#     print(f"\nBaixando {poluente}")

#     # ------------------------------------------------------
#     # Seleciona poluente
#     # ------------------------------------------------------

#     select_pol = Select(
#         driver.find_element(By.NAME, "idParametro")
#     )

#     encontrou = False

#     for option in select_pol.options:

#         texto = option.text.upper()

#         if poluente in texto:

#             select_pol.select_by_visible_text(option.text)

#             encontrou = True
#             break

#     if not encontrou:
#         print(f"Poluente não encontrado: {poluente}")
#         continue

#     time.sleep(2)

#     # ------------------------------------------------------
#     # Datas
#     # ------------------------------------------------------

#     driver.find_element(By.NAME, "dataInicial").clear()
#     driver.find_element(By.NAME, "dataInicial").send_keys(DATA_INICIO)

#     driver.find_element(By.NAME, "dataFinal").clear()
#     driver.find_element(By.NAME, "dataFinal").send_keys(DATA_FIM)

#     # ------------------------------------------------------
#     # Média diária
#     # ------------------------------------------------------

#     select_tempo = Select(
#         driver.find_element(By.NAME, "periodo")
#     )

#     for option in select_tempo.options:

#         if "DIÁRIA" in option.text.upper():
#             select_tempo.select_by_visible_text(option.text)
#             break

#     time.sleep(2)

#     # ------------------------------------------------------
#     # Exportar CSV
#     # ------------------------------------------------------

#     botoes = driver.find_elements(By.TAG_NAME, "input")

#     for botao in botoes:

#         value = botao.get_attribute("value")

#         if value and "CSV" in value.upper():

#             botao.click()
#             break

#     print("Aguardando download...")

#     time.sleep(10)

# # ==========================================================
# # FECHAR
# # ==========================================================

# driver.quit()

# # ==========================================================
# # CONCATENAR CSVs
# # ==========================================================

# arquivos = glob.glob(
#     os.path.join(DOWNLOAD_DIR, "*.csv")
# )

# dfs = []

# for arq in arquivos:

#     try:

#         df = pd.read_csv(
#             arq,
#             sep=";",
#             encoding="latin1"
#         )

#         df["arquivo_origem"] = os.path.basename(arq)

#         dfs.append(df)

#     except Exception as e:

#         print(f"Erro lendo {arq}")
#         print(e)

# # ==========================================================
# # CSV FINAL
# # ==========================================================

# if dfs:

#     final = pd.concat(dfs, ignore_index=True)

#     output_csv = os.path.join(
#         DOWNLOAD_DIR,
#         "cetesb_qualidade_ar_20240815_20240825.csv"
#     )

#     final.to_csv(
#         output_csv,
#         sep=";",
#         index=False,
#         encoding="utf-8"
#     )

#     print("\nArquivo final:")
#     print(output_csv)

# else:

#     print("Nenhum CSV encontrado.")