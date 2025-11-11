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
      - Estações separadas por poluente (camadas estimada + declarada)
      - Ruas (pretas, sem tooltip)
      - Indústrias mais próximas
      - Linhas estação–indústria
      - Pop-ups detalhados e legenda fixa
      
    Implementa GeoJSON Buffers para as áreas de representatividade para
    melhorar o desempenho da renderização no Folium/Leaflet.
    """
    rootPath = Path(rootPath or os.path.dirname(os.getcwd()))
    stations_file = rootPath / "scripts/rep_espacial/09_formatar_e_salvar_outputs/outputs/estacoes_completa.parquet"
    industries_file = rootPath / "scripts/rep_espacial/01_preprocessamento/inputs/industrial_sites_20250902.gpkg"
    rep_csv = rootPath / "scripts/rep_espacial/09_formatar_e_salvar_outputs/outputs/rep_espacial.csv"
    roads_file = rootPath / "scripts/rep_espacial/01_preprocessamento/outputs/roads.parquet"

    # === Estações ===
    st = gpd.read_parquet(stations_file).to_crs(4326)
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
        # Converte polígonos de indústria para ponto (centroide)
        ind.loc[poly_mask, "geometry"] = ind.loc[poly_mask].to_crs(3857).centroid.to_crs(4326)

    # === Ruas ===
    roads = gpd.read_parquet(roads_file).to_crs(4326)

    # === Associação estação–indústria ===
    st_3857, ind_3857 = st.to_crs(3857), ind.to_crs(3857)
    nearest = gpd.sjoin_nearest(st_3857, ind_3857, how="left", distance_col="dist_m")
    if max_distance:
        nearest = nearest[nearest["dist_m"] <= max_distance]
    nearest = nearest.to_crs(4326)
    # Copia o GeoDataFrame (nearest) e re-projeta para 3857 para o cálculo do buffer.
    st_3857_est = nearest.copy().to_crs(3857) 

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

    # === Categorias declaradas (limites MMA) ===
    CATEGORY_TO_RADIUS_M = {
        "microescala": 100,
        "mesoescala": 500,
        "bairro": 4000,
        "urbana": 50000
    }

    # === Camadas ===
    layer_roads = folium.FeatureGroup(name="Ruas (pretas)", show=True).add_to(m)
    layer_all = folium.FeatureGroup(name="Todas as estações", show=True).add_to(m)
    layer_ind = folium.FeatureGroup(name="Indústrias", show=True).add_to(m)
    layer_links = folium.FeatureGroup(name="Conexões estação–indústria", show=True).add_to(m)

    # === Ruas pretas ===
    roads_subset = roads.sample(min(1000, len(roads)), random_state=42)
    for _, r in roads_subset.iterrows():
        geom = r.geometry
        if geom.is_empty:
            continue
        if geom.geom_type == "LineString":
            folium.PolyLine([(y, x) for x, y in geom.coords], color="#000", weight=3, opacity=0.8).add_to(layer_roads)
        elif geom.geom_type == "MultiLineString":
            for line in geom.geoms:
                folium.PolyLine([(y, x) for x, y in line.coords], color="#000", weight=3, opacity=0.8).add_to(layer_roads)

    # ====================================================================
    # === Estações (estimadas + declaradas) usando GeoJSON Buffers para Performance ===
    # ====================================================================
    for pol, color in color_map.items():
        subset_nearest = nearest[nearest["POLUENTE"] == pol].copy()
        if subset_nearest.empty:
            continue

        # Filtra a cópia em 3857 para cálculo do buffer
        subset_3857 = st_3857_est[st_3857_est["POLUENTE"] == pol].copy()
        
        # --- 1. Representatividade Estimada (GeoJSON Buffer) ---
        layer_est = folium.FeatureGroup(name=f"{pol} — Estimada", show=(pol == "MP25")).add_to(m)
        
        # Prepara os dados de representatividade estimada (série de valores)
        rep_val_series = subset_3857.get("REP_ESPACIAL_m", subset_3857.get("REP_ESPACIAL", 9000)).fillna(9000).astype(float)
        
        # CORREÇÃO: Adicionar 'REP_ESPACIAL_m' ao GeoDataFrame antes de selecioná-la
        subset_3857["REP_ESPACIAL_m"] = rep_val_series 
        
        # Calcula os buffers no CRS métrico (3857)
        buffer_geoseries_3857 = subset_3857.buffer(subset_3857["REP_ESPACIAL_m"], resolution=16)
        
        # Seleciona APENAS colunas de dados não-geométricas necessárias e define a nova geometria
        cols_est = ["ID_OEMA", "UF_left", "POLUENTE", "REP_ESPACIAL_m", "dist_m"]
        subset_buffers_est = subset_3857[cols_est].set_geometry(buffer_geoseries_3857)
        subset_buffers_est = subset_buffers_est.to_crs(4326) # Converte o GeoDataFrame final para 4326

        folium.GeoJson(
            subset_buffers_est.to_json(),
            name=f"{pol} — Estimada",
            style_function=lambda x, est_color=color: {
                "fillColor": est_color,
                "color": est_color,
                "weight": 1.2,
                "fillOpacity": 0.15, 
            },
            tooltip=folium.GeoJsonTooltip(
                fields=cols_est,
                aliases=["Estação:", "UF:", "Poluente:", "Rep. Estimada (m):", "Dist. à Indústria (m):"],
                localize=True,
                style="background-color: white; color: #333333; font-family: arial; font-size: 13px; padding: 10px;",
            )
        ).add_to(layer_est)

        # --- 2. Representatividade Declarada (GeoJSON Buffer) ---
        layer_dec = folium.FeatureGroup(name=f"{pol} — Declarada", show=False).add_to(m)
        
        # Filtra as estações com categoria declarada válida
        subset_dec = subset_3857[subset_3857["REP_ESPACIAL_DECLARADA"].str.lower().isin(CATEGORY_TO_RADIUS_M.keys())].copy()
        
        if not subset_dec.empty:
            # Calcula os raios baseados na categoria declarada
            subset_dec_radius = subset_dec["REP_ESPACIAL_DECLARADA"].str.lower().map(CATEGORY_TO_RADIUS_M)
            
            # Calcula os buffers no CRS métrico (3857)
            buffer_geoseries_3857_dec = subset_dec.buffer(subset_dec_radius, resolution=16)

            # Seleciona APENAS colunas de dados não-geométricas necessárias e define a nova geometria
            cols_dec = ["ID_OEMA", "UF_left", "POLUENTE", "REP_ESPACIAL_DECLARADA"]
            subset_buffers_dec = subset_dec[cols_dec].set_geometry(buffer_geoseries_3857_dec)
            subset_buffers_dec = subset_buffers_dec.to_crs(4326) # Converte o GeoDataFrame final para 4326

            folium.GeoJson(
                subset_buffers_dec.to_json(),
                name=f"{pol} — Declarada",
                style_function=lambda x, dec_color=color: {
                    "fillColor": dec_color,
                    "color": "#000000", # Borda preta
                    "weight": 1,
                    "fillOpacity": 0.3, # Aumentado para melhor visibilidade
                },
                tooltip=folium.GeoJsonTooltip(
                    fields=cols_dec,
                    aliases=["Estação:", "UF:", "Poluente:", "Categoria Declarada:"],
                    localize=True,
                    style="background-color: white; color: #333333; font-family: arial; font-size: 13px; padding: 10px;",
                )
            ).add_to(layer_dec)

    # === Indústrias e Linhas de Conexão (Pontos e Linhas são poucos, mantidos como CircleMarker/PolyLine) ===
    # ... (O restante do código permanece inalterado) ...
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
        # Indústria
        folium.CircleMarker(
            location=(g_ind.y, g_ind.x),
            radius=5,
            color=IND_COLOR, fill=True,
            fill_color=IND_COLOR, fill_opacity=0.9,
            popup=folium.Popup(popup_html, max_width=350),
            tooltip="Indústria mais próxima"
        ).add_to(layer_ind)

        # Linha de conexão
        g_st = row.geometry
        if not g_st.is_empty:
            folium.PolyLine(
                [(g_st.y, g_st.x), (g_ind.y, g_ind.x)],
                color=LINK_COLOR, weight=1, opacity=0.6
            ).add_to(layer_links)

    # === Camada geral (pontos centrais das estações, essencial para clique/tooltip) ===
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

    # === Legenda ===
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
        + "<div><b>Declarações MMA:</b><br>"
        + "".join(
            f"<div style='margin-left:10px;'>{k}: {v} m</div>"
            for k, v in CATEGORY_TO_RADIUS_M.items()
        )
        + "<hr>"
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