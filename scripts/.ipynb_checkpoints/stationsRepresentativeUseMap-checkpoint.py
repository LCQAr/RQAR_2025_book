import geopandas as gpd
import folium
from folium.plugins import MiniMap, Fullscreen
from pathlib import Path
import os
import pandas as pd

def build_map_station_nearest_industry_by_pollutant(
    rootPath: str | Path | None = None,
    max_distance: float | None = None
) -> folium.Map:
    """
    Mapa Folium mostrando:
      - Estações separadas por poluente (círculos em metros reais = REP_ESPACIAL).
      - Indústrias mais próximas (vermelhas).
      - Linha conectando estação ↔ indústria.
      - Nova camada: todas as estações como pontos pequenos.
      - Legenda fixa.
    """
    rootPath = Path(rootPath or os.path.dirname(os.getcwd()))
    stations_file = rootPath / "data/rep_espacial/outputs/estacoes_completa.gpkg"
    industries_file = rootPath / "data/rep_espacial/inputs/industrial_sites_20250902.gpkg"

    # === Estações ===
    st = gpd.read_file(stations_file).to_crs(4326)

    # === Indústrias ===
    ind = gpd.read_file(industries_file).to_crs(4326)
    poly_mask = ind.geometry.geom_type.isin(["Polygon", "MultiPolygon"])
    if poly_mask.any():
        ind_poly = ind.loc[poly_mask].to_crs(3857)
        ind.loc[poly_mask, "geometry"] = ind_poly.geometry.centroid.to_crs(4326)

    # === Nearest join ===
    st_3857 = st.to_crs(3857)
    ind_3857 = ind.to_crs(3857)
    nearest = gpd.sjoin_nearest(st_3857, ind_3857, how="left", distance_col="dist_m")
    if max_distance:
        nearest = nearest[nearest["dist_m"] <= max_distance]
    nearest = nearest.to_crs(4326)

    # === Centro do mapa ===
#    minx, miny, maxx, maxy = st.total_bounds
#    center_lat, center_lon = (miny + maxy) / 2, (minx + maxx) / 2
#    m = folium.Map(location=[center_lat, center_lon], zoom_start=5, tiles="cartodbpositron")

    # === Centro do mapa ===
    minx, miny, maxx, maxy = st.total_bounds
    center_lat, center_lon = (miny + maxy) / 2, (minx + maxx) / 2
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=5,
        tiles="cartodbpositron",
        max_bounds=True
    )
    
    # Limites aproximados do Brasil (bounding box)
    br_bounds = [[-34.0, -74.0], [6.0, -34.0]]  # [sul-oeste, norte-leste]
    m.fit_bounds(br_bounds)
    m.options['maxBounds'] = br_bounds
    m.options['maxBoundsViscosity'] = 1.0  # trava ao sair da caixa
    m.options['minZoom'] = 4  # evita zoom out além do Brasil

    
    # === Paleta por poluente ===
    unique_pols = nearest["POLUENTE"].dropna().unique()
    color_map = {pol: f"#{hash(pol) % 0xFFFFFF:06x}" for pol in unique_pols}
    IND_COLOR = "#d62728"

    # === Camada com todas as estações (ponto simples) ===
    layer_all = folium.FeatureGroup(name="Todas as estações (ponto)", show=True).add_to(m)
    for _, row in st.iterrows():
        g = row.geometry
        if g.is_empty:
            continue
        folium.CircleMarker(
            location=(g.y, g.x),
            radius=3,
            color="blue",
            fill=True,
            fill_color="blue",
            fill_opacity=0.8,
            tooltip=f"Estação: {row.get('ID_OEMA','—')} / {row.get('UF','')}"
        ).add_to(layer_all)

    # === Camadas por poluente (círculos de representatividade) ===
    for pol in unique_pols:
        subset = nearest[nearest["POLUENTE"] == pol]
        if subset.empty:
            continue
        color = color_map[pol]
        layer_st = folium.FeatureGroup(name=f"Estações — {pol}", show=False).add_to(m)

        for _, row in subset.iterrows():
            g = row.geometry
            if g.is_empty:
                continue

            rep = row.get("REP_ESPACIAL", None)
            if pd.isna(rep) or rep <= 0:
                continue

            popup_html = (
                f"<b>Estação:</b> {row.get('ID_OEMA','—')} / {row.get('UF','')}<br>"
                f"<b>Poluente:</b> {pol}<br>"
                f"<b>Representatividade:</b> {rep} m<br>"
            )

            folium.Circle(
                location=(g.y, g.x),
                radius=float(rep),   # metros reais
                color=color,
                weight=1,
                fill=True,
                fill_color=color,
                fill_opacity=0.25,
                popup=folium.Popup(popup_html, max_width=400),
                tooltip=f"{pol} ({rep} m)"
            ).add_to(layer_st)

    # === Camada única para indústrias ===
    layer_ind = folium.FeatureGroup(name="Indústrias mais próximas", show=True).add_to(m)
    for _, row in nearest.iterrows():
        g_st = row.geometry
        g_ind = ind.loc[row["index_right"]].geometry
        if g_st.is_empty or g_ind.is_empty:
            continue

        folium.CircleMarker(
            location=(g_ind.y, g_ind.x),
            radius=5,
            color=IND_COLOR,
            fill=True,
            fill_color=IND_COLOR,
            fill_opacity=0.9,
            tooltip=f"Indústria: {row.get('Razão Social_right','—')}<br>Distância: {row['dist_m']:.0f} m"
        ).add_to(layer_ind)

        folium.PolyLine(
            [(g_st.y, g_st.x), (g_ind.y, g_ind.x)],
            color="gray", weight=1, opacity=0.4
        ).add_to(layer_ind)

    # === Extras ===
    MiniMap(toggle_display=True, position="bottomright").add_to(m)
    Fullscreen().add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)

    # === Legenda ===
    legend_items = [
        f"<div style='margin:2px 0;display:flex;align-items:center;'>"
        f"<span style='background:{col};width:14px;height:14px;margin-right:6px;"
        f"border:1px solid #555;'></span>{pol}</div>"
        for pol, col in color_map.items()
    ]
    legend_items.append(
        f"<div style='margin:6px 0 0;display:flex;align-items:center;border-top:1px solid #ddd;padding-top:6px;'>"
        f"<span style='background:{IND_COLOR};width:14px;height:14px;margin-right:6px;border:1px solid #555;'></span>"
        f"Indústrias mais próximas</div>"
    )
    legend_items.append(
        f"<div style='margin:2px 0;display:flex;align-items:center;'>"
        f"<span style='background:blue;width:14px;height:14px;margin-right:6px;border:1px solid #555;'></span>"
        f"Todas as estações (ponto)</div>"
    )

    legend_html = (
        "<div style='position:fixed;bottom:20px;left:20px;background:white;"
        "padding:8px 10px;border:1px solid #999;font-size:12px;z-index:9999;border-radius:4px;'>"
        "<b>Legenda</b><br>" + "".join(legend_items) + "</div>"
    )
    m.get_root().html.add_child(folium.Element(legend_html))

    return m



# Exemplo no Jupyter:
rootPath = Path(os.path.dirname(os.getcwd()))
m_map = build_map_station_nearest_industry_by_pollutant(rootPath=rootPath, max_distance=50000)
m_map
