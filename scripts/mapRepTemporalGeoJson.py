import pandas as pd
import geopandas as gpd
from pathlib import Path
import json
import re

ROOT = Path("/home/nobre/Notebooks/RQAR_2025_book")

REP_CSV  = ROOT / "data/MQAr_averages/REP_TEMPORAL.csv"
ST_CSV   = ROOT / "data/Monitoramento_QAr_BR.csv"

OUT_DIR = ROOT / "_static/representatividade/rep_temporal"
OUT_DIR.mkdir(exist_ok=True, parents=True)

OUT_GJ = OUT_DIR / "rep_temporal.geojson"


def _extract_id_mma(val):
    if not isinstance(val, str): return None
    m = re.match(r"^([A-Z]{2}\d{4})", val.strip().upper())
    return m.group(1) if m else None


def _format_years(val):
    if pd.isna(val): return None
    anos = [a.strip() for a in str(val).split(",") if a.strip()]
    return sorted(set(anos))


def gerar_geojson_unico():
    rep = pd.read_csv(REP_CSV)
    st  = pd.read_csv(ST_CSV)

    rep["ID_MMA_COMPLETO"] = rep["ID_MMA_COMPLETO"].astype(str).str.upper()
    rep["ID_MMA"] = rep["ID_MMA_COMPLETO"].apply(_extract_id_mma)

    st["ID_MMA_COMPLETO"] = st["ID_MMA_COMPLETO"].astype(str).str.upper()
    st["ID_MMA"] = st["ID_MMA"].astype(str).str.upper()

    # Primeiro tenta ID_MMA_COMPLETO
    g = st.merge(rep, on="ID_MMA_COMPLETO", how="left")

    # Se tudo NA, tenta ID_MMA simples
    if g["PRCNT_REP_TEMPORAL_DIARIA"].isna().all():
        g = st.merge(rep, on="ID_MMA", how="left")

    g["ANOS_MONITORADOS"] = g["ANOS_MONITORADOS"].apply(_format_years)

    gdf = gpd.GeoDataFrame(
        g,
        geometry=gpd.points_from_xy(g["LONGITUDE"], g["LATITUDE"]),
        crs="EPSG:4326"
    )

    # só estações com alguma representatividade válida
    mask = (
        gdf["PRCNT_REP_TEMPORAL_DIARIA"].notna() |
        gdf["PRCNT_REP_TEMPORAL_MENSAL"].notna() |
        gdf["PRCNT_REP_TEMPORAL_ANUAL"].notna()
    )
    gdf = gdf.loc[mask]

    gdf.to_file(OUT_GJ, driver="GeoJSON")
    print("✔ GeoJSON gerado em:", OUT_GJ)


gerar_geojson_unico()
