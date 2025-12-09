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

    rootPath = Path(rootPath or os.path.dirname(os.getcwd()))
    stations_file = rootPath / "scripts/rep_espacial/09_formatar_e_salvar_outputs/outputs/estacoes_completa.parquet"
    industries_file = rootPath / "scripts/rep_espacial/01_preprocessamento/inputs/industrial_sites_20250902.gpkg"
    rep_csv = rootPath / "scripts/rep_espacial/09_formatar_e_salvar_outputs/outputs/rep_espacial.csv"
    roads_file = rootPath / "scripts/rep_espacial/02_distancia_vias_e_ind/inputs/roads.parquet"

    # =====================================================
    # === Estações ===
    # =====================================================
    st = gpd.read_parquet(stations_file).to_crs(4326)

    # =====================================================
    # === Correção geográfica de UF via municípios — MELHOR MÉTODO ===
    # =====================================================
    muni_path = rootPath / "data/shapefiles/BR_Municipios/BR_Municipios_2024.shp"

    if muni_path.exists():
        try:
            municipios = gpd.read_file(muni_path).to_crs(4326)

            # detectar coluna da sigla UF
            possible_uf_cols = ["SIGLA_UF", "UF", "sigla_uf", "NM_UF", "ESTADO"]
            muni_uf_col = next((c for c in possible_uf_cols if c in municipios.columns), None)

            if muni_uf_col is None:
                print("⚠ Municípios carregados, mas sem coluna UF válida. Pulando correção de UF.")
            else:
                municipios["UF_REAL"] = municipios[muni_uf_col]

                # join: ponto → município real
                st_loc = gpd.sjoin(
                    st,
                    municipios[["UF_REAL", "geometry"]],
                    how="left",
                    predicate="within"
                )

                # detectar inconsistências
                st_erradas = st_loc[st_loc["UF"] != st_loc["UF_REAL"]]

                if len(st_erradas) > 0:

                    print("")

                # manter corretas
                st = st_loc[st_loc["UF"] == st_loc["UF_REAL"]].copy()

                if "index_right" in st.columns:
                    st = st.drop(columns=["index_right"])

        except Exception as e:
            print(f"⚠ Erro ao aplicar correção via municípios: {e}")
            print("⚠ Prosseguindo sem correção de UF.")

    else:
        print(f"⚠ Arquivo de municípios não encontrado em {muni_path}. Prosseguindo sem correção de UF.")

    # =====================================================
    # === Limpeza dos poluentes ===
    # =====================================================
    pollutant_map = {
        "PM10": "MP10",
        "PM25": "MP25",
        "PM1": None,
        "VOC": None
    }

    st["POLUENTE"] = st["POLUENTE"].replace(pollutant_map)
    st = st[st["POLUENTE"].notna()]

    # =====================================================
    # === REP (CSV com representatividade) ===
    # =====================================================
    rep = pd.read_csv(rep_csv)

    rep["POLUENTE"] = rep["POLUENTE"].replace(pollutant_map)
    rep = rep[rep["POLUENTE"].notna()]

    possible_cols = ["osm_id_mais_prox_valida", "osm_id_valido", "osm_id"]
    col_found = next((c for c in possible_cols if c in rep.columns), None)

    if col_found is None:
        raise KeyError(f"Nenhuma das colunas esperadas {possible_cols} foi encontrada em {rep_csv}")

    rep = rep.rename(columns={col_found: "osm_id"})

    # Integrar OSM_ID ao GeoDataFrame das estações
    st = st.merge(rep[["ID_OEMA", "osm_id"]], on="ID_OEMA", how="left")

    # =====================================================
    # === Indústrias ===
    # =====================================================
    ind = gpd.read_file(industries_file).to_crs(4326)
    poly_mask = ind.geometry.geom_type.isin(["Polygon", "MultiPolygon"])
    if poly_mask.any():
        ind.loc[poly_mask, "geometry"] = (
            ind.loc[poly_mask].to_crs(3857).centroid.to_crs(4326)
        )

    # =====================================================
    # === Ruas ===
    # =====================================================
    roads = gpd.read_parquet(roads_file).to_crs(4326)

    # =====================================================
    # === Associação estação–indústria ===
    # =====================================================
    st_3857, ind_3857 = st.to_crs(3857), ind.to_crs(3857)

    nearest = gpd.sjoin_nearest(
        st_3857,
        ind_3857,
        how="left",
        distance_col="dist_m"
    )

    if max_distance:
        nearest = nearest[nearest["dist_m"] <= max_distance]

    nearest = nearest.to_crs(4326)

    # =====================================================
    # === Centro do mapa ===
    # =====================================================
    minx, miny, maxx, maxy = st.total_bounds
    center_lat, center_lon = (miny + maxy) / 2, (minx + maxx) / 2

    brazil_bounds = [[-34.0, -74.0], [6.0, -32.0]]

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=5,
        tiles="cartodbpositron",
        min_zoom=4,
        max_bounds=True
    )

    m.fit_bounds(brazil_bounds)

    # =====================================================
    # === Paleta ===
    # =====================================================
    palette = {
        "CO": "#A8E6CF",
        "NO2": "#84C1FF",
        "O3": "#BDB2FF",
        "MP25": "#FFD6A5",
        "MP10": "#FFADAD",
        "PTS": "#FFDAC1",
        "SO2": "#E2F0CB"
    }

    IND_COLOR = "#E57373"
    ALL_ST_COLOR = "#64B5F6"
    LINK_COLOR = "#B0BEC5"

    color_map = {
        p: palette.get(p, "#CCCCCC")
        for p in nearest["POLUENTE"].dropna().unique()
    }

    # =====================================================
    # === Camadas ===
    # =====================================================
    layer_roads = folium.FeatureGroup(name="Ruas (pretas)", show=True).add_to(m)
    layer_all = folium.FeatureGroup(name="Todas as estações", show=True).add_to(m)
    layer_ind = folium.FeatureGroup(name="Indústrias", show=True).add_to(m)
    layer_links = folium.FeatureGroup(name="Conexões estação–indústria", show=True).add_to(m)

    # =====================================================
    # === Ruas filtradas ===
    # =====================================================
    linked_road_ids = nearest["osm_id"].dropna().unique()
    try:
        roads_to_show = roads[roads["osm_id"].isin(linked_road_ids)]
    except KeyError:
        roads_to_show = roads.head(0)

    for _, r in roads_to_show.iterrows():
        geom = r.geometry
        if geom.is_empty:
            continue
        if geom.geom_type == "LineString":
            folium.PolyLine([(y, x) for x, y in geom.coords],
                            color="#000", weight=3, opacity=0.8).add_to(layer_roads)
        elif geom.geom_type == "MultiLineString":
            for line in geom.geoms:
                folium.PolyLine([(y, x) for x, y in line.coords],
                                color="#000", weight=3, opacity=0.8).add_to(layer_roads)

    # =====================================================
    # === Estações por poluente ===
    # =====================================================
    for pol, color in color_map.items():
        subset = nearest[nearest["POLUENTE"] == pol]
        if subset.empty:
            continue

        layer_est = folium.FeatureGroup(
            name=f"{pol} — Estimada",
            show=(pol == "MP25")
        ).add_to(m)

        for _, row in subset.iterrows():
            g = row.geometry
            if g.is_empty:
                continue

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
                fill=True,
                fill_color=color, fill_opacity=0.15,
                popup=folium.Popup(popup_html_est, max_width=350),
                tooltip=f"{row.get('ID_OEMA','—')} ({pol})"
            ).add_to(layer_est)

    # =====================================================
    # === Indústrias ===
    # =====================================================
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
            color=IND_COLOR,
            fill=True,
            fill_color=IND_COLOR,
            fill_opacity=0.9,
            popup=folium.Popup(popup_html, max_width=350),
            tooltip="Indústria mais próxima"
        ).add_to(layer_ind)

        g_st = row.geometry
        if not g_st.is_empty:
            folium.PolyLine(
                [(g_st.y, g_st.x), (g_ind.y, g_ind.x)],
                color=LINK_COLOR,
                weight=1,
                opacity=0.6
            ).add_to(layer_links)

    # =====================================================
    # === Todas as estações ===
    # =====================================================
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

    # =====================================================
    # === Extras ===
    # =====================================================
    MiniMap(toggle_display=True, position="bottomright").add_to(m)
    Fullscreen().add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)

    # =====================================================
    # === Legenda ===
    # =====================================================
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
        + "<div><span style='background:#000;width:14px;height:14px;margin-right:6px;"
        "border:1px solid #555;display:inline-block;'></span>Ruas</div>"
        + f"<div><span style='background:{IND_COLOR};width:14px;height:14px;"
        "margin-right:6px;border:1px solid #555;display:inline-block;'></span>Indústrias</div>"
        + "</div>"
    )
    m.get_root().html.add_child(folium.Element(legend_html))

    # =====================================================
    # === Salvar ===
    # =====================================================
    if save:
        out_dir = rootPath / "_static" / "representatividade"
        out_dir.mkdir(parents=True, exist_ok=True)
        output_file = out_dir / "mapa_estacoes_industrias_dual.html"
        m.save(str(output_file))
        rel_path = "../_static/representatividade/mapa_estacoes_industrias_dual.html"
        return m, rel_path

    return m, None
