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
LOG_DIR = "../cipc_log"

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
        pattern_img = str(output_dir / "*" / f"{VAR_PRODUCT}_{date_str}*.{ext}")

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



