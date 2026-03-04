# Cria um html para controle das imagens

#!/usr/bin/env python3

import os
import sys
import glob

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
</style>
</head>
<body>

<h2>{VAR_PREFIX} - Sentinel-5P</h2>

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
var index = 0;
var timer = null;

var slider = document.getElementById("slider");

function updateFrame() {{
    document.getElementById("frame").src = images[index];
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

</script>

</body>
</html>
""")

print(f"Viewer criado em: {html_path}")