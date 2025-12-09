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

def _extract_id_mma(val):
    if not isinstance(val, str): return None
    m = re.match(r"^([A-Z]{2}\d{4})", val.strip().upper())
    return m.group(1) if m else None

def _format_years(val):
    if pd.isna(val): return None
    # Converte para string, separa por vírgula e remove espaços
    anos = [a.strip() for a in str(val).split(",") if a.strip()]
    return sorted(set(anos))

def gerar_geojsons():
    rep = pd.read_csv(REP_CSV)
    st  = pd.read_csv(ST_CSV)

    rep["ID_MMA_COMPLETO"] = rep["ID_MMA_COMPLETO"].astype(str).str.upper()
    rep["ID_MMA"] = rep["ID_MMA_COMPLETO"].apply(_extract_id_mma)

    st["ID_MMA_COMPLETO"] = st["ID_MMA_COMPLETO"].astype(str).str.upper()
    st["ID_MMA"] = st["ID_MMA"].astype(str).str.upper()

    # Tenta primeiro pelo ID completo
    g = st.merge(rep, on="ID_MMA_COMPLETO", how="left")

    # Se vazio ou falhar muito, tenta ID_MMA simples (fallback)
    if g["PRCNT_REP_TEMPORAL_DIARIA"].isna().all():
        g = st.merge(rep, on="ID_MMA", how="left")

    # --- ALTERAÇÃO AQUI ---
    # Processa os anos monitorados
    g["ANOS_MONITORADOS"] = g["ANOS_MONITORADOS_y"].apply(_format_years)
    
    # Processa os anos representativos (nova coluna)
    # Verifica se a coluna existe antes de aplicar para evitar erro
    if "ANOS_REPRESENTATIVOS" in g.columns:
        g["ANOS_REPRESENTATIVOS"] = g["ANOS_REPRESENTATIVOS"].apply(_format_years)
    else:
        g["ANOS_REPRESENTATIVOS"] = None
    # ----------------------

    gdf = gpd.GeoDataFrame(
        g,
        geometry=gpd.points_from_xy(g["LONGITUDE"], g["LATITUDE"]),
        crs="EPSG:4326"
    )

    # função auxiliar
    def salvar(mask_col, nome):
        out = OUT_DIR / nome
        # Filtra apenas onde tem dados na coluna de porcentagem
        sub = gdf[gdf[mask_col].notna()].copy()
        sub.to_file(out, driver="GeoJSON")
        print("✔ gerado:", out)

    salvar("PRCNT_REP_TEMPORAL_DIARIA", "rep_temporal_diario.geojson")
    salvar("PRCNT_REP_TEMPORAL_MENSAL", "rep_temporal_mensal.geojson")
    salvar("PRCNT_REP_TEMPORAL_ANUAL",  "rep_temporal_anual.geojson")

gerar_geojsons()