# -*- coding: utf-8 -*-
"""
Mapa de Violações — HTML leve e standalone (para Jupyter Book)
--------------------------------------------------------------
- Gera 1 arquivo: _static/mapas_html/mapa_violacoes.html
- Controles: Padrão (PI-1..PF), Poluente (MP₂.₅ etc.), Ano
- Carrega GeoJSON on-demand via fetch() (leve para o navegador)
- Mostra aviso se só existir PF, se arquivo faltar, etc.
- Mantém visual: cores, popups, mini-mapa, fullscreen, limites BR

Autor: Robson Will
"""

from pathlib import Path
import json
import re


def mapa_violacoes_standalone(rootPath: str):
    root = Path(rootPath)
    base_dir = root / "_static" / "mapas" / "violacoes"
    out_dir  = root / "_static" / "mapas_html"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_html = out_dir / "mapa_violacoes.html"

    if not base_dir.exists():
        raise FileNotFoundError(f"Pasta de GeoJSONs não encontrada: {base_dir}")

    # Ordem fixa de padrões
    ordem_padroes = ["PI-1", "PI-2", "PI-3", "PI-4", "PF"]
    padroes = [p for p in ordem_padroes if (base_dir / p).exists()]

    # Poluentes reconhecidos (nomes base nos arquivos)
    poluentes_base = ["MP25", "MP10", "NO2", "SO2", "O3", "CO"]
    pol_fmt = {"MP10": "MP₁₀", "MP25": "MP₂.₅", "NO2": "NO₂", "SO2": "SO₂", "O3": "O₃", "CO": "CO"}

    # ---- Escaneia o disco para montar um manifesto leve (metadados) ----
    pat = re.compile(r"^(MP10|MP25|NO2|SO2|O3|CO)_(\d{4})\.geojson$", re.I)
    availability = {pad: {pol: [] for pol in poluentes_base} for pad in ordem_padroes}
    anos_set, pol_set = set(), set()

    for pad in padroes:
        pdir = base_dir / pad
        for f in pdir.glob("*.geojson"):
            m = pat.match(f.name)
            if not m:
                continue
            pol = m.group(1).upper()
            ano = int(m.group(2))
            if pol in availability[pad]:
                availability[pad][pol].append(ano)
                anos_set.add(ano)
                pol_set.add(pol)

    # ordena e limpa
    for pad in availability:
        for pol in availability[pad]:
            availability[pad][pol] = sorted(set(availability[pad][pol]))

    anos_sorted = sorted(anos_set)
    if not anos_sorted:
        raise RuntimeError("Nenhum ano detectado nos GeoJSONs.")

    pols_sorted = [p for p in poluentes_base if p in pol_set] or poluentes_base
    default_pol   = "MP25" if "MP25" in pols_sorted else pols_sorted[0]
    default_pad   = padroes[0]
    default_year  = max(anos_sorted)

    manifest = {
        "padroes": padroes,
        "poluentes": pols_sorted,
        "anos": anos_sorted,
        "availability": availability,
        "default": {"padrao": default_pad, "poluente": default_pol, "ano": default_year},
        "pol_fmt": pol_fmt
    }

    # HTML com JS puro (Leaflet) — carrega GeoJSON via fetch relativo a este HTML
    html = f"""<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Mapa de Violações — CONAMA 506/2024</title>

<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet.fullscreen@2.4.0/Control.FullScreen.css"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet-minimap@3.6.1/dist/Control.MiniMap.min.css"/>

<style>
body{{margin:0;padding:12px;font-family:Arial, sans-serif;background:#fff;}}
#controls{{display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin-bottom:10px;}}
.control{{display:flex;align-items:center;gap:8px;height:38px;}}
.label{{font-size:14px;font-weight:600;color:#333;white-space:nowrap;}}
.select{{appearance:none;padding:6px 10px;border:1px solid #999;border-radius:6px;background:#f9f9f9;cursor:pointer;font-size:14px;}}
.range-wrap{{display:flex;align-items:center;gap:8px;}}
.button{{padding:6px 14px;border-radius:6px;border:1px solid #005a9e;background:#0078d7;color:#fff;font-weight:600;cursor:pointer;}}
.button:hover{{background:#005a9e;}}
#status{{font-size:13px;color:crimson;margin-left:8px;}}
#map{{width:100%;height:680px;border:1px solid #ddd;opacity:0;transition:opacity .35s;}}
.leaflet-control.custom-legend{{background:#fff;padding:8px;border-radius:6px;box-shadow:0 1px 4px rgba(0,0,0,.4);font-size:12px;}}
.notice{{margin:6px 0;padding:6px 10px;border-left:4px solid #C00;background:#ffecec;color:#600;border-radius:4px;display:none;}}
</style>
</head>

<body>

<div id="controls">
  <div class="control">
    <span class="label">Padrão:</span>
    <div id="padroes" class="control"></div>
  </div>

  <div class="control">
    <span class="label">Poluente:</span>
    <select id="selPol" class="select"></select>
  </div>

  <div class="control range-wrap">
    <span class="label">Ano:</span>
    <input id="ano" type="range" min="0" max="0" value="0" step="1"/>
    <span id="anoVal" style="font-weight:600;"></span>
  </div>

  <div class="control" style="flex:1;">
    <button id="btn" class="button">Gerar mapa</button>
    <span id="status"></span>
  </div>
</div>

<div id="warn" class="notice"></div>
<div id="map"></div>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/leaflet.fullscreen@2.4.0/Control.FullScreen.js"></script>
<script src="https://unpkg.com/leaflet-minimap@3.6.1/dist/Control.MiniMap.min.js"></script>

<script>
// ===== Manifesto (metadados) — gerado pelo Python =====
const MANIFEST = {json.dumps(manifest, ensure_ascii=False)};

// Caminho relativo a partir deste HTML (_static/mapas_html/ → ../mapas/violacoes/)
const BASE_PATH = "../mapas/violacoes/";

// ===== UI =====
const PADROES = MANIFEST.padroes;
const POLS    = MANIFEST.poluentes;
const ANOS    = MANIFEST.anos;
const DISPON  = MANIFEST.availability;
const POL_FMT = MANIFEST.pol_fmt;
const DEF     = MANIFEST.default;

let currentPadrao = DEF.padrao;
let currentPol    = DEF.poluente;
let currentAno    = DEF.ano;

const padroesDiv = document.getElementById('padroes');
const selPol     = document.getElementById('selPol');
const anoRange   = document.getElementById('ano');
const anoVal     = document.getElementById('anoVal');
const btn        = document.getElementById('btn');
const statusEl   = document.getElementById('status');
const warnEl     = document.getElementById('warn');

function renderPadroes(){{
  padroesDiv.innerHTML = "";
  PADROES.forEach(p=>{{
    const b = document.createElement('button');
    b.textContent = p;
    b.className = "button";
    if(p===currentPadrao) b.style.background="#555", b.style.borderColor="#333";
    b.onclick = ()=>{{ currentPadrao=p; renderPadroes(); }};
    padroesDiv.appendChild(b);
  }});
}}
function renderPols(){{
  selPol.innerHTML = "";
  POLS.forEach(pb=>{{
    const opt = document.createElement('option');
    opt.value = pb;
    opt.textContent = POL_FMT[pb] || pb;
    selPol.appendChild(opt);
  }});
  selPol.value = currentPol;
}}
function renderAnos(){{
  anoRange.min = 0;
  anoRange.max = ANOS.length-1;
  let idx = ANOS.indexOf(currentAno);
  if(idx<0) idx = ANOS.length-1;
  anoRange.value = idx;
  anoVal.textContent = ANOS[idx];
}}

selPol.addEventListener('change', ()=>{{ currentPol = selPol.value; }});
anoRange.addEventListener('input', ()=>{{ anoVal.textContent = ANOS[parseInt(anoRange.value,10)] || ""; }});

// ===== Leaflet =====
let map=null, layer=null, legend=null;
function ensureMap(){{
  if(map) return;
  map = L.map('map').setView([-14.2,-51.9],4);
  const base = L.tileLayer('https://cartodb-basemaps-a.global.ssl.fastly.net/light_all/{{z}}/{{x}}/{{y}}.png',
    {{maxZoom:19, attribution:'© OpenStreetMap, © CARTO'}});
  base.addTo(map);
  const mini = new L.Control.MiniMap(base, {{toggleDisplay:true}}).addTo(map);
  L.control.fullscreen({{position:'topleft'}}).addTo(map);
  const b = [[-34,-74],[6,-34]];
  map.fitBounds(b); map.setMaxBounds(b); map.options.minZoom = 4;
  map.getContainer().style.opacity = 1;
}}
function colorViol(v){{
  const n = Number(v);
  if(!isFinite(n)) return "gray";
  if(n<=10) return "rgb(0,200,0)";
  if(n<=20) return "rgb(150,220,0)";
  if(n<=50) return "rgb(255,220,0)";
  if(n<=100) return "rgb(255,140,0)";
  return "rgb(255,0,0)";
}}
function addLegend(){{
  if(legend) try{{legend.remove();}}catch{{}}
  legend = L.control({{position:'bottomleft'}});
  legend.onAdd = function(){{
    const div = L.DomUtil.create('div','leaflet-control custom-legend');
    div.innerHTML = `<b>Faixas de violações:</b><br>
      <div style='margin-top:5px;'>
        <div><span style='background:rgb(0,200,0);width:18px;height:10px;display:inline-block;'></span> ≤10</div>
        <div><span style='background:rgb(150,220,0);width:18px;height:10px;display:inline-block;'></span> 11–20</div>
        <div><span style='background:rgb(255,220,0);width:18px;height:10px;display:inline-block;'></span> 21–50</div>
        <div><span style='background:rgb(255,140,0);width:18px;height:10px;display:inline-block;'></span> 51–100</div>
        <div><span style='background:rgb(255,0,0);width:18px;height:10px;display:inline-block;'></span> >100</div>
      </div>`;
    return div;
  }};
  legend.addTo(map);
}}

async function exists(url){{
  try{{ const r = await fetch(url, {{method:'HEAD'}}); return r.ok; }} catch{{ return false; }}
}}

async function showOnlyPFIfApplies(pol, ano, pad){{
  // se só existir PF naquele ano/poluente, exibe aviso
  const checks = await Promise.all(["PI-1","PI-2","PI-3","PI-4"].map(p=>exists(`${{BASE_PATH}}${{p}}/${{pol}}_${{ano}}.geojson`)));
  const hasPI = checks.some(Boolean);
  const hasPF = await exists(`${{BASE_PATH}}PF/${{pol}}_${{ano}}.geojson`);
  if(hasPF && !hasPI && pad!=="PF"){{
    warnEl.style.display = "block";
    warnEl.innerHTML = `⚠️ Para <b>${{POL_FMT[pol]||pol}}</b> em <b>${{ano}}</b>, apenas o padrão <span style='background:#eee;padding:1px 6px;border-radius:4px;'>PF</span> possui dados.`;
    return true;
  }}
  warnEl.style.display = "none";
  return false;
}}

async function render(){{
  ensureMap();
  statusEl.textContent = "";
  const idx = parseInt(anoRange.value,10) || 0;
  currentAno = ANOS[Math.max(0, Math.min(idx, ANOS.length-1))];
  anoVal.textContent = currentAno;

  if(await showOnlyPFIfApplies(currentPol, currentAno, currentPadrao)) return;

  const url = `${{BASE_PATH}}${{currentPadrao}}/${{currentPol}}_${{currentAno}}.geojson`;
  statusEl.textContent = "Carregando...";
  try {{
    const resp = await fetch(url);
    if(!resp.ok) throw new Error(`HTTP ${{resp.status}}`);
    const gj = await resp.json();

    if(layer) try{{ map.removeLayer(layer); }}catch{{}} layer=null;
    if(legend) try{{ legend.remove(); }}catch{{}} legend=null;

    layer = L.geoJSON(gj, {{
      pointToLayer:(f, latlng)=>{{
        const p = f.properties || {{}};
        const col = colorViol(p.VIOLACOES);
        return L.circleMarker(latlng, {{
          radius:6, color:col, weight:2, opacity:0.4, fill:true, fillColor:col, fillOpacity:0.55
        }});
      }},
      onEachFeature:(f, lyr)=>{{
        const p = f.properties || {{}};
        const polB = p.POLUENTE || currentPol;
        const polE = POL_FMT[polB] || polB;
        const exc  = (p.PCT_EXC==null || isNaN(Number(p.PCT_EXC))) ? "inválido" : Number(p.PCT_EXC).toFixed(1)+"%";
        const nval = (p.N_VALIDOS==null) ? "–" : String(p.N_VALIDOS);
        const viol = (p.VIOLACOES==null) ? "–" : String(p.VIOLACOES);
        const html = `<div style='font-family:Arial;font-size:12px;'>
          <b>${{p.ID_MMA_COMPLETO||""}}</b><br>
          Poluente: ${{polE}}<br>
          Padrão: ${{p.PADRAO||currentPadrao}}<br>
          Ano: ${{p.ANO||currentAno}}<br>
          Dados válidos: ${{nval}}<br>
          Violações: ${{viol}}<br>
          Excedência: ${{exc}}
        </div>`;
        lyr.bindPopup(html, {{maxWidth:260}});
      }}
    }}).addTo(map);

    addLegend();

    // Ajuste de bounds se possível
    try {{
      const fg = L.featureGroup([layer]);
      const b  = fg.getBounds();
      if(b && b.isValid()) map.fitBounds(b, {{padding:[20,20]}});
    }} catch {{}}

    statusEl.textContent = "";
  }} catch(err) {{
    console.error(err);
    statusEl.textContent = "Arquivo não encontrado ou inválido.";
  }}
}}

// === Inicialização ===
function init(){{
  renderPadroes();
  renderPols();
  renderAnos();
  btn.addEventListener('click', render);
  // primeira renderização
  render();
}}
init();
</script>
</body>
</html>
"""
    out_html.write_text(html, encoding="utf-8")
    print(f"💾 HTML leve gerado em: {out_html}")
    return out_html
