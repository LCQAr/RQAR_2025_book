# -*- coding: utf-8 -*-
"""
Gera versão inline do mapa de violações (sem fetch) para uso direto no Jupyter Notebook.
Lê os GeoJSONs da pasta _static/mapas/violacoes e embute todos no HTML final.
"""

import os
import json
from pathlib import Path
from IPython.display import HTML, display

def gerar_mapa_inline(rootPath=None, save_html=True):
    print("🚀 Gerando mapa inline (versão Jupyter)...")

    # === Caminhos principais ===
    rootPath = Path(rootPath or os.getcwd())
    mapas_dir = rootPath / "_static" / "mapas"
    viol_dir = mapas_dir / "violacoes"

    if not viol_dir.exists():
        raise FileNotFoundError(f"Pasta de GeoJSONs não encontrada: {viol_dir}")

    # === Carrega GeoJSONs em memória ===
    geojson_data = {}
    for padrao_dir in sorted(viol_dir.iterdir()):
        if padrao_dir.is_dir():
            for geo_file in padrao_dir.glob("*.geojson"):
                chave = f"{padrao_dir.name}/{geo_file.stem}"
                with open(geo_file, "r", encoding="utf-8") as f:
                    geojson_data[chave] = json.load(f)
    print(f"🗺️ {len(geojson_data)} arquivos GeoJSON incorporados.")

    # === HTML + JS (inline, sem fetch) ===
    html = f"""
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<title>Mapa de Violações Inline — CONAMA 506/2024</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  html, body, #map {{ height: 100%; width: 100%; margin: 0; }}
  .control-box {{
    position: fixed; top: 10px; left: 10px;
    background: white; padding: 10px 14px; border-radius: 8px;
    box-shadow: 0 1px 5px rgba(0,0,0,0.3);
    z-index: 9999; font-family: Arial; font-size: 13px;
  }}
</style>
</head>
<body>
<div id="map"></div>

<script>
const allData = {json.dumps(geojson_data)};  // todos os GeoJSONs embutidos

const map = L.map('map').setView([-14.2, -51.9], 4);
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
  maxZoom: 10,
  attribution: '&copy; OpenStreetMap'
}}).addTo(map);

function getColor(v) {{
  const ratio = Math.min(1, Math.max(0, v / 100));
  if (ratio < 0.5) {{
    const r = Math.round(510 * ratio);
    return `rgb(${{r}},200,0)`;
  }} else {{
    const g = Math.round(200 - 400 * (ratio - 0.5));
    return `rgb(255,${{Math.max(g,0)}},0)`;
  }}
}}

let camadaAtual = null;

function carregar(padrao, pol, ano) {{
  const chave = padrao + "/" + pol + "_" + ano;
  const data = allData[chave];
  if (!data) {{
    alert("⚠️ Nenhum dado disponível para " + chave);
    return;
  }}
  if (camadaAtual) map.removeLayer(camadaAtual);

  camadaAtual = L.geoJSON(data, {{
    pointToLayer: (feature, latlng) => {{
      const viol = feature.properties.VIOLACOES || 0;
      return L.circleMarker(latlng, {{
        radius: 6,
        color: getColor(viol),
        fillOpacity: 0.85
      }}).bindPopup(`
        <b>${{feature.properties.ID_MMA_COMPLETO}}</b><br>
        Poluente: ${{feature.properties.POLUENTE}}<br>
        Padrão: ${{feature.properties.PADRAO}}<br>
        Ano: ${{feature.properties.ANO}}<br>
        Violações: ${{viol}}<br>
        Excedência: ${{feature.properties.PCT_EXC}}%
      `);
    }}
  }}).addTo(map);
}}
</script>

<div class="control-box">
  <b>Poluente:</b><br>
  <select id="selPol">
    <option>MP10</option><option>MP25</option><option>SO2</option>
    <option>NO2</option><option>O3</option><option>CO</option><option>PTS</option>
  </select><br><br>

  <b>Padrão:</b><br>
  <select id="selPadrao">
    <option>PI-1</option><option>PI-2</option><option>PI-3</option>
    <option>PI-4</option><option>PF</option>
  </select><br><br>

  <b>Ano:</b><br>
  <input id="ano" type="number" min="2005" max="2024" value="2020" style="width:80px;"><br><br>
  <button onclick="carregar(
    document.getElementById('selPadrao').value,
    document.getElementById('selPol').value,
    document.getElementById('ano').value
  )">Carregar</button>
</div>

</body>
</html>
"""

    # === Salva HTML (opcional) ===
    if save_html:
        out_path = mapas_dir / "mapa_violacoes_inline.html"
        out_path.write_text(html, encoding="utf-8")
        print(f"💾 HTML salvo em: {out_path}")

    # === Exibe no Jupyter ===
    display(HTML(html))
    print("✅ Mapa inline renderizado com sucesso no notebook.")


# Execução direta (opcional)
if __name__ == "__main__":
    gerar_mapa_inline("/home/nobre/Notebooks/RQAR_2025_book/_static/mapas", save_html=True)
