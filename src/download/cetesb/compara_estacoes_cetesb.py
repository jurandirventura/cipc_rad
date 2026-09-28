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

ARQUIVO_OFICIAL = Path(
    "/home/jurandir/cipc_data/cetesb/"
    "lista_estacoes_cetesb_oficial.json"
)

ARQUIVO_GERADO = Path(
    "/home/jurandir/cipc_data/cetesb/"
    "lista_estacoes_geradoAutomaticamente.json"
)

ARQUIVO_COMPARACAO = Path(
    "/home/jurandir/cipc_data/cetesb/"
    "comparacao_estacoes_cetesb.csv"
)

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

    nome = unicodedata.normalize(
        "NFD",
        nome
    )

    nome = "".join(
        c
        for c in nome
        if unicodedata.category(c) != "Mn"
    )

    nome = nome.replace("-", " ")
    nome = nome.replace("_", " ")
    nome = nome.replace(".", " ")

    nome = re.sub(
        r"[^a-z0-9 ]+",
        " ",
        nome
    )

    nome = re.sub(
        r"\s+",
        " ",
        nome
    ).strip()

    return nome


# ============================================================
# NORMALIZAR CÓDIGO
# ============================================================

def normalizar_codigo(codigo):

    if codigo is None:
        return ""

    codigo = str(codigo).strip()

    if codigo.lower() in (
        "",
        "none",
        "null",
        "nan",
        "nat"
    ):
        return ""

    if codigo.endswith(".0"):
        codigo = codigo[:-2]

    return codigo


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
# OBTER CÓDIGO DISPONÍVEL
# ============================================================
#
# Ordem de prioridade:
#
# 1. código verdadeiro do arquivo automático
# 2. codigo_cetesb
# 3. código auxiliar
#
# O código retornado SEMPRE será único.
# ============================================================

def obter_codigo_estacao(
    codigo,
    codigo_cetesb,
    codigos_utilizados
):

    codigo_str = normalizar_codigo(
        codigo
    )

    codigo_cetesb_str = normalizar_codigo(
        codigo_cetesb
    )

    # --------------------------------------------------------
    # 1. Código verdadeiro do arquivo automático
    # --------------------------------------------------------

    if (
        codigo_str
        and codigo_str not in codigos_utilizados
    ):

        return codigo_str

    # --------------------------------------------------------
    # 2. Código oficial CETESB
    # --------------------------------------------------------

    if (
        codigo_cetesb_str
        and codigo_cetesb_str not in codigos_utilizados
    ):

        return codigo_cetesb_str

    # --------------------------------------------------------
    # 3. Nenhum código disponível.
    #
    # O chamador deverá gerar código auxiliar.
    # --------------------------------------------------------

    return ""


# ============================================================
# GERAR CÓDIGO AUXILIAR ÚNICO
# ============================================================
#
# Os códigos oficiais ArcGIS atualmente estão na faixa
# 1..84 e os códigos automáticos existentes são inferiores
# a 1000.
#
# Portanto começamos em 1000 para evitar colisões.
# ============================================================

def gerar_codigo_auxiliar(codigos_utilizados):

    codigo = 1000

    while str(codigo) in codigos_utilizados:
        codigo += 1

    return str(codigo)


# ============================================================
# OBTER CÓDIGO DEFINITIVO
# ============================================================
#
# Centraliza toda a regra:
#
# automático -> codigo_cetesb -> auxiliar
#
# Isso evita que algum caminho do programa esqueça de gerar
# um código auxiliar.
# ============================================================

def obter_codigo_definitivo(
    codigo,
    codigo_cetesb,
    codigos_utilizados,
    motivo_auxiliar=None
):

    codigo = obter_codigo_estacao(
        codigo,
        codigo_cetesb,
        codigos_utilizados
    )

    if codigo:

        codigos_utilizados.add(
            codigo
        )

        return codigo

    codigo_auxiliar = gerar_codigo_auxiliar(
        codigos_utilizados
    )

    codigos_utilizados.add(
        codigo_auxiliar
    )

    if motivo_auxiliar:

        print()
        print(
            f"ATENÇÃO: {motivo_auxiliar}"
        )

        print(
            f"  codigo_cetesb={normalizar_codigo(codigo_cetesb)}"
        )

        print(
            f"  Utilizando código auxiliar={codigo_auxiliar}"
        )

    return codigo_auxiliar


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

    codigo_cetesb = normalizar_codigo(
        attr.get("COD")
    )

    nome = attr.get(
        "Inserir_no"
    )

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
# VALIDAR LISTA FINAL
# ============================================================

def validar_lista_final(lista_final):

    print()
    print(
        "=========================================="
    )
    print(
        "VALIDAÇÃO DA LISTA FINAL"
    )
    print(
        "=========================================="
    )

    codigos = []

    codigos_vazios = []

    problemas = []

    for i, item in enumerate(lista_final):

        codigo = normalizar_codigo(
            item.get("codigo")
        )

        if not codigo:

            codigos_vazios.append(
                i
            )

            problemas.append(
                f"Índice {i}: "
                f"estação '{item.get('nome')}' "
                f"sem código."
            )

        else:

            codigos.append(
                codigo
            )

    # --------------------------------------------------------
    # Procurar duplicados
    # --------------------------------------------------------

    vistos = set()
    duplicados = set()

    for codigo in codigos:

        if codigo in vistos:
            duplicados.add(codigo)

        vistos.add(codigo)

    if duplicados:

        problemas.append(
            "Códigos duplicados: "
            + ", ".join(
                sorted(
                    duplicados,
                    key=lambda x: int(x)
                    if x.isdigit()
                    else x
                )
            )
        )

    # --------------------------------------------------------
    # Resultado
    # --------------------------------------------------------

    print(
        f"Total de estações: "
        f"{len(lista_final)}"
    )

    print(
        f"Códigos válidos: "
        f"{len(codigos)}"
    )

    print(
        f"Códigos únicos: "
        f"{len(set(codigos))}"
    )

    print(
        f"Códigos sem valor: "
        f"{len(codigos_vazios)}"
    )

    if problemas:

        print()
        print(
            "ERROS ENCONTRADOS:"
        )

        for problema in problemas:

            print(
                "  -",
                problema
            )

        print(
            "=========================================="
        )

        raise ValueError(
            "A lista final possui códigos "
            "nulos, vazios ou duplicados. "
            "O arquivo lista_estacoes.json "
            "não será atualizado."
        )

    print(
        "VALIDAÇÃO OK: "
        "todos os códigos são únicos e válidos."
    )

    print(
        "=========================================="
    )


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

    print(
        "Lista oficial atualizada:"
    )

    print(
        ARQUIVO_OFICIAL
    )

    # ========================================================
    # 3. CARREGAR LISTA AUTOMÁTICA
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
    # 4. PREPARAR
    # ========================================================

    lista_final = []

    comparacao = []

    codigos_utilizados = set()

    # ========================================================
    # 5. CONJUNTO DE NOMES OFICIAIS
    # ========================================================

    nomes_oficiais = set()

    for cetesb in oficiais:

        nome = normalizar_nome(
            cetesb.get("nome")
        )

        if nome:

            nomes_oficiais.add(
                nome
            )

    # ========================================================
    # 6. PERCORRER LISTA OFICIAL
    # ========================================================

    for cetesb in oficiais:

        nome_cetesb = cetesb.get(
            "nome"
        )

        codigo_cetesb = normalizar_codigo(
            cetesb.get(
                "codigo_cetesb",
                ""
            )
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

            print()
            print(
                "ATENÇÃO:",
                nome_cetesb,
                "não encontrado no arquivo automático."
            )

            codigo = obter_codigo_definitivo(
                None,
                codigo_cetesb,
                codigos_utilizados,
                motivo_auxiliar=(
                    "estação oficial sem código disponível"
                )
            )

            if (
                codigo_cetesb
                and codigo == codigo_cetesb
            ):

                print(
                    f"  Utilizando codigo={codigo} "
                    f"(fallback de codigo_cetesb)"
                )

            lista_final.append({

                "codigo":
                    codigo,

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
                    "",

                "lon_arquivo":
                    "",

                "situacao":
                    "NAO_ENCONTRADO_NO_AUTOMATICO"
            })

            continue

        # ====================================================
        # NOME DUPLICADO NO AUTOMÁTICO
        # ====================================================

        if len(candidatos) > 1:

            print()
            print(
                "ATENÇÃO: nome duplicado:"
            )

            print(
                f"  {nome_cetesb}"
            )

            for candidato in candidatos:

                print(
                    f"    código: "
                    f"{candidato.get('codigo')} "
                    f"| tipo: "
                    f"{candidato.get('tipo')} "
                    f"| nome: "
                    f"{candidato.get('nome')}"
                )

            codigo = obter_codigo_definitivo(
                None,
                codigo_cetesb,
                codigos_utilizados,
                motivo_auxiliar=(
                    "nome duplicado e "
                    "codigo_cetesb já utilizado"
                )
            )

            if (
                codigo_cetesb
                and codigo == codigo_cetesb
            ):

                print(
                    f"  Utilizando codigo={codigo} "
                    f"(codigo_cetesb)"
                )

            else:

                print(
                    f"  Utilizando codigo={codigo}"
                )

            lista_final.append({

                "codigo":
                    codigo,

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
                    "",

                "lon_arquivo":
                    "",

                "situacao":
                    "NOME_DUPLICADO"
            })

            continue

        # ====================================================
        # EXISTE EXATAMENTE UM CANDIDATO
        # ====================================================

        local = candidatos[0]

        codigo = obter_codigo_definitivo(
            local.get("codigo"),
            codigo_cetesb,
            codigos_utilizados,
            motivo_auxiliar=(
                "código automático e codigo_cetesb "
                "já utilizados"
            )
        )

        # ----------------------------------------------------
        # Comparação das coordenadas
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

            "codigo":
                codigo,

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
    # 7. ESTAÇÕES SOMENTE NO AUTOMÁTICO
    # ========================================================

    print()
    print(
        "=========================================="
    )
    print(
        "VERIFICANDO ESTAÇÕES HISTÓRICAS"
    )
    print(
        "=========================================="
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

        # ----------------------------------------------------
        # Já existe na lista oficial.
        # ----------------------------------------------------

        if chave_local in nomes_oficiais:

            continue

        # ----------------------------------------------------
        # Estação somente no automático.
        # ----------------------------------------------------

        codigo_automatico = normalizar_codigo(
            local.get("codigo")
        )

        codigo = obter_codigo_definitivo(
            codigo_automatico,
            None,
            codigos_utilizados,
            motivo_auxiliar=(
                f"estação histórica '{nome_local}' "
                f"sem código disponível"
            )
        )

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
    # 8. VALIDAR ANTES DE SALVAR
    # ========================================================

    validar_lista_final(
        lista_final
    )

    # ========================================================
    # 9. SALVAR COMPARAÇÃO
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
    # 10. SALVAR LISTA FINAL
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
    # 11. RESUMO
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

    print(
        f"Códigos utilizados: "
        f"{len(codigos_utilizados)}"
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

    print()
    print(
        "PROCESSAMENTO CONCLUÍDO COM SUCESSO."
    )


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":
    main()


