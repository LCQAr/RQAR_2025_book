# -*- coding: utf-8 -*-
"""
Mapa de Violações — versão final com:
- ordem de padrões fixa (PI-1 → PI-4, PF)
- poluentes com subscrito (MP₁₀, MP₂.₅, NO₂, SO₂, O₃, CO)
- abertura padrão em MP₂.₅
- aviso se o poluente só possuir PF
- salvamento automático em _static/mapas_html/
Autor: Robson Will
"""

import geopandas as gpd
import folium
from folium import plugins
from pathlib import Path
from IPython.display import display, HTML, clear_output
import ipywidgets as widgets
import time
import pandas as pd


def mapa_violacoes_interativo(rootPath):
    root = Path(rootPath)
    base_dir = root / "_static" / "mapas" / "violacoes"

    if not base_dir.exists():
        raise FileNotFoundError(f"Pasta de GeoJSONs não encontrada: {base_dir}")

    # === Ordem fixa dos padrões ===
    ordem_padroes = ["PI-1", "PI-2", "PI-3", "PI-4", "PF"]
    padroes = [p for p in ordem_padroes if (base_dir / p).exists()]

    # === Mapeamento de poluentes com subscritos ===
    poluentes_fmt = {
        "MP10":  "MP₁₀",
        "MP2.5": "MP₂.₅",
        "NO2":   "NO₂",
        "SO2":   "SO₂",
        "O3":    "O₃",
        "CO":    "CO",
    }
    fmt_rev = {v: k for k, v in poluentes_fmt.items()}  # reverso exibição → base

    # === Identificar poluentes e anos disponíveis ===
    poluentes_raw = sorted({f.stem.split("_")[0] for f in base_dir.glob("*/*.geojson")})
    anos = sorted({int(f.stem.split("_")[1]) for f in base_dir.glob("*/*.geojson")})
    poluentes = [poluentes_fmt.get(p, p) for p in poluentes_raw]

    # === Default: MP₂.₅ se existir ===
    default_poluente = "MP₂.₅" if "MP₂.₅" in poluentes else poluentes[0]

    # === Widgets ===
    padrao_sel = widgets.ToggleButtons(options=padroes, description="Padrão:")
    poluente_sel = widgets.Dropdown(options=poluentes, value=default_poluente, description="Poluente:")
    ano_slider = widgets.IntSlider(
        value=max(anos), min=min(anos), max=max(anos), step=1,
        description="Ano:", continuous_update=False, layout=widgets.Layout(width="400px")
    )
    ano_label = widgets.Label(str(max(anos)))
    out = widgets.Output()

    # === Funções auxiliares ===
    def nome_base(p_exib):
        """Converte 'MP₂.₅' → 'MP2.5' para leitura de arquivo"""
        return fmt_rev.get(p_exib, p_exib)

    def caminho(padrao, pol_exib, ano):
        return base_dir / padrao / f"{nome_base(pol_exib)}_{ano}.geojson"

    def existe(padrao, pol_exib, ano):
        return caminho(padrao, pol_exib, ano).exists()

    # === Função principal ===
    def atualizar_mapa(_=None):
        clear_output(wait=True)
        display(ui)

        ano = ano_slider.value
        ano_label.value = str(ano)
        padrao = padrao_sel.value
        pol_exib = poluente_sel.value
        geo_path = caminho(padrao, pol_exib, ano)

        # --- Verificação: só PF ---
        so_pf = False
        if not geo_path.exists():
            tem_pf = existe("PF", pol_exib, ano)
            tem_algum_pi = any(existe(pi, pol_exib, ano) for pi in ["PI-1","PI-2","PI-3","PI-4"])
            if tem_pf and not tem_algum_pi and padrao != "PF":
                so_pf = True

        if not geo_path.exists():
            with out:
                out.clear_output()
                if so_pf:
                    display(HTML(
                        f"<b style='color:#C00;'>⚠️ Para {pol_exib} em {ano}, apenas o padrão "
                        f"<span style='background:#eee;padding:2px 6px;border-radius:4px;'>PF</span> possui dados.</b>"
                    ))
                else:
                    display(HTML(f"<b style='color:#C00;'>⚠️ Nenhum dado para {padrao}/{pol_exib}/{ano}.</b>"))
            return

        gdf = gpd.read_file(geo_path)
        if gdf.empty:
            with out:
                out.clear_output()
                display(HTML(f"<b style='color:#C00;'>⚠️ Arquivo vazio: {geo_path.name}</b>"))
            return

        # === Mapa base ===
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

        # === Cores ===
        def get_color(v):
            try:
                v = float(v)
            except Exception:
                return "gray"
            if v <= 10:
                return "rgb(0,200,0)"
            elif v <= 20:
                return "rgb(150,220,0)"
            elif v <= 50:
                return "rgb(255,220,0)"
            elif v <= 100:
                return "rgb(255,140,0)"
            else:
                return "rgb(255,0,0)"

        # === Marcadores ===
        for _, row in gdf.iterrows():
            viol = row.get("VIOLACOES", 0)
            n_validos = row.get("N_VALIDOS", None)
            exc = row.get("PCT_EXC", None)

            exc_str = "inválido" if pd.isna(exc) else f"{exc:.1f}%"
            n_validos_str = "–" if pd.isna(n_validos) else f"{int(n_validos)}"
            color = get_color(viol)
            pol_fmt_popup = poluentes_fmt.get(row.get("POLUENTE",""), row.get("POLUENTE",""))

            popup = f"""
            <div style='font-family:Arial; font-size:12px;'>
                <b>{row.get('ID_MMA_COMPLETO','')}</b><br>
                Poluente: {pol_fmt_popup}<br>
                Padrão: {row.get('PADRAO','')}<br>
                Ano: {row.get('ANO','')}<br>
                Dados válidos: {n_validos_str}<br>
                Violações: {viol}<br>
                Excedência: {exc_str}
            </div>
            """
            folium.CircleMarker(
                location=[row.geometry.y, row.geometry.x],
                radius=6,
                color=color,
                opacity=0.4,
                weight=2,
                fill=True,
                fill_color=color,
                fill_opacity=0.55,
                popup=folium.Popup(popup, max_width=260)
            ).add_to(m)

        # === Legenda ===
        legend_html = """
        <div style='position: fixed; bottom: 10px; left: 10px; width: 200px;
                     background-color: white; border-radius: 6px;
                     padding: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.4);
                     font-size: 12px; font-family: Arial; z-index:9999;'>
            <b>Faixas de violações:</b><br>
            <div style='margin-top:5px;'>
                <div><span style='background:rgb(0,180,0);width:18px;height:10px;display:inline-block;'></span> 0</div>
                <div><span style='background:rgb(200,230,0);width:18px;height:10px;display:inline-block;'></span> 1–10</div>
                <div><span style='background:rgb(255,220,0);width:18px;height:10px;display:inline-block;'></span> 11–20</div>
                <div><span style='background:rgb(255,160,0);width:18px;height:10px;display:inline-block;'></span> 21–50</div>
                <div><span style='background:rgb(255,80,0);width:18px;height:10px;display:inline-block;'></span> 51–100</div>
                <div><span style='background:rgb(220,0,0);width:18px;height:10px;display:inline-block;'></span> >100</div>
            </div>
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend_html))

        # === Salvar HTML (mantido) ===
        output_dir = root / "_static" / "mapas_html"
        output_dir.mkdir(parents=True, exist_ok=True)
        nome_html = f"mapa_{padrao}_{nome_base(poluente_sel.value)}_{ano}.html"
        output_html = output_dir / nome_html
        try:
            m.save(str(output_html))
            print(f"💾 Mapa salvo em: {output_html}")
        except Exception as e:
            print(f"⚠️ Erro ao salvar mapa: {e}")

        # === Exibição Estática/Persistente (MODIFICADA) ===
        # Esta é a parte crucial: exibir o objeto Folium 'm' diretamente
        # dentro do output do widget, sem a transição JavaScript.
        # Isso garante que a representação HTML gerada pelo Folium
        # seja capturada e persistida pelo nbconvert/Jupyter Book.
        with out:
            out.clear_output(wait=True)
            display(m)


    # === Ligações ===
    padrao_sel.observe(atualizar_mapa, "value")
    poluente_sel.observe(atualizar_mapa, "value")
    ano_slider.observe(atualizar_mapa, "value")

    # === Layout final ===
    controles = widgets.HBox([padrao_sel, poluente_sel])
    ano_box = widgets.HBox([ano_slider, ano_label])
    ui = widgets.VBox([controles, ano_box, out])
    display(ui)
    atualizar_mapa()


# Execução direta (teste isolado)
if __name__ == "__main__":
    mapa_violacoes_interativo("/home/nobre/Notebooks/RQAR_2025_book")# -*- coding: utf-8 -*-
"""
Mapa de Violações — versão final com:
- ordem de padrões fixa (PI-1 → PI-4, PF)
- poluentes com subscrito (MP₁₀, MP₂.₅, NO₂, SO₂, O₃, CO)
- abertura padrão em MP₂.₅
- aviso se o poluente só possuir PF
- salvamento automático em _static/mapas_html/
Autor: Robson Will
"""

import geopandas as gpd
import folium
from folium import plugins
from pathlib import Path
from IPython.display import display, HTML, clear_output
import ipywidgets as widgets
import time
import pandas as pd


def mapa_violacoes_interativo(rootPath):
    root = Path(rootPath)
    base_dir = root / "_static" / "mapas" / "violacoes"

    if not base_dir.exists():
        raise FileNotFoundError(f"Pasta de GeoJSONs não encontrada: {base_dir}")

    # === Ordem fixa dos padrões ===
    ordem_padroes = ["PI-1", "PI-2", "PI-3", "PI-4", "PF"]
    padroes = [p for p in ordem_padroes if (base_dir / p).exists()]

    # === Mapeamento de poluentes com subscritos ===
    poluentes_fmt = {
        "MP10":  "MP₁₀",
        "MP2.5": "MP₂.₅",
        "NO2":   "NO₂",
        "SO2":   "SO₂",
        "O3":    "O₃",
        "CO":    "CO",
    }
    fmt_rev = {v: k for k, v in poluentes_fmt.items()}  # reverso exibição → base

    # === Identificar poluentes e anos disponíveis ===
    poluentes_raw = sorted({f.stem.split("_")[0] for f in base_dir.glob("*/*.geojson")})
    anos = sorted({int(f.stem.split("_")[1]) for f in base_dir.glob("*/*.geojson")})
    poluentes = [poluentes_fmt.get(p, p) for p in poluentes_raw]

    # === Default: MP₂.₅ se existir ===
    default_poluente = "MP₂.₅" if "MP₂.₅" in poluentes else poluentes[0]

    # === Widgets ===
    padrao_sel = widgets.ToggleButtons(options=padroes, description="Padrão:")
    poluente_sel = widgets.Dropdown(options=poluentes, value=default_poluente, description="Poluente:")
    ano_slider = widgets.IntSlider(
        value=max(anos), min=min(anos), max=max(anos), step=1,
        description="Ano:", continuous_update=False, layout=widgets.Layout(width="400px")
    )
    ano_label = widgets.Label(str(max(anos)))
    out = widgets.Output()

    # === Funções auxiliares ===
    def nome_base(p_exib):
        """Converte 'MP₂.₅' → 'MP2.5' para leitura de arquivo"""
        return fmt_rev.get(p_exib, p_exib)

    def caminho(padrao, pol_exib, ano):
        return base_dir / padrao / f"{nome_base(pol_exib)}_{ano}.geojson"

    def existe(padrao, pol_exib, ano):
        return caminho(padrao, pol_exib, ano).exists()

    # === Função principal ===
    def atualizar_mapa(_=None):
        clear_output(wait=True)
        display(ui)

        ano = ano_slider.value
        ano_label.value = str(ano)
        padrao = padrao_sel.value
        pol_exib = poluente_sel.value
        geo_path = caminho(padrao, pol_exib, ano)

        # --- Verificação: só PF ---
        so_pf = False
        if not geo_path.exists():
            tem_pf = existe("PF", pol_exib, ano)
            tem_algum_pi = any(existe(pi, pol_exib, ano) for pi in ["PI-1","PI-2","PI-3","PI-4"])
            if tem_pf and not tem_algum_pi and padrao != "PF":
                so_pf = True

        if not geo_path.exists():
            with out:
                out.clear_output()
                if so_pf:
                    display(HTML(
                        f"<b style='color:#C00;'>⚠️ Para {pol_exib} em {ano}, apenas o padrão "
                        f"<span style='background:#eee;padding:2px 6px;border-radius:4px;'>PF</span> possui dados.</b>"
                    ))
                else:
                    display(HTML(f"<b style='color:#C00;'>⚠️ Nenhum dado para {padrao}/{pol_exib}/{ano}.</b>"))
            return

        gdf = gpd.read_file(geo_path)
        if gdf.empty:
            with out:
                out.clear_output()
                display(HTML(f"<b style='color:#C00;'>⚠️ Arquivo vazio: {geo_path.name}</b>"))
            return

        # === Mapa base ===
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

        # === Cores ===
        def get_color(v):
            try:
                v = float(v)
            except Exception:
                return "gray"
            if v <= 10:
                return "rgb(0,200,0)"
            elif v <= 20:
                return "rgb(150,220,0)"
            elif v <= 50:
                return "rgb(255,220,0)"
            elif v <= 100:
                return "rgb(255,140,0)"
            else:
                return "rgb(255,0,0)"

        # === Marcadores ===
        for _, row in gdf.iterrows():
            viol = row.get("VIOLACOES", 0)
            n_validos = row.get("N_VALIDOS", None)
            exc = row.get("PCT_EXC", None)

            exc_str = "inválido" if pd.isna(exc) else f"{exc:.1f}%"
            n_validos_str = "–" if pd.isna(n_validos) else f"{int(n_validos)}"
            color = get_color(viol)
            pol_fmt_popup = poluentes_fmt.get(row.get("POLUENTE",""), row.get("POLUENTE",""))

            popup = f"""
            <div style='font-family:Arial; font-size:12px;'>
                <b>{row.get('ID_MMA_COMPLETO','')}</b><br>
                Poluente: {pol_fmt_popup}<br>
                Padrão: {row.get('PADRAO','')}<br>
                Ano: {row.get('ANO','')}<br>
                Dados válidos: {n_validos_str}<br>
                Violações: {viol}<br>
                Excedência: {exc_str}
            </div>
            """
            folium.CircleMarker(
                location=[row.geometry.y, row.geometry.x],
                radius=6,
                color=color,
                opacity=0.4,
                weight=2,
                fill=True,
                fill_color=color,
                fill_opacity=0.55,
                popup=folium.Popup(popup, max_width=260)
            ).add_to(m)

        # === Legenda ===
        legend_html = """
        <div style='position: fixed; bottom: 10px; left: 10px; width: 200px;
                     background-color: white; border-radius: 6px;
                     padding: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.4);
                     font-size: 12px; font-family: Arial; z-index:9999;'>
            <b>Faixas de violações:</b><br>
            <div style='margin-top:5px;'>
                <div><span style='background:rgb(0,200,0);width:18px;height:10px;display:inline-block;'></span>  ≤10</div>
                <div><span style='background:rgb(150,220,0);width:18px;height:10px;display:inline-block;'></span>  11–20</div>
                <div><span style='background:rgb(255,220,0);width:18px;height:10px;display:inline-block;'></span>  21–50</div>
                <div><span style='background:rgb(255,140,0);width:18px;height:10px;display:inline-block;'></span>  51–100</div>
                <div><span style='background:rgb(255,0,0);width:18px;height:10px;display:inline-block;'></span>  >100</div>
            </div>
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend_html))

        # === Salvar HTML (mantido) ===
        output_dir = root / "_static" / "mapas_html"
        output_dir.mkdir(parents=True, exist_ok=True)
        nome_html = f"mapa_{padrao}_{nome_base(poluente_sel.value)}_{ano}.html"
        output_html = output_dir / nome_html
        try:
            m.save(str(output_html))
            print(f"💾 Mapa salvo em: {output_html}")
        except Exception as e:
            print(f"⚠️ Erro ao salvar mapa: {e}")

        # === Exibição Estática/Persistente (MODIFICADA) ===
        # Esta é a parte crucial: exibir o objeto Folium 'm' diretamente
        # dentro do output do widget, sem a transição JavaScript.
        # Isso garante que a representação HTML gerada pelo Folium
        # seja capturada e persistida pelo nbconvert/Jupyter Book.
        with out:
            out.clear_output(wait=True)
            display(m)


    # === Ligações ===
    padrao_sel.observe(atualizar_mapa, "value")
    poluente_sel.observe(atualizar_mapa, "value")
    ano_slider.observe(atualizar_mapa, "value")

    # === Layout final ===
    controles = widgets.HBox([padrao_sel, poluente_sel])
    ano_box = widgets.HBox([ano_slider, ano_label])
    ui = widgets.VBox([controles, ano_box, out])
    display(ui)
    atualizar_mapa()


# Execução direta (teste isolado)
if __name__ == "__main__":
    mapa_violacoes_interativo("/home/nobre/Notebooks/RQAR_2025_book")