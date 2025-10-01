# -*- coding: utf-8 -*-
"""
Mapa + Tabela: População atendida por estação de monitoramento
- Mostra pontos proporcionais à população atendida + buffers reais
- Gera tabela por estado com população coberta e número de estações
"""

import geopandas as gpd
import pandas as pd
import folium
from folium.plugins import MiniMap, Fullscreen
from pathlib import Path
import os
from IPython.display import display, HTML

# ========================
# Configurações
# ========================
rootPath   = Path(os.path.dirname(os.getcwd()))
OUTPUT_DIR = rootPath / "data/outputs"

BUFFER_PATH = OUTPUT_DIR / "buffers_var.gpkg"
POP_PATH    = OUTPUT_DIR / "populacao_varbuf.csv"
SETOR_PATH  = rootPath / "data/setores_censitarios/BR_setores_pop2022.gpkg"

# Dicionário de UFs
codigo_para_uf = {
    12: 'AC', 27: 'AL', 13: 'AM', 16: 'AP', 29: 'BA', 23: 'CE', 53: 'DF',
    32: 'ES', 52: 'GO', 21: 'MA', 31: 'MG', 50: 'MS', 51: 'MT', 15: 'PA',
    25: 'PB', 26: 'PE', 22: 'PI', 41: 'PR', 33: 'RJ', 24: 'RN', 11: 'RO',
    14: 'RR', 43: 'RS', 42: 'SC', 28: 'SE', 35: 'SP', 17: 'TO'
}

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

# ========================
# Função principal do mapa
# ========================
def build_map_pop():
    buffers = gpd.read_file(BUFFER_PATH).to_crs(4326)
    pop = pd.read_csv(POP_PATH)

    # Garante chave ID
    if "ID" not in buffers.columns:
        buffers = buffers.reset_index(drop=False).rename(columns={"index": "ID"})
    buffers = buffers.merge(pop, on="ID", how="left")

    # Centro do mapa
    try:
        minx, miny, maxx, maxy = buffers.total_bounds
        center_lat, center_lon = (miny + maxy) / 2, (minx + maxx) / 2
    except Exception:
        center_lat, center_lon = -14.2, -52.9

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=4,
        tiles="cartodbpositron",
        control_scale=True,
        max_bounds=True
    )
    br_bounds = [[-34.0, -74.0], [6.0, -34.0]]
    m.fit_bounds(br_bounds)
    m.options['maxBounds'] = br_bounds
    m.options['maxBoundsViscosity'] = 1.0
    m.options['minZoom'] = 4

    for _, row in buffers.iterrows():
        geom = row.geometry.centroid
        lat, lon = geom.y, geom.x
        pop_val = row.get("POP_BUFFER", None)
        color = get_color(pop_val)
        folium.Circle(
            location=(lat, lon),
            radius=500,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.6,
            weight=1,
            tooltip=f"ID: {row['ID']}<br>População atendida: {int(pop_val) if pd.notna(pop_val) else '—'}"
        ).add_to(m)

    return m




