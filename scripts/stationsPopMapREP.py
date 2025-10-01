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
from pathlib import Path

# Importa o cálculo de população
from scripts.popUnderStationREP import popUnderStationREP

# ========================
# Configurações
# ========================
rootPath   = Path(os.path.dirname(os.getcwd()))
OUTPUT_DIR = rootPath / "data/outputs"

BUFFER_PATH = OUTPUT_DIR / "buffers_var.gpkg"
POP_PATH    = OUTPUT_DIR / "populacao_varbuf.csv"
SETOR_PATH  = rootPath / "data/setores_censitarios/BR_setores_pop2022.gpkg"

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

def get_radius_m(pop_value):
    """Raio em metros, proporcional à população atendida"""
    if pd.isna(pop_value) or pop_value <= 0:
        return 500   # mínimo
    return max(500, min(20_000, (pop_value ** 0.5) * 30))  # cresce e limita

# ========================
# Função principal
# ========================
def build_map_pop(
    cap_radius_by_rep: bool = True,     # limita o raio do círculo pelo REP_ESPACIAL
    show_rep_circles: bool = True       # mostra camada com círculos REP_ESPACIAL
):
    # --- Garante que buffers + população existam ---
    popUnderStationREP(method="A")  # se não existir, cria buffers e populacao_varbuf.csv

    # --- Lê buffers e população ---
    buffers = gpd.read_file(BUFFER_PATH).to_crs(4326)
    pop = pd.read_csv(POP_PATH)

    # Garante chave ID
    if "ID" not in buffers.columns:
        buffers = buffers.reset_index(drop=False).rename(columns={"index": "ID"})

    # Merge com a população
    buffers = buffers.merge(pop, on="ID", how="left")

    # Descobre REP_ESPACIAL
    rep_col = None
    if "REP_ESPACIAL" in buffers.columns:
        rep_col = "REP_ESPACIAL"

    # Centróides para posicionar os círculos
    pts = buffers.to_crs(5880).copy()   # CRS métrico
    pts["geometry"] = pts.geometry.centroid
    pts = pts.to_crs(4326)

    # Centro do mapa
    try:
        minx, miny, maxx, maxy = buffers.total_bounds
        center_lat, center_lon = (miny + maxy) / 2, (minx + maxx) / 2
    except Exception:
        center_lat, center_lon = -14.2, -52.9

    # --- Mapa base com restrição ao Brasil ---
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=4,
        tiles="cartodbpositron",
        control_scale=True,
        max_bounds=True
    )
    
    # Limites aproximados do Brasil (bounding box WGS84)
    br_bounds = [[-34.0, -74.0], [6.0, -34.0]]  # [sul-oeste, norte-leste]
    m.fit_bounds(br_bounds)
    m.options['maxBounds'] = br_bounds
    m.options['maxBoundsViscosity'] = 1.0  # trava ao sair da caixa
    m.options['minZoom'] = 4  # evita zoom out além do Brasil


    # Buffers reais (polígonos)
#    folium.GeoJson(
#        buffers[["ID", "geometry"]],
#        name="Buffers das estações (polígonos)",
#        style_function=lambda f: {"color": "#2171b5", "weight": 1, "fillOpacity": 0.05}
#    ).add_to(m)

    # (Opcional) círculos de REP_ESPACIAL
#    if show_rep_circles and rep_col is not None:
#        layer_rep = folium.FeatureGroup(
#            name="Área de representação (círculos REP_ESPACIAL)", show=False
#        ).add_to(m)
#        for _, row in pts.iterrows():
#            geom = row.geometry
#            if geom is None or geom.is_empty:
#                continue
#            rep = row.get(rep_col)
#            if pd.isna(rep) or rep <= 0:
#                continue
#            lat, lon = geom.y, geom.x
#            folium.Circle(
#                location=(lat, lon),
#                radius=float(rep),
#                color="#111111",
#                weight=1,
#                fill=False,
#                opacity=0.9,
#            ).add_to(layer_rep)

    # Círculos proporcionais de população
    layer_pts = folium.FeatureGroup(
        name="População atendida (círculos proporcionais)", show=True
    ).add_to(m)

    for _, row in pts.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        lat, lon = geom.y, geom.x

        pop_val = row.get("POP_BUFFER", None)

        # --- Raio fixado pelo REP_ESPACIAL ---
        rep = row.get(rep_col) if rep_col is not None else None
        if pd.isna(rep) or rep <= 0:
            radius = 500   # valor mínimo para não sumir do mapa
        else:
            radius = float(rep)

        color = get_color(pop_val)
        rep_txt = (f"{int(rep)} m" if pd.notna(rep) else "—")
        pop_txt = int(pop_val) if pd.notna(pop_val) else "—"

        folium.Circle(
            location=(lat, lon),
            radius=radius,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.6,
            weight=1,
            tooltip=(
                f"ID: {row['ID']}<br>"
                f"População atendida: {pop_txt}<br>"
                f"REP_ESPACIAL: {rep_txt}"
            )
        ).add_to(layer_pts)


    return m
