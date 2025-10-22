# -*- coding: utf-8 -*-
"""
Mapa Folium: População atendida por estação
- Raio = REP_ESPACIAL
- Cor = escala de população
- Join pelo ID (buffers_var.gpkg x populacao_varbuf.csv)
"""

import geopandas as gpd
import pandas as pd
import folium
from folium.plugins import MiniMap, Fullscreen
from branca.element import MacroElement
from jinja2 import Template
from pathlib import Path
import os

# ========================
# Configurações
# ========================
rootPath   = Path(os.path.dirname(os.getcwd()))
OUTPUT_DIR = rootPath / "data" / "outputs"

BUFFER_PATH = OUTPUT_DIR / "buffers_var.gpkg"
POP_PATH    = OUTPUT_DIR / "populacao_varbuf.csv"

STATIC_DIR  = rootPath / "_static"
REP_STATIC_DIR = STATIC_DIR / "representatividade"
REP_STATIC_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_HTML_NAME = "mapa_pop_estacoes.html"

# ========================
# Helpers
# ========================
def get_color(pop_value):
    if pd.isna(pop_value):
        return "#999999"
    elif pop_value < 1_000:
        return "#fee5d9"
    elif pop_value < 10_000:
        return "#fcae91"
    elif pop_value < 100_000:
        return "#fb6a4a"
    elif pop_value < 1_000_000:
        return "#de2d26"
    else:
        return "#a50f15"

def add_legend(m):
    legend_html = """
    {% macro html(this, kwargs) %}
    <div style="
        position: fixed; 
        bottom: 50px; left: 50px; width: 220px; height: 180px; 
        z-index:9999; font-size:14px;
        background-color: white; padding: 10px; border:2px solid grey;
        ">
        <b>População atendida</b><br>
        <i style="background:#fee5d9;width:18px;height:18px;float:left;margin-right:5px;"></i> < 1 mil<br>
        <i style="background:#fcae91;width:18px;height:18px;float:left;margin-right:5px;"></i> 1k – 10k<br>
        <i style="background:#fb6a4a;width:18px;height:18px;float:left;margin-right:5px;"></i> 10k – 100k<br>
        <i style="background:#de2d26;width:18px;height:18px;float:left;margin-right:5px;"></i> 100k – 1M<br>
        <i style="background:#a50f15;width:18px;height:18px;float:left;margin-right:5px;"></i> > 1M<br>
        <i style="background:#999999;width:18px;height:18px;float:left;margin-right:5px;"></i> sem dado
    </div>
    {% endmacro %}
    """
    macro = MacroElement()
    macro._template = Template(legend_html)
    m.get_root().add_child(macro)
    return m

# ========================
# Função principal
# ========================
def build_map_pop(html_name: str = DEFAULT_HTML_NAME, height: int = 800):
    # --- Carregar arquivos ---
    buf = gpd.read_file(BUFFER_PATH).to_crs(4326)
    pop = pd.read_csv(POP_PATH)

    # Join pelo ID
    buf["ID"] = buf["ID"].astype(int)
    pop["ID"] = pop["ID"].astype(int)
    buf_pop = buf.merge(pop, on="ID", how="left")

    # Centro do mapa
    minx, miny, maxx, maxy = buf_pop.total_bounds
    center_lat, center_lon = (miny + maxy) / 2, (minx + maxx) / 2

    # Mapa
    br_bounds = [[-34.0, -74.0], [6.0, -34.0]]
    m = folium.Map(location=[center_lat, center_lon],
                   zoom_start=4,
                   tiles="cartodbpositron",
                   control_scale=True)
    m.fit_bounds(br_bounds)
    m.options["minZoom"] = 4
    m.options["maxBounds"] = br_bounds
    m.options["maxBoundsViscosity"] = 1.0

    # Controles extras
    Fullscreen(position="topright").add_to(m)
    MiniMap(toggle_display=True).add_to(m)

    # --- Plota círculos ---
    for _, row in buf_pop.iterrows():
        if row.geometry is None:
            continue
        geom = row.geometry.centroid
        lat, lon = geom.y, geom.x
        pop_val = row.get("POP_BUFFER", None)
        radius = float(row.get("REP_ESPACIAL", 0))
        color = get_color(pop_val)

        folium.Circle(
            location=(lat, lon),
            radius=radius,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.6,
            weight=1,
            tooltip=f"Estação: {row.get('ID_OEMA','?')}<br>"
                    f"UF: {row.get('UF','?')}<br>"
                    f"Poluente: {row.get('POLUENTE','?')}<br>"
                    f"População atendida: {int(pop_val) if pd.notna(pop_val) else '—'}<br>"
                    f"Raio oficial: {radius:.0f} m"
        ).add_to(m)

    # Legenda
    add_legend(m)

    # Salvar HTML
    html_path = REP_STATIC_DIR / html_name
    m.save(str(html_path))
    print(f"✅ Mapa salvo em {html_path}")
    return m, str(html_path)
