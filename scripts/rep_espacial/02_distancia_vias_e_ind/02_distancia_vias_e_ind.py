"""Esse arquivo resulta em 5 variáveis, uma para cada poluente: subset_co, subset_no2, subset_o3, subset_pm, subset_so2.

Essas variáveis são a planilha de estações (stations) para cada poluente com todas as suas colunas originais, adicionada das colunas:
    - 'average_daily_vehicle_count_{}k' --> fluxo veicular médio diário (ADT) da via mais próxima 
    dentro da faixa de ADT {}.
    - 'distance_{}k' --> distância (m) da estação até a via mais próxima dentro da faixa de ADT {}.
    - 'osm_id_{}k' --> código OpenStreetMaps da via mais próxima dentro da faixa de ADT {}.

onde {} é o valor da faixa de fluxo veicular médio (ADT) observada.


# Exemplo do subset_co -----------------------------------------------
['COLUNAS ORIGINAIS DA PLANILHA', 'osm_id_1k',
 'average_daily_vehicle_count_1k', 'distance_1k', 'osm_id_10k',
 'average_daily_vehicle_count_10k', 'distance_10k', 'osm_id_20k',
 'average_daily_vehicle_count_20k', 'distance_20k', 'osm_id_30k',
 'average_daily_vehicle_count_30k', 'distance_30k', 'osm_id_40k',
 'average_daily_vehicle_count_40k', 'distance_40k', 'osm_id_50k',
 'average_daily_vehicle_count_50k', 'distance_50k', 'osm_id_60k',
 'average_daily_vehicle_count_60k', 'distance_60k', 'Razão Social',
 'industry_geom', 'distance_to_industry]

"""
# ========================= IMPORTANDO PACOTES ====================================
import geopandas as gpd
from pathlib import Path
import pandas as pd
import numpy as np
import os

# ============================== CAMINHOS ============================
# Caminho da pasta mãe
root_path = os.path.dirname(os.getcwd())

# Caminho da pasta de inputs
inputs_path = root_path + '/02_distancia_vias_e_ind/inputs'

# Caminho da pasta de outputs
outputs_path = root_path + '/02_distancia_vias_e_ind/outputs'

# Arquivo de todas as vias do BR
roads_path = '/home/nobre/Notebooks/' + os.readlink(inputs_path + '/roads.txt')

# Arquivo de indústrias BR (Gerais, mineração e aterros)
industrial_path = '/home/nobre/Notebooks/' + os.readlink(inputs_path + '/industrial_gdf.txt')

# Planilha de estações de monitoramento do BR
stations_path = '/home/nobre/Notebooks/' + os.readlink(inputs_path + '/stations.txt')


# ============== FUNÇÃO DE DISTÂNCIA ============================================
"""
Esta seção faz a junção espacial entre estações e as vias mais próximas para a cada, dentro de cada faixa de ADT, segundo as faixas disponíveis para cada poluente. Então, 3 colunas são criadas para cada faixa de ADT com vias de ADT > 0: 
    - 'osm_id_{}k': int.
        Código de indentificação de vias do OPenStreetMaps
    - 'average_daily_vehicle_count_{}k': float.
        Fluxo médio diário de veículos para a via mais próxima dentro de cada faixa de ADT
    - 'distance_{}k': float.
        Distância de cada estação para cada via, em metros
    
"""

def get_distance_to_stations(stations:gpd.GeoDataFrame,
                             poll:str,
                             roads:gpd.GeoDataFrame,
                             industries:gpd.GeoDataFrame,
                             get_industries:bool=True):
    """
    Esta função calcula a distância entre cada estação e a via mais próxima, dentro de
    cada faixa de ADT (fluxo médio diário de 10k, 20k, 40k, etc), adicionando 3 colunas:
        'osm_id_{}k': 
            Código de identificação do OpenStreetMaps para a via mais próximas dentro
            da faixa de ADT de {}k
        'average_daily_vehicle_count_{}k': 
            Fluxo médio diário de veículos para a via mais próxima na faixa de ADT de {}k
        'distance_{}k': 
            Distância entre cada estação e a via mais próxima na faixa de ADT de {}k

    Parameters
    ----------
    stations : gpd.GeoDataFrame
        Geodataframe de estações de monitoramento da qualidade do ar contendo as colunas
        'COD_POLUENTE', 'EPSG', 'ID_OEMA', 'POLUENTE'.
    poll : str
        One of 5 following pollutants: 'co', 'so2', 'no2', 'pm' and 'o3'.
    roads: gpd.GeoDataFrame
        Geodataframe de vias com colunas 'average_daily_vehicle_count' e 'osm_id'
    industries: gpd.GeoDataFrame
        Geodataframe de indústrias ativas com colunas 'Razão Social', 'industry_geom'
        e 'geometry'.
    get_industries : bool, optional
        Se True a função também retorna a indústria mais próxima de cada estação, 
        adicionando as colunas 'distance_to_industry', 'industry_geom' e 'Razão Social'.
        Valor padrão é False.

    Returns
    -------
    Geodataframe de input com 3 colunas adicionais para cada faixa de ADT com uma via
    de ADT não nulo: 'osm_id_{}k', 'average_daily_vehicle_count_{}k' and 'distance_{}k'.
    O padrão de get_industries = True também retorna as colunas 'distance_to_industry',
    'industry_geom' e 'Razão Social' para a indústria mais próxima de cada estação.
    """
    # Dicionário de faixas de ADT (value * 1000)
    pollutants_adt_dict = {'co':[1, 10, 20, 30, 40, 50, 60, np.inf],
                           'so2':[1, 10, 20, 30, 40, 50, 60, np.inf],
                           'no2':[1, 10, 15, 20, 40, 70, 110, np.inf],
                           'pm': [1, 15, 20, 30, 40, 50, 60, 70, 80, np.inf],
                           'o3':[10, 15, 20, 40, 70, 110, np.inf]}

    # Dicionário de subsets por poluente
    poll_codes = {
        'co': [7],
        'so2': [3],
        'no2': [4],
        'pm': [1,2,8],
        'o3': [5]
    }

    # Filtrando subsets de estações e adt_list para o poluente
    poll_subset = stations[stations['COD_POLUENTE'].isin(poll_codes[poll])]
    adt_list = pollutants_adt_dict[poll]

    # Criando dicionários de subsets para cada EPSG 
    roads_subsets = {}
    stations_subsets = {}
    industries_subsets = {}
    
    # Criando dicionário de epsg
    choices = {'{}'.format(q): q for q in stations['EPSG'].unique()}

    # Iterando por códigos EPSG
    for epsg in choices.keys():
        
         # Criando sub dataframes de estações e definindo o SRC
         stations_subsets[epsg] = (
             poll_subset[poll_subset['EPSG'] == epsg]
             .to_crs(epsg)
         )
    
         # Criando sub dataframes de vias para cada EPSG
         roads_subsets[epsg] = roads.to_crs(epsg)
    
         # Criando sub dataframe de indústrias para cada EPSG
         industries_subsets[epsg] = industries.to_crs(epsg)
         
         # Iterando sobre valores de ADT
         for idx, adt in enumerate(adt_list[0:-1]):
             filtered_roads = (
                 roads_subsets[epsg]
                 .loc[(roads_subsets[epsg][adt_col] >= adt * 1000) &
                      (roads_subsets[epsg][adt_col] < adt_list[idx + 1] * 1000),
                 ['osm_id', adt_col, 'geometry']]
                 )
             
             if filtered_roads.empty:
                 continue

             # Calculando distâncias da via mais próxima, para cada faixa de ADT
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
     
             # Removendo right index do sjoin
             stations_subsets[epsg].drop(columns='index_{}k'.format(adt),
                                         inplace=True)
             
             rename_cols = {}
             if 'osm_id' in stations_subsets[epsg].columns:
                 rename_cols['osm_id'] = f'osm_id_{adt}k'
             if adt_col in stations_subsets[epsg].columns:
                 rename_cols[adt_col] = f'{adt_col}_{adt}k'
             if rename_cols:
                 stations_subsets[epsg].rename(columns=rename_cols, inplace=True)
             
             # Removendo linhas duplicadas pelo fato de existir diversas vias
             # com a mesma distância da estação
             if f'{adt_col}_{adt}k' in stations_subsets[epsg].columns:
                 stations_subsets[epsg] = (
                     stations_subsets[epsg]
                     .sort_values(by=f'{adt_col}_{adt}k',ascending=False)
                     .drop_duplicates(subset=['ID_OEMA',
                                              f'distance_{adt}k',
                                              'POLUENTE'])
                  )
            
                        
         if get_industries == True:
             # Calculando a distância da estação para a indústria mais próxima
             stations_subsets[epsg] = (
                 gpd.sjoin_nearest(stations_subsets[epsg],
                                   industries_subsets[epsg][['Razão Social',
                                                             'industry_geom',
                                                             'geometry']],
                                   distance_col="distance_to_industry")
                 )
         
         # Removendo duplicatas com todas as colunas duplicadas
         stations_subsets[epsg] = (
             stations_subsets[epsg]
             .drop_duplicates(subset= ['ID_OEMA', 'POLUENTE']))
         
         # Removendo right index do sjoin 
         stations_subsets[epsg].drop(columns='index_right', inplace=True)
         
         # Reprojetando geometria de cada subdataframe para WGC 84 
         stations_subsets[epsg] = stations_subsets[epsg].to_crs(4326)
         
    # Concatenando sub geodataframes
    stations_by_poll = (
        gpd.GeoDataFrame(pd.concat([stations_subsets[df] 
                                    for df 
                                    in stations_subsets])
                         )
        )
    
    return stations_by_poll


# Lendo inputs ----------------------------------------------------
stations = gpd.read_parquet(stations_path)
roads = gpd.read_parquet(roads_path)
industrial_gdf = gpd.read_parquet(industrial_path)

# Definindo nomes de colunas como variáveis
adt_col = 'average_daily_vehicle_count'
vehicle_count_col = 'vehicle_count'

# Aplicando função ---------------------------------------------------
subset_co = get_distance_to_stations(stations=stations,
                                     poll='co',
                                     roads=roads,
                                     industries=industrial_gdf,
                                     get_industries=True)

subset_no2 = get_distance_to_stations(stations=stations,
                                      poll='no2',
                                      roads=roads,
                                      industries=industrial_gdf,
                                      get_industries=True)

subset_o3 = get_distance_to_stations(stations=stations,
                                     poll='o3',
                                     roads=roads,
                                     industries=industrial_gdf,
                                     get_industries=True)

subset_pm = get_distance_to_stations(stations=stations,
                                     poll='pm',
                                     roads=roads,
                                     industries=industrial_gdf,
                                     get_industries=True)

subset_so2 = get_distance_to_stations(stations=stations,
                                      poll='so2',
                                      roads=roads,
                                      industries=industrial_gdf,
                                      get_industries=True)


# ========================== SALVANDO OUTPUTS ========================
subset_co.to_parquet(outputs_path + '/subset_co.parquet')
subset_no2.to_parquet(outputs_path + '/subset_no2.parquet')
subset_o3.to_parquet(outputs_path + '/subset_o3.parquet')
subset_pm.to_parquet(outputs_path + '/subset_pm.parquet')
subset_so2.to_parquet(outputs_path + '/subset_so2.parquet')