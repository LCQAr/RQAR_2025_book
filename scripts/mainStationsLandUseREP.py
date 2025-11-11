# -*- coding: utf-8 -*-
"""
Mapa: Buffers variáveis com uso do solo (MapBiomas)
- Cria camadas por poluente e camadas gerais com buffers e pontos.
- Gera tabela detalhada de composição percentual de uso do solo.
"""

from __future__ import annotations

import os
import logging
from html import escape
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import folium
from folium.plugins import MiniMap, Fullscreen

# Dependências do repositório
import scripts.stationsLandUse as stl

pd.set_option('future.no_silent_downcasting', True)
logging.getLogger("pyogrio._io").setLevel(logging.ERROR)

# =========================
# Configs e constantes
# =========================
rootPath = Path(os.path.dirname(os.getcwd()))
OUTPUT_DIR = Path(rootPath / "data/outputs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

LAND_USE_MAP = {
    "Floresta":     ["1", "3", "4", "5", "6", "49"],
    "Herbácea":     ["10", "11", "12", "32", "29", "50"],
    "Agropecuária": ["14", "15", "18", "19", "39", "20", "40", "62", "41",
                     "36", "46", "47", "35", "48", "9", "21"],
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
# Helpers
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
    vals = pd.to_numeric(row[groups].infer_objects(copy=False), errors='coerce')
    vals = vals.fillna(0.0).astype('float64')
    return vals.idxmax() if float(vals.sum()) > 0 else np.nan


def _percent_table(row, groups=GROUPS):
    """Percentuais simples em texto (não usado agora)."""
    parts = []
    for g in groups:
        val = row.get(f"{g}_perc", None)
        if val is not None and not pd.isna(val):
            parts.append(f"{g}: {val:.1f}%")
    return "<br>".join(parts)


def _percent_bar_table(row):
    """Tabela HTML com barrinhas coloridas por grupo de uso do solo"""
    lines = []
    for grp in GROUPS:
        v = row.get(f"{grp}_perc")
        if pd.notna(v):
            w = int(max(0, min(100, v)))  # largura proporcional
            lines.append(
                f"<tr>"
                f"<td style='padding-right:6px;'>{escape(grp)}</td>"
                f"<td style='width:100px;'>"
                f"<div style='height:8px;background:{escape(GROUP_COLORS[grp])};width:{w}px;'></div>"
                f"</td>"
                f"<td style='padding-left:6px;'>{v:.1f}%</td>"
                f"</tr>"
            )
    return "<table>" + "".join(lines) + "</table>"


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
    CRS_METRIC = "EPSG:5880"  # SIRGAS 2000 / Brazil Albers Equal Area
    try:
        gdf_metric = gdf_ll.to_crs(CRS_METRIC)
    except Exception:
        gdf_metric = gdf_ll.to_crs(3857)
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
# Função principal
# =========================
def build_map_varbuf(
    file: str = "/home/nobre/Notebooks/RQAR_2025_book/scripts/rep_espacial/09_formatar_e_salvar_outputs/outputs/rep_espacial.csv",
    rootPath: str | Path | None = None,
    year: int = 2024,
    pixelSize: int = 30 * 30,
    uf_shp_path: str | Path | None = None,
    show_buffer_circles: bool = True,
    show_buffer_polygons: bool = True,
    save: bool = False,
    save_path: str | Path | None = None,
) -> folium.Map:

    """
    Lê CSV (rep_espacial) com LATITUDE/LONGITUDE e colunas POLUENTE/REP_ESPACIAL,
    calcula uso do solo por buffer e cria camadas no mapa:
      - camada "Todos os buffers" (polígonos coloridos pela predominância),
      - camadas por poluente (círculos reais do tamanho do buffer),
      - camada "Todas as estações" (um marcador pequeno por estação com tabela de TODOS os poluentes).
    """
    # =====================
    # Preparação de dados
    # =====================
    rootPath = Path(rootPath or os.path.dirname(os.getcwd()))
    inputFolder = rootPath / "data"
    mapbiomasFolder = inputFolder / "MAPBIOMAS"

    p = Path(file)
    station_csv = p if p.exists() else (inputFolder / file)
    df = pd.read_csv(station_csv)

    for col in ["LATITUDE", "LONGITUDE", "POLUENTE"]:
        if col not in df.columns:
            raise ValueError(f"Coluna obrigatória ausente no CSV: {col}")

    group_key = "ID_OEMA" if "ID_OEMA" in df.columns else ("ID_MMA" if "ID_MMA" in df.columns else None)
    if group_key is None:
        df["_latr"] = pd.to_numeric(df["LATITUDE"], errors="coerce").round(5)
        df["_lonr"] = pd.to_numeric(df["LONGITUDE"], errors="coerce").round(5)
        group_key = "_station_id"
        df[group_key] = df["_latr"].astype(str) + "_" + df["_lonr"].astype(str)
        df.drop(columns=["_latr", "_lonr"], inplace=True)

    if "REP_ESPACIAL" not in df.columns:
        raise ValueError("O CSV deve conter a coluna 'REP_ESPACIAL'.")
    df["REP_ESPACIAL"] = pd.to_numeric(df["REP_ESPACIAL"], errors="coerce")

    geom_pts = gpd.points_from_xy(df["LONGITUDE"], df["LATITUDE"])
    gdf_pts = gpd.GeoDataFrame(df.copy(), geometry=geom_pts, crs="EPSG:4326")

    gdf_m = gdf_pts.to_crs(3857)
    buffers = [
        (geom.buffer(float(dist)) if (geom is not None and pd.notna(dist) and dist > 0) else None)
        for geom, dist in zip(gdf_m.geometry, gdf_m["REP_ESPACIAL"])
    ]
    gdf_var = gdf_m.copy()
    gdf_var["geometry"] = buffers
    gdf_var = gdf_var.to_crs(4326)
    gdf_var["buffer"] = gdf_pts["REP_ESPACIAL"].reindex(gdf_var.index)
    gdf_var = gdf_var[~gdf_var.geometry.isna()].copy()

    stats_var = stl.cutMapbiomas(str(mapbiomasFolder), gdf_var, year, "", pixelSize)
    dfv = aggregate_land_use(stats_var, LAND_USE_MAP)

    sums = dfv[GROUPS].sum(axis=1).replace(0, np.nan)
    for g in GROUPS:
        dfv[f"{g}_perc"] = (100 * dfv[g] / sums).round(1)
    dfv["GRUPO_PRED_VAR"] = dfv.apply(lambda r: predominant_group(r, GROUPS), axis=1)
    dfv.loc[sums.isna(), "GRUPO_PRED_VAR"] = np.nan

    gdf_var = gdf_var.join(dfv[GROUPS + [f"{g}_perc" for g in GROUPS] + ["GRUPO_PRED_VAR"]], how="left")
    if "UF" in gdf_var.columns:
        dfv["UF"] = gdf_var["UF"].values
    if "CIDADE" in gdf_var.columns:
        dfv["CIDADE"] = gdf_var["CIDADE"].values
    if "LATITUDE" in gdf_var.columns:
        dfv["LATITUDE"] = gdf_var["LATITUDE"].values
    if "LONGITUDE" in gdf_var.columns:
        dfv["LONGITUDE"] = gdf_var["LONGITUDE"].values
    if "POLUENTE" in gdf_var.columns:
        dfv["POLUENTE"] = gdf_var["POLUENTE"].values
    if "REP_ESPACIAL" in gdf_var.columns:
        dfv["REP_ESPACIAL"] = gdf_var["REP_ESPACIAL"].values
    dfv.to_csv(OUTPUT_DIR / "uso_solo_varbuf.csv", index=False)

    gdf_pts_center = _centroids_in_wgs84(gdf_var)
    center_lat, center_lon = _center_from_bounds(gdf_pts_center)

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=4,
        tiles="OpenStreetMap",
        control_scale=True,
        max_bounds=True
    )
    folium.TileLayer("cartodbpositron", name="CartoDB Positron").add_to(m)

    br_bounds = [[-34.0, -74.0], [6.0, -34.0]]
    m.fit_bounds(br_bounds)
    m.options['maxBounds'] = br_bounds
    m.options['maxBoundsViscosity'] = 1.0
    m.options['minZoom'] = 4

    # =====================
    # Camadas
    # =====================

    # Camadas por poluente
    pols = sorted([p for p in gdf_pts_center["POLUENTE"].dropna().unique()])
    layer_by_pol = {pol: folium.FeatureGroup(name=f"Poluente: {pol}", show=False).add_to(m) for pol in pols}

    # Camada geral (um ponto pequeno por estação, popup detalhado)
    layer_all = folium.FeatureGroup(name="Todas as estações (tabela completa)", show=True).add_to(m)

    for sid, group in gdf_pts_center.groupby(group_key):
        g0 = group[~group.geometry.is_empty].iloc[0]
        lat, lon = g0.geometry.y, g0.geometry.x

        header = []
        for c in ["UF", "CIDADE", group_key]:
            if c in group.columns and pd.notna(g0.get(c)):
                alias = "ID" if c == group_key else c.capitalize()
                header.append(f"<b>{escape(alias)}:</b> {escape(str(g0.get(c)))}")
        header_html = "<br>".join(header)

        rows = []
        for pol in sorted(group["POLUENTE"].dropna().unique()):
            sub = group[group["POLUENTE"] == pol]
            r = sub.iloc[0]
            rep_txt = f"{int(r.get('REP_ESPACIAL'))} m" if pd.notna(r.get("REP_ESPACIAL")) else "—"
            pred = r.get("GRUPO_PRED_VAR", "—")
            comp = _percent_bar_table(r)
            rows.append(
                f"<tr><td>{escape(str(pol))}</td>"
                f"<td>{rep_txt}</td>"
                f"<td style='color:{GROUP_COLORS.get(pred, '#333')};font-weight:bold'>{escape(str(pred))}</td>"
                f"<td>{comp}</td></tr>"
            )

        table_html = (
            "<table border='1' style='border-collapse:collapse;font-size:11px;'>"
            "<tr><th>Poluente</th><th>Buffer</th><th>Predom.</th><th>Composição</th></tr>"
            + "".join(rows) + "</table>"
        )

        popup_html = f"""
        <div style="max-height:400px;overflow-y:auto;overflow-x:hidden;
                    width:500px;padding-right:6px;">
        {header_html}<br>{table_html}
        </div>
        """
        folium.CircleMarker(
            location=(lat, lon),
            radius=5,
            color="#444444",
            fill=True,
            fill_color="#444444",
            fill_opacity=0.9,
            weight=1,
            popup=folium.Popup(popup_html, max_width=520),
            tooltip=f"Estação: {sid}",
        ).add_to(layer_all)

    # Marcadores por poluente (círculos reais)
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

        rep = row.get("REP_ESPACIAL")
        if pd.isna(rep) or rep <= 0:
            continue
        rep_txt = f"{int(rep)} m"
        comp = _percent_bar_table(row)

        header = []
        for c in ["UF", "CIDADE", group_key]:
            if c in gdf_pts_center.columns and pd.notna(row.get(c)):
                alias = "ID" if c == group_key else c.capitalize()
                header.append(f"<b>{escape(alias)}:</b> {escape(str(row.get(c)))}")
        header.append(f"<b>Poluente:</b> {escape(str(pol))}")
        header.append(f"<b>Buffer:</b> {rep_txt}")

        html = "<br>".join(header) + f"<br><b>Predominância:</b> {escape(str(pred)) if pd.notna(pred) else '—'}"
        popup_html = f"""
        <div style="max-height:400px;overflow-y:auto;overflow-x:hidden;
                    width:500px;padding-right:6px;">
        {html}<br><b>Composição:</b><br>{comp}
        </div>
        """
        folium.Circle(
            location=(lat, lon),
            radius=float(rep),
            color=color,
            weight=1,
            fill=True,
            fill_color=color,
            fill_opacity=0.3,
            popup=folium.Popup(popup_html, max_width=520),
            tooltip=f"{pol} — Predom.: {pred}" if pd.notna(pred) else f"{pol}",
        ).add_to(layer_by_pol[pol])


    # =====================
    # Extras
    # =====================
    MiniMap(toggle_display=True, position="bottomright").add_to(m)
    Fullscreen().add_to(m)
    m.get_root().html.add_child(
        folium.Element(_folium_categorical_legend("Predominância — buffers (MapBiomas)", GROUP_COLORS))
    )
    folium.LayerControl(collapsed=False).add_to(m)
    if save:
        save_path = save_path or Path(rootPath) / "_static/representatividade/bufferUsoDoSolo.html"
        save_path.parent.mkdir(parents=True, exist_ok=True)
        m.save(str(save_path))
        print(f"💾 Mapa salvo em: {save_path}")

    return m


# =========================
# Execução direta (teste)
# =========================
if __name__ == "__main__":
    m_var = build_map_varbuf()
    #m_var.save("bufferUsoDoSolo.html")
    print("Mapa com buffer variável salvo como bufferUsoDoSolo.html")
