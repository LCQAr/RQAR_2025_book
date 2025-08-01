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

def explore_with_bounds(
    gdf,
    column=None,
    bounds=None,  # [south, west, north, east]
    cmap="Set1",
    legend=True,
    zoom_start=4,
    min_zoom=4,
    center=None):
    """
    Display a GeoDataFrame using geopandas.explore() with map zoom restricted to a given bounding box.

    Parameters
    ----------
    gdf : GeoDataFrame
        The data to plot.
    column : str, optional
        Column used for coloring.
    bounds : list or tuple of float, optional
        Bounding box as [south, west, north, east].
        If None, uses gdf total bounds.
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
    
    # If no bounds provided, use total_bounds
    if bounds is None:
        minx, miny, maxx, maxy = gdf.total_bounds
        bounds = [miny, minx, maxy, maxx]

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
    return base_map

def espacial_poluentes_monitorados():
    
        
    # Caminho para a pasta de dados
    rootPath = os.path.dirname(os.getcwd())
    
    # Lendo o csv
    aqmData = pd.read_csv(rootPath+'/data/Monitoramento_QAr_BR.csv',encoding = 'unicode_escape')
    aqmData['ID_OEMA'] = aqmData['ID_OEMA'].str.replace(' ', '') 
    aqmData['POLUENTE'] = aqmData['POLUENTE'].str.upper()
    
    # Agrupamento por estado quando tivermos mais de uma fonte de informação
    aqmDataGrouped = aqmData.groupby(['ID_OEMA','LATITUDE','LONGITUDE','CATEGORIA','FUNCIONAMENTO']).agg({
        'POLUENTE': lambda x: ', '.join(x),
    }).reset_index()

    aqmDataGrouped['N° Poluentes Medidos'] = aqmDataGrouped['POLUENTE'].apply(lambda x: len(x.split(',')))

    gdf = gpd.GeoDataFrame(
        aqmDataGrouped, geometry=gpd.points_from_xy(aqmDataGrouped.LONGITUDE, aqmDataGrouped.LATITUDE), crs="EPSG:4326"
    )

    brazil= gpd.read_file(rootPath+'/data/shapefiles/BR_Pais_2024/BR_Pais_2024.shp')

    
    # Get total bounds: [minx, miny, maxx, maxy]
    minx, miny, maxx, maxy = brazil.to_crs(4326).buffer(0.5).total_bounds
    
    # Convert to [south, west, north, east] for folium
    brazil_bounds = [miny, minx, maxy, maxx]
    
    base_map = explore_with_bounds(
        gdf,
        column=None,
        bounds=brazil_bounds,  # [south, west, north, east]
        cmap="Set1",
        legend=True,
        zoom_start=4,
        min_zoom=4,
        center=None)
    
    return gdf.explore(column="N° Poluentes Medidos", tooltip=["ID_OEMA", "POLUENTE","N° Poluentes Medidos",'CATEGORIA','FUNCIONAMENTO'],
            marker_kwds={"radius": 5},m=base_map,min_zoom=4,categorical=True,)





    