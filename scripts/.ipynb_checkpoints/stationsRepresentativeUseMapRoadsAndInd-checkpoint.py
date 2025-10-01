import geopandas as gpd
import folium
from folium.plugins import MiniMap, Fullscreen
from pathlib import Path
import os
import pandas as pd
from shapely.ops import nearest_points

def build_map_station_nearest_industry_by_pollutant(
    rootPath: str | Path | None = None,
    max_distance: float | None = None,
    max_road_distance: float = 10000  # distância máx. entre estação e rua (m)
) -> folium.Map:
    """
    Mapa Folium mostrando:
      - Estações separadas por poluente (círculos em metros reais = REP_ESPACIAL).
      - Ruas mais próximas (por poluente) e linha conectando estação ↔ rua.
      - Indústrias mais próximas (vermelhas).
      - Linhas conectando estação ↔ indústria (cinza).
      - Camada com todas as estações como pontos pequenos.
      - Legenda fixa.
    """
    rootPath = Path(rootPath or os.path.dirname(os.getcwd()))
    stations_file = rootPath / "data/rep_espacial/outputs/estacoes_completa.gpkg"
    industries_file = rootPath / "data/rep_espacial/inputs/industrial_sites_20250902.gpkg"
    rep_csv = rootPath / "scripts/rep_espacial/09_formatar_e_salvar_outputs/outputs/rep_espacial.csv"
    roads_file = rootPath / "scripts/rep_espacial/01_preprocessamento/outputs/roads.parquet"

    # === Estações ===
    st = gpd.read_file(stations_file).to_crs(4326)

    # === CSV com info de rua mais próxima ===
    rep = pd.read_csv(rep_csv)
    possible_cols = ["osm_id_mais_prox_valida", "osm_id_valido", "osm_id"]
    col_found = next((c for c in possible_cols if c in rep.columns), None)
    if col_found is None:
        raise KeyError(f"Nenhuma das colunas esperadas {possible_cols} foi encontrada em {rep_csv}")
    rep = rep.rename(columns={col_found: "osm_id"})
    st = st.merge(rep[["ID_OEMA", "osm_id"]], on="ID_OEMA", how="left")

    # === Indústrias ===
    ind = gpd.read_file(industries_file).to_crs(4326)
    poly_mask = ind.geometry.geom_type.isin(["Polygon", "MultiPolygon"])
    if poly_mask.any():
        ind_poly = ind.loc[poly_mask].to_crs(3857)
        ind.loc[poly_mask, "geometry"] = ind_poly.geometry.centroid.to_crs(4326)

    # === Vias ===
    roads = gpd.read_parquet(roads_file).to_crs(4326)

    # === Nearest join (estações ↔ indústrias) ===
    st_3857 = st.to_crs(3857)
    ind_3857 = ind.to_crs(3857)
    nearest = gpd.sjoin_nearest(st_3857, ind_3857, how="left", distance_col="dist_m")
    if max_distance:
        nearest = nearest[nearest["dist_m"] <= max_distance]
    nearest = nearest.to_crs(4326)

    # === Centro do mapa ===
    minx, miny, maxx, maxy = st.total_bounds
    center_lat, center_lon = (miny + maxy) / 2, (minx + maxx) / 2
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=5,
        tiles="cartodbpositron",
        max_bounds=True
    )
    br_bounds = [[-34.0, -74.0], [6.0, -34.0]]
    m.fit_bounds(br_bounds)
    m.options['maxBounds'] = br_bounds
    m.options['maxBoundsViscosity'] = 1.0
    m.options['minZoom'] = 4

    # === Paleta de cores suaves por poluente ===
    palette = {
        "CO":   "#A8E6CF",  # verde água claro
        "NO2":  "#84C1FF",  # azul claro
        "O3":   "#BDB2FF",  # lavanda suave
        "MP25": "#FFD6A5",  # laranja pastel
        "MP10": "#FFADAD",  # rosa suave
        "PTS":  "#FFDAC1",  # pêssego claro
        "SO2":  "#E2F0CB",  # verde amarelado
    }
    IND_COLOR = "#E57373"     # vermelho suave
    ALL_ST_COLOR = "#64B5F6"  # azul médio
    LINK_COLOR = "#B0BEC5"    # cinza azulado

    unique_pols = nearest["POLUENTE"].dropna().unique()
    color_map = {pol: palette.get(pol, "#CCCCCC") for pol in unique_pols}

    # === Camada com todas as estações (ponto simples) ===
    layer_all = folium.FeatureGroup(name="Todas as estações (ponto)", show=True).add_to(m)
    for _, row in st.iterrows():
        g = row.geometry
        if g.is_empty:
            continue
        folium.CircleMarker(
            location=(g.y, g.x),
            radius=3,
            color=ALL_ST_COLOR,
            fill=True,
            fill_color=ALL_ST_COLOR,
            fill_opacity=0.8,
            tooltip=f"Estação: {row.get('ID_OEMA','—')} / {row.get('UF','')}"
        ).add_to(layer_all)

    # === Camadas por poluente (estações + ruas + conexões) ===
    for pol in unique_pols:
        subset = nearest[nearest["POLUENTE"] == pol]
        if subset.empty:
            continue
        color = color_map[pol]

        layer_st = folium.FeatureGroup(name=f"Estações — {pol}", show=False).add_to(m)
        layer_roads_pol = folium.FeatureGroup(name=f"Ruas — {pol}", show=False).add_to(m)

        for _, row in subset.iterrows():
            g = row.geometry
            if g.is_empty:
                continue

            rep_val = row.get("REP_ESPACIAL", None)
            if pd.isna(rep_val) or rep_val <= 0:
                continue

            # Estação
            folium.Circle(
                location=(g.y, g.x),
                radius=float(rep_val),
                color=color,
                weight=1,
                fill=True,
                fill_color=color,
                fill_opacity=0.25,
                popup=folium.Popup(
                    f"<b>Estação:</b> {row.get('ID_OEMA','—')} / {row.get('UF','')}<br>"
                    f"<b>Poluente:</b> {pol}<br>"
                    f"<b>Representatividade:</b> {rep_val} m<br>",
                    max_width=400,
                    alpha= 0.5
                ),
                tooltip=f"{pol} ({rep_val} m)"
            ).add_to(layer_st)

            # Rua associada
            osm_id = row.get("osm_id", None)
            if pd.notna(osm_id):
                road_candidates = roads.loc[roads["osm_id"] == osm_id].copy()
                if not road_candidates.empty:
                    st_proj = gpd.GeoSeries([g], crs=4326).to_crs(3857).iloc[0]
                    roads_proj = road_candidates.to_crs(3857)
                    roads_proj["dist"] = roads_proj.distance(st_proj)
                    road = roads_proj.sort_values("dist").iloc[0].geometry

                    if road.distance(st_proj) < max_road_distance:
                        road4326 = gpd.GeoSeries([road], crs=3857).to_crs(4326).iloc[0]
                        folium.GeoJson(
                            road4326,
                            style_function=lambda x, col=color: {
                                "color": col,
                                "weight": 2,
                                "opacity": 0.7,
                            },
                            tooltip=f"Rua OSM ID: {osm_id}"
                        ).add_to(layer_roads_pol)

                        p_station = gpd.GeoSeries([g], crs=4326).to_crs(3857).iloc[0]
                        p_near_station, p_near_road = nearest_points(p_station, road)
                        folium.PolyLine(
                            [(p_near_station.y, p_near_station.x), (p_near_road.y, p_near_road.x)],
                            color=color, weight=1, opacity=0.6
                        ).add_to(layer_roads_pol)

    # === Camada de indústrias ===
    layer_ind = folium.FeatureGroup(name="Indústrias mais próximas", show=True).add_to(m)
    for _, row in nearest.iterrows():
        g_ind = ind.loc[row["index_right"]].geometry
        if g_ind.is_empty:
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

    # === Camada de conexões estação ↔ indústria ===
    layer_ind_links = folium.FeatureGroup(name="Conexões estação-indústria", show=True).add_to(m)
    for _, row in nearest.iterrows():
        g_st = row.geometry
        g_ind = ind.loc[row["index_right"]].geometry
        if g_st.is_empty or g_ind.is_empty:
            continue
        folium.PolyLine(
            [(g_st.y, g_st.x), (g_ind.y, g_ind.x)],
            color=LINK_COLOR, weight=1, opacity=0.4
        ).add_to(layer_ind_links)

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
        f"<span style='background:{ALL_ST_COLOR};width:14px;height:14px;margin-right:6px;border:1px solid #555;'></span>"
        f"Todas as estações (ponto)</div>"
    )
    legend_items.append(
        f"<div style='margin:2px 0;display:flex;align-items:center;'>"
        f"<span style='background:{LINK_COLOR};width:14px;height:14px;margin-right:6px;border:1px solid #555;'></span>"
        f"Conexões estação-indústria</div>"
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
