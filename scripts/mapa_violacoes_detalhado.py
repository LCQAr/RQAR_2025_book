# -*- coding: utf-8 -*-
"""
Mapa de Violações da Qualidade do Ar — CONAMA 506/2024
- 24h (MP10, MP2,5, SO2, PTS, Fumaça): média diária (00–24h)  [CONAMA 506/2024 Anexo I]
- 1h (NO2): máxima média horária do dia                      [nota ²]
- 8h (O3, CO): máxima média móvel 8h do dia                  [nota ³]
- Anual: média aritmética anual; PTS anual: média geométrica [nota ¹ e ⁴]
Units: CO em ppm; demais em µg/m³ (§4º, art. 3º)
"""

import os
import pandas as pd
import geopandas as gpd
import folium
from folium import FeatureGroup
from folium.plugins import Fullscreen, MiniMap
from pathlib import Path
import json
import numpy as np

def mapa_violacoes_detalhado(rootPath=None, overwrite=False):
    print("🚀 Gerando mapa de violações...")

    # =======================
    # Caminhos principais
    # =======================
    rootPath = Path(rootPath or os.path.dirname(os.getcwd()))
    data_dir = rootPath / "data"
    averages_dir = data_dir / "MQAr_averages"
    meta_csv = data_dir / "Monitoramento_QAr_BR.csv"
    fases_csv = data_dir / "fases_CONAMA506.csv"
    output_dir = data_dir / "outputs"
    output_dir.mkdir(exist_ok=True)
    csv_violacoes = output_dir / "violacoes_estacoes.csv"

    static_dir = rootPath / "_static" / "mapas"
    static_dir.mkdir(parents=True, exist_ok=True)
    html_out = static_dir / "mapa_violacoes_detalhado.html"

    # =======================
    # Leitura de metadados
    # =======================
    meta = pd.read_csv(meta_csv)
    fases = pd.read_csv(fases_csv)

    fases["pollutant"] = fases["pollutant"].astype(str).str.strip().str.upper()
    fases["phase"] = fases["phase"].astype(str).str.strip().str.upper()

    fases = fases[
        (~fases["phase"].isin(["", "NAN", "NONE", "NULL"])) &
        (~fases["pollutant"].isin(["", "NAN", "NONE", "NULL"]))
    ]

    poluentes_validos = ["CO", "SO2", "NO2", "O3", "MP10", "MP25", "PTS"]  # foco do mapa
    fases = fases[fases["pollutant"].isin(poluentes_validos)]

    poluente_nomes = {
        "CO": "CO",
        "SO2": "SO₂",
        "NO2": "NO₂",
        "O3": "O₃",
        "MP10": "MP₁₀",
        "MP25": "MP₂.₅",
        "PTS": "PTS"
    }

    padroes_brutos = [p for p in fases["phase"].unique() if "E" not in p]
    ordem_padroes = ["PI-1", "PI-2", "PI-3", "PI-4", "PF"]
    padroes = sorted(padroes_brutos, key=lambda x: ordem_padroes.index(x) if x in ordem_padroes else 99)
    poluentes = [p for p in poluentes_validos if p in fases["pollutant"].unique()]

    meta = meta[meta["POLUENTE"].isin(poluentes)]

    # =======================
    # Funções auxiliares (CONAMA 506)
    # =======================
    def media_geometrica(x):
        x = pd.to_numeric(x, errors="coerce").dropna()
        x = x[x > 0]
        if len(x) == 0:
            return np.nan
        return float(np.exp(np.mean(np.log(x))))

    def calcular_metricas(df, ave_time: str, pol: str):
        """
        Retorna DataFrame com coluna de referência para comparação com o padrão,
        obedecendo às métricas do Anexo I da CONAMA 506/2024.

        Saídas possíveis:
          - Para 24h/8h/1h: tabela diária com colunas ['DATA_DIA','VALOR_METRICA']
          - Para 'anual'   : tabela anual com colunas ['ANO','VALOR_METRICA']
        """
        # Normalizar DATA
        if "DATA" not in df.columns:
            poss = [c for c in df.columns if "DATA" in c.upper() or "DATE" in c.upper()]
            if poss:
                df = df.rename(columns={poss[0]: "DATA"})
            else:
                return None

        df["DATA"] = pd.to_datetime(df["DATA"], errors="coerce")
        df = df.dropna(subset=["DATA", "VALOR"]).sort_values("DATA")
        if df.empty:
            return None

        at = str(ave_time).strip().lower()

        # ---- 24 horas: média diária (00–24h) ----
        if at == "24":
            df["DATA_DIA"] = df["DATA"].dt.floor("D")
            # Para 24h, usamos média aritmética diária (CONAMA 506)
            df24 = df.groupby("DATA_DIA", as_index=False)["VALOR"].mean()
            df24 = df24.rename(columns={"VALOR": "VALOR_METRICA"})
            return df24

        # ---- 1 hora: máxima média horária do dia (NO2) ----
        if at == "1":
            df["DATA_DIA"] = df["DATA"].dt.floor("D")
            # Se os dados já são horários, basta o máximo do dia
            df1 = df.groupby("DATA_DIA", as_index=False)["VALOR"].max()
            df1 = df1.rename(columns={"VALOR": "VALOR_METRICA"})
            return df1

        # ---- 8 horas: máxima média móvel 8h do dia (O3, CO) ----
        if at == "8":
            # rolling de 8 amostras (assumindo frequência horária)
            df = df.set_index("DATA").sort_index()
            df["mm8h"] = df["VALOR"].rolling(window=8, min_periods=6).mean()
            df = df.reset_index()
            df["DATA_DIA"] = df["DATA"].dt.floor("D")
            df8 = df.groupby("DATA_DIA", as_index=False)["mm8h"].max()
            df8 = df8.rename(columns={"mm8h": "VALOR_METRICA"})
            return df8

        # ---- Anual: média aritmética; PTS anual = geométrica ----
        if at == "anual":
            df["ANO"] = df["DATA"].dt.year
            if pol == "PTS":
                dfy = df.groupby("ANO", as_index=False).agg(VALOR_METRICA=("VALOR", media_geometrica))
            else:
                dfy = df.groupby("ANO", as_index=False)["VALOR"].mean().rename(columns={"VALOR": "VALOR_METRICA"})
            return dfy

        return None

    # =======================
    # Cálculo de violações
    # =======================
    registros = []

    for pol in poluentes:
        ave_times_pol = (
            fases.loc[fases["pollutant"] == pol, "ave_time"]
            .astype(str).str.lower().unique()
        )

        for ave_folder in ave_times_pol:
            pasta = averages_dir / ave_folder / pol
            if not pasta.exists():
                continue

            fases_filt = fases[
                (fases["pollutant"] == pol) &
                (fases["ave_time"].astype(str).str.lower() == ave_folder)
            ]
            if fases_filt.empty:
                continue

            for arq in pasta.glob("*.csv"):
                try:
                    df = pd.read_csv(arq)
                except Exception:
                    continue
                if "VALOR" not in df.columns:
                    continue

                df_calc = calcular_metricas(df, ave_folder, pol)  # << CONAMA 506
                if df_calc is None or df_calc.empty:
                    continue

                est_id = arq.stem

                # Escolher coluna temporal para agregar por ano
                if "DATA_DIA" in df_calc.columns:
                    df_calc["ANO"] = pd.to_datetime(df_calc["DATA_DIA"]).dt.year

                for _, fase in fases_filt.iterrows():
                    # Limite (aceita y1/y0/y1_val)
                    lim = None
                    for col in ["y1", "y0", "y1_val"]:
                        if col in fase and pd.notna(fase[col]):
                            try:
                                lim = float(str(fase[col]).replace(",", "."))
                                break
                            except Exception:
                                continue
                    if lim is None:
                        continue

                    # Contagem/percentual de excedências por ano
                    if "ANO" in df_calc.columns and "VALOR_METRICA" in df_calc.columns:
                        for ano, grp in df_calc.groupby("ANO"):
                            total = len(grp)
                            viol = int((grp["VALOR_METRICA"] > lim).sum())
                            pct = round((viol / total) * 100, 2) if total else 0.0

                            registros.append({
                                "ID_MMA_COMPLETO": est_id,
                                "POLUENTE": pol,
                                "ANO": int(ano),
                                "PADRAO": fase["phase"],
                                "LIMITE": lim,
                                "VIOLACOES": viol,
                                "PCT_EXC": pct,
                                "TIPO_MEDIA": ave_folder
                            })
                    else:
                        # Caso anual já agregado (sem DATA_DIA)
                        for _, linha in df_calc.iterrows():
                            ano = int(linha["ANO"])
                            valor = float(linha["VALOR_METRICA"])
                            viol = int(valor > lim)
                            registros.append({
                                "ID_MMA_COMPLETO": est_id,
                                "POLUENTE": pol,
                                "ANO": ano,
                                "PADRAO": fase["phase"],
                                "LIMITE": lim,
                                "VIOLACOES": viol,
                                "PCT_EXC": viol * 100.0,
                                "TIPO_MEDIA": ave_folder
                            })

    df_viol = pd.DataFrame(registros)

    # Remover 2025, se desejado (basta comentar a linha abaixo para manter)
    df_viol = df_viol[df_viol["ANO"] != 2025]

    if df_viol.empty:
        raise RuntimeError("❌ Nenhum dado de violação foi calculado.")

    anos_disponiveis = sorted(df_viol["ANO"].unique())
    df_viol.to_csv(csv_violacoes, index=False)

    # =======================
    # GeoJoin com metadados
    # =======================
    meta_coords = meta.drop_duplicates("ID_MMA")[["ID_MMA", "LATITUDE", "LONGITUDE", "POLUENTE", "ID_OEMA"]].copy()
    meta_coords["LATITUDE"] = meta_coords["LATITUDE"].astype(str).str.replace(",", ".", regex=False)
    meta_coords["LONGITUDE"] = meta_coords["LONGITUDE"].astype(str).str.replace(",", ".", regex=False)
    meta_coords["LATITUDE"] = pd.to_numeric(meta_coords["LATITUDE"], errors="coerce")
    meta_coords["LONGITUDE"] = pd.to_numeric(meta_coords["LONGITUDE"], errors="coerce")
    meta_coords = meta_coords.dropna(subset=["LATITUDE", "LONGITUDE"]).reset_index(drop=True)

    gdf = gpd.GeoDataFrame(
        meta_coords,
        geometry=gpd.points_from_xy(meta_coords["LONGITUDE"], meta_coords["LATITUDE"]),
        crs="EPSG:4326"
    )

    anos = anos_disponiveis
    ANO_INICIAL = max(anos)
    PADRAO_INICIAL = padroes[0] if padroes else ""

    # =======================
    # Mapa base
    # =======================
    m = folium.Map(
        location=[-14.2, -51.9], zoom_start=4.2,
        max_bounds=True,
        min_lat=-35, max_lat=6,
        min_lon=-74, max_lon=-34,
        tiles="CartoDB positron"
    )
    Fullscreen(position="topleft").add_to(m)
    MiniMap(toggle_display=True).add_to(m)

    # =======================
    # Criação dos FeatureGroups
    # =======================
    grupos = {}
    layer_vars = {}

    def achar_base_id(id_completo: str):
        match = gdf[gdf["ID_MMA"].astype(str) == str(id_completo)]
        if not match.empty:
            return match.iloc[0]
        match = gdf[gdf["ID_MMA"].apply(lambda x: str(id_completo).startswith(str(x)))]
        if not match.empty:
            return match.iloc[0]
        return None

    max_viol_global = int(df_viol["VIOLACOES"].max() or 1)

    def get_color(n):
        ratio = min(1, max(0, n / max_viol_global))
        if ratio < 0.5:
            r = int(510 * ratio)
            g = 200
            b = 0
        else:
            r = 255
            g = int(200 - 400 * (ratio - 0.5))
            b = 0
        return f"rgb({r},{max(g,0)},{b})"

    for padrao in padroes:
        for ano in anos:
            for pol in poluentes:
                df_filt = df_viol[
                    (df_viol["PADRAO"].str.strip().str.upper() == padrao) &
                    (df_viol["ANO"] == ano) &
                    (df_viol["POLUENTE"] == pol)
                ]
                if df_filt.empty:
                    continue

                nome_grupo = f"{padrao} - {ano} - {pol}"
                show_initial = (padrao == PADRAO_INICIAL and ano == ANO_INICIAL and pol == poluentes[0])
                grupo = FeatureGroup(name=nome_grupo, show=show_initial)

                for _, row in df_filt.iterrows():
                    base_row = achar_base_id(row["ID_MMA_COMPLETO"])
                    if base_row is None:
                        continue
                    total_viol = int(row["VIOLACOES"])
                    color = get_color(total_viol)
                    geom = base_row.geometry

                    unidade = "ppm" if pol == "CO" else "µg/m³"  # << CONAMA 506

                    popup_html = f"""
                    <div style="font-family:Arial; font-size:12px;">
                      <b>{base_row['ID_MMA']}</b><br>
                      <b>Órgão:</b> {base_row['ID_OEMA']}<br>
                      <b>Poluente:</b> {poluente_nomes.get(pol, pol)}<br>
                      <b>Padrão:</b> {padrao}<br>
                      <b>Ano:</b> {ano}<br>
                      <b>Limite:</b> {row['LIMITE']} {unidade}<br>
                      <b>Violações:</b> {total_viol}<br>
                      <b>Excedência:</b> {row['PCT_EXC']}%
                    </div>
                    """
                    folium.CircleMarker(
                        location=[geom.y, geom.x],
                        radius=6,
                        color=color,
                        fill=True,
                        fill_opacity=0.85,
                        popup=folium.Popup(popup_html, max_width=360)
                    ).add_to(grupo)

                grupo.add_to(m)
                grupos[nome_grupo] = grupo
                layer_vars[nome_grupo] = grupo.get_name()

    # =================================================================
    # Controles interativos
    # =================================================================
    map_id = m.get_name()
    layer_map = json.dumps(layer_vars)

    ano_min, ano_max = min(anos), max(anos)
    pol_opts_html = "".join(f"<option value='{p}'>{poluente_nomes[p]}</option>" for p in poluentes)

    radios_html = "".join(
        f"<label style='display:flex;align-items:center;margin:2px 0;'>"
        f"<input type='radio' name='padraoSel' value='{p}' {'checked' if i == 0 else ''} onchange='updateLayers()'>"
        f"<span>{p}</span></label>"
        for i, p in enumerate(padroes)
    )

    mid_viol = max_viol_global // 2

    js = f"""
<script>
const MAP_ID = '{map_id}';
const LAYER_INDEX = {layer_map};
let currentAno = {ANO_INICIAL};
let currentPol = '{poluentes[0]}';

function clearAllLayers(mapObj) {{
  for (const [groupName, varName] of Object.entries(LAYER_INDEX)) {{
    const layer = window[varName];
    if (layer && mapObj.hasLayer(layer)) {{
      mapObj.removeLayer(layer);
    }}
  }}
}}

function showLayer(mapObj, key) {{
  const layerToShow = window[LAYER_INDEX[key]];
  if (layerToShow) {{
    mapObj.addLayer(layerToShow);
  }}
}}

function updateLayers() {{
  const mapObj = window[MAP_ID];
  const selectedPadrao = document.querySelector('input[name="padraoSel"]:checked');
  const selEl = document.getElementById('selPoll');
  if (!selectedPadrao || !selEl) return;

  const padrao = selectedPadrao.value;
  currentPol = selEl.value;
  const targetKey = padrao + ' - ' + currentAno + ' - ' + currentPol;

  clearAllLayers(mapObj);

  if (Object.prototype.hasOwnProperty.call(LAYER_INDEX, targetKey)) {{
    showLayer(mapObj, targetKey);
  }} else {{
    console.log("⚠️ Sem dados para:", targetKey);
  }}

  document.getElementById('anoLabel').innerText = currentAno;
}}

function onAnoChange(val) {{
  currentAno = parseInt(val);
  updateLayers();
}}

document.addEventListener('DOMContentLoaded', () => {{
  setTimeout(updateLayers, 800);
}});
</script>
"""

    html_controls = f"""
<div style="position: fixed; top: 10px; left: 10px; background: white; padding: 8px 12px;
     border-radius: 6px; box-shadow: 0 1px 4px rgba(0,0,0,0.3); z-index: 9999; font-family: Arial;">
  <label>Poluente:</label>
  <select id="selPoll" onchange="updateLayers()">{pol_opts_html}</select>
</div>

<div style="position: fixed; top: 70px; right: 10px; background: white; padding: 10px; border-radius: 6px;
     box-shadow: 0 1px 4px rgba(0,0,0,0.3); z-index:9999; font-family: Arial; font-size: 13px;">
  <div style="margin-bottom:4px;"><b>Padrão:</b></div>
  <div style="max-height: 140px; overflow-y: auto;">{radios_html}</div>
  <hr style="margin:6px 0;">
  <div><b>Ano: <span id="anoLabel">{ANO_INICIAL}</span></b></div>
  <input type="range" id="anoSlider" min="{ano_min}" max="{ano_max}" value="{ANO_INICIAL}"
         step="1" oninput="onAnoChange(this.value)" style="width:160px;">
</div>

<div style="position: fixed; bottom: 10px; left: 10px; background: white; padding: 8px 10px;
     border-radius: 6px; box-shadow: 0 1px 4px rgba(0,0,0,0.3); z-index:9999; font-family: Arial; font-size: 12px;">
  <b>Legenda (nº de violações):</b><br>
  <div style="width:160px;height:10px;
       background: linear-gradient(to right, rgb(0,200,0), rgb(255,200,0), rgb(255,0,0));
       margin:4px 0;border-radius:2px;"></div>
  <div style="display:flex;justify-content:space-between;text-align:center;width:160px;">
    <span>0</span><span>~{mid_viol}</span><span>{max_viol_global}</span>
  </div>
</div>
"""

    m.get_root().html.add_child(folium.Element(js + html_controls))
    m.save(html_out)

    print(f"✅ HTML salvo em: {html_out}")
    return m


if __name__ == "__main__":
    mapa_violacoes_detalhado()
