# Organiza a leitura dos produtos de satélite

### FUNCIONA PARA GOES-AOD MAS NÃO PARA SENTINEL-5P
import pandas as pd
import numpy as np
from satellite.raster_reader import get_satellite_mean

#--------------------

### CHAT PEDIU PARA MANTER ESSE SCRIPT
def get_satellite_series(
    sat_index,
    datas_unicas,
    lat_station,
    lon_station,
    delta,
    scale=1.0
):

    print("\n===== GET SATELLITE SERIES =====")
    print("Lat:", lat_station)
    print("Lon:", lon_station)
    print("Delta:", delta)
    print("Scale:", scale)
    print("Datas:", datas_unicas)
    print("Índice possui:", len(sat_index), "dias")

    sat_dates = []
    sat_values = []

    for data_ref in datas_unicas:

        yyyymmdd = pd.Timestamp(data_ref).strftime("%Y%m%d")

        arquivos = sat_index.get(yyyymmdd)

        print(
            "DATA:",
            yyyymmdd,
            "ARQUIVOS:",
            len(arquivos) if isinstance(arquivos, list) else arquivos
        )

        if arquivos is None:
            continue

        if isinstance(arquivos, str):
            arquivos = [arquivos]

        valores = []

        for tif_file in arquivos:

            valor = get_satellite_mean(
                tif_file,
                lat_station,
                lon_station,
                delta
            )

            print(
                "SAT:",
                tif_file,
                "=>",
                valor
            )

            if np.isfinite(valor):
                valores.append(valor)

        if not valores:
            continue

        valor_medio = np.mean(valores)

        sat_dates.append(
            pd.Timestamp(data_ref)
        )

        sat_values.append(
            valor_medio * scale
        )

    print(
        "RESULTADO SAT:",
        sat_dates,
        sat_values
    )

    return sat_dates, sat_values


# #------------------

# =========================================================
# GOES-16 AOD
#
# O índice GOES utiliza:
#
#     YYYYMMDD -> lista de arquivos
#
# Exemplo:
#
#     20240816 -> [
#         arquivo_20240816_000000.tif,
#         arquivo_20240816_001000.tif,
#         ...
#     ]
#
# Seleciona 1 arquivo por hora, escolhendo o arquivo
# mais próximo da hora cheia, e depois calcula
# a média diária.
# =========================================================

def get_goes_series_hourly(
    goes_index,
    datas_unicas,
    lat_station,
    lon_station,
    delta,
    scale=1.0
):

    import re
    import time

    print("\n")
    print("==============================================")
    print("===== GET GOES SERIES HOURLY ================")
    print("==============================================")

    print("Lat:", lat_station)
    print("Lon:", lon_station)
    print("Delta:", delta)
    print("Scale:", scale)
    print("Datas:", datas_unicas)
    print("Índice possui:", len(goes_index), "dias")

    goes_dates = []
    goes_values = []

    inicio_total = time.perf_counter()

    # =====================================================
    # LOOP DOS DIAS
    # =====================================================

    for data_ref in datas_unicas:

        inicio_dia = time.perf_counter()

        data_ref = pd.Timestamp(data_ref)

        yyyymmdd = data_ref.strftime("%Y%m%d")

        print("\n==============================================")
        print("GOES DATA:", yyyymmdd)
        print("==============================================")

        # =================================================
        # PEGA OS ARQUIVOS DIRETAMENTE PELO DIA
        # =================================================

        arquivos = goes_index.get(
            yyyymmdd
        )

        print(
            "ARQUIVOS DO DIA:",
            len(arquivos)
            if isinstance(arquivos, list)
            else arquivos
        )

        if arquivos is None:

            print(
                "GOES: nenhum arquivo encontrado para",
                yyyymmdd
            )

            continue

        # -------------------------------------------------
        # Se vier apenas uma string
        # -------------------------------------------------

        if isinstance(arquivos, str):

            arquivos = [
                arquivos
            ]

        # =================================================
        # SELECIONA 1 ARQUIVO POR HORA
        # =================================================

        arquivos_horarios = {}

        for tif_file in arquivos:

            nome = str(tif_file)

            # -------------------------------------------------
            # Procura YYYYMMDD_HHMMSS
            # -------------------------------------------------

            match = re.search(
                r"(\d{8})_(\d{6})",
                nome
            )

            if not match:

                print(
                    "GOES: timestamp não encontrado:",
                    nome
                )

                continue

            data_str = match.group(1)

            hora_str = match.group(2)

            # -------------------------------------------------
            # Garante que é realmente o dia solicitado
            # -------------------------------------------------

            if data_str != yyyymmdd:

                continue

            hora = int(
                hora_str[0:2]
            )

            minuto = int(
                hora_str[2:4]
            )

            segundo = int(
                hora_str[4:6]
            )

            # -------------------------------------------------
            # Distância até a hora cheia
            # -------------------------------------------------

            segundos_desde_hora = (
                minuto * 60 +
                segundo
            )

            distancia = min(
                segundos_desde_hora,
                3600 - segundos_desde_hora
            )

            # -------------------------------------------------
            # Verifica se já existe arquivo selecionado
            # para esta hora
            # -------------------------------------------------

            atual = arquivos_horarios.get(
                hora
            )

            # -------------------------------------------------
            # Guarda o arquivo mais próximo da hora cheia
            # -------------------------------------------------

            if (
                atual is None
                or distancia < atual["distancia"]
            ):

                arquivos_horarios[hora] = {

                    "arquivo": tif_file,

                    "distancia": distancia,

                    "hora_str": hora_str
                }

        # =================================================
        # ARQUIVOS SELECIONADOS
        # =================================================

        arquivos_selecionados = [

            arquivos_horarios[h]

            for h in sorted(
                arquivos_horarios
            )
        ]

        print(
            "ARQUIVOS ENCONTRADOS:",
            len(arquivos)
        )

        print(
            "ARQUIVOS SELECIONADOS:",
            len(arquivos_selecionados),
            "(1 por hora)"
        )

        # -------------------------------------------------
        # Mostra os arquivos selecionados
        # -------------------------------------------------

        for item in arquivos_selecionados:

            print(
                "  HORA:",
                item["hora_str"],
                "| distância:",
                item["distancia"],
                "s",
                "| arquivo:",
                item["arquivo"]
            )

        # =================================================
        # CALCULA VALORES HORÁRIOS
        # =================================================

        valores = []

        for item in arquivos_selecionados:

            tif_file = item["arquivo"]

            hora_str = item["hora_str"]

            inicio_tif = time.perf_counter()

            valor = get_satellite_mean(
                tif_file,
                lat_station,
                lon_station,
                delta
            )

            tempo_tif = (
                time.perf_counter()
                - inicio_tif
            )

            print(
                "GOES:",
                yyyymmdd,
                hora_str,
                "=>",
                valor,
                f"tempo={tempo_tif:.3f}s"
            )

            if np.isfinite(valor):

                valores.append(
                    valor
                )

        # =================================================
        # NENHUM VALOR VÁLIDO
        # =================================================

        if not valores:

            print(
                "GOES:",
                yyyymmdd,
                "=> NENHUM VALOR VÁLIDO"
            )

            continue

        # =================================================
        # MÉDIA DIÁRIA
        # =================================================

        valor_medio = np.mean(
            valores
        )

        valor_final = (
            valor_medio * scale
        )

        goes_dates.append(
            data_ref
        )

        goes_values.append(
            valor_final
        )

        tempo_dia = (
            time.perf_counter()
            - inicio_dia
        )

        print(
            "GOES MÉDIA DIÁRIA:",
            yyyymmdd,
            "=>",
            valor_final
        )

        print(
            f"TEMPO DIA {yyyymmdd}: "
            f"{tempo_dia:.3f}s"
        )

    # =====================================================
    # RESULTADO FINAL
    # =====================================================

    tempo_total = (
        time.perf_counter()
        - inicio_total
    )

    print("\n")
    print("==============================================")
    print("===== RESULTADO GOES HOURLY ==================")
    print("==============================================")

    print(
        "DATAS:",
        goes_dates
    )

    print(
        "VALORES:",
        goes_values
    )

    print(
        f"TEMPO TOTAL GOES = "
        f"{tempo_total:.3f}s"
    )

    return goes_dates, goes_values

#--------------------
# def get_goes_series_hourly(
#     goes_index,
#     datas_unicas,
#     lat_station,
#     lon_station,
#     delta,
#     scale=1.0
# ):
#     """
#     Extrai dados GOES-AOD.

#     Para cada dia:
#         1. localiza todos os arquivos GOES daquele dia;
#         2. seleciona apenas um arquivo por hora;
#         3. escolhe o arquivo mais próximo da hora cheia;
#         4. calcula a média dos valores horários;
#         5. gera um único valor diário.

#     Exemplo de arquivos:

#         20240820_140000
#         20240820_141000
#         20240820_142000
#         ...
        
#     Para a hora 14, será escolhido o arquivo mais próximo de 14:00.
#     """

#     import re
#     import time

#     print("\n==============================================")
#     print("===== GET GOES SERIES HOURLY =====")
#     print("==============================================")

#     print("Lat:", lat_station)
#     print("Lon:", lon_station)
#     print("Delta:", delta)
#     print("Scale:", scale)
#     print("Datas:", datas_unicas)
#     print("Índice GOES possui:", len(goes_index), "entradas")

#     goes_dates = []
#     goes_values = []

#     inicio_total = time.perf_counter()

#     # =========================================================
#     # PERCORRE OS DIAS
#     # =========================================================

#     for data_ref in datas_unicas:

#         inicio_dia = time.perf_counter()

#         data_ref = pd.Timestamp(data_ref)

#         yyyymmdd = data_ref.strftime("%Y%m%d")

#         print("\n==============================================")
#         print("GOES DATA:", yyyymmdd)
#         print("==============================================")

#         # =====================================================
#         # LOCALIZA TODOS OS ARQUIVOS GOES DO DIA
#         #
#         # O índice GOES pode estar no formato:
#         #
#         # YYYYMMDD_HHMMSS -> arquivo
#         #
#         # Por isso procuramos pelas chaves.
#         # =====================================================

#         arquivos_dia = []

#         for key, tif_file in goes_index.items():

#             key_str = str(key)

#             # -------------------------------------------------
#             # Caso a chave já contenha:
#             #
#             # 20240820_143020
#             # -------------------------------------------------

#             if key_str.startswith(yyyymmdd + "_"):

#                 arquivos_dia.append(
#                     (
#                         key_str,
#                         tif_file
#                     )
#                 )

#                 continue

#             # -------------------------------------------------
#             # Caso a chave não tenha timestamp, mas o nome
#             # do arquivo tenha.
#             # -------------------------------------------------

#             nome = str(tif_file)

#             match = re.search(
#                 r"(\d{8})_(\d{6})",
#                 nome
#             )

#             if match:

#                 data_str = match.group(1)

#                 if data_str == yyyymmdd:

#                     arquivos_dia.append(
#                         (
#                             match.group(1) + "_" + match.group(2),
#                             tif_file
#                         )
#                     )

#         # =====================================================
#         # ORDENA
#         # =====================================================

#         arquivos_dia = sorted(
#             arquivos_dia,
#             key=lambda x: x[0]
#         )

#         print(
#             "ARQUIVOS GOES ENCONTRADOS:",
#             len(arquivos_dia)
#         )

#         if not arquivos_dia:

#             print(
#                 "Nenhum arquivo GOES encontrado para",
#                 yyyymmdd
#             )

#             continue

#         # =====================================================
#         # SELECIONA 1 ARQUIVO POR HORA
#         #
#         # Escolhe o arquivo mais próximo de:
#         #
#         # 00:00
#         # 01:00
#         # 02:00
#         # ...
#         # 23:00
#         # =====================================================

#         arquivos_horarios = {}

#         for key, tif_file in arquivos_dia:

#             try:

#                 data_hora = pd.to_datetime(
#                     key,
#                     format="%Y%m%d_%H%M%S"
#                 )

#             except Exception as e:

#                 print(
#                     "Erro convertendo chave:",
#                     key,
#                     e
#                 )

#                 continue

#             hora = data_hora.hour

#             minuto = data_hora.minute

#             segundo = data_hora.second

#             # -------------------------------------------------
#             # Segundos desde o início da hora
#             # -------------------------------------------------

#             segundos_desde_hora = (
#                 minuto * 60 +
#                 segundo
#             )

#             # -------------------------------------------------
#             # Distância para a hora cheia
#             #
#             # Exemplo:
#             #
#             # 13:50 -> 600 segundos
#             # 14:10 -> 600 segundos
#             #
#             # Portanto ambos estão igualmente próximos de
#             # uma hora cheia.
#             # -------------------------------------------------

#             distancia = min(
#                 segundos_desde_hora,
#                 3600 - segundos_desde_hora
#             )

#             atual = arquivos_horarios.get(
#                 hora
#             )

#             # -------------------------------------------------
#             # Guarda o arquivo mais próximo da hora cheia
#             # -------------------------------------------------

#             if (
#                 atual is None
#                 or distancia < atual["distancia"]
#             ):

#                 arquivos_horarios[hora] = {

#                     "arquivo": tif_file,

#                     "key": key,

#                     "distancia": distancia
#                 }

#         # =====================================================
#         # LISTA FINAL DOS ARQUIVOS
#         # =====================================================

#         arquivos_selecionados = [

#             arquivos_horarios[h]

#             for h in sorted(
#                 arquivos_horarios
#             )
#         ]

#         print(
#             "ARQUIVOS SELECIONADOS:",
#             len(arquivos_selecionados)
#         )

#         for item in arquivos_selecionados:

#             print(
#                 "  ",
#                 item["key"],
#                 "distância:",
#                 item["distancia"],
#                 "s"
#             )

#         # =====================================================
#         # CALCULA OS VALORES HORÁRIOS
#         # =====================================================

#         valores = []

#         for item in arquivos_selecionados:

#             tif_file = item["arquivo"]

#             key = item["key"]

#             inicio_tif = time.perf_counter()

#             valor = get_satellite_mean(
#                 tif_file,
#                 lat_station,
#                 lon_station,
#                 delta
#             )

#             tempo_tif = (
#                 time.perf_counter()
#                 - inicio_tif
#             )

#             print(
#                 "GOES:",
#                 key,
#                 "=>",
#                 valor,
#                 f"tempo={tempo_tif:.3f}s"
#             )

#             if np.isfinite(valor):

#                 valores.append(
#                     valor
#                 )

#         # =====================================================
#         # NENHUM VALOR VÁLIDO
#         # =====================================================

#         if not valores:

#             print(
#                 "Nenhum valor GOES válido para",
#                 yyyymmdd
#             )

#             continue

#         # =====================================================
#         # MÉDIA DIÁRIA
#         # =====================================================

#         valor_medio = np.mean(
#             valores
#         )

#         goes_dates.append(
#             data_ref
#         )

#         goes_values.append(
#             valor_medio * scale
#         )

#         tempo_dia = (
#             time.perf_counter()
#             - inicio_dia
#         )

#         print(
#             "GOES MÉDIA DIÁRIA:",
#             yyyymmdd,
#             "=>",
#             valor_medio * scale
#         )

#         print(
#             f"TEMPO DIA {yyyymmdd}: "
#             f"{tempo_dia:.3f}s"
#         )

#     # =========================================================
#     # RESULTADO
#     # =========================================================

#     tempo_total = (
#         time.perf_counter()
#         - inicio_total
#     )

#     print("\n==============================================")
#     print("===== RESULTADO GOES HORÁRIO =====")
#     print("==============================================")

#     print(
#         "DATAS:",
#         goes_dates
#     )

#     print(
#         "VALORES:",
#         goes_values
#     )

#     print(
#         f"TEMPO TOTAL GOES = "
#         f"{tempo_total:.3f}s"
#     )

#     return goes_dates, goes_values




#-------------------


### eSSA VERSÃO não funcionou para o goes-aod
# def get_goes_series_hourly(
#     goes_index,
#     datas_unicas,
#     lat_station,
#     lon_station,
#     delta,
#     scale=1.0
# ):
#     """
#     Extrai dados GOES usando no máximo um arquivo por hora.

#     Os arquivos GOES normalmente possuem timestamps como:

#         YYYYMMDD_HHMMSS

#     Exemplo:

#         20240820_140000
#         20240820_141000
#         20240820_142000
#         ...

#     Neste caso será utilizado apenas o primeiro arquivo
#     disponível de cada hora.

#     Depois os valores horários são utilizados para calcular
#     uma média diária.
#     """

#     goes_dates = []
#     goes_values = []

#     for data_ref in datas_unicas:

#         data_ref = pd.Timestamp(data_ref)

#         prefix = data_ref.strftime("%Y%m%d")

#         # -------------------------------------------------
#         # Arquivos daquele dia
#         # -------------------------------------------------

#         arquivos_dia = sorted(
#             (
#                 key,
#                 tif_file
#             )
#             for key, tif_file in goes_index.items()
#             if key.startswith(prefix + "_")
#         )

#         print(
#             "\nGOES DATA:",
#             prefix,
#             "ARQUIVOS:",
#             len(arquivos_dia)
#         )

#         if not arquivos_dia:
#             continue

#         # -------------------------------------------------
#         # Seleciona apenas 1 arquivo por hora
#         # -------------------------------------------------

#         arquivos_hora = {}

#         for key, tif_file in arquivos_dia:

#             try:

#                 data_hora = pd.to_datetime(
#                     key,
#                     format="%Y%m%d_%H%M%S"
#                 )

#             except Exception as e:

#                 print(
#                     "Erro convertendo chave GOES:",
#                     key,
#                     e
#                 )

#                 continue

#             hora = data_hora.strftime("%Y%m%d_%H")

#             # Primeiro arquivo encontrado daquela hora
#             if hora not in arquivos_hora:

#                 arquivos_hora[hora] = (
#                     key,
#                     tif_file
#                 )

#         print(
#             "GOES:",
#             len(arquivos_dia),
#             "arquivos encontrados"
#         )

#         print(
#             "GOES:",
#             len(arquivos_hora),
#             "arquivos selecionados (1/hora)"
#         )

#         # -------------------------------------------------
#         # Calcula valor de cada arquivo horário
#         # -------------------------------------------------

#         valores_horarios = []

#         for hora in sorted(arquivos_hora):

#             key, tif_file = arquivos_hora[hora]

#             valor = get_satellite_mean(
#                 tif_file,
#                 lat_station,
#                 lon_station,
#                 delta
#             )

#             if not np.isfinite(valor):
#                 continue

#             valores_horarios.append(
#                 valor
#             )

#             print(
#                 "GOES HORA:",
#                 key,
#                 "=>",
#                 valor
#             )

#         # -------------------------------------------------
#         # Média diária
#         # -------------------------------------------------

#         if not valores_horarios:
#             continue

#         valor_diario = np.mean(
#             valores_horarios
#         )

#         goes_dates.append(
#             data_ref
#         )

#         goes_values.append(
#             valor_diario * scale
#         )

#         print(
#             "GOES MÉDIA DIÁRIA:",
#             prefix,
#             "=>",
#             valor_diario * scale
#         )

#     print(
#         "\n===== RESULTADO GOES HORÁRIO ====="
#     )

#     print(
#         "DATAS:",
#         goes_dates
#     )

#     print(
#         "VALORES:",
#         goes_values
#     )

#     return goes_dates, goes_values




#------------------

### Essa função não está sendo utilizada....  
### Verificar, se realmente não estiver sendo usada, remover
# =========================================================
# Função para leitura dos produtos GOES com data + hora
# =========================================================
def get_goes_series(
    goes_index,
    datas_unicas,
    lat_station,
    lon_station,
    delta,
    scale=1.0
):
    """
    Extrai série temporal dos produtos GOES.

    O índice GOES utiliza chaves no formato:

        YYYYMMDD_HHMMSS

    Exemplo:

        20240816_143020
        20240816_152020
        20240816_181020

    Retorna um ponto para cada arquivo GOES disponível.
    """

    goes_dates = []
    goes_values = []

    for data_ref in datas_unicas:

        data_ref = pd.Timestamp(data_ref)

        prefix = data_ref.strftime(
            "%Y%m%d"
        )

        # -------------------------------------------------
        # Todos os arquivos GOES daquele dia
        # -------------------------------------------------

        arquivos_dia = sorted(
            (
                key,
                tif_file
            )
            for key, tif_file in goes_index.items()
            if key.startswith(prefix + "_")
        )

        # -------------------------------------------------
        # Processa cada horário
        # -------------------------------------------------

        for key, tif_file in arquivos_dia:

            valor = get_satellite_mean(
                tif_file,
                lat_station,
                lon_station,
                delta
            )

            print("\n>>> TESTANDO ARQUIVO GOES")
            print("KEY =", key)
            print("ARQUIVO =", tif_file)
            print("LAT =", lat_station)
            print("LON =", lon_station)
            print("DELTA =", delta)          
            print(">>> RESULTADO =", valor)

            if not np.isfinite(valor):
                continue

            # ---------------------------------------------
            # YYYYMMDD_HHMMSS
            # →
            # Timestamp
            # ---------------------------------------------

            data_hora = pd.to_datetime(
                key,
                format="%Y%m%d_%H%M%S"
            )

            goes_dates.append(
                data_hora
            )

            goes_values.append(
                valor * scale
            )

    return goes_dates, goes_values


### Essa versão funcionou para o goes-aod mas não apareceu 
### o satélite Sentinel-5P
# # =========================================================
# # Função para leitura dos produtos de satélite
# # =========================================================

# def get_satellite_series(
#     sat_index,
#     datas_unicas,
#     lat_station,
#     lon_station,
#     delta,
#     scale=1.0
# ):

#     import time

#     print("\n===== GET SATELLITE SERIES =====")
#     print("Lat:", lat_station)
#     print("Lon:", lon_station)
#     print("Delta:", delta)
#     print("Scale:", scale)
#     print("Datas:", datas_unicas)
#     print("Índice possui:", len(sat_index), "dias")

#     sat_dates = []
#     sat_values = []

#     inicio_total = time.perf_counter()

#     for data_ref in datas_unicas:

#         inicio_dia = time.perf_counter()

#         data_ref = pd.Timestamp(data_ref)

#         yyyymmdd = data_ref.strftime("%Y%m%d")

#         arquivos = sat_index.get(
#             yyyymmdd
#         )

#         print(
#             "\nDATA:",
#             yyyymmdd,
#             "ARQUIVOS:",
#             len(arquivos) if isinstance(arquivos, list) else arquivos
#         )

#         if arquivos is None:
#             continue

#         if isinstance(arquivos, str):
#             arquivos = [arquivos]

#         # =================================================
#         # SELECIONA 1 ARQUIVO POR HORA
#         # =================================================

#         arquivos_horarios = {}

#         for tif_file in arquivos:

#             # -------------------------------------------------
#             # Extrai o horário do nome/caminho do arquivo
#             # -------------------------------------------------

#             nome = str(tif_file)

#             # Procura padrão YYYYMMDD_HHMMSS
#             import re

#             match = re.search(
#                 r"(\d{8})_(\d{6})",
#                 nome
#             )

#             if not match:
#                 continue

#             data_str = match.group(1)
#             hora_str = match.group(2)

#             if data_str != yyyymmdd:
#                 continue

#             hora = int(
#                 hora_str[0:2]
#             )

#             minuto = int(
#                 hora_str[2:4]
#             )

#             segundo = int(
#                 hora_str[4:6]
#             )

#             # -------------------------------------------------
#             # Distância para a hora cheia
#             # -------------------------------------------------

#             segundos_desde_hora = (
#                 minuto * 60 +
#                 segundo
#             )

#             # Distância circular dentro da hora
#             distancia = min(
#                 segundos_desde_hora,
#                 3600 - segundos_desde_hora
#             )

#             # -------------------------------------------------
#             # Guarda o mais próximo da hora cheia
#             # -------------------------------------------------

#             atual = arquivos_horarios.get(
#                 hora
#             )

#             if (
#                 atual is None
#                 or distancia < atual["distancia"]
#             ):

#                 arquivos_horarios[hora] = {

#                     "arquivo": tif_file,

#                     "distancia": distancia
#                 }

#         # =================================================
#         # PROCESSA OS ARQUIVOS HORÁRIOS
#         # =================================================

#         arquivos_selecionados = [

#             arquivos_horarios[h]["arquivo"]

#             for h in sorted(
#                 arquivos_horarios
#             )
#         ]

#         print(
#             "ARQUIVOS SELECIONADOS:",
#             len(arquivos_selecionados)
#         )

#         valores = []

#         for tif_file in arquivos_selecionados:

#             inicio_tif = time.perf_counter()

#             valor = get_satellite_mean(
#                 tif_file,
#                 lat_station,
#                 lon_station,
#                 delta
#             )

#             tempo_tif = (
#                 time.perf_counter()
#                 - inicio_tif
#             )

#             print(
#                 "GOES:",
#                 tif_file,
#                 "=>",
#                 valor,
#                 f"tempo={tempo_tif:.3f}s"
#             )

#             if np.isfinite(valor):

#                 valores.append(
#                     valor
#                 )

#         # =================================================
#         # NENHUM VALOR VÁLIDO
#         # =================================================

#         if not valores:
#             continue

#         # =================================================
#         # MÉDIA DIÁRIA
#         # =================================================

#         valor_medio = np.mean(
#             valores
#         )

#         sat_dates.append(
#             data_ref
#         )

#         sat_values.append(
#             valor_medio * scale
#         )

#         tempo_dia = (
#             time.perf_counter()
#             - inicio_dia
#         )

#         print(
#             f"TEMPO DIA {yyyymmdd}: "
#             f"{tempo_dia:.3f}s"
#         )

#     tempo_total = (
#         time.perf_counter()
#         - inicio_total
#     )

#     print(
#         "\n===== RESULTADO SAT ====="
#     )

#     print(
#         "DATAS:",
#         sat_dates
#     )

#     print(
#         "VALORES:",
#         sat_values
#     )

#     print(
#         f"TEMPO TOTAL GOES = "
#         f"{tempo_total:.3f}s"
#     )

#     return sat_dates, sat_values


# # VERSÃO FUNCIONAVA MAS DEPOIS DE MUDAR PARA BUSCAR ARQUIVOS 
# # GOES MAIS PRÓXIMO DA HORA E NÃO DE 10 EM 10 MINUTOS, FOI 
# # ALTERADA PARA A NOVA VERSÃO. Essa versão também está causando 
# # o erro: 
# # ERRO REAL NO FETCH: TypeError: NetworkError when attempting to fetch resource.
# def get_satellite_series(
#     sat_index,
#     datas_unicas,
#     lat_station,
#     lon_station,
#     delta,
#     scale=1.0
# ):

#     print("\n===== GET SATELLITE SERIES =====")
#     print("Lat:", lat_station)
#     print("Lon:", lon_station)
#     print("Delta:", delta)
#     print("Scale:", scale)
#     print("Datas:", datas_unicas)
#     print("Índice possui:", len(sat_index), "dias")


#     sat_dates = []
#     sat_values = []

#     for data_ref in datas_unicas:

#         yyyymmdd = pd.Timestamp(
#             data_ref
#         ).strftime("%Y%m%d")

#         arquivos = sat_index.get(
#             yyyymmdd
#         )

#         print(
#             "DATA:",
#             yyyymmdd,
#             "ARQUIVOS:",
#             len(arquivos) if isinstance(arquivos, list) else arquivos
#         )        

#         if arquivos is None:
#             continue

#         # ==================================================
#         # Produto diário
#         # ==================================================

#         if isinstance(arquivos, str):

#             arquivos = [arquivos]

#         # ==================================================
#         # GOES
#         # ==================================================

#         valores = []

#         for tif_file in arquivos:

#             valor = get_satellite_mean(
#                 tif_file,
#                 lat_station,
#                 lon_station,
#                 delta
#             )

#             print(
#                 "GOES:",
#                 tif_file,
#                 "=>",
#                 valor
#             )


#             if np.isfinite(valor):

#                 valores.append(
#                     valor
#                 )

#         # --------------------------------------------------
#         # Nenhum valor válido
#         # --------------------------------------------------

#         if not valores:
#             continue

#         # --------------------------------------------------
#         # Média diária
#         # --------------------------------------------------

#         valor_medio = np.mean(
#             valores
#         )

#         sat_dates.append(
#             pd.Timestamp(data_ref)
#         )

#         sat_values.append(
#             valor_medio * scale
#         )

#     print(
#         "RESULTADO GOES:",
#         sat_dates,
#         sat_values
#     )

#     return sat_dates, sat_values





# import pandas as pd
# import numpy as np

# from satellite.raster_reader import get_satellite_mean


# # =========================================================
# # Função para leitura dos produtos de satélite
# # =========================================================

# def get_satellite_series(
#     sat_index,
#     datas_unicas,
#     lat_station,
#     lon_station,
#     delta,
#     scale=1.0
# ):

#     sat_dates = []
#     sat_values = []

#     for data_ref in datas_unicas:

#         yyyymmdd = pd.Timestamp(
#             data_ref
#         ).strftime("%Y%m%d")

#         arquivos = sat_index.get(yyyymmdd)

#         if arquivos is None:
#             continue

#         # =====================================================
#         # Produto diário: um único TIFF
#         # =====================================================

#         if isinstance(arquivos, str):

#             valor = get_satellite_mean(
#                 arquivos,
#                 lat_station,
#                 lon_station,
#                 delta
#             )

#             if np.isfinite(valor):

#                 sat_dates.append(
#                     pd.Timestamp(data_ref)
#                 )

#                 sat_values.append(
#                     valor * scale
#                 )

#         # =====================================================
#         # GOES: vários TIFFs no mesmo dia
#         # =====================================================

#         else:

#             valores = []

#             for arquivo in arquivos:

#                 valor = get_satellite_mean(
#                     arquivo,
#                     lat_station,
#                     lon_station,
#                     delta
#                 )

#                 if np.isfinite(valor):

#                     valores.append(valor)

#             if valores:

#                 valor_medio = np.mean(valores)

#                 sat_dates.append(
#                     pd.Timestamp(data_ref)
#                 )

#                 sat_values.append(
#                     valor_medio * scale
#                 )

#     return sat_dates, sat_values



###**************************** gráfico funciona para sat e estação, goes-aod nao.
# def get_satellite_series(
#     sat_index,
#     datas_unicas,
#     lat_station,
#     lon_station,
#     delta,
#     scale=1.0
# ):

#     sat_dates = []
#     sat_values = []

#     for data_ref in datas_unicas:

#         yyyymmdd = pd.Timestamp(
#             data_ref
#         ).strftime("%Y%m%d")

#         arquivos = sat_index.get(yyyymmdd)

#         if not arquivos:
#             continue

#         # -------------------------------------------------
#         # Compatibilidade com índice antigo:
#         # se vier apenas uma string, transforma em lista
#         # -------------------------------------------------
#         if isinstance(arquivos, str):

#             arquivos = [arquivos]

#         valores_dia = []

#         # -------------------------------------------------
#         # Processa todos os horários daquele dia
#         # -------------------------------------------------
#         for tif_file in arquivos:

#             try:

#                 valor = get_satellite_mean(
#                     tif_file,
#                     lat_station,
#                     lon_station,
#                     delta
#                 )

#                 if np.isfinite(valor):

#                     valores_dia.append(
#                         valor
#                     )

#             except Exception as e:

#                 print(
#                     f"Erro lendo {tif_file}: {e}"
#                 )

#         # -------------------------------------------------
#         # Nenhum valor válido naquele dia
#         # -------------------------------------------------
#         if not valores_dia:
#             continue

#         # -------------------------------------------------
#         # Média dos horários válidos
#         # -------------------------------------------------
#         valor_medio = np.mean(
#             valores_dia
#         )

#         sat_dates.append(
#             pd.Timestamp(data_ref)
#         )

#         sat_values.append(
#             valor_medio * scale
#         )

#     return sat_dates, sat_values




# # Organiza a leitura dos produtos de satélite
# # get_satellite_series()

# import pandas as pd
# import numpy as np

# from satellite.raster_reader import get_satellite_mean

# # =========================================================
# # Função para leitura dos produtos de satélite
# # =========================================================
# def get_satellite_series(
#     sat_index,
#     datas_unicas,
#     lat_station,
#     lon_station,
#     delta,
#     scale=1.0
# ):

#     sat_dates = []
#     sat_values = []

#     for data_ref in datas_unicas:

#         yyyymmdd = pd.Timestamp(
#             data_ref
#         ).strftime("%Y%m%d")

#         arquivos = sat_index.get(yyyymmdd)

#         if not arquivos:
#             continue

#         # =====================================================
#         # Garantir que seja sempre uma lista
#         # =====================================================

#         if isinstance(arquivos, str):

#             arquivos = [arquivos]

#         valores_dia = []

#         # =====================================================
#         # Ler todos os arquivos daquela data
#         # =====================================================

#         for tif_file in arquivos:

#             try:

#                 valor = get_satellite_mean(
#                     tif_file,
#                     lat_station,
#                     lon_station,
#                     delta
#                 )

#                 if np.isfinite(valor):

#                     valores_dia.append(
#                         valor
#                     )

#             except Exception as e:

#                 print(
#                     f"Erro lendo {tif_file}: {e}"
#                 )

#         # =====================================================
#         # Se nenhum arquivo possui valor válido
#         # =====================================================

#         if not valores_dia:
#             continue

#         # =====================================================
#         # Média diária dos horários disponíveis
#         # =====================================================

#         valor_medio = np.mean(
#             valores_dia
#         )

#         sat_dates.append(
#             pd.Timestamp(data_ref)
#         )

#         sat_values.append(
#             valor_medio * scale
#         )

#     return sat_dates, sat_values





# def get_satellite_series(
#     sat_index,
#     datas_unicas,
#     lat_station,
#     lon_station,
#     delta,
#     scale=1.0
# ):

#     sat_dates = []
#     sat_values = []

#     for data_ref in datas_unicas:

#         yyyymmdd = pd.Timestamp(
#             data_ref
#         ).strftime("%Y%m%d")

#         tif_file = sat_index.get(yyyymmdd)

#         if tif_file is None:
#             continue

#         valor = get_satellite_mean(
#             tif_file,
#             lat_station,
#             lon_station,
#             delta
#         )

#         if np.isfinite(valor):

#             sat_dates.append(
#                 pd.Timestamp(data_ref)
#             )

#             sat_values.append(
#                 valor * scale
#             )

#     return sat_dates, sat_values


