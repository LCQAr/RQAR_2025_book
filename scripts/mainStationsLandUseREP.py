# -*- coding: utf-8 -*-

from __future__ import annotations
import os
from pathlib import Path
from html import escape
import geopandas as gpd
import os
import numpy as np
import pandas as pd
pd.set_option('future.no_silent_downcasting', True)
import geopandas as gpd
import folium
from folium.plugins import MiniMap, Fullscreen
import warnings
# Dependências do seu repositório
import scripts.stationsLandUse as stl  # stationBuffers, cutMapbiomas, stationUnionByUF
from pathlib import Path
import logging

# Defina a pasta de saída
rootPath = Path(os.path.dirname(os.getcwd()))
OUTPUT_DIR = Path(rootPath / "data/outputs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
logging.getLogger("pyogrio._io").setLevel(logging.ERROR)
# =========================
# Configs e constantes
# =========================
LAND_USE_MAP = {
    "Floresta":     ["1", "3", "4", "5", "6", "49"],
    "Herbácea":     ["10", "11", "12", "32", "29", "50"],
    "Agropecuária": ["14", "15", "18", "19", "39", "20", "40", "62", "41", "36", "46", "47", "35", "48", "9", "21"],
    "Não Vegetada": ["22", "23", "25", "26", "33", "31", "27"],
    "Urbanizada":   ["24"],
    "Mineração":    ["30"],
}
GROUP_COLORS = {
    "Floresta": "#2ca02c",
    "Herbácea": "#1f78b4",
    "Agropecuária": "#ff7f00",
    "Não Vegetada": "#b15928",
    "Urbanizada": "#e31a1c",
    "Mineração": "#6a3d9a",
}
GROUPS = list(LAND_USE_MAP.keys())


# =========================
# Helpers genéricos
# =========================
def aggregate_land_use(df: pd.DataFrame, land_use_map: dict) -> pd.DataFrame:
    df_agg = df.copy()
    cols_as_str = {str(c): c for c in df.columns}
    for group, codes in land_use_map.items():
        present_cols = [cols_as_str[c] for c in codes if c in cols_as_str]
        if present_cols:
            df_agg[group] = (
                df_agg[present_cols]
                .apply(pd.to_numeric, errors='coerce')
                .fillna(0.0)
                .sum(axis=1)
            )
        else:
            df_agg[group] = 0.0
    return df_agg


def predominant_group(row: pd.Series, groups: list[str]) -> str | float:
    # Converte valores para numérico, preservando NaN onde não for número
    vals = pd.to_numeric(row[groups].infer_objects(copy=False), errors='coerce')
    vals = vals.fillna(0.0).astype('float64')
    return vals.idxmax() if float(vals.sum()) > 0 else np.nan

def _percent_table(row, groups=GROUPS):
    """
    Gera string HTML com a composição percentual dos grupos de uso do solo.
    """
    parts = []
    for g in groups:
        val = row.get(f"{g}_perc", None)
        if val is not None and not pd.isna(val):
            parts.append(f"{g}: {val:.1f}%")
    return "<br>".join(parts)


def _pick_uf_name_column(uf_gdf: gpd.GeoDataFrame):
    for c in ["SIGLA_UF", "NM_UF", "UF", "NOME", "NOME_UF", "name", "Name"]:
        if c in uf_gdf.columns:
            return c
    for c in uf_gdf.columns:
        if pd.api.types.is_string_dtype(uf_gdf[c]):
            return c
    return uf_gdf.columns[0]


def _folium_categorical_legend(title, color_map):
    items = "".join(
        f"<div style='margin:2px 0;display:flex;align-items:center;'>"
        f"<span style='display:inline-block;width:12px;height:12px;background:{escape(color)};"
        f"margin-right:6px;border:1px solid #555;'></span>{escape(label)}</div>"
        for label, color in color_map.items()
    )
    return (
        f"<div style='position:fixed;bottom:20px;left:20px;z-index:9999;"
        f"background:rgba(255,255,255,0.9);padding:8px 10px;border:1px solid #bbb;"
        f"border-radius:4px;font-size:12px;'>"
        f"<div style='font-weight:600;margin-bottom:4px'>{escape(title)}</div>{items}</div>"
    )


def _autofind_uf_shapefile(base_folder: Path) -> Path | None:
    candidates = []
    for sub in [base_folder, base_folder / "SHAPES", base_folder / "shapes", base_folder / "Shapefiles"]:
        if not sub.exists():
            continue
        candidates += list(sub.rglob("*UF*.shp"))
        candidates += list(sub.rglob("*Estados*.shp"))
        candidates += list(sub.rglob("BR_UF*.shp"))
    return candidates[0] if candidates else None


def _safe_set_crs(gdf: gpd.GeoDataFrame, epsg: int = 4326) -> gpd.GeoDataFrame:
    try:
        return gdf.set_crs(epsg, allow_override=True)
    except Exception:
        return gdf


def _centroids_in_wgs84(gdf_ll: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Calcula centróides corretos (em CRS métrico) e retorna em 4326."""
    CRS_METRIC = "EPSG:5880"  # SIRGAS 2000 / Brazil Albers Equal Area (boa p/ Brasil)
    try:
        gdf_metric = gdf_ll.to_crs(CRS_METRIC)
    except Exception:
        gdf_metric = gdf_ll.to_crs(3857)  # fallback
    pts_metric = gdf_metric.geometry.centroid
    pts_wgs = pts_metric.to_crs(4326)
    out = gdf_ll.copy()
    out = out.set_geometry(pts_wgs)
    return _safe_set_crs(out, 4326)


def _center_from_bounds(gdf_ll: gpd.GeoDataFrame) -> tuple[float, float]:
    try:
        minx, miny, maxx, maxy = gdf_ll.to_crs(4326).total_bounds
        return (miny + maxy) / 2, (minx + maxx) / 2
    except Exception:
        return -14.2, -52.9

'''
# =========================
# Função: Figura 8 (1 km)
# =========================
def build_map_1k(
    file: str = "Monitoramento_QAr_BR.csv",
    rootPath: str | Path | None = None,
    year: int = 2024,
    pixelSize: int = 30 * 30,
    uf_shp_path: str | Path | None = None,
    show_buffer_circles: bool = True,
    show_buffer_polygons: bool = False,
) -> folium.Map:
    """
    Retorna o mapa Folium da Figura 8 (predominância 1 km + buffers opcionais).
    """
    rootPath = Path(rootPath or os.path.dirname(os.getcwd()))
    inputFolder = rootPath / "data"
    mapbiomasFolder = inputFolder / "MAPBIOMAS"

    # Buffers e corte
    gdf_1k = stl.stationBuffers(str(inputFolder / file), 1000)
    gdf_1k = _safe_set_crs(gdf_1k, 4326)

    stats_1k = stl.cutMapbiomas(str(mapbiomasFolder), gdf_1k, year, "", pixelSize)
    df1k = aggregate_land_use(stats_1k, LAND_USE_MAP)
    # FIX: usar o helper correto (sem underscore no nome)
    df1k["GRUPO_PRED_1k"] = df1k.apply(lambda r: predominant_group(r, GROUPS), axis=1)
    # Salva tabela com resultados de 1 km
    out1k = df1k.copy()
    out1k.insert(0, "ID", gdf_1k.index)  # garante um ID
    out1k.to_csv(OUTPUT_DIR / "uso_solo_1km.csv", index=False, encoding="utf-8")


    # Junta atributos (só grupos + predominância) e faz centróides corretos
    cols_keep = [c for c in df1k.columns if (c in GROUPS) or (c == "GRUPO_PRED_1k")]
    gdf1k = gdf_1k.join(df1k[cols_keep].reindex(gdf_1k.index), how="left")
    gdf1k_pts = _centroids_in_wgs84(gdf1k)

    center_lat, center_lon = _center_from_bounds(gdf1k_pts)

    # UFs
    uf_gdf = None
    if uf_shp_path:
        p = Path(uf_shp_path)
        if p.exists():
            uf_gdf = gpd.read_file(p)
    else:
        auto_p = _autofind_uf_shapefile(inputFolder)
        if auto_p:
            uf_gdf = gpd.read_file(auto_p)
    if uf_gdf is not None:
        try:
            uf_gdf = uf_gdf.to_crs(4326)
        except Exception:
            pass

    # Mapa Folium
    m = folium.Map(location=[center_lat, center_lon], zoom_start=4, tiles="OpenStreetMap", control_scale=True)
    folium.TileLayer("cartodbpositron", name="CartoDB Positron").add_to(m)

    # UFs
    if uf_gdf is not None:
        name_col = _pick_uf_name_column(uf_gdf)
        folium.GeoJson(
            uf_gdf,
            name="UFs",
            style_function=lambda f: {"color": "#808080", "weight": 1, "fillColor": "#f8f8f8", "fillOpacity": 0.7},
            tooltip=folium.GeoJsonTooltip(fields=[name_col], aliases=["UF: "], sticky=False) if name_col else None,
        ).add_to(m)

    # Pontos por predominância (1 km)
    layer_pts = folium.FeatureGroup(name="Estações — predominância (1 km)", show=True).add_to(m)
    for _, row in gdf1k_pts.iterrows():
        grp = row.get("GRUPO_PRED_1k")
        if pd.isna(grp) or grp not in GROUP_COLORS:
            continue
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        lat, lon = geom.y, geom.x
        folium.CircleMarker(
            location=(lat, lon),
            radius=5,
            color=GROUP_COLORS[grp],
            fill=True,
            fill_color=GROUP_COLORS[grp],
            fill_opacity=0.9,
            weight=1,
            tooltip=f"Predom. 1 km: {grp}",
        ).add_to(layer_pts)

    # Buffers 1 km
    if show_buffer_circles:
        layer_circ = folium.FeatureGroup(name="Buffers 1 km (círculo)", show=False).add_to(m)
        for _, row in gdf1k_pts.iterrows():
            geom = row.geometry
            if geom is None or geom.is_empty:
                continue
            folium.Circle(location=(geom.y, geom.x), radius=1000, color="#0066ff", weight=1, fill=False, opacity=0.9).add_to(layer_circ)

    if show_buffer_polygons:
        gdf1_poly = gdf_1k.to_crs(4326)[["geometry"]].copy()
        gdf1_poly["geometry"] = gdf1_poly.geometry.simplify(0.0005)
        layer_poly = folium.FeatureGroup(name="Buffers 1 km (polígono)", show=False).add_to(m)
        folium.GeoJson(gdf1_poly, style_function=lambda f: {"color": "#0066ff", "weight": 1, "fill": False}).add_to(layer_poly)

    MiniMap(toggle_display=True, position="bottomright").add_to(m)
    Fullscreen().add_to(m)
    m.get_root().html.add_child(folium.Element(_folium_categorical_legend("Predominância (1 km) — MapBiomas/2023", GROUP_COLORS)))
    folium.LayerControl(collapsed=False).add_to(m)
    return m
'''
'''
# =========================
# Função: Figura 9 (5 km)
# =========================
def build_map_5k(
    file: str = "Monitoramento_QAr_BR.csv",
    rootPath: str | Path | None = None,
    year: int = 2024,
    pixelSize: int = 30 * 30,
    uf_shp_path: str | Path | None = None,
    filter_representative: bool = False,
    show_buffer_circles: bool = True,
    show_buffer_polygons: bool = False,
) -> folium.Map:
    """
    Retorna o mapa Folium da Figura 9 (predominância 5 km + popup com percentuais + buffers opcionais).
    """
    rootPath = Path(rootPath or os.path.dirname(os.getcwd()))
    inputFolder = rootPath / "data"
    mapbiomasFolder = inputFolder / "MAPBIOMAS"

    # Buffers e corte
    gdf_1k = stl.stationBuffers(str(inputFolder / file), 1000)
    gdf_1k = _safe_set_crs(gdf_1k, 4326)   # FIX: usar _safe_set_crs
    gdf_5k = stl.stationBuffers(str(inputFolder / file), 5000)
    gdf_5k = _safe_set_crs(gdf_5k, 4326)   # FIX: usar _safe_set_crs

    stats_5k = stl.cutMapbiomas(str(mapbiomasFolder), gdf_5k, year, "", pixelSize)
    df5k = aggregate_land_use(stats_5k, LAND_USE_MAP)

    # Filtro opcional de representatividade
    if filter_representative:
        rep_cols = [c for c in df5k.columns if str(c).upper() in ["REPRESENTATIVO", "REPRESENTATIVA", "ESP_REP", "REP"]]
        if rep_cols:
            col = rep_cols[0]
            mask = df5k[col].astype(str).str.upper().isin(["1", "SIM", "TRUE", "VERDADEIRO", "S"])
            if mask.any():
                df5k = df5k[mask].copy()

    # Percentuais e predominância
    sums = df5k[GROUPS].sum(axis=1).replace(0, np.nan)
    for g in GROUPS:
        df5k[f"{g}_perc"] = (100 * df5k[g] / sums).round(1)
    df5k["GRUPO_PRED_5k"] = df5k[GROUPS].idxmax(axis=1)
    out5k = df5k.copy()
    out5k.insert(0, "ID", gdf_5k.index)
    out5k.to_csv(OUTPUT_DIR / "uso_solo_5km.csv", index=False, encoding="utf-8")
    df5k.loc[sums.isna(), "GRUPO_PRED_5k"] = np.nan

    # Pontos (usa centróides corretos do 1k; alinhamento por índice)
    gdf1k_pts = _centroids_in_wgs84(gdf_1k)
    df5k = df5k.reindex(gdf1k_pts.index)

    center_lat, center_lon = _center_from_bounds(gdf1k_pts)

    # UFs
    uf_gdf = None
    if uf_shp_path:
        p = Path(uf_shp_path)
        if p.exists():
            uf_gdf = gpd.read_file(p)
    else:
        auto_p = _autofind_uf_shapefile(inputFolder)
        if auto_p:
            uf_gdf = gpd.read_file(auto_p)
    if uf_gdf is not None:
        try:
            uf_gdf = uf_gdf.to_crs(4326)
        except Exception:
            pass

    # Mapa Folium
    m = folium.Map(location=[center_lat, center_lon], zoom_start=4, tiles="OpenStreetMap", control_scale=True)
    folium.TileLayer("cartodbpositron", name="CartoDB Positron").add_to(m)

    # UFs
    if uf_gdf is not None:
        name_col = _pick_uf_name_column(uf_gdf)
        folium.GeoJson(
            uf_gdf,
            name="UFs",
            style_function=lambda f: {"color": "#808080", "weight": 1, "fillColor": "#f8f8f8", "fillOpacity": 0.7},
            tooltip=folium.GeoJsonTooltip(fields=[name_col], aliases=["UF: "], sticky=False) if name_col else None,
        ).add_to(m)

    # Helper para popup de percentuais
    def _percent_table(row):
        lines = []
        for grp in GROUPS:
            v = row.get(f"{grp}_perc")
            if pd.notna(v):
                w = int(max(0, min(100, v)))
                lines.append(
                    f"<tr><td style='padding-right:8px;'>{escape(grp)}</td>"
                    f"<td style='width:90px;'><div style='height:8px;background:{escape(GROUP_COLORS[grp])};width:{w}px;'></div></td>"
                    f"<td style='padding-left:6px;'>{v:.1f}%</td></tr>"
                )
        return "<table>" + "".join(lines) + "</table>"

    # Pontos por predominância (5 km) + popup
    layer_pts = folium.FeatureGroup(name="Estações — composição & predominância (5 km)", show=True).add_to(m)
    for idx, row in gdf1k_pts.iterrows():
        if idx not in df5k.index:
            continue
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        lat, lon = geom.y, geom.x

        grp5 = df5k.loc[idx, "GRUPO_PRED_5k"]
        color = GROUP_COLORS.get(grp5, "#333")

        header = []
        for c in ["UF", "CIDADE", "CD_MUN", "ID_MMA"]:
            if c in gdf1k_pts.columns and pd.notna(row.get(c)):
                header.append(f"<b>{escape(c)}:</b> {escape(str(row.get(c)))}")
        header_html = "<br>".join(header)
        perc_html = _percent_table(df5k.loc[idx])

        html = (
            f"{header_html}"
            f"<br><b>Predominância (5 km):</b> {escape(str(grp5)) if pd.notna(grp5) else '—'}"
            f"<br><b>Composição (5 km):</b><br>{perc_html}"
        )

        folium.CircleMarker(
            location=(lat, lon),
            radius=5,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.9,
            weight=1,
            popup=folium.Popup(html, max_width=420),
            tooltip=f"Predom. 5 km: {grp5}" if pd.notna(grp5) else "Sem predominância",
        ).add_to(layer_pts)

    # Buffers 5 km
    if show_buffer_circles:
        layer_circ = folium.FeatureGroup(name="Buffers 5 km (círculo)", show=False).add_to(m)
        for _, r in gdf1k_pts.iterrows():
            geom = r.geometry
            if geom is None or geom.is_empty:
                continue
            folium.Circle(location=(geom.y, geom.x), radius=5000, color="#111111", weight=1, fill=False, opacity=0.9).add_to(layer_circ)

    if show_buffer_polygons:
        gdf5_poly = gdf_5k.to_crs(4326)[["geometry"]].copy()
        gdf5_poly["geometry"] = gdf5_poly.geometry.simplify(0.0008)
        layer_poly = folium.FeatureGroup(name="Buffers 5 km (polígono)", show=False).add_to(m)
        folium.GeoJson(gdf5_poly, style_function=lambda f: {"color": "#111111", "weight": 1, "fill": False}).add_to(layer_poly)

    MiniMap(toggle_display=True, position="bottomright").add_to(m)
    Fullscreen().add_to(m)
    m.get_root().html.add_child(folium.Element(_folium_categorical_legend("Predominância (5 km) — MapBiomas/2023", GROUP_COLORS)))
    folium.LayerControl(collapsed=False).add_to(m)
    return m

# =========================
# Função: Mapa com buffer variável por estação (usa REP_ESPACIAL em metros)
# =========================

def build_map_varbuf(
    parquet_file: str | Path = None,
    rootPath: str | Path | None = None,
    year: int = 2024,
    pixelSize: int = 30 * 30,
    uf_shp_path: str | Path | None = None,
    show_buffer_circles: bool = True,
    show_buffer_polygons: bool = False,
) -> folium.Map:
    """
    Gera um mapa Folium com predominância/composição de uso do solo,
    calculadas dentro de um buffer variável por estação definido pela coluna
    REP_ESPACIAL (em metros). Usa diretamente o arquivo Parquet com geometria.
    """

    # --- Pastas
    rootPath = Path(rootPath or os.path.dirname(os.getcwd()))
    inputFolder = rootPath / "data"
    mapbiomasFolder = inputFolder / "MAPBIOMAS"

    # --- Caminho padrão do Parquet se não informado
    if parquet_file is None:
        parquet_file = rootPath / "data/rep_espacial/outputs/rep_espacial.parquet"

    # --- Leitura do parquet (já vem com geometria em WKB)
    gdf = gpd.read_parquet(parquet_file)
    
    # Se já for GeoDataFrame com geometria shapely, mantém
    if not isinstance(gdf, gpd.GeoDataFrame):
        gdf = gpd.GeoDataFrame(gdf, geometry="geometry", crs="EPSG:4326")
    else:
        # garante CRS
        gdf = gdf.set_crs("EPSG:4326", allow_override=True)


    # --- Garantir coluna REP_ESPACIAL válida
    if "REP_ESPACIAL" not in gdf.columns:
        raise ValueError("O Parquet deve conter a coluna 'REP_ESPACIAL'.")

    gdf["REP_ESPACIAL"] = pd.to_numeric(gdf["REP_ESPACIAL"], errors="coerce").fillna(1000).astype(int)

    # --- Buffers variáveis
    gdf_m = gdf.to_crs(3857)
    buffers = [geom.buffer(float(dist)) if geom is not None else None
               for geom, dist in zip(gdf_m.geometry, gdf_m["REP_ESPACIAL"])]
    gdf_var = gdf_m.copy()
    gdf_var["geometry"] = buffers
    gdf_var = gdf_var.to_crs(4326)



    # 🔧 FIX: adicionar coluna 'buffer' para compatibilidade com cutMapbiomas
    gdf_var["buffer"] = gdf["REP_ESPACIAL"].astype(int).reindex(gdf_var.index)


    # Salvar buffers variáveis como GeoPackage
    out_buf = OUTPUT_DIR / "buffers_var.gpkg"
    warnings.filterwarnings("ignore", category=UserWarning)
    gdf_var.to_file(out_buf, driver="GPKG")

    # --- Cálculos de uso do solo via MapBiomas
    stats_var = stl.cutMapbiomas(str(mapbiomasFolder), gdf_var, year, "", pixelSize)
    dfv = aggregate_land_use(stats_var, LAND_USE_MAP)

    # Percentuais e predominância
    sums = dfv[GROUPS].sum(axis=1).replace(0, np.nan)
    for g in GROUPS:
        dfv[f"{g}_perc"] = (100 * dfv[g] / sums).round(1)
    dfv["GRUPO_PRED_VAR"] = dfv[GROUPS].idxmax(axis=1)
    dfv.loc[sums.isna(), "GRUPO_PRED_VAR"] = np.nan

    # Salva tabela com resultados
    outVar = dfv.copy()
    outVar.insert(0, "ID", gdf_var.index)
    outVar.to_csv(OUTPUT_DIR / "uso_solo_varbuf.csv", index=False, encoding="utf-8")

    # --- Junta atributos às coordenadas (centróides dos buffers)
    gdf_pts_center = _centroids_in_wgs84(gdf_var)
    cols_keep = GROUPS + [f"{g}_perc" for g in GROUPS] + ["GRUPO_PRED_VAR"]
    gdf_pts_center = gdf_pts_center.join(dfv[cols_keep].reindex(gdf_pts_center.index), how="left")

    center_lat, center_lon = _center_from_bounds(gdf_pts_center)

    # --- UFs (opcional)
    uf_gdf = None
    if uf_shp_path:
        p = Path(uf_shp_path)
        if p.exists():
            uf_gdf = gpd.read_file(p)
    else:
        auto_p = _autofind_uf_shapefile(inputFolder)
        if auto_p:
            uf_gdf = gpd.read_file(auto_p)
    if uf_gdf is not None:
        try:
            uf_gdf = uf_gdf.to_crs(4326)
        except Exception:
            pass

    # --- Mapa Folium
    m = folium.Map(location=[center_lat, center_lon], zoom_start=4, tiles="OpenStreetMap", control_scale=True)
    folium.TileLayer("cartodbpositron", name="CartoDB Positron").add_to(m)

    # UFs
    if uf_gdf is not None:
        name_col = _pick_uf_name_column(uf_gdf)
        folium.GeoJson(
            uf_gdf,
            name="UFs",
            style_function=lambda f: {"color": "#808080", "weight": 1,
                                      "fillColor": "#f8f8f8", "fillOpacity": 0.7},
            tooltip=folium.GeoJsonTooltip(fields=[name_col], aliases=["UF: "], sticky=False)
            if name_col else None,
        ).add_to(m)

    # Helper de popup
    def _percent_table(row):
        lines = []
        for grp in GROUPS:
            v = row.get(f"{grp}_perc")
            if pd.notna(v):
                w = int(max(0, min(100, v)))
                lines.append(
                    f"<tr><td style='padding-right:8px;'>{escape(grp)}</td>"
                    f"<td style='width:90px;'><div style='height:8px;background:{escape(GROUP_COLORS[grp])};width:{w}px;'></div></td>"
                    f"<td style='padding-left:6px;'>{v:.1f}%</td></tr>"
                )
        return "<table>" + "".join(lines) + "</table>"

    # Marcadores
    layer_pts = folium.FeatureGroup(name="Estações — composição & predominância (buffer variável)", show=True).add_to(m)
    for idx, row in gdf_pts_center.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        lat, lon = geom.y, geom.x
        grp = row.get("GRUPO_PRED_VAR")
        color = GROUP_COLORS.get(grp, "#333")

        header = []
        for c in ["UF", "CIDADE", "CD_MUN", "ID_MMA"]:
            if c in gdf_pts_center.columns and pd.notna(row.get(c)):
                header.append(f"<b>{escape(c)}:</b> {escape(str(row.get(c)))}")
        header.append(f"<b>REP_ESPACIAL:</b> {int(row.get('REP_ESPACIAL'))} m")

        html = (
            "<br>".join(header)
            + f"<br><b>Predominância:</b> {escape(str(grp)) if pd.notna(grp) else '—'}"
            + f"<br><b>Composição no buffer:</b><br>{_percent_table(row)}"
        )

        folium.CircleMarker(
            location=(lat, lon),
            radius=5,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.9,
            weight=1,
            popup=folium.Popup(html, max_width=420),
            tooltip=f"Predom.: {grp}" if pd.notna(grp) else "Sem predominância",
        ).add_to(layer_pts)

    # Círculos proporcionais
    if show_buffer_circles:
        layer_circ = folium.FeatureGroup(name="Buffers variáveis (círculo)", show=False).add_to(m)
        for _, r in gdf_pts_center.iterrows():
            geom = r.geometry
            if geom is None or geom.is_empty:
                continue
            folium.Circle(
                location=(geom.y, geom.x),
                radius=float(r["REP_ESPACIAL"]),
                color="#222222",
                weight=1,
                fill=False,
                opacity=0.9
            ).add_to(layer_circ)

    # Polígonos reais
    if show_buffer_polygons:
        gdf_poly = gdf_var.to_crs(4326)[["geometry"]].copy()
        gdf_poly["geometry"] = gdf_poly.geometry.simplify(0.0008)
        layer_poly = folium.FeatureGroup(name="Buffers variáveis (polígono)", show=False).add_to(m)
        folium.GeoJson(gdf_poly, style_function=lambda f: {"color": "#222222", "weight": 1, "fill": False}).add_to(layer_poly)

    MiniMap(toggle_display=True, position="bottomright").add_to(m)
    Fullscreen().add_to(m)
    m.get_root().html.add_child(
        folium.Element(_folium_categorical_legend("Predominância — buffer variável (MapBiomas/2023)", GROUP_COLORS))
    )
    folium.LayerControl(collapsed=False).add_to(m)
    return m
'''
'''

def build_map_varbuf(
    file: str = "/home/nobre/Notebooks/RQAR_2025_book/data/rep_espacial/outputs/rep_espacial.csv",
    rootPath: str | Path | None = None,
    year: int = 2024,
    pixelSize: int = 30 * 30,
    uf_shp_path: str | Path | None = None,
    show_buffer_circles: bool = True,
    show_buffer_polygons: bool = False,
) -> folium.Map:
    """
    Gera um mapa Folium com buffers variáveis definidos por REP_ESPACIAL (m).
    Mostra camadas por poluente e também uma camada geral "Todas as estações"
    onde cada estação mostra todos os poluentes no popup.
    """
    # Pastas
    rootPath = Path(rootPath or os.path.dirname(os.getcwd()))
    inputFolder = rootPath / "data"
    mapbiomasFolder = inputFolder / "MAPBIOMAS"

    # --- Leitura do CSV
    df = pd.read_csv(file)
    if "LONGITUDE" not in df.columns or "LATITUDE" not in df.columns:
        raise ValueError("O arquivo deve conter as colunas 'LONGITUDE' e 'LATITUDE'.")
    if "REP_ESPACIAL" not in df.columns:
        raise ValueError("O arquivo deve conter a coluna 'REP_ESPACIAL'.")

    # GDF de pontos
    geom_pts = gpd.points_from_xy(df["LONGITUDE"], df["LATITUDE"])
    gdf_pts = gpd.GeoDataFrame(df.copy(), geometry=geom_pts, crs="EPSG:4326")

    # Buffers variáveis
    gdf_m = gdf_pts.to_crs(3857)
    buffers = [geom.buffer(dist) if geom is not None else None
               for geom, dist in zip(gdf_m.geometry, gdf_m["REP_ESPACIAL"])]
    gdf_var = gpd.GeoDataFrame(
        gdf_pts.drop(columns="geometry").copy(),
        geometry=gpd.GeoSeries(buffers, index=gdf_pts.index, crs=gdf_m.crs)
    ).to_crs(4326)

    # Uso do solo (MapBiomas)
    stats_var = stl.cutMapbiomas(str(mapbiomasFolder), gdf_var, year, "", pixelSize)
    dfv = aggregate_land_use(stats_var, LAND_USE_MAP)

    # Percentuais e predominância
    sums = dfv[GROUPS].sum(axis=1).replace(0, np.nan)
    for g in GROUPS:
        dfv[f"{g}_perc"] = (100 * dfv[g] / sums).round(1)
    dfv["GRUPO_PRED_VAR"] = dfv[GROUPS].idxmax(axis=1)
    dfv.loc[sums.isna(), "GRUPO_PRED_VAR"] = np.nan

    # Junta atributos
    gdf_pts_center = _centroids_in_wgs84(gdf_var)
    cols_keep = GROUPS + [f"{g}_perc" for g in GROUPS] + ["GRUPO_PRED_VAR"]
    gdf_pts_center = gdf_pts_center.join(dfv[cols_keep].reindex(gdf_pts_center.index), how="left")


    center_lat, center_lon = _center_from_bounds(gdf_pts_center)

    # --- UFs
    uf_gdf = None
    if uf_shp_path:
        p = Path(uf_shp_path)
        if p.exists():
            uf_gdf = gpd.read_file(p)
    else:
        auto_p = _autofind_uf_shapefile(inputFolder)
        if auto_p:
            uf_gdf = gpd.read_file(auto_p)
    if uf_gdf is not None:
        try:
            uf_gdf = uf_gdf.to_crs(4326)
        except Exception:
            pass

    # --- Mapa base
    m = folium.Map(location=[center_lat, center_lon], zoom_start=4, tiles="OpenStreetMap", control_scale=True)
    folium.TileLayer("cartodbpositron", name="CartoDB Positron").add_to(m)

    if uf_gdf is not None:
        name_col = _pick_uf_name_column(uf_gdf)
        folium.GeoJson(
            uf_gdf,
            name="UFs",
            style_function=lambda f: {"color": "#808080", "weight": 1, "fillColor": "#f8f8f8", "fillOpacity": 0.7},
            tooltip=folium.GeoJsonTooltip(fields=[name_col], aliases=["UF: "], sticky=False) if name_col else None,
        ).add_to(m)

    # Helper de popup (percentuais)
    def _percent_table(row):
        lines = []
        for grp in GROUPS:
            v = row.get(f"{grp}_perc")
            if pd.notna(v):
                w = int(max(0, min(100, v)))
                lines.append(
                    f"<tr><td style='padding-right:8px;'>{escape(grp)}</td>"
                    f"<td style='width:90px;'><div style='height:8px;background:{escape(GROUP_COLORS[grp])};width:{w}px;'></div></td>"
                    f"<td style='padding-left:6px;'>{v:.1f}%</td></tr>"
                )
        return "<table>" + "".join(lines) + "</table>"

    # ========================
    # Camada geral (todas as estações)
    # ========================
    layer_all = folium.FeatureGroup(name="Todas as estações", show=True).add_to(m)
    for station_id, group in gdf_pts_center.groupby("ID_OEMA"):
        row0 = group.iloc[0]
        geom = row0.geometry
        if geom is None or geom.is_empty:
            continue
        lat, lon = geom.y, geom.x

        # Cabeçalho da estação
        header = []
        for c in ["UF", "CIDADE", "CD_MUN", "ID_OEMA", "REP_ESPACIAL"]:
            if c in row0 and pd.notna(row0.get(c)):
                header.append(f"<b>{escape(c)}:</b> {escape(str(row0.get(c)))}")
        header_html = "<br>".join(header)

        # Lista de todos os poluentes da estação
        pol_tables = []
        for _, r in group.iterrows():
            pol = r.get("POLUENTE", "—")
            grp = r.get("GRUPO_PRED_VAR")
            perc_html = _percent_table(r)
            pol_tables.append(
                f"<b>Poluente:</b> {escape(str(pol))}"
                f"<br><b>Predominância:</b> {escape(str(grp)) if pd.notna(grp) else '—'}"
                f"<br><b>Composição:</b><br>{perc_html}<br>"
            )
        all_pols_html = "<hr>".join(pol_tables)

        html = f"{header_html}<br>{all_pols_html}"

        folium.CircleMarker(
            location=(lat, lon),
            radius=6,
            color="#000",
            fill=True,
            fill_color="#555",
            fill_opacity=0.8,
            weight=1,
            popup=folium.Popup(html, max_width=450),
            tooltip=f"Estação {station_id} — {len(group)} poluentes"
        ).add_to(layer_all)

    # ========================
    # Camadas por poluente
    # ========================
    unique_pols = gdf_pts_center["POLUENTE"].dropna().unique()
    for pol in unique_pols:
        layer_pol = folium.FeatureGroup(name=f"Poluente: {pol}", show=False).add_to(m)
        sub = gdf_pts_center[gdf_pts_center["POLUENTE"] == pol]
        for _, row in sub.iterrows():
            geom = row.geometry
            if geom is None or geom.is_empty:
                continue
            lat, lon = geom.y, geom.x
            grp = row.get("GRUPO_PRED_VAR")
            color = GROUP_COLORS.get(grp, "#333")
            header = []
            for c in ["UF", "CIDADE", "CD_MUN", "ID_OEMA", "REP_ESPACIAL"]:
                if c in row and pd.notna(row.get(c)):
                    header.append(f"<b>{escape(c)}:</b> {escape(str(row.get(c)))}")
            header_html = "<br>".join(header)
            perc_html = _percent_table(row)
            html = (
                f"{header_html}"
                f"<br><b>Poluente:</b> {escape(str(pol))}"
                f"<br><b>Predominância:</b> {escape(str(grp)) if pd.notna(grp) else '—'}"
                f"<br><b>Composição:</b><br>{perc_html}"
            )
            folium.CircleMarker(
                location=(lat, lon),
                radius=6,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.9,
                weight=1,
                popup=folium.Popup(html, max_width=450),
                tooltip=f"{pol} — Predom.: {grp}" if pd.notna(grp) else f"{pol} — sem predominância",
            ).add_to(layer_pol)

    # Buffers (círculos e polígonos)
    if show_buffer_circles:
        layer_circ = folium.FeatureGroup(name="Buffers variáveis (círculo)", show=False).add_to(m)
        for _, r in gdf_pts_center.iterrows():
            geom = r.geometry
            if geom is None or geom.is_empty:
                continue
            folium.Circle(
                location=(geom.y, geom.x),
                radius=float(r["REP_ESPACIAL"]),
                color="#222222",
                weight=1,
                fill=False,
                opacity=0.9
            ).add_to(layer_circ)

    if show_buffer_polygons:
        gdf_poly = gdf_var.to_crs(4326)[["geometry"]].copy()
        gdf_poly["geometry"] = gdf_poly.geometry.simplify(0.0008)
        layer_poly = folium.FeatureGroup(name="Buffers variáveis (polígono)", show=False).add_to(m)
        folium.GeoJson(gdf_poly, style_function=lambda f: {"color": "#222222", "weight": 1, "fill": False}).add_to(layer_poly)

    MiniMap(toggle_display=True, position="bottomright").add_to(m)
    Fullscreen().add_to(m)
    m.get_root().html.add_child(
        folium.Element(_folium_categorical_legend("Predominância — buffer variável (MapBiomas/2023)", GROUP_COLORS))
    )
    folium.LayerControl(collapsed=False).add_to(m)
    return m
'''
def build_map_varbuf(
    file: str = "rep_espacial/outputs/rep_espacial.csv",
    rootPath: str | Path | None = None,
    year: int = 2024,
    pixelSize: int = 30 * 30,
    uf_shp_path: str | Path | None = None,
    show_buffer_circles: bool = True,
    show_buffer_polygons: bool = True,
) -> folium.Map:
    """
    Lê CSV (rep_espacial) com LATITUDE/LONGITUDE e colunas POLUENTE/REP_ESPACIAL,
    calcula uso do solo por buffer, cria:
      - camada "Todos os buffers" (polígonos coloridos pela predominância),
      - camadas por poluente,
      - camada "Todas as estações" (um marcador por estação com tabela de TODOS os poluentes).
    """

    # Pastas
    rootPath = Path(rootPath or os.path.dirname(os.getcwd()))
    inputFolder = rootPath / "data"
    mapbiomasFolder = inputFolder / "MAPBIOMAS"

    # Caminho do CSV (aceita absoluto também)
    p = Path(file)
    station_csv = p if p.exists() else (inputFolder / file)

    # --- Leitura das estações (como pontos WGS84)
    df = pd.read_csv(station_csv)

    # Campos mínimos
    for col in ["LATITUDE", "LONGITUDE", "POLUENTE"]:
        if col not in df.columns:
            raise ValueError(f"Coluna obrigatória ausente no CSV: {col}")

    # ID de agrupamento da estação
    group_key = "ID_OEMA" if "ID_OEMA" in df.columns else ("ID_MMA" if "ID_MMA" in df.columns else None)
    if group_key is None:
        # Sem ID de estação? crio um fake por coordenada
        df["_latr"] = pd.to_numeric(df["LATITUDE"], errors="coerce").round(5)
        df["_lonr"] = pd.to_numeric(df["LONGITUDE"], errors="coerce").round(5)
        group_key = "_station_id"
        df[group_key] = df["_latr"].astype(str) + "_" + df["_lonr"].astype(str)
        df.drop(columns=["_latr", "_lonr"], inplace=True)

    # Garantir REP_ESPACIAL numérico (sem inventar; só usa o que veio)
    if "REP_ESPACIAL" not in df.columns:
        raise ValueError("O CSV deve conter a coluna 'REP_ESPACIAL' (raio do buffer em metros).")
    df["REP_ESPACIAL"] = pd.to_numeric(df["REP_ESPACIAL"], errors="coerce")

    # GeoDataFrame de pontos
    geom_pts = gpd.points_from_xy(df["LONGITUDE"], df["LATITUDE"])
    gdf_pts = gpd.GeoDataFrame(df.copy(), geometry=geom_pts, crs="EPSG:4326")

    # --- Gera buffers variáveis em CRS métrico e volta para WGS84
    gdf_m = gdf_pts.to_crs(3857)  # métrico
    # buffer por linha (pode haver NaN em REP_ESPACIAL → ignora nesses)
    buffers = [
        (geom.buffer(float(dist)) if (geom is not None and pd.notna(dist) and dist > 0) else None)
        for geom, dist in zip(gdf_m.geometry, gdf_m["REP_ESPACIAL"])
    ]
    gdf_var = gdf_m.copy()
    gdf_var["geometry"] = buffers
    gdf_var = gdf_var.to_crs(4326)

    # Coluna 'buffer' (compatibilidade com cutMapbiomas)
    gdf_var["buffer"] = gdf_pts["REP_ESPACIAL"].reindex(gdf_var.index)

    # Remover linhas sem geometria (REP_ESPACIAL vazio ou inválido)
    gdf_var = gdf_var[~gdf_var.geometry.isna()].copy()

    # --- Uso do solo via MapBiomas
    stats_var = stl.cutMapbiomas(str(mapbiomasFolder), gdf_var, year, "", pixelSize)
    dfv = aggregate_land_use(stats_var, LAND_USE_MAP)

    # Percentuais e predominância
    sums = dfv[GROUPS].sum(axis=1).replace(0, np.nan)
    for g in GROUPS:
        dfv[f"{g}_perc"] = (100 * dfv[g] / sums).round(1)
    dfv["GRUPO_PRED_VAR"] = dfv.apply(lambda r: predominant_group(r, GROUPS), axis=1)
    dfv.loc[sums.isna(), "GRUPO_PRED_VAR"] = np.nan

    # Junta resultados de uso do solo de volta no GDF (mesmo índice)
    cols_use = GROUPS + [f"{g}_perc" for g in GROUPS] + ["GRUPO_PRED_VAR"]
    gdf_var = gdf_var.join(dfv[cols_use], how="left")

    # --- Centróides dos buffers para posicionar marcadores
    gdf_pts_center = _centroids_in_wgs84(gdf_var)

    center_lat, center_lon = _center_from_bounds(gdf_pts_center)

    # --- UFs (opcional)
    uf_gdf = None
    if uf_shp_path:
        pshp = Path(uf_shp_path)
        if pshp.exists():
            uf_gdf = gpd.read_file(pshp)
    else:
        auto_p = _autofind_uf_shapefile(inputFolder)
        if auto_p:
            uf_gdf = gpd.read_file(auto_p)
    if uf_gdf is not None:
        try:
            uf_gdf = uf_gdf.to_crs(4326)
        except Exception:
            pass

    # --- Mapa base com limites do Brasil
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=4,
        tiles="OpenStreetMap",
        control_scale=True,
        max_bounds=True
    )
    folium.TileLayer("cartodbpositron", name="CartoDB Positron").add_to(m)
    
    # Limites aproximados do Brasil (WGS84)
    br_bounds = [[-34.0, -74.0], [6.0, -34.0]]  # [sul-oeste, norte-leste]
    m.fit_bounds(br_bounds)
    m.options['maxBounds'] = br_bounds
    m.options['maxBoundsViscosity'] = 1.0  # impede de arrastar para fora
    m.options['minZoom'] = 4  # trava o zoom out além do Brasil


    # UFs
    if uf_gdf is not None:
        name_col = _pick_uf_name_column(uf_gdf)
        folium.GeoJson(
            uf_gdf,
            name="UFs",
            style_function=lambda f: {"color": "#808080", "weight": 1, "fillColor": "#f8f8f8", "fillOpacity": 0.7},
            tooltip=folium.GeoJsonTooltip(fields=[name_col], aliases=["UF: "], sticky=False) if name_col else None,
        ).add_to(m)

    # --- Helper: barra de percentuais
    def _percent_table(row):
        lines = []
        for grp in GROUPS:
            v = row.get(f"{grp}_perc")
            if pd.notna(v):
                w = int(max(0, min(100, v)))
                lines.append(
                    f"<tr><td style='padding-right:8px;'>{escape(grp)}</td>"
                    f"<td style='width:90px;'><div style='height:8px;background:{escape(GROUP_COLORS[grp])};width:{w}px;'></div></td>"
                    f"<td style='padding-left:6px;'>{v:.1f}%</td></tr>"
                )
        return "<table>" + "".join(lines) + "</table>"

    # --- Layer: Todos os buffers (polígonos com cor da predominância)
    if show_buffer_polygons:
        layer_poly_all = folium.FeatureGroup(name="Todos os buffers (polígonos)", show=False).add_to(m)

        def _poly_style(feat):
            pred = feat["properties"].get("GRUPO_PRED_VAR")
            color = GROUP_COLORS.get(pred, "#444444")
            return {"color": color, "weight": 1, "fillColor": color, "fillOpacity": 0.25}

        folium.GeoJson(
            gdf_var[["geometry", "GRUPO_PRED_VAR"]],
            style_function=_poly_style,
            tooltip=folium.GeoJsonTooltip(fields=["GRUPO_PRED_VAR"], aliases=["Predominância:"], sticky=False),
        ).add_to(layer_poly_all)

    # --- Layer: círculos proporcionais (raio = REP_ESPACIAL)
    if show_buffer_circles:
        layer_circ = folium.FeatureGroup(name="Buffers variáveis (círculo)", show=False).add_to(m)
        for _, r in gdf_pts_center.iterrows():
            geom = r.geometry
            if geom is None or geom.is_empty or pd.isna(r.get("REP_ESPACIAL")):
                continue
            folium.Circle(
                location=(geom.y, geom.x),
                radius=float(r["REP_ESPACIAL"]),
                color="#222222",
                weight=1,
                fill=False,
                opacity=0.9
            ).add_to(layer_circ)

    # --- Layers por poluente
    pols = sorted([p for p in gdf_pts_center["POLUENTE"].dropna().unique()])
    layer_by_pol = {}
    for pol in pols:
        layer_by_pol[pol] = folium.FeatureGroup(name=f"Poluente: {pol}", show=False).add_to(m)

    # --- Layer: Todas as estações (um ponto por estação, popup com TODOS os poluentes daquela estação)
    layer_all = folium.FeatureGroup(name="Todas as estações (tabela completa)", show=True).add_to(m)

    # função para escolher a "melhor" linha por poluente (garantir REP_ESPACIAL e predominância)
    def _pick_best_row(subdf: pd.DataFrame) -> pd.Series:
        sub = subdf.copy()
        sub["_score"] = sub["REP_ESPACIAL"].notna().astype(int) + sub["GRUPO_PRED_VAR"].notna().astype(int)
        sub = sub.sort_values(["_score"], ascending=False)
        return sub.iloc[0]

    # Um marcador por estação
    for sid, group in gdf_pts_center.groupby(group_key):
        # posição do ponto: pego o primeiro com geometria válida
        g0 = group[~group.geometry.is_empty].iloc[0]
        lat, lon = g0.geometry.y, g0.geometry.x

        # cabeçalho
        header = []
        for c in ["UF", "CIDADE", group_key]:
            if c in group.columns and pd.notna(g0.get(c)):
                alias = "ID" if c == group_key else c.capitalize()
                header.append(f"<b>{escape(alias)}:</b> {escape(str(g0.get(c)))}")
        header_html = "<br>".join(header)

        # tabela: uma linha por POLUENTE (com REP_ESPACIAL correto)
        rows = []
        for pol in sorted(group["POLUENTE"].dropna().unique()):
            sub = group[group["POLUENTE"] == pol]
            r = _pick_best_row(sub)
            rep = r.get("REP_ESPACIAL")
            rep_txt = f"{int(rep)} m" if pd.notna(rep) else "—"
            pred = r.get("GRUPO_PRED_VAR", "—")
            color = GROUP_COLORS.get(pred, "#333")
            comp = _percent_table(r)
            rows.append(
                f"<tr>"
                f"<td>{escape(str(pol))}</td>"
                f"<td>{rep_txt}</td>"
                f"<td style='color:{color};font-weight:bold'>{escape(str(pred))}</td>"
                f"<td>{comp}</td>"
                f"</tr>"
            )

        table_html = (
            "<table border='1' style='border-collapse:collapse;font-size:11px;'>"
            "<tr><th>Poluente</th><th>Buffer</th><th>Predom.</th><th>Composição</th></tr>"
            + "".join(rows) + "</table>"
        )

        html = header_html + "<br>" + table_html

        folium.CircleMarker(
            location=(lat, lon),
            radius=5,
            color="#444444",
            fill=True,
            fill_color="#444444",
            fill_opacity=0.9,
            weight=1,
            popup=folium.Popup(html, max_width=520),
            tooltip=f"Estação: {sid}",
        ).add_to(layer_all)

    # --- Marcadores nas camadas por poluente (um ponto por registro)
    for _, row in gdf_pts_center.iterrows():
        pol = row.get("POLUENTE")
        if pd.isna(pol) or pol not in layer_by_pol:
            continue
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        lat, lon = geom.y, geom.x
        pred = row.get("GRUPO_PRED_VAR")
        color = GROUP_COLORS.get(pred, "#333")

        # popup simples da linha
        rep = row.get("REP_ESPACIAL")
        rep_txt = f"{int(rep)} m" if pd.notna(rep) else "—"
        comp = _percent_table(row)
        header = []
        for c in ["UF", "CIDADE", group_key]:
            if c in gdf_pts_center.columns and pd.notna(row.get(c)):
                alias = "ID" if c == group_key else c.capitalize()
                header.append(f"<b>{escape(alias)}:</b> {escape(str(row.get(c)))}")
        header.append(f"<b>Poluente:</b> {escape(str(pol))}")
        header.append(f"<b>Buffer:</b> {rep_txt}")
        html = "<br>".join(header) + f"<br><b>Predominância:</b> {escape(str(pred)) if pd.notna(pred) else '—'}" \
               + f"<br><b>Composição:</b><br>{comp}"

        folium.CircleMarker(
            location=(lat, lon),
            radius=5,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.9,
            weight=1,
            popup=folium.Popup(html, max_width=520),
            tooltip=f"{pol} — Predom.: {pred}" if pd.notna(pred) else f"{pol}",
        ).add_to(layer_by_pol[pol])

    MiniMap(toggle_display=True, position="bottomright").add_to(m)
    Fullscreen().add_to(m)
    m.get_root().html.add_child(
        folium.Element(_folium_categorical_legend("Predominância — buffers (MapBiomas)", GROUP_COLORS))
    )
    folium.LayerControl(collapsed=False).add_to(m)
    return m











# =========================
# Execução direta (teste)
# =========================
if __name__ == "__main__":
    # Teste rápido: gera mapas e salva HTMLs locais (opcional)
#   m1 = build_map_1k()
#    m1.save("figura8_interativo.html")
#    m2 = build_map_5k()
#    m2.save("figura9_interativo.html")
    m_var = build_map_varbuf()  # usa REP_ESPACIAL do CSV; se não existir, cria sintética 100–5000 m
#    m_var.save("figura_buffer_variavel.html")
    print("Mapa com buffer variável salvo como figura_buffer_variavel.html")
    print("Mapas salvos para inspeção local.")
