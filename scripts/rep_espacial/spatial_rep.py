#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug 19 13:48:15 2025

@author: brunojalowski
"""
# %% ============================== PACOTES ===================================
import geopandas as gpd
from pathlib import Path
from long_2_utm_zone import long_2_utm_zone
from utm_zone_2_epsg import utm_zone_2_epsg
import pandas as pd
import numpy as np
import os

# Deactivates scientific notation
pd.set_option('display.float_format', '{:.2f}'.format)

# =========================== CAMINHOS ========================================
root_path = os.path.dirname(os.getcwd())

inputs_path = root_path + '/data/rep_espacial/inputs'

outputs_path = root_path + '/data/rep_espacial/outputs'

flow_path = inputs_path + '/processed_roads.parquet'

industrial_path = inputs_path + '/industrial_sites_20250902.gpkg'

stations_path = root_path + '/data/Monitoramento_QAr_BR.csv' # constantemente atualizado

# ========================== GEODATAFRAMES DE VIAS DO BRASIL =============================
"""Lendo geodataframe de vias, com as colunas obrigatórias:
    'osm_id': int de código de identificação de vias do OpenStreetMaps
    'surface': string com informação do tipo da superfície da via
    'average_daily_vehicle_count': float com informação do ADT de cada via
    'geometry': LineString de geometria da via
"""
# Lendo geodataframe
gdf = (gpd
       .read_parquet(path=flow_path))

gdf = gdf.astype({'osm_id': int}) 
######'average_daily_vehicle_count': float,

# Removendo a coluna de datetime do índice
gdf.reset_index(drop=False,
                inplace=True)





## FIXME - Criando coluna temporária de average_daily_vehicle_count (ADT)
############################################################################################
# TEST SECTION
# COLUNA TEMPORÁRIA DE ADT !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
values = [5000, 11000, 16000, 21000, 36000, 43000, 55000, 63000,
          75000, 84000, 93000,101000, 130000]

gdf['average_daily_vehicle_count'] = (
    np.tile(values,
            int(np.ceil(len(gdf) / len(values)))
           )[:len(gdf)]
)
############################################################################################







# %% ====================== CRIANDO MODELO DE VIAS ====================================
"""O input para as vias é uma série temporal, logo esta seção remove as duplicatas
temporais de cada via, mantendo apenas uma geometria para cada osm_id"""
# Pegando apenas um instante de tempo (Removendo duplicatas temporais)
roads = (
    gdf
    .drop_duplicates(subset='osm_id')
    .reset_index(drop=True)
)

"""Definiu-se 1000 veículos/dia como o fluxo diário médio (ADT) mínimo para uma 
via ser considerada como via principal, termo utilizado no Guia de Monitoramento
da Qualidade do Ar do Brasil."""
# Pegando vias com ADT superior a 1000 veículos/dia
roads = roads[roads['average_daily_vehicle_count'] > 1000]


# =========================== ZONAS INDUSTRIAIS =============================
""" Esta seção lê o arquivo de indústrias, com as colunas obrigatórias:
        'Razão Social': str.
            Nome comercial do empreendimento
        'geometry': Point ou Polygon.
            Geometrias representando indústrias, áreas de mineração e aterros sanitários
"""
# Lendo arquivo de indústrias
industrial_gdf = gpd.read_file(industrial_path)

# Duplicando a coluna de geometria para transmitir ela após o sjoin_nearest na seção 6.2
industrial_gdf['industry_geom'] = industrial_gdf.geometry


# ================== ESTAÇÕES DE MONITORAMENTO DA QUALIDADE DO AR =========================
"""
Esta seção faz a leitura do arquivo de estações de monitoramento da qualidade do ar 
do Brasil, com as colunas obrigatórias:
- 'LONGITUDE': float.
- 'LATITUDE': float.
- 'COD_POLUENTE': float
- 'POLUENTE': str.
- 'ID_OEMA': str.

Em seguida, cada estação é enquadrada dentro de uma zona UTM e atribui-se o código EPSG correspondente, de acordo com a zona UTM e a latitude de cada uma.

Por fim, dentre todas as linhas de estações, o geodataframe é reduzido às que monitoram os poluentes a seguir:
- monóxido de carbono (CO)
- dióxido de enxofre (SO2)
- dióxido de nitrogênio (NO2)
- ozônio (O3)
- material particulado de diâmetro inferior a 10 micrômetros (MP10)
- material particulado de diâmetro inferior a 2.5 micrômetros (MP2.5)
- material particulado total (PTS)"""


# Lendo o arquivo de estações de monitoramento
stations = pd.read_csv(filepath_or_buffer=stations_path,
                      dtype={'LONGITUDE': float,
                             'LATITUDE':float,
                             'COD_POLUENTE':float,
                             'POLUENTE':str,
                             'ID_OEMA':str
                            }
                      )

# Transformando em GeoDataFrame
stations = gpd.GeoDataFrame(stations,
                            geometry=gpd.points_from_xy(stations.LONGITUDE,
                                                        stations.LATITUDE,
                                                        crs='EPSG:4326'))
# Determinando a zona UTM para cada estação
stations.loc[:,'utm_zone'] = long_2_utm_zone(stations
                                             .geometry
                                             .centroid
                                             .x)

# Determinando do código EPSG para cada estação
stations.loc[:,'EPSG'] = utm_zone_2_epsg(stations['utm_zone'],
                                         stations.geometry
                                         .centroid
                                         .x)

# Removendo a coluna auxiliar de zona UTM
stations.drop(columns='utm_zone', inplace=True)

# Filtrando as estações que monitoram CO, SO2, O3, NO2, PM10, PM2.5 e PTS
stations = stations[stations['COD_POLUENTE'].isin([1.0, 2.0, 3.0, 4.0,
                                                   5.0, 7.0, 8.0])]


# ========= DISTÂNCIA DA VIA MAIS PRÓXIMA A CADA ESTAÇÃO ============================
""" 
"""
# Criando dicionários de subsets para cada EPSG 
roads_subsets = {}
stations_subsets = {}
industries_subsets = {}

# Duplicando coluna de geometria das ruas para preservá-la no sjoin
roads['road_geom'] = roads.geometry

# Criando dicionário de epsg
choices = {'{}'.format(q): q for q in stations['EPSG'].unique()}

## Calculando distâncias -----------------------------------------------------------
# Iterando por códigos EPSG
for epsg in choices.keys():
    
     # Criando sub dataframes de estações e definindo o SRC
     stations_subsets[epsg] = (
         stations[stations['EPSG'] == epsg]
         .to_crs(epsg)
     )

     # Criando sub dataframes de vias para cada EPSG
     roads_subsets[epsg] = roads[['osm_id','road_geom','geometry']].to_crs(epsg)

     # Calculando distâncias da via mais próxima, para cada faixa de ADT
     stations_subsets[epsg] = (
        gpd.sjoin_nearest(stations_subsets[epsg],
                          roads_subsets[epsg],
                          how='left',
                          distance_col='distance_m')
     )

     # Reprojetando geometria de cada subdataframe para WGC 84 
     stations_subsets[epsg] = stations_subsets[epsg].to_crs(4326)

## Concatenando subconjuntos de estações ----------------------------------------------
distances = (
    gpd.GeoDataFrame(pd.concat([stations_subsets[df] 
                                for df 
                                in stations_subsets])
                         )
        )

# Removendo linhas duplicadas de uma mesma estação
distances.drop_duplicates(subset='ID_OEMA', inplace=True)

## Salvando para csv de distâncias de ruas a estações -----------------------------------
distances.to_parquet(outputs_path+'/distances_to_roads.parquet')


# ========= DISTÂNCIA DE VIAS DE VÁRIOS ADTs E INDÚSTRIAS ÀS ESTAÇÕES ===================
"""
Esta seção faz a junção espacial entre estações e as vias mais próximas para a cada, dentro de cada faixa de ADT, segundo as faixas disponíveis para cada poluente. Então, 3 colunas são criadas para cada faixa de ADT com vias de ADT > 0: 
- 'osm_id_{}k': int.
    - Código de indentificação de vias do OPenStreetMaps
- 'average_daily_vehicle_count_{}k': float.
    - Fluxo médio diário de veículos para a via mais próxima dentro de cada faixa de ADT
- 'distance_{}k': float.
    - Distância de cada estação para cada via, em metros
"""

# Função
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
             adt_col = 'average_daily_vehicle_count'
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


# Aplicando função ----------------------------------------------------
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


# ============ CLASSIFICAÇÃO DE REPRESENTATIVIDADE ESPACIAL DAS ESTAÇÕES ====================
"""
Para a classificação, existem diferentes tabelas de referência para cada poluente, mostrando as distâncias mínimas e máximas que a estação deve estar das vias principais mais próximas, de acordo com os fluxos médios diários das vias (ADT). Essas tabelas impõem distâncias para os valores de ADT de 15k, 20k, 40, etc, e todos os valores intermediários devem ser interpolados.

Esta seção visa à organização das tabelas de referência, à adição de linhas de valores de ADT intermediários e à interpolação das distâncias mínimas e máximas para cada um deles. Depois disso, os limites de distância para cada fluxo serão adicionados a cada dataframe de poluente e as distâncias de cada via para cada estação serão classificadas como True se se encontrarem dentro desses limites. Isso cria colunas de True/False para cada classe de representatividade espacial existente na tabela de referência de cada poluente (micro, meso, bairro, urbana).

Como passo final, cada linha (via) será enquadrada dentro de uma das 4 classes de representatividade espacial, seguindo a ordem de prioridade micro > meso > bairro > urbana, logo a classe escolhida será sempre a classe mais restritiva. Por exemplo, se a via tem valores True tanto para micro, bairro e urbana, ela será classificada como micro.

"""

## Montando tabelas de referência ---------------------------------------------------

# Lendo os arquivos para cada tabela
# https://www.gov.br/mma/pt-br/assuntos/meio-ambiente-urbano-recursos-hidricos-qualidade-ambiental/qualidade-do-ar/guia-tecnico-para-o-monitoramento-e-avaliacao-da-qualidade-do-ar.pdf

ref_table_co = pd.read_csv(inputs_path + '/ref_table_so2eco.csv')
ref_table_no2 = pd.read_csv(inputs_path + '/ref_table_no2.csv')
ref_table_o3 = pd.read_csv(inputs_path + '/ref_table_o3.csv')
ref_table_pm = pd.read_csv(inputs_path + '/ref_table_pm.csv')
ref_table_so2 = pd.read_csv(inputs_path + '/ref_table_so2eco.csv')

# Nota da EPA acerca da ocorrência de valores intermediários de ADT
'''
Distância da borda da via mais próxima. A distância para contagens de veículos (ADT)
intermediárias deve ser interpolada a partir dos valores das tabelas baseados na
contagem de veículos observada.

# https://www.ecfr.gov/current/title-40/chapter-I/subchapter-C/part-58/appendix-Appendix%20E%20to%20Part%2058
'''

# Dicionário de faixas de ADT (real = valor * 1000)
pollutants_adt_dict = {'co':[1, 10, 20, 30, 40, 50, 60, np.inf],
                       'so2':[1, 10, 20, 30, 40, 50, 60, np.inf],
                       'no2':[1, 10, 15, 20, 40, 70, 110, np.inf],
                       'pm': [1, 15, 20, 30, 40, 50, 60, 70, 80, np.inf],
                       'o3':[10, 15, 20, 40, 70, 110, np.inf]}

# Definindo coluna de adt como índice
interpolated_co = ref_table_co.set_index('avg_adt').squeeze()
interpolated_no2 = ref_table_no2.set_index('avg_adt').squeeze()
interpolated_o3 = ref_table_o3.set_index('avg_adt').squeeze()
interpolated_pm = ref_table_pm.set_index('avg_adt').squeeze()
interpolated_so2 = ref_table_so2.set_index('avg_adt').squeeze()


## Interpolando os limites das classes de representatividade --------------------------------
# Montando dicionário de dataframes para interpolação
interpolated_dict = {
    'co': interpolated_co,
    'so2': interpolated_so2,
    'no2': interpolated_no2,
    'pm': interpolated_pm,
    'o3': interpolated_o3
}

# Redefinindo dicionário de subsets de poluentes
pollutant_subsets = {
    'co': subset_co,
    'so2': subset_so2,
    'no2': subset_no2,
    'pm': subset_pm,
    'o3': subset_o3
}

# Interpolação
# Iterando sobre os poluentes e os subsets de poluentes
for poll, subset in pollutant_subsets.items():
    
    # Iterando sobre os valores de adt da tabela de referencia de cada poluente
    for idx, adt_band in enumerate(pollutants_adt_dict[poll][:-1]):
        col_name = f'average_daily_vehicle_count_{adt_band}k'
        
        if col_name not in subset.columns:
            print(f"[WARNING] '{col_name}' nonexistant in subset_{poll}")
            continue
        
        # Iterando sobre os valores de adt para cada via do subset do poluente
        for adt_value in subset[col_name]:
            interpolated_dict[poll].loc[adt_value] = np.nan
                
    # Organizar pelo índice de modo ascendente
    interpolated_dict[poll].sort_index(inplace=True)
                
    # Interpolando os valores NaN #FIXME
    interpolated_dict[poll].interpolate(method='index',
                                        inplace=True)
                
    # Resetando index
    interpolated_dict[poll].reset_index(inplace=True)


## Adicionando ao gdf de vias os limites das tabelas interpoladas ----------------------------
# Iterando sobre os poluentes e seus subconjuntos
for poll, subset in pollutant_subsets.items():
    
    # Iterando sobre os valores de ADT da ref_table para cada poluente
    for idx, adt_band in enumerate(pollutants_adt_dict[poll][:-1]):
        col_name = f'average_daily_vehicle_count_{adt_band}k'
        
        # Registrando valores de ADT sem vias para cada poluente
        if col_name not in subset.columns:
            print(f"[AVISO] '{col_name}' não existe no subset_{poll}")
            continue
        
        # Obtendo a tabela do lado direito (para o merge)
        interp_df = interpolated_dict[poll].copy()
        
        # Renomeando a primeira coluna, para que a função merge não adicione sufixo
        suffix = f"_{adt_band}k"
        interp_df = interp_df.rename(columns={
            col: f"{col}{suffix}" 
            for col
            in interp_df.columns
            if col != 'avg_adt'
        })
        
        # Mesclando colunas com limites de distância para cada ADT e classe representativa
        pollutant_subsets[poll] = pollutant_subsets[poll].merge(
            right= interp_df,
            how='left',
            left_on= col_name,
            right_on='avg_adt',
            suffixes=(None, f"_{adt_band}k")
            )
        
        # Removendo colunas 'avg_adt_{}k' adicionadas anteriormente
        if (idx != 0) and (f'avg_adt_{adt_band}k' 
                           in pollutant_subsets[poll].columns):
            pollutant_subsets[poll].drop(columns=[f'avg_adt_{adt_band}k'],
                                         inplace=True)
    
    # Remove a primeira coluna 'avg_adt' adicionada
    pollutant_subsets[poll].drop(columns=['avg_adt'], inplace=True)
        
    # Preenchendo valores nulos com np.inf (somente colunas 
    # {micro/meso/bairro/urb}_max podem ter nulos)
    cols = list(pollutant_subsets[poll].filter(like='k').columns)
    pollutant_subsets[poll].loc[:,cols] = (
        pollutant_subsets[poll]
        .loc[:,cols]
        .astype(float)
        .fillna(np.inf)
    )
        
del suffix


## Verificando se as vias de cada faixa de ADT estão dentro dos limites de cada classe ----------
"""Cria uma coluna para cada valor de ADT e poluente, verificando se a via está dentro 
dos limites dessa classe"""
# Iterando sobre os poluentes e seus subconjuntos
for poll, subset in pollutant_subsets.items():
    
    if poll != 'pm':
        
        # Iterando sobre os valores de ADT da ref_table para cada poluente
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
        
            # URBANO
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
            # Exclui banda 1k do cálculo meso para PM
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
        
            # URBANO
            col_urb_min = f'urb_min_{adt_band}k'
            col_urb_max = f'urb_max_{adt_band}k'
            # Exclui banda 80k do cálculo urbano para PM
            if col_urb_min in cols and col_urb_max in cols and adt_band != 80:
                pollutant_subsets[poll][f'rep_urb_{adt_band}k'] = np.where(
                    (subset[distance] > subset[col_urb_min]) &
                    (subset[distance] < subset[col_urb_max]),
                    True,
                    False)

# Removendo de variáveis temporárias
del col_bairro_max, col_bairro_min, col_meso_max, col_meso_min, col_micro_max
del col_micro_min, col_urb_max, col_urb_min, distance, cols


## Verificando se cada estação possui ao menos uma via de ao menos uma faixa de ADT que se 
## encontre dentro dos limites de cada classe de representatividade -----------------------------

# Atribuindo GeoDataFrames do dicionário para variáveis individuais
subset_co = pollutant_subsets['co']
subset_no2 = pollutant_subsets['no2']
subset_o3 = pollutant_subsets['o3']
subset_pm = pollutant_subsets['pm']
subset_so2 = pollutant_subsets['so2']

# Função auxiliar para verificar se existem colunas de cada escala
def safe_any(df, like_str):
    """
    Filtra todas as colunas de um dataframe com uma substring comum no nome
    e verifica se há pelo menos um valor True em cada linha, retornando uma série de True.
    Caso contrário ou se estiver vazio, retorna uma série de False.
    
    Essa função é necessária porque, se não houver colunas no dataframe filtrado,
    a função .all retorna uma série de True, o que é enganoso.
    
    Parâmetros
    ----------
    df : dataframe 
        DataFrame com várias colunas contendo um elemento repetido no nome.
    like_str: str
        Substring comum nos nomes das colunas do DataFrame.

    Retorna
    -------
    filtered : série de booleans
        Série booleana com o mesmo tamanho que o DataFrame original.
    """
    # Filtra todas as colunas que contêm a string específica no nome
    filtered = df.filter(like=like_str)
    
    # Se não houver colunas correspondentes, retorna uma série de False
    if filtered.shape[1] == 0:
        return pd.Series([False] * len(df), index=df.index)
        
    return filtered.any(axis='columns')


# Aplicando a função para verificar a validade de cada rep_{classe} --------------

# CO ---------------------------------
subset_co['rep_micro_any'] = safe_any(subset_co, 'rep_micro')
subset_co['rep_bairro_any'] = safe_any(subset_co, 'rep_bairro')

# NO2 -------------------------------
subset_no2['rep_bairro_any'] = safe_any(subset_no2, 'rep_bairro')
subset_no2['rep_urb_all_any'] = safe_any(subset_no2, 'rep_urb')

# O3 --------------------------------
subset_o3['rep_bairro_any'] = safe_any(subset_o3, 'rep_bairro')
subset_o3['rep_urb_any'] = safe_any(subset_o3, 'rep_urb')

# PM -------------------------------
subset_pm['rep_meso_any'] = safe_any(subset_pm, 'rep_meso')
subset_pm['rep_bairro_any'] = safe_any(subset_pm, 'rep_bairro')
subset_pm['rep_urb_any'] = safe_any(subset_pm, 'rep_urb')

# SO2 -------------------------------------------
subset_so2['rep_micro_any'] = safe_any(subset_so2, 'rep_micro')
subset_so2['rep_bairro_any'] = safe_any(subset_so2, 'rep_bairro')


#============== CLASSIFICANDO O STATUS DE REPRESENTATIVIDADE DE CADA ESTAÇÃO ===================
def classify_spatial_rep(subset):
    """
    Verifica valores True nas colunas referentes a cada escala espacial
    e atribui a cada estação a escala mais restritiva, seguindo a ordem abaixo:    
                      1º  >   2º   >    3º    >   4º
                    MICRO > MESO > BAIRRO > URBANA
    
    A lógica é que, se houver pelo menos uma via que determine que a estação é 
    representativa espacialmente para uma classe mais restritiva, então ela
    é considerada representativa nessa escala.

    Parâmetros
    ----------
    subset : geodataframe 
        Subconjunto das estações de monitoramento, referente a um único poluente

    Retorna
    -------
    subset : geodataframe
        Subconjunto de entrada com uma nova coluna chamada 'REP_ESPACIAL_NAME'
    """
    conditions = []
    choices = []
    
    if 'rep_micro_any' in subset.columns:
        conditions.append(subset['rep_micro_any'] == True)
        choices.append('micro')
        
    if 'rep_meso_any' in subset.columns:
        conditions.append(subset['rep_meso_any'] == True)
        choices.append('meso')
    
    if 'rep_bairro_any' in subset.columns:
        conditions.append(subset['rep_bairro_any'] == True)
        choices.append('bairro')
        
    if 'rep_urb_any' in subset.columns:
        conditions.append(subset['rep_urb_any'] == True)
        choices.append('urbana')

    # Atribui o nome da escala mais restritiva encontrada, ou 'não representativo' caso
    # nenhuma se aplique
    subset['REP_ESPACIAL_NAME'] = np.select(
        conditions,
        choices,
        default='não representativo'
    )
    
    return subset

# Aplicando a classificação de representatividade espacial para cada poluente
subset_co = classify_spatial_rep(subset_co)
subset_no2 = classify_spatial_rep(subset_no2)
subset_o3 = classify_spatial_rep(subset_o3)
subset_pm = classify_spatial_rep(subset_pm)
subset_so2 = classify_spatial_rep(subset_so2)


# =================== CRIANDO BUFFER DE REPRESENTATIVIDADE ESPACIAL ======================
"""microscale: < 100 m
   mesoscale: 100 m < x < 500 m
   escala de bairro: 500 m < x < 4000 m
   escala urbana: 4000 m < x < 50000 m
""" 

def create_buffered_gdf(subset,
                        buffer_sizes,
                        target_crs="EPSG:4326",
                        create_buffer=True):
    """
    Cria colunas com tamanhos de buffer para um GeoDataFrame, agrupando por códigos EPSG,
    com a opção de criar geometrias de buffer.

    Parâmetros:
        subset (GeoDataFrame): GeoDataFrame de entrada com as colunas 'EPSG', 
        'REP_ESPACIAL_NAME' e 'geometry'.
        
        buffer_sizes (dict): Dicionário que mapeia os valores de `REP_ESPACIAL_NAME`
        para tamanhos de buffer (em metros).
        
        target_crs (str): CRS (sistema de referência espacial) para reprojetar o 
        GeoDataFrame final. Padrão é 'EPSG:4326'.
        
        create_buffer (bool): Verifica se as geometrias de buffer devem ser criadas. 
        Padrão é True.

    Retorna:
        GeoDataFrame: O GeoDataFrame de entrada com colunas adicionais:
            "REP_ESPACIAL": int.
                Tamanho do buffer de representatividade espacial
            "REP_ESPACIAL_NAME": str.
                Nome da classe de representatividade espacial 
            "REP_ESPACIAL_BUFFER": polígono. 
                Geometrias de buffer ao redor das estações no CRS de destino.
    """
    
    buffered_gdfs = []

    for epsg in subset['EPSG'].unique():
        # Filtra o subset e projeta para o respectivo EPSG
        gdf_epsg = subset[subset['EPSG'] == epsg].to_crs(epsg)

        # Remove a coluna REP_ESPACIAL existente
        gdf_epsg = gdf_epsg.drop(columns=['REP_ESPACIAL'])
        
        # Mapeia os tamanhos dos buffers com base no nome da representatividade
        gdf_epsg['REP_ESPACIAL'] = (
            gdf_epsg['REP_ESPACIAL_NAME']
            .map(buffer_sizes)
            .fillna(0)
        )
        
        # Cria as geometrias de buffer se create_buffer for True
        if create_buffer == True:
            gdf_epsg['REP_ESPACIAL_BUFFER'] = (
                gdf_epsg
                .geometry
                .buffer(gdf_epsg['REP_ESPACIAL'])
                .to_crs(target_crs)
            )

        # Reprojeta para o CRS de destino
        gdf_epsg = gdf_epsg.to_crs(target_crs)

        # Adiciona à lista
        buffered_gdfs.append(gdf_epsg)

    # Combina todos os GeoDataFrames com buffer
    buffered_subset = gpd.GeoDataFrame(
        pd.concat(buffered_gdfs, ignore_index=True),
        crs=target_crs
    )

    return buffered_subset


# Dicionário de tamanhos de buffer de acordo com REP_ESPACIAL_NAME
buffer_sizes = {
    'urbana': 50000,
    'bairro': 4000,
    'meso': 500,
    'micro': 100,
}

# Aplicando a função
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


# =============================== FORMATAÇÃO DOS OUTPUTS =============================
# 1) estacoes_completa
# Unindo poluentes em um gdf final completo
buffered_stations = pd.concat([buffered_subset_co,
                               buffered_subset_no2,
                               buffered_subset_o3,
                               buffered_subset_pm,
                               buffered_subset_so2])


# 2) rep_espacial
# Removendo colunas auxiliares
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
# Aplicando função
filtered_stations = drop_aux_cols(buffered_stations) 

# ======================== SALVANDO OUTPUTS =========================================
# Salvando o GeoDataFrame com a indústria mais próxima de cada estação
buffered_stations.to_parquet(outputs_path + '/estacoes_completa.parquet')


# Salvando o GeoDataFrame de input com as estações, sua classificação de 
# representatividade espacial e o tamanho do buffer
"""Todas as colunas da planilha de estações + ['REP_ESPACIAL','REP_ESPACIAL_NAME']"""
filtered_stations.to_parquet(outputs_path + '/rep_espacial.parquet')


