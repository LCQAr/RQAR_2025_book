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
    'FLAG':         ''
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
    aqmData = pd.read_csv(rootPath+'/data/Monitoramento_QAr_BR.csv',encoding = 'unicode_escape')
    aqmData['ID_OEMA'] = aqmData['ID_OEMA'].str.replace(' ', '') 
    aqmData['POLUENTE'] = aqmData['POLUENTE'].str.upper()

    # Remove colunas com todos valores iguais a NaN
    aqmData = aqmData.dropna(axis=1, how='all')

    remaining_columns = aqmData.columns[aqmData.columns != 'POLUENTE'].tolist()
    #print(remaining_columns)
    
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

    # Renomeando colunas com primeira letra em maiúsculo
    gdf = columns_renamer(gdf)
    #print(gdf)

    # Extrai o centroide dos locais onde existe monitoramento para centralizar o mapa
    center_geom = gdf.unary_union.centroid
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








    