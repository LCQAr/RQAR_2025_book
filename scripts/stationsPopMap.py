# -*- coding: utf-8 -*-
"""
Mapa: População atendida por estação de monitoramento
Mostra pontos proporcionais à população atendida + buffers reais
"""

import geopandas as gpd
import pandas as pd
import folium
from folium.plugins import MiniMap, Fullscreen
from pathlib import Path
import os

# ========================
# Configurações
# ========================
rootPath   = Path(os.path.dirname(os.getcwd()))
OUTPUT_DIR = rootPath / "data/outputs"

BUFFER_PATH = OUTPUT_DIR / "buffers_var.gpkg"
POP_PATH    = OUTPUT_DIR / "populacao_varbuf.csv"

# ========================
# Funções auxiliares
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

def get_radius_m(pop_value):
    """Raio em metros, proporcional à população atendida"""
    if pd.isna(pop_value) or pop_value <= 0:
        return 500   # mínimo
    return max(500, min(20_000, (pop_value ** 0.5) * 30))  # cresce e limita

# ========================
# Função principal
# ========================
def build_map_pop():
    buffers = gpd.read_file(BUFFER_PATH).to_crs(4326)
    pop = pd.read_csv(POP_PATH)

    if "ID" not in buffers.columns:
        buffers = buffers.reset_index(drop=False).rename(columns={"index": "ID"})

    buffers = buffers.merge(pop, on="ID", how="left")


    pts = buffers.to_crs(5880).copy()   # reprojeta para CRS em metros
    pts["geometry"] = pts.geometry.centroid
    pts = pts.to_crs(4326)              # volta para lat/lon, que o folium entende


    center_lat, center_lon = -14.2, -52.9
    m = folium.Map(location=[center_lat, center_lon], zoom_start=4,
                   tiles="cartodbpositron", control_scale=True)

    # Buffers reais
    folium.GeoJson(
        buffers[["ID", "geometry"]],
        name="Buffers das estações",
        style_function=lambda f: {"color": "#2171b5", "weight": 1, "fillOpacity": 0.05}
    ).add_to(m)

    # Círculos proporcionais
    layer_pts = folium.FeatureGroup(name="População atendida", show=True).add_to(m)
    for _, row in pts.iterrows():
        geom = row.geometry
        if geom.is_empty:
            continue
        lat, lon = geom.y, geom.x
        pop_val = row.get("POP_BUFFER", None)

        folium.Circle(
            location=(lat, lon),
            radius=get_radius_m(pop_val),  # em metros
            color=get_color(pop_val),
            fill=True,
            fill_color=get_color(pop_val),
            fill_opacity=0.6,
            weight=1,
            tooltip=f"ID: {row['ID']}<br>População atendida: {int(pop_val) if pd.notna(pop_val) else '—'}"
        ).add_to(layer_pts)

    MiniMap(toggle_display=True, position="bottomright").add_to(m)
    Fullscreen().add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)

    legend_html = """
    <div style='position: fixed; bottom: 20px; left: 20px; z-index: 9999;
    background: white; padding: 8px; border: 1px solid #bbb; border-radius: 4px;'>
    <b>População atendida</b><br>
    <div><span style='display:inline-block;width:12px;height:12px;background:#fee5d9;margin-right:4px;'></span> < 1 mil</div>
    <div><span style='display:inline-block;width:12px;height:12px;background:#fcae91;margin-right:4px;'></span> 1k – 10k</div>
    <div><span style='display:inline-block;width:12px;height:12px;background:#fb6a4a;margin-right:4px;'></span> 10k – 100k</div>
    <div><span style='display:inline-block;width:12px;height:12px;background:#de2d26;margin-right:4px;'></span> 100k – 1M</div>
    <div><span style='display:inline-block;width:12px;height:12px;background:#a50f15;margin-right:4px;'></span> > 1M</div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    return m
