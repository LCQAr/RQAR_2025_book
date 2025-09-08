# -*- coding: utf-8 -*-

from __future__ import annotations
import os
from pathlib import Path
from html import escape

import numpy as np
import pandas as pd
pd.set_option('future.no_silent_downcasting', True)
import geopandas as gpd
import folium
from folium.plugins import MiniMap, Fullscreen

# Dependências do seu repositório
import scripts.stationsLandUse as stl  # stationBuffers, cutMapbiomas, stationUnionByUF

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
    file: str = "Monitoramento_QAr_BR.csv",
    rootPath: str | Path | None = None,
    year: int = 2024,
    pixelSize: int = 30 * 30,
    uf_shp_path: str | Path | None = None,
    rep_min_m: int = 100,
    rep_max_m: int = 5000,
    show_buffer_circles: bool = True,
    show_buffer_polygons: bool = False,
    seed: int = 42,
) -> folium.Map:
    """
    Gera um mapa Folium com predominância/c composição de uso do solo,
    calculadas dentro de um buffer variável por estação definido pela coluna
    REP_ESPACIAL (em metros). Se a coluna não existir, cria-se uma coluna
    sintética (determinística) no intervalo [rep_min_m, rep_max_m] para teste.
    """
    # Pastas
    rootPath = Path(rootPath or os.path.dirname(os.getcwd()))
    inputFolder = rootPath / "data"
    mapbiomasFolder = inputFolder / "MAPBIOMAS"
    station_csv = inputFolder / file

    # --- Leitura das estações (como pontos WGS84)
    df = pd.read_csv(station_csv)
    if "LONGITUDE" not in df.columns or "LATITUDE" not in df.columns:
        raise ValueError("O CSV de estações deve conter as colunas 'LONGITUDE' e 'LATITUDE'.")

    # Garante/Cria REP_ESPACIAL (m)
    if "REP_ESPACIAL" in df.columns:
        rep_raw = pd.to_numeric(df["REP_ESPACIAL"], errors="coerce")
    else:
        rep_raw = pd.Series(np.nan, index=df.index, dtype="float64")

    valid = rep_raw.notna() & (rep_raw > 0)

    rng = np.random.RandomState(seed)  # determinístico
    synth = pd.Series(rng.uniform(rep_min_m, rep_max_m, size=len(df))).round(0)

    rep = pd.Series(np.nan, index=df.index, dtype="float64")
    rep.loc[valid] = rep_raw.loc[valid].clip(lower=rep_min_m, upper=rep_max_m)
    rep.loc[~valid] = synth.loc[~valid]

    df["REP_ESPACIAL"] = rep.astype(int)
    # --- DEDUPLICAÇÃO DE ESTAÇÕES ---
    # Tente deduplicar por ID; se não houver, deduplica por coordenadas
    id_cols = [c for c in ["ID_MMA", "COD_ESTACAO", "ID_ESTACAO", "ESTACAO_ID"] if c in df.columns]
    if id_cols:
        # mantém a linha com maior REP_ESPACIAL para cada estação
        df = (df.sort_values("REP_ESPACIAL", ascending=False)
                .drop_duplicates(subset=id_cols, keep="first")
                .reset_index(drop=True))
    else:
        # dedup por coordenadas (arredonda p/ evitar ruído de casas decimais)
        df["_latr"] = pd.to_numeric(df["LATITUDE"], errors="coerce").round(5)
        df["_lonr"] = pd.to_numeric(df["LONGITUDE"], errors="coerce").round(5)
        df = (df.sort_values("REP_ESPACIAL", ascending=False)
                .drop_duplicates(subset=["_latr", "_lonr"], keep="first")
                .drop(columns=["_latr", "_lonr"])
                .reset_index(drop=True))


    # GeoDataFrame de pontos
    geom_pts = gpd.points_from_xy(df["LONGITUDE"], df["LATITUDE"])
    gdf_pts = gpd.GeoDataFrame(df.copy(), geometry=geom_pts, crs="EPSG:4326")

    # --- Gera buffers variáveis em CRS métrico e volta para WGS84
    gdf_m = gdf_pts.to_crs(3857)  # métrico
    # buffer por linha (distância em metros vinda de REP_ESPACIAL)
    buffers = [geom.buffer(dist) if geom is not None else None
               for geom, dist in zip(gdf_m.geometry, gdf_m["REP_ESPACIAL"])]
    gdf_var = gpd.GeoDataFrame(gdf_pts.drop(columns="geometry").copy(),
                               geometry=gpd.GeoSeries(buffers, index=gdf_pts.index, crs=gdf_m.crs)).to_crs(4326)

    if "buffer" not in gdf_var.columns:
        gdf_var["buffer"] = gdf_pts["REP_ESPACIAL"].astype(int).reindex(gdf_var.index)

    # --- Cálculos de uso do solo via MapBiomas dentro dos buffers variáveis
    stats_var = stl.cutMapbiomas(str(mapbiomasFolder), gdf_var, year, "", pixelSize)
    dfv = aggregate_land_use(stats_var, LAND_USE_MAP)

    # Percentuais e predominância
    sums = dfv[GROUPS].sum(axis=1).replace(0, np.nan)
    for g in GROUPS:
        dfv[f"{g}_perc"] = (100 * dfv[g] / sums).round(1)
    dfv["GRUPO_PRED_VAR"] = dfv[GROUPS].idxmax(axis=1)
    dfv.loc[sums.isna(), "GRUPO_PRED_VAR"] = np.nan

    # Junta atributos às coordenadas (centróides corretos para posicionar os marcadores)
    gdf_pts_center = _centroids_in_wgs84(gdf_var)  # usa centróide do buffer
    cols_keep = (GROUPS
                 + [f"{g}_perc" for g in GROUPS]
                 + ["GRUPO_PRED_VAR"])
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

    # Desenho das UFs
    if uf_gdf is not None:
        name_col = _pick_uf_name_column(uf_gdf)
        folium.GeoJson(
            uf_gdf,
            name="UFs",
            style_function=lambda f: {"color": "#808080", "weight": 1, "fillColor": "#f8f8f8", "fillOpacity": 0.7},
            tooltip=folium.GeoJsonTooltip(fields=[name_col], aliases=["UF: "], sticky=False) if name_col else None,
        ).add_to(m)

    # Helper de popup (tabela de percentuais)
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

    # Marcadores por predominância no buffer variável
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
        header_html = "<br>".join(header)

        perc_html = _percent_table(row)
        html = (
            f"{header_html}"
            f"<br><b>Predominância:</b> {escape(str(grp)) if pd.notna(grp) else '—'}"
            f"<br><b>Composição no buffer:</b><br>{perc_html}"
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

    # Camada com círculos (raio = REP_ESPACIAL)
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

    # Camada com polígonos (buffers reais)
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

# =========================
# Execução direta (teste)
# =========================
if __name__ == "__main__":
    # Teste rápido: gera mapas e salva HTMLs locais (opcional)
    m1 = build_map_1k()
#    m1.save("figura8_interativo.html")
    m2 = build_map_5k()
#    m2.save("figura9_interativo.html")
    m_var = build_map_varbuf()  # usa REP_ESPACIAL do CSV; se não existir, cria sintética 100–5000 m
#    m_var.save("figura_buffer_variavel.html")
    print("Mapa com buffer variável salvo como figura_buffer_variavel.html")
    print("Mapas salvos para inspeção local.")
