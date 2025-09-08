#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug 19 13:48:15 2025

@author: brunojalowski
"""
# %% ============================== PACKAGES ===================================
import geopandas as gpd
from pathlib import Path
from long_2_utm_zone import long_2_utm_zone
from utm_zone_2_epsg import utm_zone_2_epsg
import pandas as pd
import numpy as np
import os

# Deactivates scientific notation
pd.set_option('display.float_format', '{:.2f}'.format)

# %% ================================ PATHS ==========================================
rootPath = os.path.dirname(os.getcwd())

inputs_path = rootPath + '/data/rep_espacial/inputs'

outputs_path = rootPath + '/data/rep_espacial/outputs'

flow_path = inputs_path + '/bruno_florianopolis_2025_7_1_0_23.parquet'

industrial_path = inputs_path + '/industrial_sites_20250902.gpkg'

stations_path = inputs_path + '/Monitoramento_QAr_BR.csv'


# %% =================== FLOW AND SPEED DATA FROM TOMTOM ==============================

# Reading geodataframe
gdf = (gpd
       .read_parquet(path=flow_path)
       .astype({'osm_id': int,
                'vehicle_count': float,
                'average_daily_vehicle_count': float,
                'road_length': float,
                'vkt_per_hour': float,
                'surface': str,
                'avg_traffic_level': float}
               )
       )


# Removing datetime column as index
gdf.reset_index(drop=False,
                inplace=True)


# %% Road surface reclassification--------------------------------------------------------
"""
Classificação atual:
    array(['asphalt', 'paving_stones', 'compacted', None, 'unpaved', 'sett',
       'paved', 'cobblestone', 'metal', 'ground', 'gravel', 'dirt',
       'concrete:plates'], dtype=object)

Reclassificação:
    paved = asphalt, paving_stones,sett, paved, cobblestone, metal,
            concrete:plates
    unpaved = compacted, None, unpaved, ground, gravel, dirt
"""

gdf.loc[(gdf['surface'] == 'asphalt') |
        (gdf['surface'] == 'paving_stones') |
        (gdf['surface'] == 'sett') |
        (gdf['surface'] == 'cobblestone') |
        (gdf['surface'] == 'metal') |
        (gdf['surface'] == 'concrete:plates'),
        'surface'] = 'paved'

gdf.loc[(gdf['surface'] == 'compacted') |
        (gdf['surface'] == 'None') |
        (gdf['surface'] is None) |
        (gdf['surface'] == 'ground') |
        (gdf['surface'] == 'gravel') |
        (gdf['surface'] == 'dirt'), 'surface'] = 'unpaved'

# %% =========================ROAD TEMPLATE ====================================
# Get roads for a single instant of time (drop temporal duplicates)
roads = gdf.drop_duplicates(subset='osm_id').reset_index(drop=True)

# Filter all roads with adt lesser than 10k
roads = roads[roads['average_daily_vehicle_count'] > 1000]

# %% ======================= INDUSTRIAL SITES =====================================
industrial_gdf = gpd.read_file(industrial_path)

# Saving geometry for safekeeping after sjoin_nearest with stations
industrial_gdf['industry_geom'] = industrial_gdf.geometry

# %% ==================== AIR MONITORING STATIONS ===================================
stations = gpd.read_file(stations_path)

stations = gpd.GeoDataFrame(stations,
                            geometry=gpd.points_from_xy(stations.LONGITUDE,
                                                        stations.LATITUDE,
                                                        crs='EPSG:4326'))

stations.loc[:,'utm_zone'] = long_2_utm_zone(stations
                                             .geometry
                                             .centroid
                                             .x)

# Atribuindo código EPSG SIRGAS 2000 projetado de acordo com a zona 
# UTM e a latitude
stations.loc[:,'EPSG'] = utm_zone_2_epsg(stations['utm_zone'],
                                         stations.geometry
                                         .centroid
                                         .x)

# Dropping utm_zone column
stations.drop(columns='utm_zone', inplace=True)

# Converting code numbers to float
stations['COD_POLUENTE'] = pd.to_numeric(stations['COD_POLUENTE'],
                                         errors='coerce')

# Filtering stations with pollutant, discarding other atmospheric variables
stations = stations[stations['COD_POLUENTE'].isin([1.0, 2.0, 3.0, 4.0,
                                                   5.0, 7.0, 8.0])]


#%% ====== GET DISTANCE OF ROADS OF VARIOUS ADT BANDS AND INDUSTRIES TO EACH STATION =========
def get_distance_to_stations(stations:gpd.GeoDataFrame,
                             poll:str,
                             roads:gpd.GeoDataFrame,
                             industries:gpd.GeoDataFrame,
                             get_industries:bool=True):
    """
    Returns the input geodataframe with additional columns with the closest roads
    of each ADT (Average Daily Traffic) band (10k, 20k, 40k etc) and  

    Parameters
    ----------
    stations : gpd.GeoDataFrame
        Geodataframe of air monitoring stations containing the columns 'COD_POLUENTE',
        'EPSG', 'ID_OEMA', 'POLUENTE' .
    poll : str
        One of 5 following pollutants: 'co', 'so2', 'no2', 'pm' and 'o3'.
    roads: gpd.GeoDataFrame
        Geodataframe of roads with columns 'average_daily_vehicle_count' and 'osm_id'
        (identifier code from OpenStreetMaps).
    industries: gpd.GeoDataFrame
        Geodataframe of active industries with columns 'Razão Social', 'industry_geom'
        and 'geometry'.
    get_industries : bool, optional
        If True the function also gets the closest industry to each station, adding
        the columns 'distance_to_industry', 'industry_geom' and 'Razão Social'.
        The default is True.

    Returns
    -------
    Input geodataframe with 3 additional columns for each ADT band with an existing
    road within it: 'osm_id_{}k', 'average_daily_vehicle_count_{}k' and 'distance_{}k'.
    The default also returns the columns 'distance_to_industry', 'industry_geom' and 
    'Razão Social' for the closest industry to each station.

    """
    # Dict of average daily vehicle count (value * 1000)
    pollutants_adt_dict = {'co':[1, 10, 20, 30, 40, 50, 60, np.inf],
                           'so2':[1, 10, 20, 30, 40, 50, 60, np.inf],
                           'no2':[1, 10, 15, 20, 40, 70, 110, np.inf],
                           'pm': [1, 15, 20, 30, 40, 50, 60, 70, 80, np.inf],
                           'o3':[10, 15, 20, 40, 70, 110, np.inf]}

    # Dict of subsets by pollutant
    poll_codes = {
        'co': [7],
        'so2': [3],
        'no2': [4],
        'pm': [1,2,8],
        'o3': [5]
    }
    
    # Filtering station subset and adt_list for the pollutant 
    poll_subset = stations[stations['COD_POLUENTE'].isin(poll_codes[poll])]
    adt_list = pollutants_adt_dict[poll]
    
    # Creating dictionaries of subsets for each EPSG 
    roads_subsets = {}
    stations_subsets = {}
    industries_subsets = {}
    
    # Creating epsg dictionary
    choices = {'{}'.format(q): q for q in stations['EPSG'].unique()}

    # Iterating over EPSG codes
    for epsg in choices.keys():
        
         # Creating stations sub dataframe and setting respective crs
         stations_subsets[epsg] = (
             poll_subset[poll_subset['EPSG'] == epsg]
             .to_crs(epsg)
         )
    
         # Creating sub dataframe of roads for each EPSG
         roads_subsets[epsg] = roads.to_crs(epsg)
    
    
         # Creating sub dataframe of industries for each EPSG
         """creates a subset with all industries that are the closest to a 
         station inside given epsg and converts it to that crs"""
         industries_subsets[epsg] = industries.to_crs(epsg)
         

         # Iterating over adt values
         for idx, adt in enumerate(adt_list[0:-1]):
             adt_col = 'average_daily_vehicle_count'
             filtered_roads = (
                 roads_subsets[epsg]
                 .loc[(roads_subsets[epsg][adt_col] >= adt * 1000) &
                 (roads_subsets[epsg][adt_col] < adt_list[idx + 1] * 1000),
                 ['osm_id', adt_col, 'geometry']]
                 )
             
             if filtered_roads.empty:
                 continue
             
             # Calculating distance to the closest road, for each road class
             stations_subsets[epsg] = (
                gpd.sjoin_nearest(stations_subsets[epsg],
                                  filtered_roads,
                                  how='left',
                                  lsuffix=('{}k'.format(adt_list[idx - 1])
                                                        if idx > 0
                                                        else None),
                                  rsuffix='{}k'.format(adt),
                                  distance_col='distance_{}k'.format(adt))
                 )
     
             # Dropping right index from sjoin
             stations_subsets[epsg].drop(columns='index_{}k'.format(adt),
                                         inplace=True)
             
             rename_cols = {}
             if 'osm_id' in stations_subsets[epsg].columns:
                 rename_cols['osm_id'] = f'osm_id_{adt}k'
             if adt_col in stations_subsets[epsg].columns:
                 rename_cols[adt_col] = f'{adt_col}_{adt}k'
             if rename_cols:
                 stations_subsets[epsg].rename(columns=rename_cols, inplace=True)
             
             # Drop duplicated lines derived from multiple roads with same 
             # distance to the station
             if f'{adt_col}_{adt}k' in stations_subsets[epsg].columns:
                 stations_subsets[epsg] = (
                     stations_subsets[epsg]
                     .sort_values(by=f'{adt_col}_{adt}k',ascending=False)
                     .drop_duplicates(subset=['ID_OEMA',
                                              f'distance_{adt}k',
                                              'POLUENTE'])
                  )
            
                        
         if get_industries == True:
             # Calculates distance from each station to closest industry
             stations_subsets[epsg] = (
                 gpd.sjoin_nearest(stations_subsets[epsg],
                                   industries_subsets[epsg][['Razão Social',
                                                             'industry_geom',
                                                             'geometry']],
                                   distance_col="distance_to_industry")
                 )
         
         # Dropping duplicates with all columns duplicated
         stations_subsets[epsg] = (
             stations_subsets[epsg]
             .drop_duplicates(subset= ['ID_OEMA', 'POLUENTE']))
         
         # Dropping right index from sjoin
         stations_subsets[epsg].drop(columns='index_right', inplace=True)
         
         # Reprojecting geometry of each sub dataframe to WGS 84
         stations_subsets[epsg] = stations_subsets[epsg].to_crs(4326)
         
         
    # Concatenating sub gdfs back to main gdf
    stations_by_poll = (
        gpd.GeoDataFrame(pd.concat([stations_subsets[df] 
                                    for df 
                                    in stations_subsets])
                         )
        )
    return stations_by_poll


# Applying function
subset_co = get_distance_to_stations(stations=stations,
                                     poll='co',
                                     roads=roads,
                                     industries=industrial_gdf,
                                     get_industries=True)

subset_no2 = get_distance_to_stations(stations=stations,
                                      poll='no2',,
                                      roads=roads,
                                      industries=industrial_gdf,
                                      get_industries=True)

subset_o3 = get_distance_to_stations(stations=stations,
                                     poll='o3',,
                                     roads=roads,
                                     industries=industrial_gdf,
                                     get_industries=True)

subset_pm = get_distance_to_stations(stations=stations,
                                     poll='pm',,
                                     roads=roads,
                                     industries=industrial_gdf,
                                     get_industries=True)

subset_so2 = get_distance_to_stations(stations=stations,
                                      poll='so2',,
                                      roads=roads,
                                      industries=industrial_gdf,
                                      get_industries=True)

#%% =============== PREPROCESSING FOR REPRESENTATIVENESS CLASSIFICATION ===============

# Reading reference tables for classification
# https://www.gov.br/mma/pt-br/assuntos/meio-ambiente-urbano-recursos-hidricos-qualidade-ambiental/qualidade-do-ar/guia-tecnico-para-o-monitoramento-e-avaliacao-da-qualidade-do-ar.pdf

ref_table_co = pd.read_csv(inputs_path + '/ref_table_so2eco.csv')
ref_table_no2 = pd.read_csv(inputs_path + '/ref_table_no2.csv')
ref_table_o3 = pd.read_csv(inputs_path + '/ref_table_o3.csv')
ref_table_pm = pd.read_csv(inputs_path + '/ref_table_pm.csv')
ref_table_so2 = pd.read_csv(inputs_path + '/ref_table_so2eco.csv')


# Note from tables indicating what to do with intermediate adt values
'''
Distance from the edge of the nearest traffic lane. The distance for 
intermediate traffic counts should be interpolated from the table values based
on the actual traffic count.

# https://www.ecfr.gov/current/title-40/chapter-I/subchapter-C/part-58/appendix-Appendix%20E%20to%20Part%2058
'''

# Dict of average daily vehicle count (real = value * 1000)
pollutants_adt_dict = {'co':[1, 10, 20, 30, 40, 50, 60, np.inf],
                       'so2':[1, 10, 20, 30, 40, 50, 60, np.inf],
                       'no2':[1, 10, 15, 20, 40, 70, 110, np.inf],
                       'pm': [1, 15, 20, 30, 40, 50, 60, 70, 80, np.inf],
                       'o3':[10, 15, 20, 40, 70, 110, np.inf]}

## Preparing dataframe for interpolation ----------------------------------------------
interpolated_co = ref_table_co.set_index('avg_adt').squeeze()
interpolated_no2 = ref_table_no2.set_index('avg_adt').squeeze()
interpolated_o3 = ref_table_o3.set_index('avg_adt').squeeze()
interpolated_pm = ref_table_pm.set_index('avg_adt').squeeze()
interpolated_so2 = ref_table_so2.set_index('avg_adt').squeeze()

# Setting dict of dfs for interpolation
interpolated_dict = {
    'co': interpolated_co,
    'so2': interpolated_so2,
    'no2': interpolated_no2,
    'pm': interpolated_pm,
    'o3': interpolated_o3
}

# Redefining pollutant subsets dictionary
pollutant_subsets = {
    'co': subset_co,
    'so2': subset_so2,
    'no2': subset_no2,
    'pm': subset_pm,
    'o3': subset_o3
}

## Interpolation of representativeness class limits -----------------------------------
# Iterating over pollutants and pollutant subsets
for poll, subset in pollutant_subsets.items():
    
    # Iterating over adt values from ref_table for each pollutant
    for idx, adt_band in enumerate(pollutants_adt_dict[poll][:-1]):
        col_name = f'average_daily_vehicle_count_{adt_band}k'

        if col_name not in subset.columns:
            print(f"[WARNING] '{col_name}' nonexistant in subset_{poll}")
            continue
        
        # Iterating over adt values for each road in the pollutant subset
        for adt_value in subset[col_name]:
            interpolated_dict[poll].loc[adt_value] = np.nan
                
    # Sorting index ascending
    interpolated_dict[poll].sort_index(inplace=True)
                
    # Interpolating nan values #FIXME
    interpolated_dict[poll].interpolate(method='index',
                                        inplace=True)
                
    # Resetting index
    interpolated_dict[poll].reset_index(inplace=True)
                

## Adding columns with rep class limits -----------------------------------------------
# Iterating over pollutants and pollutant subsets
for poll, subset in pollutant_subsets.items():
    
    # Iterating over adt values from ref_table for each pollutant
    for idx, adt_band in enumerate(pollutants_adt_dict[poll][:-1]):
        col_name = f'average_daily_vehicle_count_{adt_band}k'
        
        # Registering adt values without roads for each pollutant
        if col_name not in subset.columns:
            print(f"[WARNING] '{col_name}' nonexistant in subset_{poll}")
            continue
        
        # Getting right-side table (for the merge)
        interp_df = interpolated_dict[poll].copy()
        
        # Renaming first column, that the merge function won't add suffix
        suffix = f"_{adt_band}k"
        interp_df = interp_df.rename(columns={
            col: f"{col}{suffix}" 
            for col
            in interp_df.columns
            if col != 'avg_adt'
        })
        
        # Merging columns with distance limits for each adt and rep class
        pollutant_subsets[poll] = pollutant_subsets[poll].merge(
            right= interp_df,
            how='left',
            left_on= col_name,
            right_on='avg_adt',
            suffixes=(None, f"_{adt_band}k")
            )
        
        # Dropping added avg_adt_{}k columns
        if (idx != 0) and (f'avg_adt_{adt_band}k' 
                           in pollutant_subsets[poll].columns):
            pollutant_subsets[poll].drop(columns=[f'avg_adt_{adt_band}k'],
                                         inplace=True)
    
    # Drop first added avg_adt column
    pollutant_subsets[poll].drop(columns=['avg_adt'], inplace=True)
        
    # Filling nan values with np.inf (only {micro/meso/bairro/urb}_max are nan)
    pollutant_subsets[poll].fillna(np.inf, inplace=True)
    pollutant_subsets[poll].infer_objects(copy=False)
        
del suffix


# %% Checking if all REP_ESPACIAL_NAMEs are True or False------------------------------------
# Iterating over pollutants and pollutant subsets
for poll, subset in pollutant_subsets.items():
    
    if poll != 'pm':
        
        # Iterating over adt values from ref_table for each pollutant
        for idx, adt_band in enumerate(pollutants_adt_dict[poll][:-1]):
            distance = f'distance_{adt_band}k'
            cols = subset.columns
        
            # MICRO
            col_micro_min = f'micro_min_{adt_band}k'
            col_micro_max = f'micro_max_{adt_band}k'
            if col_micro_min in cols and col_micro_max in cols:
                pollutant_subsets[poll][f'rep_micro_{adt_band}k'] = np.where(
                    (subset[distance] > subset[col_micro_min]) &
                    (subset[distance] < subset[col_micro_max]),
                    True,
                    False)
        
            # MESO
            col_meso_min = f'meso_min_{adt_band}k'
            col_meso_max = f'meso_max_{adt_band}k'
            if col_meso_min in cols and col_meso_max in cols:
                pollutant_subsets[poll][f'rep_meso_{adt_band}k'] = np.where(
                    (subset[distance] > subset[col_meso_min]) &
                    (subset[distance] < subset[col_meso_max]),
                    True,
                    False)
        
            # BAIRRO
            col_bairro_min = f'bairro_min_{adt_band}k'
            col_bairro_max = f'bairro_max_{adt_band}k'
            if col_bairro_min in cols and col_bairro_max in cols:
                pollutant_subsets[poll][f'rep_bairro_{adt_band}k'] = np.where(
                    (subset[distance] > subset[col_bairro_min]) &
                    (subset[distance] < subset[col_bairro_max]),
                    True,
                    False)
        
            # URB
            col_urb_min = f'urb_min_{adt_band}k'
            col_urb_max = f'urb_max_{adt_band}k'
            if col_urb_min in cols and col_urb_max in cols:
                pollutant_subsets[poll][f'rep_urb_{adt_band}k'] = np.where(
                    (subset[distance] > subset[col_urb_min]) &
                    (subset[distance] < subset[col_urb_max]),
                    True,
                    False)
            
            
    else:
        for idx, adt_band in enumerate(pollutants_adt_dict[poll][:-1]):
            distance = f'distance_{adt_band}k'
            cols = subset.columns
        
            # MICRO
            col_micro_min = f'micro_min_{adt_band}k'
            col_micro_max = f'micro_max_{adt_band}k'
            if col_micro_min in cols and col_micro_max in cols:
                pollutant_subsets[poll][f'rep_micro_{adt_band}k'] = np.where(
                    (subset[distance] > subset[col_micro_min]) &
                    (subset[distance] < subset[col_micro_max]),
                    True,
                    False)
        
            # MESO
            col_meso_min = f'meso_min_{adt_band}k'
            col_meso_max = f'meso_max_{adt_band}k'
            if col_meso_min in cols and col_meso_max in cols and adt_band != 1:
                pollutant_subsets[poll][f'rep_meso_{adt_band}k'] = np.where(
                    (subset[distance] > subset[col_meso_min]) &
                    (subset[distance] < subset[col_meso_max]),
                    True,
                    False)
        
            # BAIRRO
            col_bairro_min = f'bairro_min_{adt_band}k'
            col_bairro_max = f'bairro_max_{adt_band}k'
            if col_bairro_min in cols and col_bairro_max in cols:
                pollutant_subsets[poll][f'rep_bairro_{adt_band}k'] = np.where(
                    (subset[distance] > subset[col_bairro_min]) &
                    (subset[distance] < subset[col_bairro_max]),
                    True,
                    False)
        
            # URB
            col_urb_min = f'urb_min_{adt_band}k'
            col_urb_max = f'urb_max_{adt_band}k'
            if col_urb_min in cols and col_urb_max in cols and adt_band != 80:
                pollutant_subsets[poll][f'rep_urb_{adt_band}k'] = np.where(
                    (subset[distance] > subset[col_urb_min]) &
                    (subset[distance] < subset[col_urb_max]),
                    True,
                    False)

del col_bairro_max, col_bairro_min, col_meso_max, col_meso_min, col_micro_max
del col_micro_min, col_urb_max, col_urb_min, distance, cols
    
# %% Checking validity of each REP_ESPACIAL_NAME (micro/meso/bairro/urbana)-----------------
# Assigning gdfs from dictionary to individual variables
subset_co = pollutant_subsets['co']
subset_no2 = pollutant_subsets['no2']
subset_o3 = pollutant_subsets['o3']
subset_pm = pollutant_subsets['pm']
subset_so2 = pollutant_subsets['so2']

# Helper function for checking if there are existing columns of each scale

def safe_all(df, like_str):
    """
    Filters all columns from a dataframe with a common substring in their names
    and checks if each line is all True, returning a series of True. If not or if
    empty, returns a series of False.
    
    This function is necessary because if there are no columns in the filtered
    dataframe, the .all function returns a series of True and that is misleading.
    
    Parameters
    ----------
    df : dataframe 
        dataframe with several columns with a repeting element.
    like_str: str
        common substring within dataframe columns.

    Returns
    -------
    filtered : series of bool
        Series of bool with lenght equal to 
        
    """
    # Filters all columns with specific str in name
    filtered = df.filter(like=like_str)
    
    # If there are no matching columns, it returns a Series of False
    if filtered.shape[1] == 0:
        return pd.Series([False] * len(df), index=df.index)
        
    return filtered.all(axis='columns')


# Applying function to check validity of each REP_ESPACIAL_NAME----------------------------
# CO ---------------------------------
subset_co['rep_micro_all'] = safe_all(subset_co, 'rep_micro')
subset_co['rep_bairro_all'] = safe_all(subset_co, 'rep_bairro')

# NO2 -------------------------------
subset_no2['rep_bairro_all'] = safe_all(subset_no2, 'rep_bairro')
subset_no2['rep_urb_all'] = safe_all(subset_co, 'rep_urb')

# O3 --------------------------------
subset_o3['rep_bairro_all'] = safe_all(subset_o3, 'rep_bairro')
subset_o3['rep_urb_all'] = safe_all(subset_o3, 'rep_urb')

# PM -------------------------------
subset_pm['rep_meso_all'] = safe_all(subset_pm, 'rep_meso')
subset_pm['rep_bairro_all'] = safe_all(subset_pm, 'rep_bairro')
subset_pm['rep_urb_all'] = safe_all(subset_pm, 'rep_urb')

# SO2 -------------------------------------------
subset_so2['rep_micro_all'] = safe_all(subset_so2, 'rep_micro')
subset_so2['rep_bairro_all'] = safe_all(subset_so2, 'rep_bairro')


# %% CLASSIFYING THE REPRESENTATIVENESS STATUS OF EACH STATION-----------------
def classify_spatial_rep(subset):
    """
    It checks the validity of each REP_ESPACIAL_NAME (all adt bands for a single scale
    must be True for it to be valid) and the station receives the more 
    comprehensive spatial scale, is the following order.
    
    MICRO < MESO < BAIRRO < URBANA

    Parameters
    ----------
    subset : geodataframe 
        Subset of total monitoring stations, relative to a single pollutant

    Returns
    -------
    subset : geodataframe
        input subset with a column 'REP_ESPACIAL_NAME'

    """
    conditions = []
    choices = []
    
    if 'rep_urb_all' in subset.columns:
        conditions.append(subset['rep_urb_all'] == True)
        choices.append('urbana')
    
    if 'rep_bairro_all' in subset.columns:
        conditions.append(subset['rep_bairro_all'] == True)
        choices.append('bairro')
        
    if 'rep_meso_all' in subset.columns:
        conditions.append(subset['rep_meso_all'] == True)
        choices.append('meso')

    if 'rep_micro_all' in subset.columns:
        conditions.append(subset['rep_micro_all'] == True)
        choices.append('micro')
    
    subset['REP_ESPACIAL_NAME'] = np.select(conditions,
                                    choices,
                                    default='não representativo')
    
    return subset

subset_co = classify_spatial_rep(subset_co)
subset_no2 = classify_spatial_rep(subset_no2)
subset_o3 = classify_spatial_rep(subset_o3)
subset_pm = classify_spatial_rep(subset_pm)
subset_so2 = classify_spatial_rep(subset_so2)


#%% REPRESENTATIVENESS BUFFERS -----------------------------------------------------
"""microscale: < 100 m
   mesoscale: 100 m < x < 500 m
   neighbourhood scale: 500 m < x < 4000 m
   urban scale: 4000 m < x < 50000 m
""" 

def create_buffered_gdf(subset,
                        buffer_sizes,
                        target_crs="EPSG:4326",
                        create_buffer=True):
    """
    Creates buffer size columns for a GeoDataFrame grouped by EPSG codes, with
    an option for creating bufffer geometries.

    Parameters:
        subset_co (GeoDataFrame): Input GeoDataFrame with 'EPSG', 'REP_ESPACIAL_NAME', 
        and 'geometry' columns.
        
        buffer_sizes (dict): Dictionary mapping `REP_ESPACIAL_NAME` values to buffer 
        sizes.
        
        target_crs (str): CRS to reproject the final GeoDataFrame to. Default 
        is 'EPSG:4326'.
        
        create_buffer (bool): checks if buffer geometry is created. Default is
        True

    Returns:
        GeoDataFrame: A single GeoDataFrame with buffered geometries in the 
        target CRS.
    """
    
    buffered_gdfs = []

    for epsg in subset['EPSG'].unique():
        # Subset and project to respective EPSG
        gdf_epsg = subset[subset['EPSG'] == epsg].to_crs(epsg)

        # Dropping existing REP_ESPACIAL column
        gdf_epsg.drop(columns=['REP_ESPACIAL'])
        
        # Map buffer sizes and create buffer geometries
        gdf_epsg['REP_ESPACIAL'] = (gdf_epsg['REP_ESPACIAL_NAME']
                                   .map(buffer_sizes)
                                   .fillna(0))
        
        # Creates buffer geometries if True
        if create_buffer == True:
            gdf_epsg['buffer'] = (gdf_epsg
                                  .geometry
                                  .buffer(gdf_epsg['buffer_size'])
                                  .to_crs(target_crs))

        # Replace geometry with buffer and reproject to target CRS
        gdf_epsg = gdf_epsg.to_crs(target_crs)

        # Append to list
        buffered_gdfs.append(gdf_epsg)

    # Combine all buffered GeoDataFrames
    buffered_subset = gpd.GeoDataFrame(
        pd.concat(buffered_gdfs, ignore_index=True),
        crs=target_crs
    )

    return buffered_subset


# Buffer sizes dictionary according to REP_ESPACIAL_NAME
buffer_sizes = {
    'urbana': 50000,
    'bairro': 4000,
    'meso': 500,
    'micro': 100,
}

# Applying function
# CO 
buffered_subset_co = create_buffered_gdf(subset_co,
                                         buffer_sizes,
                                         target_crs='EPSG:4326',
                                         create_buffer=False)
# NO2 
buffered_subset_no2 = create_buffered_gdf(subset_no2,
                                         buffer_sizes,
                                         target_crs='EPSG:4326',
                                         create_buffer=False)
# O3
buffered_subset_o3 = create_buffered_gdf(subset_o3,
                                         buffer_sizes,
                                         target_crs='EPSG:4326',
                                         create_buffer=False)
# PM 
buffered_subset_pm = create_buffered_gdf(subset_pm,
                                         buffer_sizes,
                                         target_crs='EPSG:4326',
                                         create_buffer=False)
# SO2 
buffered_subset_so2 = create_buffered_gdf(subset_so2,
                                         buffer_sizes,
                                         target_crs='EPSG:4326',
                                         create_buffer=False)

## REFINING DATAFRAMES FOR INTENDED OUTPUTS----------------------------------------------------
# 1) stations_and_industries
cols = ['ID_OEMA', 'geometry', 'Razão Social', 'distance_to_industry']
stations_and_industries = pd.concat([buffered_subset_co[cols],
                               buffered_subset_no2[cols],
                               buffered_subset_o3[cols],
                               buffered_subset_pm[cols],
                               buffered_subset_so2[cols]])



# 2) buffered_stations
# Removing auxiliar columns
def drop_aux_cols(subset):
    return subset.drop(columns= (list(subset
                                      .filter(like='rep')
                                      .columns) +
                                 list(subset
                                      .filter(like='min')
                                      .columns) +
                                 list(subset
                                      .filter(like='max')
                                      .columns) +
                                 list(subset
                                      .filter(like='k')
                                      .columns) +
                                 ['EPSG','distance_to_industry',
                                  'Razão Social', 'industry_geom']
                                 )
                       )
    
buffered_subset_co = drop_aux_cols(buffered_subset_co)
buffered_subset_no2 = drop_aux_cols(buffered_subset_no2)
buffered_subset_o3 = drop_aux_cols(buffered_subset_o3)
buffered_subset_pm = drop_aux_cols(buffered_subset_pm)
buffered_subset_so2 = drop_aux_cols(buffered_subset_so2)

buffered_stations = pd.concat([buffered_subset_co,
                               buffered_subset_no2,
                               buffered_subset_o3,
                               buffered_subset_pm,
                               buffered_subset_so2])

## SAVING DATA---------------------------------------------------------------
# Saving geodataframe with closest industry to each station
"""['ID_OEMA', 'geometry', 'Razão Social', 'distance_to_industry','industry_geom']"""
stations_and_industries.to_parquet(outputs_path + '/stations_and_industries.parquet')


# Saving geodataframe with stations, their spatial representativeness classification
# and buffer size
"""All columns from stations spreadsheet + ['REP_ESPACIAL','REP_ESPACIAL_NAME']"""
buffered_stations.to_parquet(outputs_path + '/rep_espacial.parquet')





