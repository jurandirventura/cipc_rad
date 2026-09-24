#!/usr/bin/env python3

import json
import csv
import re
import unicodedata
import requests
from pathlib import Path

# ============================================================
# CONFIGURAÇÃO
# ============================================================

# ------------------------------------------------------------
# LISTA OFICIAL CETESB
#
# Esta é a fonte principal das informações das estações:
#
# codigo_cetesb
# nome
# tipo
# status
# latitude
# longitude
# ------------------------------------------------------------

ARQUIVO_OFICIAL = Path(
    "/home/jurandir/cipc_data/cetesb/"
    "lista_estacoes_cetesb_oficial.json"
)


# ------------------------------------------------------------
# LISTA GERADA AUTOMATICAMENTE
#
# Será utilizada somente para obter:
#
# codigo = código verdadeiro da estação
# ------------------------------------------------------------

ARQUIVO_GERADO = Path(
    "/home/jurandir/cipc_data/cetesb/"
    "lista_estacoes_geradoAutomaticamente.json"
)


# ------------------------------------------------------------
# ARQUIVO DE COMPARAÇÃO
# ------------------------------------------------------------

ARQUIVO_COMPARACAO = Path(
    "/home/jurandir/cipc_data/cetesb/"
    "comparacao_estacoes_cetesb.csv"
)


# ------------------------------------------------------------
# LISTA FINAL
# ------------------------------------------------------------

ARQUIVO_FINAL = Path(
    "/home/jurandir/cipc_data/cetesb/"
    "lista_estacoes.json"
)


# ============================================================
# NORMALIZAR NOME
# ============================================================

def normalizar_nome(nome):

    if nome is None:
        return ""

    nome = str(nome).strip().lower()

    # Remover acentos
    nome = unicodedata.normalize(
        "NFD",
        nome
    )

    nome = "".join(
        c
        for c in nome
        if unicodedata.category(c) != "Mn"
    )

    # Padronizar separadores
    nome = nome.replace("-", " ")
    nome = nome.replace("_", " ")
    nome = nome.replace(".", " ")

    # Remover caracteres especiais
    nome = re.sub(
        r"[^a-z0-9 ]+",
        " ",
        nome
    )

    # Espaços múltiplos
    nome = re.sub(
        r"\s+",
        " ",
        nome
    ).strip()

    return nome


# ============================================================
# CARREGAR JSON
# ============================================================

def carregar_json(arquivo):

    with open(
        arquivo,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


# ============================================================
# ÍNDICE DA LISTA GERADA AUTOMATICAMENTE
# ============================================================

def criar_indice_gerado(dados):

    indice = {}

    for st in dados:

        nome = normalizar_nome(
            st.get("nome")
        )

        if not nome:
            continue

        indice.setdefault(
            nome,
            []
        ).append(st)

    return indice


# ============================================================
# COMPARAR COORDENADAS
# ============================================================

def coordenadas_iguais(
    a,
    b,
    tolerancia=0.000001
):

    if a is None or b is None:
        return a == b

    try:

        return (
            abs(
                float(a) - float(b)
            )
            <= tolerancia
        )

    except (
        TypeError,
        ValueError
    ):

        return False



# ============================================================
# CONFIGURAÇÃO DA CONSULTA ARCGIS / CETESB
# ============================================================

URL_CETESB = (
    "https://arcgis.cetesb.sp.gov.br/server/rest/services/"
    "ESTA%C3%87%C3%95ES_QUALIDADE_DO_AR/MapServer/0/query"
)


# ============================================================
# BAIXAR ESTAÇÕES DO ARCGIS / CETESB
# ============================================================

def baixar_estacoes_cetesb():

    params = {
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": "4674",
        "f": "json",
    }

    print("Consultando CETESB...")
    print(URL_CETESB)

    response = requests.get(
        URL_CETESB,
        params=params,
        timeout=60
    )

    response.raise_for_status()

    data = response.json()

    if "error" in data:

        raise RuntimeError(
            "Erro retornado pela CETESB:\n"
            f"{data['error']}"
        )

    features = data.get(
        "features",
        []
    )

    print(
        f"Estações recebidas da CETESB: "
        f"{len(features)}"
    )

    return features


# ============================================================
# CONVERTER ESTAÇÃO ARCGIS
# ============================================================

def converter_estacao(feature):

    attr = feature.get(
        "attributes",
        {}
    )

    geometry = feature.get(
        "geometry"
    ) or {}

    # --------------------------------------------------------
    # CÓDIGO ARCGIS
    #
    # Será armazenado como codigo_cetesb.
    # --------------------------------------------------------

    codigo_cetesb = attr.get("COD")

    if codigo_cetesb is not None:

        codigo_cetesb = str(
            codigo_cetesb
        ).strip()

        # ArcGIS pode devolver, por exemplo, 59.0
        if codigo_cetesb.endswith(".0"):

            codigo_cetesb = (
                codigo_cetesb[:-2]
            )

    # --------------------------------------------------------
    # NOME
    # --------------------------------------------------------

    nome = attr.get(
        "Inserir_no"
    )

    # --------------------------------------------------------
    # COORDENADAS
    #
    # IMPORTANTE:
    #
    # geometry.x = longitude
    # geometry.y = latitude
    #
    # NÃO utilizar os campos LATITUDE/LONGITUDE
    # dos atributos ArcGIS.
    # --------------------------------------------------------

    latitude = geometry.get(
        "y"
    )

    longitude = geometry.get(
        "x"
    )

    return {

        "codigo_cetesb":
            codigo_cetesb,

        "nome":
            nome,

        "tipo":
            attr.get("TIPO"),

        "status":
            attr.get("STATUS"),

        "latitude":
            latitude,

        "longitude":
            longitude
    }


# ============================================================
# MAIN
# ============================================================

def main():

    # ========================================================
    # 1. BAIXAR LISTA OFICIAL DO ARCGIS
    # ========================================================

    features = baixar_estacoes_cetesb()

    oficiais = [
        converter_estacao(feature)
        for feature in features
    ]

    print(
        f"Estações na lista oficial: "
        f"{len(oficiais)}"
    )

    # ========================================================
    # 2. SALVAR LISTA OFICIAL
    # ========================================================

    with open(
        ARQUIVO_OFICIAL,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            oficiais,
            f,
            ensure_ascii=False,
            indent=4
        )

    # ========================================================
    # 2. CARREGAR LISTA AUTOMÁTICA
    # ========================================================

    gerados = carregar_json(
        ARQUIVO_GERADO
    )

    print(
        f"Estações no arquivo automático: "
        f"{len(gerados)}"
    )

    indice_gerado = (
        criar_indice_gerado(
            gerados
        )
    )

    # ========================================================
    # 3. PREPARAR
    # ========================================================

    lista_final = []
    comparacao = []

    codigos_gerados_utilizados = set()

    # ========================================================
    # 4. PERCORRER A LISTA OFICIAL
    #
    # A lista oficial é a MASTER.
    # ========================================================

    for cetesb in oficiais:

        nome_cetesb = cetesb.get(
            "nome"
        )

        codigo_cetesb = cetesb.get(
            "codigo_cetesb",
            ""
        )

        chave = normalizar_nome(
            nome_cetesb
        )

        candidatos = (
            indice_gerado.get(
                chave,
                []
            )
        )

        # ====================================================
        # NÃO ENCONTRADO NO AUTOMÁTICO
        # ====================================================

        if not candidatos:

            print(
                "ATENÇÃO:",
                nome_cetesb,
                "não encontrado no arquivo automático."
            )

            lista_final.append({

                "codigo": "",

                "codigo_cetesb":
                    codigo_cetesb,

                "nome":
                    nome_cetesb,

                "tipo":
                    cetesb.get("tipo"),

                "status":
                    cetesb.get("status"),

                "latitude":
                    cetesb.get("latitude"),

                "longitude":
                    cetesb.get("longitude")
            })

            comparacao.append({

                "codigo":
                    "",

                "codigo_cetesb":
                    codigo_cetesb,

                "nome":
                    nome_cetesb,

                "situacao":
                    "NAO_ENCONTRADO_NO_AUTOMATICO"
            })

            continue

        # ====================================================
        # NOME DUPLICADO
        # ====================================================

        if len(candidatos) > 1:

            print()
            print(
                "ATENÇÃO: nome duplicado:"
            )

            print(
                f"  {nome_cetesb}"
            )

            for local in candidatos:

                print(
                    f"    código: "
                    f"{local.get('codigo')} "
                    f"| nome: "
                    f"{local.get('nome')}"
                )

            comparacao.append({

                "codigo":
                    "",

                "codigo_cetesb":
                    codigo_cetesb,

                "nome":
                    nome_cetesb,

                "situacao":
                    "NOME_DUPLICADO"
            })

            continue

        # ====================================================
        # CORRESPONDÊNCIA ÚNICA
        # ====================================================

        local = candidatos[0]

        codigo = str(
            local.get(
                "codigo",
                ""
            )
        ).strip()

        codigos_gerados_utilizados.add(
            codigo
        )

        # ----------------------------------------------------
        # Comparação das coordenadas
        #
        # Apenas para relatório.
        #
        # As coordenadas finais vêm SEMPRE da lista oficial.
        # ----------------------------------------------------

        coords_iguais = (

            coordenadas_iguais(
                cetesb.get("latitude"),
                local.get("latitude")
            )

            and

            coordenadas_iguais(
                cetesb.get("longitude"),
                local.get("longitude")
            )
        )

        if coords_iguais:

            situacao = "OK"

        else:

            situacao = "COORDENADA_DIFERENTE"

        # ====================================================
        # LISTA FINAL
        # ====================================================

        lista_final.append({

            # Código verdadeiro da estação
            "codigo":
                codigo,

            # Código da listagem oficial CETESB
            "codigo_cetesb":
                codigo_cetesb,

            # Dados oficiais
            "nome":
                nome_cetesb,

            "tipo":
                cetesb.get("tipo"),

            "status":
                cetesb.get("status"),

            "latitude":
                cetesb.get("latitude"),

            "longitude":
                cetesb.get("longitude")
        })

        # ====================================================
        # COMPARAÇÃO
        # ====================================================

        comparacao.append({

            "codigo":
                codigo,

            "codigo_cetesb":
                codigo_cetesb,

            "nome":
                nome_cetesb,

            "lat_oficial":
                cetesb.get("latitude"),

            "lon_oficial":
                cetesb.get("longitude"),

            "lat_arquivo":
                local.get("latitude", ""),

            "lon_arquivo":
                local.get("longitude", ""),

            "situacao":
                situacao
        })

    # ========================================================
    # 5. ESTAÇÕES QUE EXISTEM SOMENTE NO AUTOMÁTICO
    #
    # Exemplo:
    #
    # Ribeirão Preto-Ipiranga
    #
    # Como ela não existe na lista oficial:
    #
    # status = Fora de Operação
    # ========================================================

    nomes_oficiais = set()

    for cetesb in oficiais:

        nomes_oficiais.add(
            normalizar_nome(
                cetesb.get("nome")
            )
        )

    for local in gerados:

        nome_local = local.get(
            "nome"
        )

        chave_local = normalizar_nome(
            nome_local
        )

        if not chave_local:
            continue

        # Já existe na lista oficial
        if chave_local in nomes_oficiais:
            continue

        codigo = str(
            local.get(
                "codigo",
                ""
            )
        ).strip()

        print(
            "Estação histórica:",
            codigo,
            "-",
            nome_local
        )

        # ====================================================
        # ADICIONAR À LISTA FINAL
        # ====================================================

        lista_final.append({

            "codigo":
                codigo,

            "codigo_cetesb":
                "",

            "nome":
                nome_local,

            "tipo":
                local.get("tipo"),

            "status":
                "Fora de Operação",

            "latitude":
                local.get("latitude"),

            "longitude":
                local.get("longitude")
        })

        # ====================================================
        # COMPARAÇÃO
        # ====================================================

        comparacao.append({

            "codigo":
                codigo,

            "codigo_cetesb":
                "",

            "nome":
                nome_local,

            "lat_oficial":
                "",

            "lon_oficial":
                "",

            "lat_arquivo":
                local.get("latitude", ""),

            "lon_arquivo":
                local.get("longitude", ""),

            "situacao":
                "FORA_DE_OPERACAO"
        })

    # ========================================================
    # 6. SALVAR COMPARAÇÃO
    # ========================================================

    campos = sorted({

        chave

        for item in comparacao

        for chave in item.keys()
    })

    with open(
        ARQUIVO_COMPARACAO,
        "w",
        encoding="utf-8",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=campos,
            delimiter=";",
            extrasaction="ignore"
        )

        writer.writeheader()

        writer.writerows(
            comparacao
        )

    print()
    print(
        "Comparação salva em:"
    )
    print(
        ARQUIVO_COMPARACAO
    )

    # ========================================================
    # 7. SALVAR LISTA FINAL
    # ========================================================

    with open(
        ARQUIVO_FINAL,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            lista_final,
            f,
            ensure_ascii=False,
            indent=4
        )

    print()
    print(
        "Lista final salva em:"
    )
    print(
        ARQUIVO_FINAL
    )

    # ========================================================
    # 8. RESUMO
    # ========================================================

    contagem = {}

    for item in comparacao:

        situacao = item.get(
            "situacao",
            ""
        )

        contagem[situacao] = (
            contagem.get(
                situacao,
                0
            ) + 1
        )

    print()
    print(
        "=========================================="
    )
    print(
        "RESUMO"
    )
    print(
        "=========================================="
    )

    print(
        f"Estações oficiais: "
        f"{len(oficiais)}"
    )

    print(
        f"Estações automáticas: "
        f"{len(gerados)}"
    )

    print(
        f"Estações na lista final: "
        f"{len(lista_final)}"
    )

    print()

    for situacao, quantidade in sorted(
        contagem.items()
    ):

        print(
            f"{situacao:35s} "
            f"{quantidade}"
        )

    print(
        "=========================================="
    )


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":
    main()





# #!/usr/bin/env python3

# import json
# import csv
# import re
# import unicodedata
# import requests
# from pathlib import Path


# # ============================================================
# # CONFIGURAÇÃO
# # ============================================================

# URL_CETESB = (
#     "https://arcgis.cetesb.sp.gov.br/server/rest/services/"
#     "ESTA%C3%87%C3%95ES_QUALIDADE_DO_AR/MapServer/0/query"
# )


# # ------------------------------------------------------------
# # LISTA GERADA AUTOMATICAMENTE
# #
# # É utilizada SOMENTE para obter o código verdadeiro
# # da estação.
# # ------------------------------------------------------------

# ARQUIVO_GERADO = Path(
#     "/home/jurandir/cipc_data/cetesb/"
#     "lista_estacoes_geradoAutomaticamente.json"
# )


# # ------------------------------------------------------------
# # LISTA OFICIAL CETESB / ARCGIS
# #
# # Contém as informações oficiais das estações atuais.
# # ------------------------------------------------------------

# ARQUIVO_OFICIAL = Path(
#     "/home/jurandir/cipc_data/cetesb/"
#     "lista_estacoes_cetesb_oficial.json"
# )


# # ------------------------------------------------------------
# # ARQUIVO DE COMPARAÇÃO
# # ------------------------------------------------------------

# ARQUIVO_COMPARACAO = Path(
#     "/home/jurandir/cipc_data/cetesb/"
#     "comparacao_estacoes_cetesb.csv"
# )


# # ------------------------------------------------------------
# # LISTA FINAL
# #
# # Esta passa a ser a lista completa utilizada pelo sistema.
# # ------------------------------------------------------------

# ARQUIVO_FINAL = Path(
#     "/home/jurandir/cipc_data/cetesb/"
#     "lista_estacoes.json"
# )


# # ============================================================
# # NORMALIZAR NOME
# # ============================================================

# def normalizar_nome(nome):

#     if nome is None:
#         return ""

#     nome = str(nome).strip().lower()

#     # Remover acentos
#     nome = unicodedata.normalize(
#         "NFD",
#         nome
#     )

#     nome = "".join(
#         c
#         for c in nome
#         if unicodedata.category(c) != "Mn"
#     )

#     # Padronizar separadores
#     nome = nome.replace("-", " ")
#     nome = nome.replace("_", " ")
#     nome = nome.replace(".", " ")

#     # Remover caracteres especiais
#     nome = re.sub(
#         r"[^a-z0-9 ]+",
#         " ",
#         nome
#     )

#     # Espaços múltiplos
#     nome = re.sub(
#         r"\s+",
#         " ",
#         nome
#     ).strip()

#     return nome


# # ============================================================
# # BAIXAR ESTAÇÕES DO ARCGIS / CETESB
# # ============================================================

# def baixar_estacoes_cetesb():

#     params = {
#         "where": "1=1",
#         "outFields": "*",
#         "returnGeometry": "true",
#         "outSR": "4674",
#         "f": "json",
#     }

#     print("Consultando CETESB...")
#     print(URL_CETESB)

#     response = requests.get(
#         URL_CETESB,
#         params=params,
#         timeout=60
#     )

#     response.raise_for_status()

#     data = response.json()

#     if "error" in data:

#         raise RuntimeError(
#             "Erro retornado pela CETESB:\n"
#             f"{data['error']}"
#         )

#     features = data.get(
#         "features",
#         []
#     )

#     print(
#         f"Estações recebidas da CETESB: "
#         f"{len(features)}"
#     )

#     return features


# # ============================================================
# # CONVERTER ESTAÇÃO ARCGIS
# # ============================================================

# def converter_estacao(feature):

#     attr = feature.get(
#         "attributes",
#         {}
#     )

#     geometry = feature.get(
#         "geometry"
#     ) or {}

#     # --------------------------------------------------------
#     # CÓDIGO ARCGIS
#     #
#     # Este será chamado de codigo_cetesb.
#     # --------------------------------------------------------

#     codigo_cetesb = attr.get("COD")

#     if codigo_cetesb is not None:

#         codigo_cetesb = str(
#             codigo_cetesb
#         ).strip()

#         # ArcGIS pode devolver 42.0
#         if codigo_cetesb.endswith(".0"):

#             codigo_cetesb = (
#                 codigo_cetesb[:-2]
#             )

#     # --------------------------------------------------------
#     # NOME
#     # --------------------------------------------------------

#     nome = attr.get(
#         "Inserir_no"
#     )

#     # --------------------------------------------------------
#     # COORDENADAS
#     #
#     # geometry.x = longitude
#     # geometry.y = latitude
#     #
#     # NÃO usar os campos LATITUDE/LONGITUDE
#     # dos atributos ArcGIS.
#     # --------------------------------------------------------

#     latitude = geometry.get(
#         "y"
#     )

#     longitude = geometry.get(
#         "x"
#     )

#     return {

#         "codigo_cetesb":
#             codigo_cetesb,

#         "nome":
#             nome,

#         "tipo":
#             attr.get("TIPO"),

#         "status":
#             attr.get("STATUS"),

#         "latitude":
#             latitude,

#         "longitude":
#             longitude
#     }


# # ============================================================
# # CARREGAR JSON
# # ============================================================

# def carregar_json(arquivo):

#     with open(
#         arquivo,
#         "r",
#         encoding="utf-8"
#     ) as f:

#         return json.load(f)


# # ============================================================
# # ÍNDICE DA LISTA GERADA AUTOMATICAMENTE
# #
# # A chave é o nome normalizado.
# #
# # O código encontrado aqui será colocado no campo:
# #
# #     "codigo"
# #
# # ============================================================

# def criar_indice_gerado(dados):

#     indice = {}

#     for st in dados:

#         nome = normalizar_nome(
#             st.get("nome")
#         )

#         if not nome:
#             continue

#         if nome not in indice:

#             indice[nome] = []

#         indice[nome].append(
#             st
#         )

#     return indice


# # ============================================================
# # COMPARAR COORDENADAS
# # ============================================================

# def coordenadas_iguais(
#     a,
#     b,
#     tolerancia=0.000001
# ):

#     if a is None or b is None:

#         return a == b

#     try:

#         return (
#             abs(
#                 float(a) - float(b)
#             )
#             <= tolerancia
#         )

#     except (
#         TypeError,
#         ValueError
#     ):

#         return False


# # ============================================================
# # MAIN
# # ============================================================

# def main():

#     # ========================================================
#     # 1. BAIXAR LISTA OFICIAL DO ARCGIS
#     # ========================================================

#     features = (
#         baixar_estacoes_cetesb()
#     )

#     oficiais = [
#         converter_estacao(feature)
#         for feature in features
#     ]

#     # --------------------------------------------------------
#     # Ordenar pelo código ArcGIS.
#     # --------------------------------------------------------

#     def chave_codigo(st):

#         try:
#             return int(
#                 st["codigo_cetesb"]
#             )

#         except (
#             TypeError,
#             ValueError
#         ):

#             return 999999

#     oficiais.sort(
#         key=chave_codigo
#     )

#     # ========================================================
#     # 2. SALVAR LISTA OFICIAL
#     # ========================================================

#     with open(
#         ARQUIVO_OFICIAL,
#         "w",
#         encoding="utf-8"
#     ) as f:

#         json.dump(
#             oficiais,
#             f,
#             ensure_ascii=False,
#             indent=4
#         )

#     print()
#     print(
#         "Arquivo oficial salvo em:"
#     )
#     print(
#         ARQUIVO_OFICIAL
#     )

#     # ========================================================
#     # 3. CARREGAR LISTA GERADA AUTOMATICAMENTE
#     # ========================================================

#     gerados = carregar_json(
#         ARQUIVO_GERADO
#     )

#     indice_gerado = (
#         criar_indice_gerado(
#             gerados
#         )
#     )

#     # ========================================================
#     # 4. COMPARAÇÃO
#     # ========================================================

#     comparacao = []

#     lista_final = []

#     codigos_gerados_utilizados = set()

#     # --------------------------------------------------------
#     # O ArcGIS é sempre a lista principal.
#     # --------------------------------------------------------

#     for cetesb in oficiais:

#         codigo_cetesb = (
#             cetesb.get(
#                 "codigo_cetesb"
#             )
#         )

#         nome_cetesb = (
#             cetesb.get("nome")
#         )

#         chave = normalizar_nome(
#             nome_cetesb
#         )

#         candidatos = (
#             indice_gerado.get(
#                 chave,
#                 []
#             )
#         )

#         # ====================================================
#         # ESTAÇÃO NÃO ENCONTRADA NO ARQUIVO AUTOMÁTICO
#         # ====================================================

#         if not candidatos:

#             comparacao.append({

#                 "codigo_cetesb":
#                     codigo_cetesb,

#                 "nome_cetesb":
#                     nome_cetesb,

#                 "codigo":
#                     "",

#                 "nome_arquivo":
#                     "",

#                 "lat_cetesb":
#                     cetesb.get(
#                         "latitude"
#                     ),

#                 "lon_cetesb":
#                     cetesb.get(
#                         "longitude"
#                     ),

#                 "lat_arquivo":
#                     "",

#                 "lon_arquivo":
#                     "",

#                 "status_cetesb":
#                     cetesb.get(
#                         "status"
#                     ),

#                 "situacao":
#                     "NAO_ENCONTRADO"
#             })

#             # ------------------------------------------------
#             # A estação continua na lista final.
#             #
#             # Como o ArcGIS é a fonte oficial, todos os
#             # dados oficiais são preservados.
#             # ------------------------------------------------

#             lista_final.append({

#                 "codigo":
#                     "",

#                 "codigo_cetesb":
#                     codigo_cetesb,

#                 "nome":
#                     nome_cetesb,

#                 "tipo":
#                     cetesb.get(
#                         "tipo"
#                     ),

#                 "status":
#                     cetesb.get(
#                         "status"
#                     ),

#                 "latitude":
#                     cetesb.get(
#                         "latitude"
#                     ),

#                 "longitude":
#                     cetesb.get(
#                         "longitude"
#                     )
#             })

#             continue

#         # ====================================================
#         # NOME DUPLICADO NO ARQUIVO AUTOMÁTICO
#         # ====================================================

#         if len(candidatos) > 1:

#             print()
#             print(
#                 "ATENÇÃO: nome duplicado "
#                 "no arquivo automático:"
#             )

#             print(
#                 f"  ArcGIS: "
#                 f"{codigo_cetesb} - "
#                 f"{nome_cetesb}"
#             )

#             for local in candidatos:

#                 print(
#                     f"    código: "
#                     f"{local.get('codigo')} "
#                     f"| nome: "
#                     f"{local.get('nome')}"
#                 )

#                 comparacao.append({

#                     "codigo_cetesb":
#                         codigo_cetesb,

#                     "nome_cetesb":
#                         nome_cetesb,

#                     "codigo":
#                         local.get(
#                             "codigo",
#                             ""
#                         ),

#                     "nome_arquivo":
#                         local.get(
#                             "nome",
#                             ""
#                         ),

#                     "lat_cetesb":
#                         cetesb.get(
#                             "latitude"
#                         ),

#                     "lon_cetesb":
#                         cetesb.get(
#                             "longitude"
#                         ),

#                     "lat_arquivo":
#                         local.get(
#                             "latitude",
#                             ""
#                         ),

#                     "lon_arquivo":
#                         local.get(
#                             "longitude",
#                             ""
#                         ),

#                     "status_cetesb":
#                         cetesb.get(
#                             "status"
#                         ),

#                     "situacao":
#                         "NOME_DUPLICADO"
#                 })

#             # ------------------------------------------------
#             # Não escolher código automaticamente.
#             # ------------------------------------------------

#             continue

#         # ====================================================
#         # CORRESPONDÊNCIA ÚNICA
#         # ====================================================

#         local = candidatos[0]

#         codigo = str(
#             local.get(
#                 "codigo",
#                 ""
#             )
#         ).strip()

#         codigos_gerados_utilizados.add(
#             codigo
#         )

#         # ----------------------------------------------------
#         # Comparar coordenadas apenas para o relatório.
#         #
#         # As coordenadas finais serão SEMPRE as do ArcGIS.
#         # ----------------------------------------------------

#         coords_iguais = (

#             coordenadas_iguais(
#                 cetesb.get(
#                     "latitude"
#                 ),
#                 local.get(
#                     "latitude"
#                 )
#             )

#             and

#             coordenadas_iguais(
#                 cetesb.get(
#                     "longitude"
#                 ),
#                 local.get(
#                     "longitude"
#                 )
#             )
#         )

#         if coords_iguais:

#             situacao = "OK"

#         else:

#             situacao = (
#                 "COORDENADA_DIFERENTE"
#             )

#         # ====================================================
#         # REGISTRO DA COMPARAÇÃO
#         # ====================================================

#         comparacao.append({

#             "codigo_cetesb":
#                 codigo_cetesb,

#             "nome_cetesb":
#                 nome_cetesb,

#             "codigo":
#                 codigo,

#             "nome_arquivo":
#                 local.get(
#                     "nome",
#                     ""
#                 ),

#             "lat_cetesb":
#                 cetesb.get(
#                     "latitude"
#                 ),

#             "lon_cetesb":
#                 cetesb.get(
#                     "longitude"
#                 ),

#             "lat_arquivo":
#                 local.get(
#                     "latitude",
#                     ""
#                 ),

#             "lon_arquivo":
#                 local.get(
#                     "longitude",
#                     ""
#                 ),

#             "status_cetesb":
#                 cetesb.get(
#                     "status"
#                 ),

#             "situacao":
#                 situacao
#         })

#         # ====================================================
#         # LISTA FINAL
#         #
#         # codigo       = código verdadeiro da estação
#         # codigo_cetesb = código ArcGIS / lista oficial
#         #
#         # Os demais dados vêm do ArcGIS.
#         # ====================================================

#         lista_final.append({

#             "codigo":
#                 codigo,

#             "codigo_cetesb":
#                 codigo_cetesb,

#             "nome":
#                 nome_cetesb,

#             "tipo":
#                 cetesb.get(
#                     "tipo"
#                 ),

#             "status":
#                 cetesb.get(
#                     "status"
#                 ),

#             "latitude":
#                 cetesb.get(
#                     "latitude"
#                 ),

#             "longitude":
#                 cetesb.get(
#                     "longitude"
#                 )
#         })

#     # ========================================================
#     # 5. ESTAÇÕES QUE SOBRARAM NO ARQUIVO AUTOMÁTICO
#     #
#     # Não existem na lista ArcGIS atual.
#     #
#     # Portanto entram como históricas:
#     #
#     #     status = "Fora de Operação"
#     # ========================================================

#     nomes_arcgis = set()

#     for cetesb in oficiais:

#         nomes_arcgis.add(
#             normalizar_nome(
#                 cetesb.get("nome")
#             )
#         )

#     for local in gerados:

#         nome_local = local.get(
#             "nome"
#         )

#         chave_local = normalizar_nome(
#             nome_local
#         )

#         if not chave_local:
#             continue

#         if chave_local in nomes_arcgis:
#             continue

#         codigo = str(
#             local.get(
#                 "codigo",
#                 ""
#             )
#         ).strip()

#         # ----------------------------------------------------
#         # Registro no relatório
#         # ----------------------------------------------------

#         comparacao.append({

#             "codigo_cetesb":
#                 "",

#             "nome_cetesb":
#                 "",

#             "codigo":
#                 codigo,

#             "nome_arquivo":
#                 nome_local,

#             "lat_cetesb":
#                 "",

#             "lon_cetesb":
#                 "",

#             "lat_arquivo":
#                 local.get(
#                     "latitude",
#                     ""
#                 ),

#             "lon_arquivo":
#                 local.get(
#                     "longitude",
#                     ""
#                 ),

#             "status_cetesb":
#                 "",

#             "situacao":
#                 "FORA_DE_OPERACAO"
#         })

#         # ----------------------------------------------------
#         # Estação histórica.
#         #
#         # Não existe codigo_cetesb atual.
#         # ----------------------------------------------------

#         lista_final.append({

#             "codigo":
#                 codigo,

#             "codigo_cetesb":
#                 "",

#             "nome":
#                 nome_local,

#             "tipo":
#                 local.get(
#                     "tipo"
#                 ),

#             "status":
#                 "Fora de Operação",

#             "latitude":
#                 local.get(
#                     "latitude"
#                 ),

#             "longitude":
#                 local.get(
#                     "longitude"
#                 )
#         })

#     # ========================================================
#     # 6. SALVAR COMPARAÇÃO
#     # ========================================================

#     campos = [

#         "codigo_cetesb",

#         "nome_cetesb",

#         "codigo",

#         "nome_arquivo",

#         "lat_cetesb",

#         "lon_cetesb",

#         "lat_arquivo",

#         "lon_arquivo",

#         "status_cetesb",

#         "situacao"
#     ]

#     with open(
#         ARQUIVO_COMPARACAO,
#         "w",
#         encoding="utf-8",
#         newline=""
#     ) as f:

#         writer = csv.DictWriter(
#             f,
#             fieldnames=campos,
#             delimiter=";"
#         )

#         writer.writeheader()

#         writer.writerows(
#             comparacao
#         )

#     print()
#     print(
#         "Comparação salva em:"
#     )
#     print(
#         ARQUIVO_COMPARACAO
#     )

#     # ========================================================
#     # 7. SALVAR LISTA FINAL
#     # ========================================================

#     with open(
#         ARQUIVO_FINAL,
#         "w",
#         encoding="utf-8"
#     ) as f:

#         json.dump(
#             lista_final,
#             f,
#             ensure_ascii=False,
#             indent=4
#         )

#     print()
#     print(
#         "Lista final salva em:"
#     )
#     print(
#         ARQUIVO_FINAL
#     )

#     # ========================================================
#     # 8. RESUMO
#     # ========================================================

#     contagem = {}

#     for item in comparacao:

#         situacao = item.get(
#             "situacao",
#             ""
#         )

#         contagem[situacao] = (
#             contagem.get(
#                 situacao,
#                 0
#             ) + 1
#         )

#     print()
#     print(
#         "=========================================="
#     )
#     print(
#         "RESUMO"
#     )
#     print(
#         "=========================================="
#     )

#     print(
#         f"Estações ArcGIS: "
#         f"{len(oficiais)}"
#     )

#     print(
#         f"Estações no arquivo automático: "
#         f"{len(gerados)}"
#     )

#     print(
#         f"Estações na lista final: "
#         f"{len(lista_final)}"
#     )

#     print()

#     for situacao, quantidade in sorted(
#         contagem.items()
#     ):

#         print(
#             f"{situacao:30s} "
#             f"{quantidade}"
#         )

#     print(
#         "=========================================="
#     )


# # ============================================================
# # EXECUÇÃO
# # ============================================================

# if __name__ == "__main__":
#     main()


