# -*- coding: utf-8 -*-
"""
Mapa Folium: Representatividade Temporal (geração + mapa)
---------------------------------------------------------
1️⃣ Faz join entre REP_TEMPORAL.csv e Monitoramento_QAr_BR.csv
2️⃣ Gera o arquivo rep_temporal_joined.csv
3️⃣ Cria o mapa interativo com popups e barras horizontais
    - Apenas pontos com pelo menos um valor válido (diário, mensal ou anual)
    - Um único ponto por estação
"""

import pandas as pd
import geopandas as gpd
import folium
from folium.plugins import MiniMap, Fullscreen
from pathlib import Path
import re

# =========================
# CONFIGURAÇÕES
# =========================
ROOT = Path("/home/nobre/Notebooks/RQAR_2025_book")
REP_CSV = ROOT / "data/MQAr_averages/REP_TEMPORAL.csv"
STATIONS_CSV = ROOT / "data/Monitoramento_QAr_BR.csv"
OUTPUT_DIR = ROOT / "data/outputs"
OUTPUT_JOINED = OUTPUT_DIR / "rep_temporal_joined.csv"
OUTPUT_HTML = ROOT / "_static/representatividade/rep_temporal_map.html"

# =========================
# FUNÇÕES AUXILIARES
# =========================
def _extract_id_mma(val):
    """Extrai o ID_MMA (ex.: SP0248) do ID_MMA_COMPLETO"""
    if not isinstance(val, str):
        return None
    m = re.match(r"^([A-Z]{2}\d{4})", val.strip().upper())
    return m.group(1) if m else None

def _bar(val, cor="#4c78a8"):
    """Gera barra horizontal de preenchimento conforme o valor (%)"""
    if pd.isna(val):
        return "<span style='color:#666'>—</span>"
    val = float(val)
    width = max(0, min(100, val))
    return (
        f"<div style='display:flex;align-items:center;gap:6px;'>"
        f"<div style='height:10px;width:120px;border:1px solid #aaa;'>"
        f"<div style='height:100%;width:{width}%;background:{cor};'></div>"
        f"</div><span>{val:.1f}%</span></div>"
    )

def get_color(v):
    """Define cor do círculo conforme a representatividade diária"""
    if pd.isna(v): return "#999999"
    if v < 25: return "#d73027"
    elif v < 50: return "#fc8d59"
    elif v < 75: return "#fee08b"
    elif v < 90: return "#d9ef8b"
    else: return "#1a9850"

def add_legend(m):
    """Adiciona legenda compacta fixa"""
    legend_html = """
    <div style="
        position: fixed; 
        bottom: 50px; left: 50px; width: 180px; 
        z-index:9999; font-size:14px;
        background-color: white; padding: 10px; border:2px solid grey;
        ">
        <b>Representatividade (%)</b><br>
        <i style="background:#d73027;width:18px;height:18px;float:left;margin-right:5px;"></i> 0–25<br>
        <i style="background:#fc8d59;width:18px;height:18px;float:left;margin-right:5px;"></i> 25–50<br>
        <i style="background:#fee08b;width:18px;height:18px;float:left;margin-right:5px;"></i> 50–75<br>
        <i style="background:#d9ef8b;width:18px;height:18px;float:left;margin-right:5px;"></i> 75–90<br>
        <i style="background:#1a9850;width:18px;height:18px;float:left;margin-right:5px;"></i> 90–100<br>
        <i style="background:#999999;width:18px;height:18px;float:left;margin-right:5px;"></i> sem dado
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))
    return m

# =========================
# FUNÇÃO PRINCIPAL
# =========================
def build_map_rep_temporal():
    print("📘 Lendo arquivos de entrada...")
    rep = pd.read_csv(REP_CSV)
    st = pd.read_csv(STATIONS_CSV)

    # Normaliza IDs
    rep["ID_MMA_COMPLETO"] = rep.get("ID_MMA_COMPLETO", rep.get("ID_MMA_COMPLETO", "")).astype(str).str.strip().str.upper()
    rep["ID_MMA"] = rep["ID_MMA_COMPLETO"].apply(_extract_id_mma)
    st["ID_MMA_COMPLETO"] = st.get("ID_MMA_COMPLETO", "").astype(str).str.strip().str.upper()
    st["ID_MMA"] = st["ID_MMA"].astype(str).str.strip().str.upper()

    # Join duplo
    print("🔗 Fazendo join por ID_MMA_COMPLETO...")
    g1 = st.merge(rep, on="ID_MMA_COMPLETO", how="left")
    if g1["PRCNT_REP_TEMPORAL_DIARIA"].isna().all():
        print("⚠️ Nenhuma correspondência via ID_MMA_COMPLETO, tentando por ID_MMA...")
        g1 = st.merge(rep, on="ID_MMA", how="left")

    # Garante diretório e salva CSV
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    g1.to_csv(OUTPUT_JOINED, index=False)
    print(f"💾 Arquivo unido salvo em: {OUTPUT_JOINED}")

    # Filtra válidos para o mapa
    df = g1.copy()
    df = df[df["LATITUDE"].notna() & df["LONGITUDE"].notna()].copy()
    mask_valida = (
        df["PRCNT_REP_TEMPORAL_DIARIA"].notna() |
        df["PRCNT_REP_TEMPORAL_MENSAL"].notna() |
        df["PRCNT_REP_TEMPORAL_ANUAL"].notna()
    )
    df = df.loc[mask_valida].copy()
    print(f"📍 Estações válidas para o mapa: {len(df)}")

    if df.empty:
        print("⚠️ Nenhum ponto com dados válidos encontrado.")
        return

    # Cria GeoDataFrame
    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df["LONGITUDE"], df["LATITUDE"]), crs="EPSG:4326")

    # --- Mapa ---
    br_bounds = [[-34.0, -74.0], [6.0, -34.0]]
    m = folium.Map(location=[-14.2, -52.9], zoom_start=4, tiles="cartodbpositron", control_scale=True)
    m.fit_bounds(br_bounds)
    Fullscreen(position="topright").add_to(m)
    MiniMap(toggle_display=True).add_to(m)

    # --- Marcadores ---
    for _, row in gdf.iterrows():
        val_diaria = row.get("PRCNT_REP_TEMPORAL_DIARIA")
        val_mensal = row.get("PRCNT_REP_TEMPORAL_MENSAL")
        val_anual = row.get("PRCNT_REP_TEMPORAL_ANUAL")
        color = get_color(val_diaria)

        popup_html = f"""
        <div style="font-size:13px;">
            <b>{row.get('CIDADE', '')}</b> ({row.get('UF', '')})<br>
            <b>ID:</b> {row.get('ID_MMA_COMPLETO', '')}<hr style="margin:4px 0;">
            <b>Temporal Diária:</b> {_bar(val_diaria, '#4c78a8')}<br>
            <b>Temporal Mensal:</b> {_bar(val_mensal, '#72b7b2')}<br>
            <b>Temporal Anual:</b> {_bar(val_anual, '#e15759')}
        </div>
        """
        popup = folium.Popup(popup_html, max_width=320)

        folium.CircleMarker(
            location=(row["LATITUDE"], row["LONGITUDE"]),
            radius=6,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.9,
            weight=1,
            popup=popup,
            tooltip=f"{row['CIDADE']} ({row['UF']})",
        ).add_to(m)

    # --- Legenda e salvar ---
    add_legend(m)
    m.save(str(OUTPUT_HTML))
    print(f"✅ Mapa salvo em: {OUTPUT_HTML}")
    return m, str(OUTPUT_HTML)


# =========================
# EXECUÇÃO DIRETA
# =========================
if __name__ == "__main__":
    print("🚀 Gerando CSV unido e mapa de representatividade temporal...")
    build_map_rep_temporal()
    print("✅ Concluído!")
