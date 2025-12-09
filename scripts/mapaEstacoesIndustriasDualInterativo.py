# -*- coding: utf-8 -*-
import os
import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import Point, LineString


# ==============================================================
# 1) SUA FUNÇÃO ORIGINAL — preservada como está
# ==============================================================

def prepare_dual_map_data(
    rootPath: str | Path | None = None,
    max_distance: float | None = None
) -> dict:
    """
    Prepara dados para o mapa dual estação–indústria em formato puro (dict),
    pronto para ser injetado em um HTML/JS (Leaflet).
    """
    rootPath = Path(rootPath or Path(os.getcwd()).parent)

    stations_file = rootPath / "scripts/rep_espacial/09_formatar_e_salvar_outputs/outputs/estacoes_completa.parquet"
    industries_file = rootPath / "scripts/rep_espacial/01_preprocessamento/inputs/industrial_sites_20250902.gpkg"
    rep_csv = rootPath / "scripts/rep_espacial/09_formatar_e_salvar_outputs/outputs/rep_espacial.csv"
    roads_file = rootPath / "scripts/rep_espacial/02_distancia_vias_e_ind/inputs/roads.parquet"

    # =====================================================
    # === Estações ===
    # =====================================================
    st = gpd.read_parquet(stations_file).to_crs(4326)

    # Correção UF por município
    muni_path = rootPath / "data/shapefiles/BR_Municipios/BR_Municipios_2024.shp"
    if muni_path.exists():
        try:
            municipios = gpd.read_file(muni_path).to_crs(4326)
            possible_uf_cols = ["SIGLA_UF", "UF", "sigla_uf", "NM_UF", "ESTADO"]
            muni_uf_col = next((c for c in possible_uf_cols if c in municipios.columns), None)
            if muni_uf_col is not None:
                municipios["UF_REAL"] = municipios[muni_uf_col]
                st_loc = gpd.sjoin(
                    st, municipios[["UF_REAL", "geometry"]],
                    how="left", predicate="within"
                )
                st = st_loc[st_loc["UF"] == st_loc["UF_REAL"]].copy()
                if "index_right" in st.columns:
                    st = st.drop(columns=["index_right"])
        except:
            pass

    # =====================================================
    # === Poluentes ===
    # =====================================================
    pollutant_map = {
        "PM10": "MP10",
        "PM25": "MP25",
        "PM1": None,
        "VOC": None
    }

    st["POLUENTE"] = st["POLUENTE"].replace(pollutant_map)
    st = st[st["POLUENTE"].notna()].copy()

    # =====================================================
    # === Representatividade CSV ===
    # =====================================================
    rep = pd.read_csv(rep_csv)
    rep["POLUENTE"] = rep["POLUENTE"].replace(pollutant_map)
    rep = rep[rep["POLUENTE"].notna()]

    possible_cols = ["osm_id_mais_prox_valida", "osm_id_valido", "osm_id"]
    col_found = next((c for c in possible_cols if c in rep.columns), None)
    if col_found is None:
        raise KeyError(f"Nenhuma das colunas esperadas {possible_cols} encontrada.")

    rep = rep.rename(columns={col_found: "osm_id"})
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
    # === Associação nearest ===
    # =====================================================
    st_3857, ind_3857 = st.to_crs(3857), ind.to_crs(3857)
    nearest = gpd.sjoin_nearest(
        st_3857,
        ind_3857,
        how="left",
        distance_col="dist_m"
    ).to_crs(4326)

    if max_distance:
        nearest = nearest[nearest["dist_m"] <= max_distance]

    # =====================================================
    # === Filtrar ruas ===
    # =====================================================
    linked_road_ids = nearest["osm_id"].dropna().unique()

    try:
        roads_to_show = roads[roads["osm_id"].isin(linked_road_ids)]
    except KeyError:
        roads_to_show = roads.head(0)

    roads_list = []
    for _, r in roads_to_show.iterrows():
        geom = r.geometry
        if geom.is_empty:
            continue
        if geom.geom_type == "LineString":
            coords = [(float(y), float(x)) for x, y in geom.coords]
            roads_list.append({"coords": coords})
        elif geom.geom_type == "MultiLineString":
            for line in geom.geoms:
                coords = [(float(y), float(x)) for x, y in line.coords]
                roads_list.append({"coords": coords})

    # =====================================================
    # === Todas as estações ===
    # =====================================================
    all_stations_list = []
    for _, row in st.iterrows():
        g = row.geometry
        if g.is_empty:
            continue
        all_stations_list.append({
            "lat": float(g.y),
            "lon": float(g.x),
            "id_oema": str(row.get("ID_OEMA", "")),
            "uf": str(row.get("UF", "")),
        })

    # =====================================================
    # === Por poluente ===
    # =====================================================
    per_pol = {}
    for pol in sorted(nearest["POLUENTE"].dropna().unique()):
        sub = nearest[nearest["POLUENTE"] == pol]
        if sub.empty:
            continue

        stations_list = []
        industries_list = []
        links_list = []
        seen_ind = set()

        for _, row in sub.iterrows():

            g_st = row.geometry
            if g_st.is_empty:
                continue

            st_lat = float(g_st.y)
            st_lon = float(g_st.x)

            rep_val = row.get("REP_ESPACIAL_m", np.nan)
            if pd.isna(rep_val):
                rep_val = row.get("REP_ESPACIAL", np.nan)
            if pd.isna(rep_val):
                rep_val = 9000.0
            rep_val = float(rep_val)

            stations_list.append({
                "lat": st_lat,
                "lon": st_lon,
                "id_oema": str(row.get("ID_OEMA", "")),
                "uf": str(row.get("UF_left", row.get("UF", ""))),
                "rep_m": rep_val,
                "dist_m": float(row.get("dist_m", np.nan)),
            })

            idx_ind = row.get("index_right")
            if idx_ind in ind.index:
                g_ind = ind.loc[idx_ind].geometry
                if not g_ind.is_empty:
                    ind_lat = float(g_ind.y)
                    ind_lon = float(g_ind.x)
                    uf_right = str(row.get("UF_right", row.get("UF", "")))

                    if idx_ind not in seen_ind:
                        industries_list.append({
                            "lat": ind_lat,
                            "lon": ind_lon,
                            "uf": uf_right,
                            "dist_m": float(row.get("dist_m", np.nan))
                        })
                        seen_ind.add(idx_ind)

                    links_list.append({
                        "st_lat": st_lat,
                        "st_lon": st_lon,
                        "ind_lat": ind_lat,
                        "ind_lon": ind_lon
                    })

        per_pol[pol] = {
            "stations": stations_list,
            "industries": industries_list,
            "links": links_list,
        }

    return {
        "roads": roads_list,
        "all_stations": all_stations_list,
        "per_pol": per_pol
    }


# ==============================================================
# 2) NOVA FUNÇÃO — EXPORTA UM GEOJSON POR POLUENTE
# ==============================================================

def export_geojson_por_poluente(rootPath=None):
    """
    Gera um arquivo GEOJSON para cada poluente:
    - buffers serão gerados no HTML (não no arquivo)
    - inclui estações, indústrias, linhas e ruas
    """

    # CORREÇÃO DO CAMINHO
    rootPath = Path(rootPath or Path(os.getcwd()).parent)

    print("🔄 Executando prepare_dual_map_data()...")
    data = prepare_dual_map_data(rootPath=rootPath)

    per_pol = data["per_pol"]
    roads = data["roads"]

    out_dir = rootPath / "_static" / "representatividade" / "uso_industria_geojson"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"📁 Pasta de saída: {out_dir}")


    print(f"📁 Pasta de saída: {out_dir}")

    for pol, block in per_pol.items():

        features = []

        # ESTAÇÕES
        for s in block["stations"]:
            features.append({
                "geometry": Point(s["lon"], s["lat"]),
                "properties": {
                    "type": "station",
                    "ID_OEMA": s["id_oema"],
                    "UF": s["uf"],
                    "REP_ESPACIAL": s["rep_m"],
                    "dist_m": s["dist_m"],
                    "POLUENTE": pol
                }
            })

        # INDÚSTRIAS
        for ind in block["industries"]:
            features.append({
                "geometry": Point(ind["lon"], ind["lat"]),
                "properties": {
                    "type": "industry",
                    "UF": ind["uf"],
                    "dist_m": ind["dist_m"],
                    "POLUENTE": pol
                }
            })

        # LINKS
        for lk in block["links"]:
            geom = LineString([
                (lk["st_lon"], lk["st_lat"]),
                (lk["ind_lon"], lk["ind_lat"])
            ])
            features.append({
                "geometry": geom,
                "properties": {
                    "type": "link",
                    "POLUENTE": pol
                }
            })

        # RUAS
        for r in roads:
            coords = [(c[1], c[0]) for c in r["coords"]]
            geom = LineString(coords)
            features.append({
                "geometry": geom,
                "properties": {
                    "type": "road",
                    "POLUENTE": pol
                }
            })

        # GeoDataFrame
        gdf = gpd.GeoDataFrame(
            [f["properties"] for f in features],
            geometry=[f["geometry"] for f in features],
            crs=4326
        )

        out_file = out_dir / f"{pol}.geojson"
        gdf.to_file(out_file, driver="GeoJSON")

        print(f"✅ {pol}.geojson salvo — {len(gdf)} features")

    print("\n🎉 **Todos os geojson foram gerados com sucesso!**")


# ==============================================================
# 3) MAIN – executa pelo terminal
# ==============================================================

if __name__ == "__main__":
    export_geojson_por_poluente()
