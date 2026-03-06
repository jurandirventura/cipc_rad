# Lê e gera imagem para o período informado de produto Sentinel_5P
# Gera uma imagem GIF e outra MP4 com as imagens selecionadas

# Versão atualizada em 05/mar já com nova estrutura

#!/usr/bin/env python3

import sys
import os
import subprocess
import logging
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import imageio.v2 as imageio
import glob

from src.config.settings import OUTPUT_DIR

# ==========================================
# CONFIGURAÇÕES
# ==========================================

MAX_WORKERS = 4
LOG_DIR = "log"

os.makedirs(LOG_DIR, exist_ok=True)

# ==========================================
# ARGUMENTOS
# ==========================================

if len(sys.argv) < 9:
    print("\nUso:")
    print("python -m src.processing.run_daily_plots START_DATE END_DATE DATA_PATTERN GROUP VAR_PRODUCT TITLE LABEL EXT [FPS]\n")
    sys.exit(1)

START_DATE = sys.argv[1]
END_DATE = sys.argv[2]
DATA_PATTERN = os.path.expanduser(sys.argv[3])

GROUP = sys.argv[4]
VAR_PRODUCT = sys.argv[5]
TITLE = sys.argv[6]
LABEL = sys.argv[7]


ext = sys.argv[8].lower().replace(".", "")

if ext not in ["png", "jpeg"]:
    raise ValueError("Extensão deve ser png ou jpeg")

FPS = 2
if len(sys.argv) == 10:
    FPS = float(sys.argv[9])




#EXT = sys.argv[8].lower()
# EXT = sys.argv[8].lower().replace(".", "")

# FPS = 2
# if len(sys.argv) == 10:
#     FPS = float(sys.argv[9])

# # if EXT not in ["png", "jpeg"]:
# #     raise ValueError("Extensão deve ser png ou jpeg")

# if EXT not in ["png", "jpeg", "jpg"]:
#     print("Extensão deve ser png ou jpeg")
#     sys.exit(1)

# ==========================================
# LOG
# ==========================================

logfile = os.path.join(LOG_DIR, f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    filename=logfile,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logging.info("Início do processamento")

# ==========================================
# VALIDAR DATAS
# ==========================================

start = datetime.strptime(START_DATE, "%Y-%m-%d")
end = datetime.strptime(END_DATE, "%Y-%m-%d")

if start > end:
    print("Data inicial maior que data final.")
    sys.exit(1)

# ==========================================
# GERAR LISTA DE DATAS
# ==========================================

dates = []

current = start
while current <= end:
    dates.append(current)
    current += timedelta(days=1)

# ==========================================
# FUNÇÃO PROCESSAMENTO
# ==========================================

def process_day(date):

    date_str = date.strftime("%Y%m%d")

    logging.info(f"Processando {date_str}")

    #pattern = DATA_PATTERN.replace("*.nc", f"*{date_str}*.nc")
    pattern = os.path.join(DATA_PATTERN, f"*{date_str}*.nc")

    files = sorted(glob.glob(pattern))

    if not files:
        logging.warning(f"{date_str} - nenhum arquivo encontrado")
        return None

    cmd = [
        sys.executable,
        "-m",
        "src.processing.read_plot_s5p",
        *files,
        GROUP,
        VAR_PRODUCT,
        TITLE,
        LABEL,
        ext
    ]

    try:

        subprocess.run(cmd, check=True)

        output_dir = OUTPUT_DIR / "figures" / VAR_PRODUCT
        pattern_img = str(output_dir / f"{VAR_PRODUCT}_{date_str}*.{ext}")

        images = sorted(glob.glob(pattern_img))

        if not images:
            logging.warning(f"{date_str} - nenhuma imagem encontrada")
            return None

        logging.info(f"{date_str} OK")

        return images[0]

    except subprocess.CalledProcessError:

        logging.error(f"{date_str} ERRO")
        return None


# ==========================================
# PROCESSAMENTO PARALELO
# ==========================================

print("\nProcessando dias...\n")

results = []

with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:

    futures = [executor.submit(process_day, d) for d in dates]

    for f in tqdm(as_completed(futures), total=len(futures)):

        r = f.result()

        if r:
            results.append(r)

# ==========================================
# GERAR ANIMAÇÕES
# ==========================================

print("\nGerando animações...\n")

results = sorted(results)

if results:

    images = [imageio.imread(f) for f in results]

    gif_file = OUTPUT_DIR / f"{VAR_PRODUCT}_{START_DATE}_{END_DATE}.gif"

    imageio.mimsave(gif_file, images, duration=1/FPS)

    print(f"GIF salvo em: {gif_file}")

    try:

        mp4_file = OUTPUT_DIR / f"{VAR_PRODUCT}_{START_DATE}_{END_DATE}.mp4"

        writer = imageio.get_writer(mp4_file, fps=FPS)

        for img in images:
            writer.append_data(img)

        writer.close()

        print(f"MP4 salvo em: {mp4_file}")

    except Exception:

        print("MP4 não gerado (ffmpeg não encontrado)")

else:

    print("Nenhuma imagem gerada")
    logging.warning("Nenhuma imagem disponível para animação")




# #!/usr/bin/env python3

# import sys
# import os
# import subprocess
# import logging
# from datetime import datetime, timedelta
# from concurrent.futures import ThreadPoolExecutor, as_completed
# from tqdm import tqdm
# import imageio.v2 as imageio
# import glob
# import shutil

# # ==========================================
# # CONFIGURAÇÕES
# # ==========================================

# MAX_WORKERS = 4
# OUTPUT_DIR = "output"
# LOG_DIR = "log"

# os.makedirs(OUTPUT_DIR, exist_ok=True)
# os.makedirs(LOG_DIR, exist_ok=True)

# # ==========================================
# # ARGUMENTOS
# # ==========================================

# if len(sys.argv) < 8:
#     print("\nUso:")
#     print("python -m src.processing.run_daily_plots START_DATE END_DATE DATA_PATTERN GROUP VAR_PRODUCT LABEL EXT [FPS]\n")
#     print("Exemplo:")
#     print('python -m src.processing.run_daily_plots 2023-10-10 2023-10-20 "~/cipc_data/L2/AER_AI/2023/*.nc" PRODUCT aerosol_index_354_388 AI png')
#     sys.exit(1)

# START_DATE = sys.argv[1]
# END_DATE = sys.argv[2]
# DATA_PATTERN = os.path.expanduser(sys.argv[3])
# GROUP = sys.argv[4]
# VAR_PRODUCT = sys.argv[5]
# LABEL = sys.argv[6]
# EXT = sys.argv[7].lower()

# FPS = 2
# if len(sys.argv) == 9:
#     FPS = float(sys.argv[8])

# # ==========================================
# # LOG
# # ==========================================

# logfile = os.path.join(LOG_DIR, f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

# logging.basicConfig(
#     filename=logfile,
#     level=logging.INFO,
#     format="%(asctime)s - %(levelname)s - %(message)s"
# )

# logging.info("Início do processamento")

# # ==========================================
# # VALIDAR DATAS
# # ==========================================

# start = datetime.strptime(START_DATE, "%Y-%m-%d")
# end = datetime.strptime(END_DATE, "%Y-%m-%d")

# if start > end:
#     print("Data inicial maior que data final.")
#     sys.exit(1)

# # ==========================================
# # GERAR LISTA DE DATAS
# # ==========================================

# dates = []
# current = start

# while current <= end:
#     dates.append(current)
#     current += timedelta(days=1)

# # ==========================================
# # FUNÇÃO PROCESSAMENTO
# # ==========================================

# def process_day(date):

#     date_str = date.strftime("%Y%m%d")
#     date_title = date.strftime("%d %b %Y")

#     TITLE = f"Sentinel-5P {VAR_PRODUCT} {date_title}"

#     # Filtra apenas arquivos daquele dia
#     pattern = DATA_PATTERN.replace("*.nc", f"*{date_str}*.nc")

#     cmd = [
#         "python3",
#         "-m",
#         "src.processing.read_plot_S5P",
#         pattern,
#         GROUP,
#         VAR_PRODUCT,
#         TITLE,
#         LABEL,
#         EXT
#     ]

#     try:

#         subprocess.run(cmd, check=True)

#         png_files = glob.glob(f"{VAR_PRODUCT}_{date_str}*.{EXT}")

#         if not png_files:
#             logging.warning(f"{date_str} - nenhum PNG encontrado")
#             return None

#         moved_files = []

#         for f in png_files:

#             dest = os.path.join(OUTPUT_DIR, os.path.basename(f))

#             if not os.path.exists(dest):
#                 shutil.move(f, dest)

#             moved_files.append(dest)

#         logging.info(f"{date_str} OK ({len(moved_files)} arquivos)")

#         return moved_files[0]

#     except subprocess.CalledProcessError:

#         logging.error(f"{date_str} ERRO")
#         return None

# # ==========================================
# # PROCESSAMENTO PARALELO
# # ==========================================

# print("\nProcessando dias...\n")

# results = []

# with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:

#     futures = [executor.submit(process_day, d) for d in dates]

#     for f in tqdm(as_completed(futures), total=len(futures)):

#         r = f.result()

#         if r:
#             results.append(r)

# # ==========================================
# # GERAR ANIMAÇÕES
# # ==========================================

# print("\nGerando animações...\n")

# results = sorted([r for r in results if os.path.exists(r)])

# if results:

#     images = [imageio.imread(f) for f in results]

#     gif_file = os.path.join(
#         OUTPUT_DIR,
#         f"{VAR_PRODUCT}_{START_DATE}_{END_DATE}.gif"
#     )

#     imageio.mimsave(gif_file, images, duration=1/FPS)

#     print(f"GIF salvo em: {gif_file}")

#     # MP4

#     os.environ["IMAGEIO_FFMPEG_EXE"] = "/usr/bin/ffmpeg"

#     mp4_file = os.path.join(
#         OUTPUT_DIR,
#         f"{VAR_PRODUCT}_{START_DATE}_{END_DATE}.mp4"
#     )

#     writer = imageio.get_writer(mp4_file, fps=FPS)

#     for img in images:
#         writer.append_data(img)

#     writer.close()

#     print(f"MP4 salvo em: {mp4_file}")

# else:

#     print("Nenhuma imagem gerada")
#     logging.warning("Nenhuma imagem disponível para animação")






# # Lê e gera imagem para o período informado de produto Sentinel_5P
# # Gera uma imagem GIF e outra MP4 com as imagens selecionadas

# #!/usr/bin/env python3

# import sys
# import os
# import subprocess
# import logging
# from datetime import datetime, timedelta
# from concurrent.futures import ThreadPoolExecutor, as_completed
# from tqdm import tqdm
# #import imageio
# import imageio.v2 as imageio
# import glob

# # ==========================================
# # CONFIGURAÇÕES
# # ==========================================

# MAX_WORKERS = 4  # número de processos paralelos
# OUTPUT_DIR = "output"
# LOG_DIR = "log"

# os.makedirs(OUTPUT_DIR, exist_ok=True)
# os.makedirs(LOG_DIR, exist_ok=True)

# # ==========================================
# # ARGUMENTOS
# # ==========================================

# # if len(sys.argv) != 9:
# if len(sys.argv) < 9:    
#     print("\nUso:")
#     print("python run_daily_plots.py START_DATE END_DATE DATA_DIR PRODUCT_PREFIX GROUP VAR_PRODUCT LABEL EXT\n")
#     sys.exit(1)

# START_DATE = sys.argv[1]
# END_DATE = sys.argv[2]
# DATA_DIR = sys.argv[3]
# PRODUCT_PREFIX = sys.argv[4]
# GROUP = sys.argv[5]
# VAR_PRODUCT = sys.argv[6]
# LABEL = sys.argv[7]
# EXT = sys.argv[8].lower()

# # FPS opcional (padrão 2 quadros por segundo)
# FPS = 2

# if len(sys.argv) == 10:
#     FPS = float(sys.argv[9])

# # ==========================================
# # LOG
# # ==========================================

# logfile = os.path.join(LOG_DIR, f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

# logging.basicConfig(
#     filename=logfile,
#     level=logging.INFO,
#     format="%(asctime)s - %(levelname)s - %(message)s"
# )

# logging.info("Início do processamento")

# # ==========================================
# # VALIDAR DATAS
# # ==========================================

# start = datetime.strptime(START_DATE, "%Y-%m-%d")
# end = datetime.strptime(END_DATE, "%Y-%m-%d")

# if start > end:
#     print("Data inicial maior que data final.")
#     sys.exit(1)

# # ==========================================
# # GERAR LISTA DE DATAS
# # ==========================================

# dates = []
# current = start
# while current <= end:
#     dates.append(current)
#     current += timedelta(days=1)

# # ==========================================
# # FUNÇÃO DE PROCESSAMENTO
# # ==========================================

# def process_day(date):

#     import glob
#     import shutil

#     date_str = date.strftime("%Y%m%d")
#     date_title = date.strftime("%d %b %Y")

#     file_pattern = f"{DATA_DIR}/{PRODUCT_PREFIX}_{date_str}*"
#     TITLE = f"Sentinel-5P {VAR_PRODUCT} {date_title}"

#     cmd = [
#         "python3",
#         "read_plot_S5P.py",
#         file_pattern,
#         GROUP,
#         VAR_PRODUCT,
#         TITLE,
#         LABEL,
#         EXT
#     ]

#     try:
#         subprocess.run(cmd, check=True)

#         # Procura todos PNG daquele dia na raiz
#         png_files = glob.glob(f"{VAR_PRODUCT}_{date_str}*.{EXT}")

#         if not png_files:
#             logging.warning(f"{date_str} - nenhum PNG encontrado após execução")
#             return None

#         moved_files = []

#         for f in png_files:
#             dest = os.path.join(OUTPUT_DIR, os.path.basename(f))

#             if not os.path.exists(dest):
#                 shutil.move(f, dest)

#             moved_files.append(dest)

#         logging.info(f"{date_str} - OK ({len(moved_files)} arquivo(s))")

#         # Retorna o primeiro (para GIF)
#         return moved_files[0]

#     except subprocess.CalledProcessError:
#         logging.error(f"{date_str} - ERRO")
#         return None

# # ==========================================
# # PROCESSAMENTO PARALELO
# # ==========================================

# print("\nProcessando dias...\n")

# results = []

# with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
#     futures = [executor.submit(process_day, d) for d in dates]

#     for f in tqdm(as_completed(futures), total=len(futures)):
#         result = f.result()
#         if result:
#             results.append(result)

# # ==========================================
# # GERAR GIF E MP4 FINAL
# # ==========================================

# print("\nGerando animações...\n")

# results = sorted([r for r in results if os.path.exists(r)])

# if results:

#     # ======================
#     # GIF
#     # ======================
#     gif_file = os.path.join(
#         OUTPUT_DIR,
#         f"{VAR_PRODUCT}_{START_DATE}_{END_DATE}.gif"
#     )

#     images = [imageio.imread(f) for f in results]
#     imageio.mimsave(gif_file, images, duration=1/FPS)

#     print(f"GIF salvo em: {gif_file}")

#     # ======================
#     # MP4
#     # ======================
 
#     os.environ["IMAGEIO_FFMPEG_EXE"] = "/usr/bin/ffmpeg"

#     mp4_file = os.path.join(
#         OUTPUT_DIR,
#         f"{VAR_PRODUCT}_{START_DATE}_{END_DATE}.mp4"
#     )

#     writer = imageio.get_writer(mp4_file, fps=FPS)

#     for img in images:
#         writer.append_data(img)

#     writer.close()

#     print(f"MP4 salvo em: {mp4_file}")


# else:
#     print("Nenhuma imagem gerada. Animações não criadas.")
#     logging.warning("Nenhuma imagem disponível para animação")











