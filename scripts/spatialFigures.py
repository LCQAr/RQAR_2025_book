#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep 11 10:45:33 2024

@author: leohoinaski
"""

#-----------------------------Importação de pacotes ------------------------------------

import os
import pandas as pd
from IPython.display import display, HTML
from typing import List
import pandas as pd
import warnings
import numpy as np
warnings.filterwarnings('ignore')
import geopandas as gpd
import ipywidgets as widgets
# Define update function
import folium
from folium import Element
from matplotlib.colors import ListedColormap    

# Dicionário para renomear as colunas
columns_names = {
    'UF':           'UF',
    'CIDADE':       'Cidade',
    'COD_IBGE':     'Cod. IBGE',
    'ID_OEMA':      'ID_OEMA',
    'ID_MMA':       'ID_MMA',
    'PROPRIETARIO': 'Proprietário',
    'PROP_ENTIDADE':'Natureza da entidade responsável',
    'OPERADOR':     'Respons. operação',
    'OP_ENTIDADE':  'Natureza da entidade operadora',
    'FUNCIONAMENTO':'Funcionamento',
    'CATEGORIA':    'Categoria',
    'METODO':       'Método',
    'CALIBRACAO':   'Calibração',
    'MARCA':        'Marca',
    'POLUENTE':     'Poluente',
    'MOBILIDADE':   'Mobilidade',
    'REP_ESPACIAL': 'Representatividade espacial',
    'FINALIDADE':   'Finalidade do monitoramento',
    'STATUS':       'Status',
    'INICIO':       'Início de operação',
    'FIM':          'Final de operação',
    'LATITUDE':     'Latitude',
    'LONGITUDE':    'Longitude',
    'MONITORAR':    'Integrado no MONITORAR?',
    'FONTE':        'Fonte',
    'REGIAO':       'Região',
    'FLAG':         '',
    'FINALIDADE':   'Finalidade',
    'ELEVACAO':     'Elevação', 
    'Indicativa':   'Indicativa',
    'INDICATIVA':   'Indicativa',
    'Referencia':   'Referência',
    'REFERENCIA':   'Referência',
    'REFERÊNCIA':   'Referência',
    
    
}


def columns_renamer(aqmDisplay):
    """
    Rename columns of a DataFrame based on a predefined mapping.

    Parameters
    ----------
    aqmDisplay : pandas.DataFrame
        The input DataFrame whose columns need to be renamed. Only the columns
        that are keys in the `columns_names` dictionary will be renamed.

    Returns
    -------
    pandas.DataFrame
        The DataFrame with renamed columns.

    Notes
    -----
    The function uses a global variable `columns_names`, which must be a dictionary
    mapping old column names to new names. Columns not found in `columns_names`
    are left unchanged.
    """
    aqmDisplay = aqmDisplay.rename(columns={k: v for k, v in columns_names.items() if k in aqmDisplay.columns})
    return aqmDisplay


def explore_with_bounds(
    gdf,
    column=None,
    cmap="Set1",
    legend=True,
    zoom_start=4,
    min_zoom=3,
    center=None):
    """
    Display a GeoDataFrame using geopandas.explore() with map zoom restricted to a given bounding box.

    Parameters
    ----------
    gdf : GeoDataFrame
        The data to plot.
    column : str, optional
        Column used for coloring.
    cmap : str
        Colormap.
    legend : bool
        Whether to display a legend.
    zoom_start : int
        Initial zoom level.
    min_zoom : int
        Minimum zoom allowed.
    center : list of float, optional
        [lat, lon] to center the map. If None, uses gdf centroid.
    """
    # Bordas do Brasil
    # Bounding box as [south, west, north, east].
    bounds = [-34.0, -74.0, 5.0, -34.0]

    # Center the map
    if center is None:
        center_geom = gdf.unary_union.centroid
        center = [center_geom.y, center_geom.x]

    # Create custom folium base map
    base_map = folium.Map(
        location=center,
        zoom_start=zoom_start,
        min_zoom=min_zoom,
        max_bounds=True
    )
    base_map.fit_bounds([[bounds[0], bounds[1]], [bounds[2], bounds[3]]])

    # Lock map panning strictly to given bounds via JavaScript
    js = f"""
    <script>
        var map = {{map}};
        map.setMaxBounds([
            [{bounds[0]}, {bounds[1]}],  // Southwest
            [{bounds[2]}, {bounds[3]}]   // Northeast
        ]);
    </script>
    """
    base_map.get_root().html.add_child(Element(js))
    
    return base_map

def spatial_rede_monitoramento(columnRef,columnsToltip,cmap):
    """
    Generate an interactive map of air quality monitoring stations in Brazil.

    The function reads monitoring station data from a CSV file, cleans and processes the data,
    aggregates pollutants per station, converts the data into a GeoDataFrame, and then generates
    an interactive map using geopandas' `.explore()` method.

    Parameters
    ----------
    columnRef : str
        The column name used to determine the color of the markers on the map.

    columnsToltip : list of str
        List of column names to be displayed as tooltips when hovering over the markers.

    cmap : str or matplotlib colormap
        The colormap used to color the markers based on `columnRef`.

    Returns
    -------
    folium.folium.Map
        An interactive map with monitoring stations plotted and styled.

    Notes
    -----
    - The CSV file is expected at: `../data/Monitoramento_QAr_BR.csv` relative to the current working directory.
    - The function expects the CSV file to have columns `LONGITUDE`, `LATITUDE`, `ID_OEMA`, and `POLUENTE`.
    - Columns are renamed using a global function `columns_renamer()`, which applies a predefined renaming dictionary.
    - Points with all `NaN` values in a column are dropped.
    - Stations measuring more than one pollutant will have their pollutants aggregated as a comma-separated string.
    - The map will be centered based on the centroid of all points.
    """

    # Caminho para a pasta de dados
    rootPath = os.path.dirname(os.getcwd())
    
    # Lendo o csv
    aqmData = pd.read_csv(rootPath+'/data/Monitoramento_QAr_BR.csv')
    aqmData['CATEGORIA'] = aqmData['CATEGORIA'].str.replace(' ', '') 
    aqmData['ID_OEMA'] = aqmData['ID_OEMA'].str.replace(' ', '') 
    aqmData['POLUENTE'] = aqmData['POLUENTE'].str.upper()
    aqmData.drop(aqmData.columns[aqmData.columns.str.contains('unnamed', case=False)], axis=1, inplace=True)
    # Remove colunas com todos valores iguais a NaN
    #aqmData = aqmData.dropna(axis=1, how='all')
    #print(aqmData.head)
    aqmData = aqmData[aqmData['LATITUDE'].notna()]
    aqmData = aqmData[aqmData['LONGITUDE'].notna()]
    aqmData = aqmData[aqmData['POLUENTE'].notna()]

    
    # Agrupamento por estado quando tivermos mais de uma fonte de informação
    aqmData = aqmData.fillna('-')
    remaining_columns = aqmData.columns[(aqmData.columns != 'POLUENTE') & (aqmData.columns != 'ID_MMA_COMPLETO') & (aqmData.columns != 'COD_POLUENTE')].tolist()
    
    
    # Agrupamento por estado quando tivermos mais de uma fonte de informação
    aqmDataGrouped = aqmData.groupby(remaining_columns).agg({
        'POLUENTE': lambda x: ', '.join(x),
    }).reset_index()
    #print(aqmDataGrouped)

    # Cria uma coluna com número de poluentes medidos
    aqmDataGrouped['N° Poluentes Medidos'] = aqmDataGrouped['POLUENTE'].apply(lambda x: len(x.split(',')))

    # Transforma em geodataframe
    gdf = gpd.GeoDataFrame(
        aqmDataGrouped, geometry=gpd.points_from_xy(aqmDataGrouped.LONGITUDE, aqmDataGrouped.LATITUDE), crs="EPSG:4326"
    )
    #print(gdf.head)
    # Renomeando colunas com primeira letra em maiúsculo
    gdf = columns_renamer(gdf)

    #print(gdf.Categoria.unique().shape[0])
    if (gdf.Categoria.unique().shape[0]==3) & (columnRef=='Categoria'):
        # Original colormap
        cmap = ListedColormap(["orange", "green"])
        # Get the list of colors from the existing colormap
        colors = cmap.colors
        #cmap = cmap.append('gray')
        colors.insert(0, 'gray')
        cmap = ListedColormap(colors)
        
    # Extrai o centroide dos locais onde existe monitoramento para centralizar o mapa
    center_geom = gdf.unary_union.centroid
    #print(center_geom)
    center = [center_geom.y, center_geom.x]

    # Cria um mapa padrão
    base_map = explore_with_bounds(
        gdf,
        column=None,
        cmap=cmap,
        legend=True,
        zoom_start=4,
        min_zoom=3,
        center=None)

    #gdf["Status"] = pd.Categorical(gdf["Status"], categories=["Ativa", "Inativa"])
    
    #columnsToltip = [s.capitalize() for s in columnsToltip]
    #columnRef = columnRef.capitalize()
    
    return gdf.explore(column=columnRef, tooltip=columnsToltip,
                       marker_kwds={"radius": 5},m=base_map,cmap=cmap, legend=True)








    

import geopandas as gpd
import folium
from folium.plugins import MiniMap, Fullscreen, MarkerCluster
from pathlib import Path
import os
import pandas as pd

def build_map_industries_by_pollution(
    industries_file: str | Path | None = None,
    rootPath: str | Path | None = None,
    sample: int | None = None,
    uf_filter: str | None = None,
) -> folium.Map:
    """
    Mapa Folium com indústrias organizadas por 'Potencial de Poluição da atividade'.
    - Polígonos são convertidos para centróides em CRS métrico.
    - Pode filtrar por UF ou usar uma amostra.
    - Se não passar industries_file, usa o caminho padrão em data/rep_espacial/inputs.
    """

    # Caminho padrão
    rootPath = Path(rootPath or os.path.dirname(os.getcwd()))
    industries_file = Path(
        industries_file or (rootPath / "data/rep_espacial/inputs/industrial_sites_20250902.gpkg")
    )

    # Carregar indústrias
    ind = gpd.read_file(industries_file).to_crs(4326)

    # Filtro opcional por UF
    if uf_filter and "UF" in ind.columns:
        ind = ind[ind["UF"].str.upper() == uf_filter.upper()]

    # Amostragem opcional
    if sample and sample < len(ind):
        ind = ind.sample(sample, random_state=42)

    # Converter polígonos em centróides (corrigindo CRS)
    poly_mask = ind.geometry.geom_type.isin(["Polygon", "MultiPolygon"])
    if poly_mask.any():
        ind_poly = ind.loc[poly_mask].to_crs(3857)  # métrico
        ind.loc[poly_mask, "geometry"] = ind_poly.geometry.centroid.to_crs(4326)

    # Centro do mapa
    minx, miny, maxx, maxy = ind.total_bounds
    center_lat, center_lon = (miny + maxy) / 2, (minx + maxx) / 2

    # Criar mapa base
    m = folium.Map(location=[center_lat, center_lon], zoom_start=5, tiles="cartodbpositron")

    # Paleta por potencial
    color_map = {
        "Pequeno": "green",
        "Médio": "orange",
        "Alto": "red"
    }

    # Criar uma camada para cada potencial
    for potencial, color in color_map.items():
        subset = ind[ind["Potencial de Poluição da atividade"].str.contains(potencial, case=False, na=False)]
        if subset.empty:
            continue

        layer = folium.FeatureGroup(name=f"Indústrias — {potencial}", show=False).add_to(m)
        cluster = MarkerCluster().add_to(layer)

        for _, row in subset.iterrows():
            g = row.geometry
            if g is None or g.is_empty:
                continue
            lat, lon = g.y, g.x
            name = row.get("Razão Social", "")
            tooltip_txt = f"Indústria: {name}" if pd.notna(name) else "Indústria"
            tooltip_txt += f"<br>Potencial: {potencial}"

            folium.CircleMarker(
                location=(lat, lon),
                radius=3,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.7,
                tooltip=tooltip_txt,
            ).add_to(cluster)

    # Extras
    MiniMap(toggle_display=True, position="bottomright").add_to(m)
    Fullscreen().add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)

    # Legenda fixa
    legend_html = "".join(
        f"<div style='display:flex;align-items:center;margin:2px 0;'>"
        f"<span style='background:{col};width:12px;height:12px;margin-right:6px;border:1px solid #555;'></span>{lab}</div>"
        for lab, col in color_map.items()
    )
    legend = (
        "<div style='position:fixed;bottom:20px;left:20px;background:white;"
        "padding:8px;border:1px solid #999;font-size:12px;z-index:9999;border-radius:4px;'>"
        "<b>Potencial de Poluição</b><br>" + legend_html + "</div>"
    )
    m.get_root().html.add_child(folium.Element(legend))

    return m


# ==== Teste rápido no Jupyter ====
rootPath = Path(os.path.dirname(os.getcwd()))

# Exemplo 1: todas as indústrias (pode pesar!)
# m_ind = build_map_industries_by_pollution()

# Exemplo 2: só SC
# m_ind = build_map_industries_by_pollution(uf_filter="SANTA CATARINA")

# Exemplo 3: amostra de 3000 indústrias
m_ind = build_map_industries_by_pollution(sample=3000)
m_ind
