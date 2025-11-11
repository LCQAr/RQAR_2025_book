# -*- coding: utf-8 -*-
import geopandas as gpd
import folium
from folium.plugins import MiniMap, Fullscreen
from pathlib import Path
import os
import pandas as pd


def build_map_station_nearest_industry_dual(
    rootPath: str | Path | None = None,
    max_distance: float | None = None,
    save: bool = False
) -> tuple:
    """
    Mapa Folium mostrando:
      - Estações separadas por poluente (camada estimada)
      - Ruas (pretas) usadas para o cálculo do buffer
      - Indústrias mais próximas
      - Linhas estação–indústria
      - Pop-ups detalhados e legenda fixa
    """
    rootPath = Path(rootPath or os.path.dirname(os.getcwd()))
    stations_file = rootPath / "scripts/rep_espacial/09_formatar_e_salvar_outputs/outputs/estacoes_completa.parquet"
    industries_file = rootPath / "scripts/rep_espacial/01_preprocessamento/inputs/industrial_sites_20250902.gpkg"
    rep_csv = rootPath / "scripts/rep_espacial/09_formatar_e_salvar_outputs/outputs/rep_espacial.csv"
    roads_file = rootPath / "scripts/rep_espacial/02_distancia_vias_e_ind/inputs/roads.parquet"

    # === Estações ===
    st = gpd.read_parquet(stations_file).to_crs(4326)
    rep = pd.read_csv(rep_csv)
    possible_cols = ["osm_id_mais_prox_valida", "osm_id_valido", "osm_id"]
    col_found = next((c for c in possible_cols if c in rep.columns), None)
    if col_found is None:
        raise KeyError(f"Nenhuma das colunas esperadas {possible_cols} foi encontrada em {rep_csv}")
    rep = rep.rename(columns={col_found: "osm_id"})
    

    # Adiciona apenas o osm_id (ID da rua) ao DataFrame das estações
    st = st.merge(rep[["ID_OEMA", "osm_id"]], on="ID_OEMA", how="left")

    # === Indústrias ===
    ind = gpd.read_file(industries_file).to_crs(4326)
    poly_mask = ind.geometry.geom_type.isin(["Polygon", "MultiPolygon"])
    if poly_mask.any():
        ind.loc[poly_mask, "geometry"] = ind.loc[poly_mask].to_crs(3857).centroid.to_crs(4326)

    # === Ruas ===
    roads = gpd.read_parquet(roads_file).to_crs(4326)

    # === Associação estação–indústria ===
    # O 'st' (com 'osm_id' da rua) é usado aqui
    st_3857, ind_3857 = st.to_crs(3857), ind.to_crs(3857)
    nearest = gpd.sjoin_nearest(st_3857, ind_3857, how="left", distance_col="dist_m")
    if max_distance:
        nearest = nearest[nearest["dist_m"] <= max_distance]
    nearest = nearest.to_crs(4326)

    # === Centro e base ===
    minx, miny, maxx, maxy = st.total_bounds
    center_lat, center_lon = (miny + maxy) / 2, (minx + maxx) / 2
    m = folium.Map(location=[center_lat, center_lon], zoom_start=5, tiles="cartodbpositron")

    # === Paleta de cores ===
    palette = {
        "CO": "#A8E6CF", "NO2": "#84C1FF", "O3": "#BDB2FF",
        "MP25": "#FFD6A5", "MP10": "#FFADAD", "PTS": "#FFDAC1", "SO2": "#E2F0CB"
    }
    IND_COLOR, ALL_ST_COLOR, LINK_COLOR = "#E57373", "#64B5F6", "#B0BEC5"
    color_map = {p: palette.get(p, "#CCCCCC") for p in nearest["POLUENTE"].dropna().unique()}

    # === Camadas ===
    layer_roads = folium.FeatureGroup(name="Ruas (pretas)", show=True).add_to(m)
    layer_all = folium.FeatureGroup(name="Todas as estações", show=True).add_to(m)
    layer_ind = folium.FeatureGroup(name="Indústrias", show=True).add_to(m)
    layer_links = folium.FeatureGroup(name="Conexões estação–indústria", show=True).add_to(m)

    # === Ruas pretas (MODIFICADO) ===
    # 1. Pega todos os IDs de ruas únicas que estão ligadas a uma estação
    # O 'nearest' já contém o 'osm_id' da rua (que veio do merge do 'st' com 'rep')
    linked_road_ids = nearest["osm_id"].dropna().unique()
    
    # 2. Filtra o GeoDataFrame de ruas para mostrar APENAS essas ruas
    # Assumindo que a coluna de ID no 'roads.parquet' também é 'osm_id'
    try:
        roads_to_show = roads[roads["osm_id"].isin(linked_road_ids)]
    except KeyError:
        print("Aviso: A coluna 'osm_id' não foi encontrada em 'roads.parquet'. Verifique o nome da coluna de ID.")
        # Tenta um fallback, como o índice (se o ID for o índice)
        try:
            roads_to_show = roads[roads.index.isin(linked_road_ids)]
        except Exception:
            # Se falhar, apenas usa um subconjunto vazio para não quebrar
            roads_to_show = roads.head(0)
    except Exception as e:
        print(f"Erro ao filtrar ruas: {e}")
        roads_to_show = roads.head(0) # Continua com ruas vazias
        
    # 3. Itera APENAS sobre as ruas filtradas
    for _, r in roads_to_show.iterrows():
        geom = r.geometry
        if geom.is_empty:
            continue
        if geom.geom_type == "LineString":
            folium.PolyLine([(y, x) for x, y in geom.coords], color="#000", weight=3, opacity=0.8).add_to(layer_roads)
        elif geom.geom_type == "MultiLineString":
            for line in geom.geoms:
                folium.PolyLine([(y, x) for x, y in line.coords], color="#000", weight=3, opacity=0.8).add_to(layer_roads)

    # === Estações (MODIFICADO) ===
    for pol, color in color_map.items():
        subset = nearest[nearest["POLUENTE"] == pol]
        if subset.empty:
            continue

        layer_est = folium.FeatureGroup(name=f"{pol} — Estimada", show=(pol == "MP25")).add_to(m)
        # Camada 'Declarada' removida

        for _, row in subset.iterrows():
            g = row.geometry
            if g.is_empty:
                continue

            # Estimada
            # Usa os valores de representatividade que já estão no 'row' (do 'nearest')
            rep_val = row.get("REP_ESPACIAL_m", row.get("REP_ESPACIAL", 9000))
            popup_html_est = f"""
            <div style="font-size:13px;">
            <b>Estação:</b> {row.get('ID_OEMA','—')}<br>
            <b>UF:</b> {row.get('UF_left', row.get('UF','—'))}<br>
            <b>Poluente:</b> {pol}<br>
            <b>Representatividade estimada:</b> {rep_val:.0f} m<br>
            <b>Distância à indústria mais próxima:</b> {row.get('dist_m',float('nan')):.0f} m
            </div>
            """
            folium.Circle(
                location=(g.y, g.x),
                radius=float(rep_val),
                color=color, weight=1.2,
                fill=True, fill_color=color, fill_opacity=0.15,
                popup=folium.Popup(popup_html_est, max_width=350),
                tooltip=f"{row.get('ID_OEMA','—')} ({pol})"
            ).add_to(layer_est)

            # Bloco 'Declarada' removido

    # === Indústrias ===
    # (Sem alterações)
    for _, row in nearest.iterrows():
        g_ind = ind.loc[row["index_right"]].geometry
        if g_ind.is_empty:
            continue
        popup_html = f"""
        <div style="font-size:13px;">
        <b>Indústria:</b> {row.get('Razão Social_right','—')}<br>
        <b>UF:</b> {row.get('UF_right', row.get('UF','—'))}<br>
        <b>Distância até estação:</b> {row['dist_m']:.0f} m
        </div>
        """
        folium.CircleMarker(
            location=(g_ind.y, g_ind.x),
            radius=5,
            color=IND_COLOR, fill=True,
            fill_color=IND_COLOR, fill_opacity=0.9,
            popup=folium.Popup(popup_html, max_width=350),
            tooltip="Indústria mais próxima"
        ).add_to(layer_ind)

        g_st = row.geometry
        if not g_st.is_empty:
            folium.PolyLine(
                [(g_st.y, g_st.x), (g_ind.y, g_ind.x)],
                color=LINK_COLOR, weight=1, opacity=0.6
            ).add_to(layer_links)

    # === Camada geral ===
    # (Sem alterações)
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
            tooltip=f"Estação: {row.get('ID_OEMA','—')} ({row.get('UF','')})"
        ).add_to(layer_all)

    # === Extras ===
    MiniMap(toggle_display=True, position="bottomright").add_to(m)
    Fullscreen().add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)

    # === Legenda (MODIFICADA) ===
    legend_html = (
        "<div style='position:fixed;bottom:20px;left:20px;background:white;"
        "padding:8px 10px;border:1px solid #999;font-size:12px;z-index:9999;border-radius:4px;'>"
        "<b>Legenda</b><br>"
        + "".join(
            f"<div style='margin:2px 0;display:flex;align-items:center;'>"
            f"<span style='background:{c};width:14px;height:14px;margin-right:6px;"
            f"border:1px solid #555;'></span>{p}</div>"
            for p, c in color_map.items()
        )
        + "<hr>"
        # Bloco 'Declarações MMA' removido
        + "<div><span style='background:#000;width:14px;height:14px;margin-right:6px;"
        "border:1px solid #555;display:inline-block;'></span>Ruas</div>"
        + f"<div><span style='background:{IND_COLOR};width:14px;height:14px;"
        "margin-right:6px;border:1px solid #555;display:inline-block;'></span>Indústrias</div>"
        + "</div>"
    )
    m.get_root().html.add_child(folium.Element(legend_html))

    # === Salvar ===
    if save:
        out_dir = rootPath / "_static" / "representatividade"
        out_dir.mkdir(parents=True, exist_ok=True)
        output_file = out_dir / "mapa_estacoes_industrias_dual.html"
        m.save(str(output_file))
        print(f"✅ Mapa salvo em: {output_file}")
        rel_path = "../_static/representatividade/mapa_estacoes_industrias_dual.html"
        return m, rel_path

    return m, None