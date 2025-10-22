# -*- coding: utf-8 -*-
"""
Mapa de Violações — versão Jupyter aprimorada com transição suave real e legenda contínua
Autor: Robson Will
"""

import geopandas as gpd
import folium
from folium import plugins
from pathlib import Path
from IPython.display import display, HTML, clear_output
import ipywidgets as widgets
import time

def mapa_violacoes_interativo(rootPath):
    root = Path(rootPath)
    base_dir = root / "_static" / "mapas" / "violacoes"

    if not base_dir.exists():
        raise FileNotFoundError(f"Pasta de GeoJSONs não encontrada: {base_dir}")

    padroes = sorted([d.name for d in base_dir.iterdir() if d.is_dir()])
    poluentes = sorted({f.stem.split("_")[0] for f in base_dir.glob("*/*.geojson")})
    anos = sorted({int(f.stem.split("_")[1]) for f in base_dir.glob("*/*.geojson")})

    # === Widgets ===
    padrao_sel = widgets.ToggleButtons(options=padroes, description="Padrão:")
    poluente_sel = widgets.Dropdown(options=poluentes, description="Poluente:")
    ano_slider = widgets.IntSlider(
        value=max(anos), min=min(anos), max=max(anos), step=1,
        description="Ano:", continuous_update=False, layout=widgets.Layout(width="400px")
    )
    ano_label = widgets.Label(str(max(anos)))
    out = widgets.Output()

    def atualizar_mapa(_=None):
        clear_output(wait=True)
        display(ui)

        ano_label.value = str(ano_slider.value)
        geo_path = base_dir / padrao_sel.value / f"{poluente_sel.value}_{ano_slider.value}.geojson"

        if not geo_path.exists():
            with out:
                out.clear_output()
                display(HTML(f"<b style='color:#C00;'>⚠️ Nenhum dado para {geo_path.name}</b>"))
            return

        gdf = gpd.read_file(geo_path)
        if gdf.empty:
            with out:
                out.clear_output()
                display(HTML(f"<b style='color:#C00;'>⚠️ Arquivo vazio: {geo_path.name}</b>"))
            return

        # === Mapa base (com limites do Brasil) ===
        m = folium.Map(
            location=[-14.2, -51.9],
            zoom_start=4.3,
            min_zoom=3.8,
            max_zoom=8,
            max_bounds=True,
            tiles="CartoDB positron"
        )
        m.fit_bounds([[-34.0, -74.0], [6.0, -34.0]])
        m.options['maxBoundsViscosity'] = 1.0

        plugins.Fullscreen(position="topleft").add_to(m)
        plugins.MiniMap(toggle_display=True).add_to(m)

        # === Função de cor dinâmica ===
        def get_color(v):
            try:
                ratio = min(1, max(0, float(v) / gdf["VIOLACOES"].max()))
            except Exception:
                ratio = 0
            if ratio < 0.5:
                r = int(510 * ratio)
                g = 200
                b = 0
            else:
                r = 255
                g = int(200 - 400 * (ratio - 0.5))
                b = 0
            return f"rgb({r},{max(g,0)},{b})"

        # === Adiciona marcadores ===
        for _, row in gdf.iterrows():
            viol = row.get("VIOLACOES", 0)
            color = get_color(viol)
            popup = f"""
            <div style='font-family:Arial; font-size:12px;'>
                <b>{row.get('ID_MMA_COMPLETO','')}</b><br>
                Poluente: {row.get('POLUENTE','')}<br>
                Padrão: {row.get('PADRAO','')}<br>
                Ano: {row.get('ANO','')}<br>
                Violações: {viol}<br>
                Excedência: {row.get('PCT_EXC','')}%
            </div>
            """
            folium.CircleMarker(
                location=[row.geometry.y, row.geometry.x],
                radius=6,
                color=color,
                opacity=0.4,           # contorno translúcido
                weight=2,              # espessura da borda
                fill=True,
                fill_color=color,
                fill_opacity=0.55,     # 🔹 transparência principal
                popup=folium.Popup(popup, max_width=260)
            ).add_to(m)


        # === Legenda contínua ===
        max_viol = int(gdf["VIOLACOES"].max())
        mid_viol = max_viol // 2
        legend_html = f"""
        <div style='position: fixed; bottom: 10px; left: 10px; width: 180px;
                    background-color: white; border-radius: 6px;
                    padding: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.4);
                    font-size: 12px; font-family: Arial; z-index:9999;'>
            <b>Legenda (nº de violações):</b><br>
            <div style='height: 10px; background: linear-gradient(to right,
                rgb(0,200,0), rgb(255,200,0), rgb(255,0,0));
                border-radius: 3px; margin: 5px 0;'></div>
            <div style='display: flex; justify-content: space-between;'>
                <span>0</span><span>~{mid_viol}</span><span>{max_viol}</span>
            </div>
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend_html))

        # === Transição suave real (fade entre atualizações) ===
        with out:
            out.clear_output(wait=True)
            display(HTML("<div style='opacity:0; transition:opacity 0.6s;' id='mapFade'></div>"))
            time.sleep(0.15)
            display(m)
            display(HTML("""
            <script>
            setTimeout(function(){
                var mapDiv = document.getElementById('mapFade');
                if(mapDiv){ mapDiv.style.opacity = 1; }
            }, 200);
            </script>
            """))

    # === Ligações ===
    padrao_sel.observe(atualizar_mapa, "value")
    poluente_sel.observe(atualizar_mapa, "value")
    ano_slider.observe(atualizar_mapa, "value")

    # === Layout geral ===
    controles = widgets.HBox([padrao_sel, poluente_sel])
    ano_box = widgets.HBox([ano_slider, ano_label])
    ui = widgets.VBox([controles, ano_box, out])
    display(ui)
    atualizar_mapa()

# Execução direta (para teste isolado)
if __name__ == "__main__":
    mapa_violacoes_interativo("/home/nobre/Notebooks/RQAR_2025_book")
