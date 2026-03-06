# Cria um html para controle das imagens


#!/usr/bin/env python3

import os
import sys
import glob
import re

if len(sys.argv) != 3:
    print("\nUso:")
    print("python make_viewer.py OUTPUT_DIR VAR_PREFIX\n")
    print("Exemplo:")
    print("python make_viewer.py output aerosol_index_354_388\n")
    sys.exit(1)

OUTPUT_DIR = sys.argv[1]
VAR_PREFIX = sys.argv[2]

# Busca imagens
images = sorted(
    [os.path.basename(f)
     for f in glob.glob(os.path.join(OUTPUT_DIR, f"{VAR_PREFIX}_*.png"))]
)

if not images:
    print("Nenhuma imagem encontrada.")
    sys.exit(1)

# Extrai datas
dates = []
for img in images:
    m = re.search(r"_(\d{8})", img)
    if m:
        d = m.group(1)
        dates.append(f"{d[0:4]}-{d[4:6]}-{d[6:8]}")
    else:
        dates.append("Unknown")

html_path = os.path.join(
    OUTPUT_DIR,
    f"{VAR_PREFIX}_viewer.html"
)

with open(html_path, "w") as f:
    f.write(f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Sentinel-5P Viewer</title>

<style>

body {{
    text-align: center;
    font-family: Arial;
    background-color: #111;
    color: white;
}}

img {{
    max-width: 95%;
    border: 2px solid white;
}}

.controls button {{
    font-size: 18px;
    margin: 5px;
}}

#subtitle {{
    font-size: 18px;
    color: #9fd3ff;
    margin-bottom: 5px;
}}

#title {{
    font-size: 48px;
    font-weight: bold;
    margin-bottom: 20px;
    color: #ffffff;
}}

</style>
</head>

<body>

<div id="subtitle">{VAR_PREFIX} - Sentinel-5P</div>
<div id="title"></div>

<img id="frame" src="{images[0]}"><br><br>

<div class="controls">
<button onclick="prevFrame()">⏪</button>
<button onclick="play()">▶</button>
<button onclick="pause()">⏸</button>
<button onclick="nextFrame()">⏩</button>
</div>

<br>
Velocidade (ms):
<input type="range" min="100" max="2000" value="1000" id="speed">

<br><br>
Frame:
<input type="range" min="0" max="{len(images)-1}" value="0" id="slider">

<script>

var images = {images};
var dates = {dates};

var index = 0;
var timer = null;

var slider = document.getElementById("slider");

function formatDate(date) {{

    var year = date.substring(0,4);
    var month = date.substring(5,7);
    var day = date.substring(8,10);

    var months = ["Jan","Feb","Mar","Apr","May","Jun",
                  "Jul","Aug","Sep","Oct","Nov","Dec"];

    return day + " " + months[parseInt(month)-1] + " " + year;
}}

function updateFrame() {{

    document.getElementById("frame").src = images[index];

    var date_str = formatDate(dates[index]);

    document.getElementById("title").innerText =
        "Sentinel-5P {VAR_PREFIX} " + date_str;

    slider.value = index;
}}

function nextFrame() {{
    index = (index + 1) % images.length;
    updateFrame();
}}

function prevFrame() {{
    index = (index - 1 + images.length) % images.length;
    updateFrame();
}}

function play() {{
    var speed = document.getElementById("speed").value;
    timer = setInterval(nextFrame, speed);
}}

function pause() {{
    clearInterval(timer);
}}

slider.oninput = function() {{
    index = parseInt(this.value);
    updateFrame();
}};

document.addEventListener("keydown", function(event) {{

    if (event.key === "ArrowRight") nextFrame();
    if (event.key === "ArrowLeft") prevFrame();

    if (event.key === " ") {{
        if (timer) pause();
        else play();
    }}
}});

updateFrame();

</script>

</body>
</html>
""")

print(f"Viewer criado em: {html_path}")

