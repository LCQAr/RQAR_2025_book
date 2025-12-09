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

pd.set_option("future.no_silent_downcasting", True)
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

# >>> NORMALIZAÇÃO DE POLUENTES <<<
pollutant_map = {
    "PM10": "MP10",
    "PM25": "MP25",
    "PM1": None,   # remover
    "VOC": None,   # remover
}

# =========================================================
# Helpers de uso do solo e popup
# =========================================================
def aggregate_land_use(
    stats_df: pd.DataFrame,
    land_use_map: dict[str, list[str]],
) -> pd.DataFrame:
    """
    Pega o DataFrame de saída do cutMapbiomas (com colunas de códigos MapBiomas)
    e cria colunas agregadas por grupo (Floresta, Herbácea, ...).

    Usa diretamente as colunas com códigos numéricos como área (m² / ha etc.),
    sem tentar adivinhar nome de coluna de área.
    """
    df = stats_df.copy()
    out = df.copy()

    for group_name, codes in land_use_map.items():
        cols = [c for c in codes if c in df.columns]
        if cols:
            out[group_name] = df[cols].sum(axis=1, min_count=1)
        else:
            out[group_name] = np.nan

    return out


def predominant_group(row: pd.Series, groups: list[str]) -> str | float:
    """
    Retorna o grupo com maior percentual (colunas `<grupo>_perc`).
    """
    best_g = np.nan
    best_val = -np.inf
    for g in groups:
        v = row.get(f"{g}_perc")
        if pd.notna(v) and v > best_val:
            best_val = v
            best_g = g
    return best_g


def _percent_bar_table(row: pd.Series) -> str:
    """
    Barra horizontal de composição de uso do solo + legenda.
    Versão sem bordas externas (igual ao estilo antigo).
    """
    vals = {}
    for g in GROUPS:
        v = row.get(f"{g}_perc")
        if pd.isna(v) or v <= 0:
            continue
        vals[g] = float(v)

    if not vals:
        return "<div style='font-size:11px;color:#555;'>Sem composição disponível</div>"

    total = sum(vals.values())
    if total <= 0:
        return "<div style='font-size:11px;color:#555;'>Sem composição disponível</div>"

    # === Barra limpa sem borda ===
    bar_segments = []
    for g, v in vals.items():
        width = max(v / total * 100.0, 2.0)
        color = GROUP_COLORS.get(g, "#777")
        bar_segments.append(
            f"<span style='display:inline-block;height:10px;width:{width:.1f}%;"
            f"background:{color};margin:0;padding:0;'></span>"
        )

    bar_html = (
        "<div style='width:100%;margin:4px 0 4px 0;padding:0;'>"
        + "".join(bar_segments) +
        "</div>"
    )

    # === Legenda (igual a sua antiga) ===
    legend_parts = []
    for g, v in vals.items():
        color = GROUP_COLORS.get(g, "#777")
        legend_parts.append(
            "<span style='margin-right:8px;white-space:nowrap;'>"
            f"<span style='display:inline-block;width:10px;height:10px;"
            f"background:{color};margin-right:3px;'></span>"
            f"{escape(g)} ({v:.0f}%)"
            "</span>"
        )

    legend_html = (
        "<div style='font-size:10px;line-height:1.2;margin-top:2px;'>"
        + "".join(legend_parts) +
        "</div>"
    )

    return bar_html + legend_html



def _centroids_in_wgs84(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Calcula centróides em 3857 e devolve em 4326, preservando atributos.
    """
    gdf_m = gdf.to_crs(3857)
    cent = gdf_m.geometry.centroid
    gdf_cent = gdf_m.copy()
    gdf_cent.geometry = cent
    return gdf_cent.to_crs(4326)


def _center_from_bounds(gdf: gpd.GeoDataFrame) -> tuple[float, float]:
    """
    Centro aproximado do conjunto (para inicializar o mapa).
    """
    minx, miny, maxx, maxy = gdf.total_bounds
    return (miny + maxy) / 2.0, (minx + maxx) / 2.0


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

    # =====================
    # Preparação de dados
    # =====================
    rootPath = Path(rootPath or os.path.dirname(os.getcwd()))
    inputFolder = rootPath / "data"
    mapbiomasFolder = inputFolder / "MAPBIOMAS"

    # Leitura do CSV inicial
    p = Path(file)
    station_csv = p if p.exists() else (inputFolder / file)
    df = pd.read_csv(station_csv)

    # >>> NORMALIZAÇÃO DE POLUENTES <<<
    df["POLUENTE"] = df["POLUENTE"].replace(pollutant_map)
    df = df[df["POLUENTE"].notna()]

    for col in ["LATITUDE", "LONGITUDE", "POLUENTE"]:
        if col not in df.columns:
            raise ValueError(f"Coluna obrigatória ausente no CSV: {col}")

    group_key = (
        "ID_OEMA"
        if "ID_OEMA" in df.columns
        else ("ID_MMA" if "ID_MMA" in df.columns else None)
    )
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

    # >>> NORMALIZAÇÃO EM gdf_pts <<<
    gdf_pts["POLUENTE"] = gdf_pts["POLUENTE"].replace(pollutant_map)
    gdf_pts = gdf_pts[gdf_pts["POLUENTE"].notna()]

    # Buffer variável
    gdf_m = gdf_pts.to_crs(3857)
    buffers = [
        geom.buffer(float(dist)) if (geom and pd.notna(dist) and dist > 0) else None
        for geom, dist in zip(gdf_m.geometry, gdf_m["REP_ESPACIAL"])
    ]

    gdf_var = gdf_m.copy()
    gdf_var["geometry"] = buffers
    gdf_var = gdf_var.to_crs(4326)
    gdf_var["buffer"] = gdf_pts["REP_ESPACIAL"].reindex(gdf_var.index)
    gdf_var = gdf_var[~gdf_var.geometry.isna()].copy()

    # >>> NORMALIZAÇÃO EM gdf_var <<<
    gdf_var["POLUENTE"] = gdf_var["POLUENTE"].replace(pollutant_map)
    gdf_var = gdf_var[gdf_var["POLUENTE"].notna()]

    # =========================
    # Cálculo do uso do solo
    # =========================
    stats_var = stl.cutMapbiomas(str(mapbiomasFolder), gdf_var, year, "", pixelSize)
    dfv = aggregate_land_use(stats_var, LAND_USE_MAP)

    # Propaga poluentes para dfv (mesma ordem de linhas)
    dfv["POLUENTE"] = gdf_var["POLUENTE"].values

    # Normalização final em dfv
    dfv["POLUENTE"] = dfv["POLUENTE"].replace(pollutant_map)
    dfv = dfv[dfv["POLUENTE"].notna()]

    # Percentuais por grupo
    sums = dfv[GROUPS].sum(axis=1).replace(0, np.nan)
    for g in GROUPS:
        dfv[f"{g}_perc"] = (100 * dfv[g] / sums).round(1)
    dfv["GRUPO_PRED_VAR"] = dfv.apply(lambda r: predominant_group(r, GROUPS), axis=1)
    dfv.loc[sums.isna(), "GRUPO_PRED_VAR"] = np.nan

    # ========= PREPARAÇÃO FINAL DOS DADOS =========
    gdf_var = gdf_var.join(
        dfv[
            GROUPS
            + [f"{g}_perc" for g in GROUPS]
            + ["GRUPO_PRED_VAR"]
        ],
        how="left",
    )

    # Centróides
    gdf_pts_center = _centroids_in_wgs84(gdf_var)

    # >>> NORMALIZAÇÃO EM gdf_pts_center <<<
    gdf_pts_center["POLUENTE"] = gdf_pts_center["POLUENTE"].replace(pollutant_map)
    gdf_pts_center = gdf_pts_center[gdf_pts_center["POLUENTE"].notna()]

    center_lat, center_lon = _center_from_bounds(gdf_pts_center)

    # ==============================================
    # Construção do mapa
    # ==============================================

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=4,
        tiles="OpenStreetMap",
        control_scale=True,
        max_bounds=True,
    )
    folium.TileLayer("cartodbpositron", name="CartoDB Positron").add_to(m)

    # =====================
    # Camadas
    # =====================
    pols = sorted(gdf_pts_center["POLUENTE"].dropna().unique())

    layer_by_pol = {
        pol: folium.FeatureGroup(name=f"Poluente: {pol}", show=False).add_to(m)
        for pol in pols
    }

    layer_all = folium.FeatureGroup(
        name="Todas as estações (tabela completa)",
        show=True,
    ).add_to(m)

    # =====================
    # Marcadores gerais
    # =====================
    for sid, group in gdf_pts_center.groupby(group_key):
        g0 = group.iloc[0]
        lat, lon = g0.geometry.y, g0.geometry.x

        group = group.copy()
        group["POLUENTE"] = group["POLUENTE"].replace(pollutant_map)
        group = group[group["POLUENTE"].notna()]

        header = []
        for c in ["UF", "CIDADE", group_key]:
            if c in group and pd.notna(g0.get(c)):
                alias = "ID" if c == group_key else c.capitalize()
                header.append(f"<b>{escape(alias)}:</b> {escape(str(g0.get(c)))}")
        header_html = "<br>".join(header)

        rows = []
        for pol in sorted(group["POLUENTE"].unique()):
            sub = group[group["POLUENTE"] == pol]
            r = sub.iloc[0]
            rep_txt = (
                f"{int(r.get('REP_ESPACIAL'))} m"
                if pd.notna(r.get("REP_ESPACIAL"))
                else "—"
            )
            pred = r.get("GRUPO_PRED_VAR", "—")
            comp = _percent_bar_table(r)
            rows.append(
                f"<tr>"
                f"<td>{escape(pol)}</td>"
                f"<td>{rep_txt}</td>"
                f"<td style='color:{GROUP_COLORS.get(pred, '#333')};"
                f"font-weight:bold'>{escape(str(pred))}</td>"
                f"<td>{comp}</td>"
                f"</tr>"
            )

        table_html = (
            "<table border='1' style='border-collapse:collapse;font-size:11px;'>"
            "<tr><th>Poluente</th><th>Buffer</th><th>Predom.</th><th>Composição</th></tr>"
            + "".join(rows)
            + "</table>"
        )

        popup_html = f"""
        <div style="max-height:400px;overflow-y:auto;overflow-x:hidden;width:500px;">
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
            popup=folium.Popup(popup_html, max_width=520),
            tooltip=f"Estação: {sid}",
        ).add_to(layer_all)

    # =====================
    # Camadas por poluente
    # =====================
    for _, row in gdf_pts_center.iterrows():
        pol = row["POLUENTE"]
        if pol not in layer_by_pol:
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

        comp = _percent_bar_table(row)
        popup_html = (
            f"<b>Poluente:</b> {pol}<br>"
            f"<b>Predom.:</b> {pred}<br>"
            f"{comp}"
        )

        folium.Circle(
            location=(lat, lon),
            radius=float(rep),
            color=color,
            weight=1,
            fill=True,
            fill_color=color,
            fill_opacity=0.3,
            popup=folium.Popup(popup_html, max_width=520),
            tooltip=pol,
        ).add_to(layer_by_pol[pol])

    MiniMap(toggle_display=True, position="bottomright").add_to(m)
    Fullscreen().add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)

    if save:
        save_path = save_path or Path(rootPath) / "_static/representatividade/bufferUsoDoSolo.html"
        save_path.parent.mkdir(parents=True, exist_ok=True)
        m.save(str(save_path))
        print(f"💾 Mapa salvo em: {save_path}")

    return m, gdf_pts_center
