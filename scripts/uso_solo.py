# -*- coding: utf-8 -*-
"""
Created on Wed Sep 11 16:09:53 2024

@author: r
    """afab
import scripts.stationsLandUse as stl
import os, sys
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd
import geopandas as gpd
from pathlib import Path
import folium
from folium.plugins import MiniMap, Fullscreen
from html import escape






upbyfile = 'Monitoramento_QAr_BR.csv'
bufferSize = 1000          # 1 km para Fig.8/Tabela 14
bufferSize5k = 5000        # 5 km para Fig.9
year = 2024
pixelSize = 30*30          # use 900 m² APENAS se o raster MapBiomas estiver em METROS
rootPath = os.path.dirname(os.getcwd())
inputFolder = rootPath + '/data'
mapbiomasFolder = inputFolder + '/MAPBIOMAS'

# Acesso a scripts
scripts_dir = rootPath + '/scripts'
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

gdf = stl.stationBuffers(inputFolder+'/'+file,bufferSize)

stationInUF = stl.stationUnionByUF(gdf)

gdfUFstations = stl.cutMapbiomas(inputFolder+'/MAPBIOMAS',stationInUF,year,'UF',pixelSize)


# ------------------------------------------------
# 0) Mapa de classes → GRUPOS (EMBUTIDO AQUI)
# ------------------------------------------------
land_use_map = {
    'Floresta':     ['1', '3', '4', '5', '6', '49'],
    'Herbácea':     ['10', '11', '12', '32', '29', '50'],
    'Agropecuária': ['14', '15', '18', '19', '39', '20', '40', '62', '41', '36', '46', '47', '35', '48', '9', '21'],
    'Não Vegetada': ['22', '23', '25', '26', '33', '31', '27'],
    'Urbanizada':   ['24'],
    'Mineração':    ['30']
}

# Paleta de cores por GRUPO (ajuste se quiser)
GROUP_COLORS = {
    'Floresta': "#2ca02c",
    'Herbácea': "#1f78b4",
    'Agropecuária': "#ff7f00",
    'Não Vegetada': "#b15928",
    'Urbanizada': "#e31a1c",
    'Mineração': "#6a3d9a"
}

# ------------------------------------------------
# Helpers
# ------------------------------------------------
def aggregate_land_use(df: pd.DataFrame, land_use_map: dict) -> pd.DataFrame:
    """    """
    Agrega colunas por códigos MapBiomas nos GRUPOS definidos em land_use_map.
    Aceita colunas com nome int (1,3,4...) ou str ('1','3','4'...).
    Cria/atualiza colunas com os nomes dos grupos contendo a soma de áreas (m²).
    """
    df_agg = df.copy()
    cols_as_str = {str(c): c for c in df.columns}  # mapeia 'str(código)' -> nome real da coluna

    for group, codes in land_use_map.items():
        present_cols = [cols_as_str[c] for c in codes if c in cols_as_str]
        if present_cols:
            df_agg[group] = df_agg[present_cols].fillna(0).sum(axis=1)
        else:
            if group not in df_agg.columns:
                df_agg[group] = 0.0
    return df_agg

def predominant_group(row: pd.Series, groups: list[str]) -> str | float:
    """Retorna o nome do grupo com maior área; NaN se soma zero."""
    vals = row[groups].fillna(0)
    return vals.idxmax() if vals.sum() > 0 else np.nan

# ------------------------------------------------
# 1) Buffers de 1 km e 5 km
# ------------------------------------------------
gdf_1k = stl.stationBuffers(inputFolder + '/' + file, bufferSize)
gdf_5k = stl.stationBuffers(inputFolder + '/' + file, bufferSize5k)

# ------------------------------------------------
# 2) Corte do MapBiomas (usa sua assinatura com 'suffix' e 'pixelSize')
# ------------------------------------------------
stats_1k = stl.cutMapbiomas(mapbiomasFolder, gdf_1k, year, '', pixelSize)
stats_5k = stl.cutMapbiomas(mapbiomasFolder, gdf_5k, year, '', pixelSize)

# 1) Agrega classes do MapBiomas em grupos (área m² por grupo)
df1k_agg = aggregate_land_use(stats_1k, land_use_map)

# 2) Grupo predominante (1 km)
df1k_agg['GRUPO_PRED_1k'] = df1k_agg.apply(lambda r: predominant_group(r, GROUPS), axis=1)

# 3) Une com a geometria dos buffers (usa índice como chave; se precisar, troque por merge por colunas)
gdf1k = gdf_1k.copy()
try:
    gdf1k = gdf1k.set_crs(4326, allow_override=True)
except Exception:
    pass

# garante alinhamento de índice
df1k_agg = df1k_agg.reindex(gdf1k.index)
gdf1k_merged = gdf1k.join(df1k_agg, how='left')

# para plotar ponto, uso centróides dos buffers
gdf1k_pts = gdf1k_merged.copy()
gdf1k_pts['geometry'] = gdf1k_pts.geometry.centroid

gdf1k_pts[['GRUPO_PRED_1k']].head()

def folium_categorical_legend(title, color_map):
    items = "".join(
        f"<div style='margin:2px 0;display:flex;align-items:center;'>"
        f"<span style='display:inline-block;width:12px;height:12px;background:{escape(color)};margin-right:6px;border:1px solid #555;'></span>"
        f"{escape(label)}</div>"
        for label, color in color_map.items()
    )
    return (
        f"<div style='position:fixed;bottom:20px;left:20px;z-index:9999;"
        f"background:rgba(255,255,255,0.9);padding:8px 10px;border:1px solid #bbb;"
        f"border-radius:4px;font-size:12px;'>"
        f"<div style='font-weight:600;margin-bottom:4px'>{escape(title)}</div>{items}</div>"
    )

def pick_uf_name_column(uf_gdf: gpd.GeoDataFrame):
    candidates = ['SIGLA_UF','NM_UF','UF','NOME','NOME_UF','name','Name']
    for c in candidates:
        if c in uf_gdf.columns:
            return c
    for c in uf_gdf.columns:
        if pd.api.types.is_string_dtype(uf_gdf[c]):
            return c
    return uf_gdf.columns[0]

# carrega shapefile de UFs se houver caminho/arquivo
uf_gdf = None
if 'uf_shp_path' in globals() and uf_shp_path and Path(uf_shp_path).exists():
    uf_gdf = gpd.read_file(uf_shp_path)
    try:
        uf_gdf = uf_gdf.to_crs(4326)
    except Exception:
        pass

# Se já existir gdf1k_pts no kernel, esta célula não altera nada.
if 'gdf1k_pts' not in globals():
    # garante CRS e centróides
    gdf1k = gdf_1k.copy()
    try:
        gdf1k = gdf1k.set_crs(4326, allow_override=True)
    except Exception:
        pass

    # agrega classes e calcula predominância (usa suas funções já carregadas)
    df1k_agg = aggregate_land_use(stats_1k, land_use_map)
    GROUPS = list(land_use_map.keys())
    df1k_agg['GRUPO_PRED_1k'] = df1k_agg.apply(lambda r: predominant_group(r, GROUPS), axis=1)

    # alinha por índice e une
    df1k_agg = df1k_agg.reindex(gdf1k.index)
    gdf1k_pts = gdf1k.join(df1k_agg, how='left')
    gdf1k_pts['geometry'] = gdf1k_pts.geometry.centroid

# centro do mapa (a partir da extensão dos pontos, com fallback Brasil)
try:
    minx, miny, maxx, maxy = gdf1k_pts.to_crs(4326).total_bounds
    center_lat, center_lon = (miny + maxy)/2, (minx + maxx)/2
except Exception:
    center_lat, center_lon = -14.2, -52.9

# garante dicionário de cores e lista de grupos
GROUPS = list(land_use_map.keys())
GROUP_COLORS = GROUP_COLORS  # já está no kernel, só garantindo o nome


# --- helpers já definidos? Se não, criamos versões rápidas ---
try:
    folium_categorical_legend
except NameError:
    from html import escape
    def folium_categorical_legend(title, color_map):
        items = "".join(
            f"<div style='margin:2px 0;display:flex;align-items:center;'>"
            f"<span style='display:inline-block;width:12px;height:12px;background:{escape(color)};margin-right:6px;border:1px solid #555;'></span>"
            f"{escape(label)}</div>"
            for label, color in color_map.items()
        )
        return (
            f"<div style='position:fixed;bottom:20px;left:20px;z-index:9999;"
            f"background:rgba(255,255,255,0.9);padding:8px 10px;border:1px solid #bbb;"
            f"border-radius:4px;font-size:12px;'>"
            f"<div style='font-weight:600;margin-bottom:4px'>{escape(title)}</div>{items}</div>"
        )
try:
    pick_uf_name_column
except NameError:
    import pandas as pd
    def pick_uf_name_column(uf_gdf):
        for c in ['SIGLA_UF','NM_UF','UF','NOME','NOME_UF','name','Name']:
            if c in uf_gdf.columns: return c
        for c in uf_gdf.columns:
            if pd.api.types.is_string_dtype(uf_gdf[c]): return c
        return uf_gdf.columns[0]

# --- garante gdf1k_pts com GRUPO_PRED_1k ---
import geopandas as gpd, pandas as pd, numpy as np, folium
from folium.plugins import MiniMap, Fullscreen
gdf1k = gdf_1k.copy()
try: gdf1k = gdf1k.set_crs(4326, allow_override=True)
except Exception: pass

GROUPS = list(land_use_map.keys())

if 'gdf1k_pts' not in globals() or 'GRUPO_PRED_1k' not in (getattr(gdf1k_pts, 'columns', [])):
    df1k_agg_full = aggregate_land_use(stats_1k, land_use_map)
    df1k_agg_full['GRUPO_PRED_1k'] = df1k_agg_full.apply(lambda r: predominant_group(r, GROUPS), axis=1)
    cols_keep = [c for c in df1k_agg_full.columns if (c in GROUPS) or (c == 'GRUPO_PRED_1k')]
    df1k_agg = df1k_agg_full[cols_keep].reindex(gdf1k.index)
    gdf1k_pts = gdf1k.join(df1k_agg, how='left')
    gdf1k_pts['geometry'] = gdf1k_pts.geometry.centroid

# centro do mapa
try:
    minx, miny, maxx, maxy = gdf1k_pts.to_crs(4326).total_bounds
    center_lat, center_lon = (miny+maxy)/2, (minx+maxx)/2
except Exception:
    center_lat, center_lon = -14.2, -52.9

# carrega UFs se não houver uf_gdf mas existir uf_shp_path
if 'uf_gdf' not in globals() and 'uf_shp_path' in globals():
    from pathlib import Path
    if uf_shp_path and Path(uf_shp_path).exists():
        uf_gdf = gpd.read_file(uf_shp_path)
        try: uf_gdf = uf_gdf.to_crs(4326)
        except Exception: pass

# --- mapa 1 km ---
m8_1k = folium.Map(location=[center_lat, center_lon], zoom_start=4, tiles="OpenStreetMap", control_scale=True)
folium.TileLayer("cartodbpositron", name="CartoDB Positron").add_to(m8_1k)

# UFs (opcional)
if 'uf_gdf' in globals() and uf_gdf is not None:
    name_col = pick_uf_name_column(uf_gdf)
    folium.GeoJson(
        uf_gdf,
        name="UFs",
        style_function=lambda f: {"color":"#808080","weight":1,"fillColor":"#f8f8f8","fillOpacity":0.7},
        tooltip=folium.GeoJsonTooltip(fields=[name_col], aliases=["UF: "], sticky=False) if name_col else None,
    ).add_to(m8_1k)

# camada de pontos (cor = predominância 1 km)
layer_pts_1k = folium.FeatureGroup(name="Estações — predominância (1 km)", show=True).add_to(m8_1k)
for _, row in gdf1k_pts.iterrows():
    grp = row.get('GRUPO_PRED_1k')
    if pd.isna(grp) or grp not in GROUP_COLORS: continue
    g = row.geometry
    if g is None or g.is_empty: continue
    lat, lon = g.y, g.x
    folium.CircleMarker(
        location=(lat, lon),
        radius=5,
        color=GROUP_COLORS[grp],
        fill=True,
        fill_color=GROUP_COLORS[grp],
        fill_opacity=0.9,
        weight=1,
        tooltip=f"Predom. 1 km: {grp}",
    ).add_to(layer_pts_1k)

# buffers 1 km — círculos (leves)
layer_buf1_circle = folium.FeatureGroup(name="Buffers 1 km (círculo)", show=False).add_to(m8_1k)
for _, r in gdf1k_pts.iterrows():
    g = r.geometry
    if g is None or g.is_empty: continue
    folium.Circle(location=(g.y, g.x), radius=1000, color="#0066ff", weight=1, fill=False, opacity=0.9).add_to(layer_buf1_circle)

# buffers 1 km — polígonos reais (opcional; pode pesar)
USE_POLYGON_1K = False
if USE_POLYGON_1K:
    gdf1_poly = gdf_1k.to_crs(4326)[['geometry']].copy()
    gdf1_poly['geometry'] = gdf1_poly.geometry.simplify(0.0005)  # ~50 m
    folium.FeatureGroup(name="Buffers 1 km (polígono)", show=False).add_to(m8_1k)
    folium.GeoJson(gdf1_poly, style_function=lambda f: {"color":"#0066ff","weight":1,"fill":False}).add_to(m8_1k)

MiniMap(toggle_display=True, position="bottomright").add_to(m8_1k)
Fullscreen().add_to(m8_1k)
m8_1k.get_root().html.add_child(folium.Element(folium_categorical_legend("Predominância (1 km) — MapBiomas/2023", GROUP_COLORS)))
folium.LayerControl(collapsed=False).add_to(m8_1k)


# --------------------------
# 5) Buffers 5 km
# --------------------------
# (A) círculos com raio (leve)
layer_buf5_circle = folium.FeatureGroup(name="Buffers 5 km (círculo)", show=False).add_to(m9_5k)
for _, r in gdf1k_pts.iterrows():
    g = r.geometry
    if g is None or g.is_empty: 
        continue
    folium.Circle(location=(g.y, g.x), radius=5000, color="#111111", weight=1, fill=False, opacity=0.9).add_to(layer_buf5_circle)

# (B) polígonos reais (mais fiel; pode pesar)
USE_POLYGON_5K = False  # mude para True se quiser ver o polígono dos buffers do gdf_5k
if USE_POLYGON_5K:
    gdf5_poly = gdf_5k.to_crs(4326)[['geometry']].copy()
    gdf5_poly['geometry'] = gdf5_poly.geometry.simplify(0.0008)  # ~80 m (ajuste se necessário)
    layer_poly5 = folium.FeatureGroup(name="Buffers 5 km (polígono)", show=False).add_to(m9_5k)
    folium.GeoJson(
        gdf5_poly,
        style_function=lambda f: {"color":"#111111","weight":1,"fill":False}
    ).add_to(layer_poly5)

# --------------------------
# 6) Extras (mini-mapa, legenda e controle)
# --------------------------
MiniMap(toggle_display=True, position="bottomright").add_to(m9_5k)
Fullscreen().add_to(m9_5k)
m9_5k.get_root().html.add_child(folium.Element(folium_categorical_legend("Predominância (5 km) — MapBiomas/2023", GROUP_COLORS)))
folium.LayerControl(collapsed=False).add_to(m9_5k)(['ESTADO', 'ESTAÇÃO']).apply(merge_values).reset_index(drop=True)


#%%
# Create a function to assign regions based on UF
def assign_region(uf):
    for region, states in regions.items():
        if uf in states:
            return region
    return None

def createRegion (df):    
    # Add the region column
    df['REGIÃO'] = df['ESTADO'].map(lambda x: assign_region(x))   
    df_sorted = df[['REGIÃO','ESTADO', 'CIDADE', 'ESTAÇÃO', 'TIPO', 'Certificação', 'STATUS', 'FONTE', 'land_use_name']]
    df_sorted = df.sort_values(by=['REGIÃO', 'ESTADO', 'CIDADE'])
    return df_sorted

df_sorted = createRegion(estacoes_grouped)



num = df_sorted.groupby('ESTADO').count()



