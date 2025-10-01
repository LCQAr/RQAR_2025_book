"""
Este arquivo produz as variáveis:
    - roads  --> gdf de vias com geometria e valores de ADT
    - industrial_gdf  --> gdf de industrias
    - stations --> gdf de estações de monitoramento com geometria e poluentes
"""
# ========== IMPORTANDO PACOTES ==============================
# Pacotes e funções
import geopandas as gpd
from pathlib import Path
from long_2_utm_zone import long_2_utm_zone
from utm_zone_2_epsg import utm_zone_2_epsg
import pandas as pd
import numpy as np
import os

# Desativando notação científica
pd.set_option('display.float_format', '{:.2f}'.format)


# ========== DEFININDO CAMINHOS ================================
# Caminho da pasta mãe
root_path = os.path.dirname(os.getcwd())

# Caminho da pasta de inputs
inputs_path = root_path + '/01_preprocessamento/inputs'

# Caminho da pasta de outputs
outputs_path = root_path + '/01_preprocessamento/outputs'

# Arquivo de todas as vias do BR
roads_path = inputs_path + '/processed_roads_dissolved.parquet'

# Arquivo de códigos de vias e os respecitvos fluxo médios diários em um
# buffer de 250 metros das estações
flow_path = inputs_path + '/stations_may_jun_2025.parquet'

# Arquivo de indústrias BR (Gerais, mineração e aterros)
industrial_path = inputs_path + '/industrial_sites_20250902.gpkg'

# Planilha de estações de monitoramento do BR
stations_path = (
    os.path.dirname(os.path.dirname(os.path.dirname(os.getcwd()))) + 
    '/data/Monitoramento_QAr_BR.csv')


# ================ GEODATAFRAME DE VIAS DO BRASIL ==================================
"""Lendo geodataframe de vias, com as colunas obrigatórias:
    'osm_id': int de código de identificação de vias do OpenStreetMaps
    'geometry': LineString de geometria da via
"""
roads = (gpd
         .read_parquet(path=roads_path)
         .reset_index(drop=False)
         .astype({'osm_id': int}))

#-------------------------------------
# Lendo parquet com ADT das vias filtradas para 250 m de cada estação
roads_with_adt = pd.read_parquet(flow_path)

# ------------------------------------
# Definindo nomes de colunas como variáveis
adt_col = 'average_daily_vehicle_count'
vehicle_count_col = 'vehicle_count'

# ------------------------------------
# Cálculo do ADT para cada código de via
roads_with_adt = roads_with_adt.groupby(['osm_id','weekday'])['vehicle_count'].sum()
roads_with_adt = roads_with_adt.groupby('osm_id').mean().reset_index()

# Renomeando coluna vehicle count para ADT
roads_with_adt = roads_with_adt.rename({vehicle_count_col : adt_col}, axis=1)

# ------------------------------------
# Selecionando vias com ADT calculado
roads = pd.merge(roads, roads_with_adt, how='inner', on='osm_id')

# ------------------------------------
"""Definiu-se 1000 veículos/dia como o fluxo diário médio (ADT) mínimo para uma 
via ser considerada como via principal, termo utilizado no Guia de Monitoramento
da Qualidade do Ar do Brasil."""
# Pegando vias com ADT superior a 1000 veículos/dia
roads = roads.loc[roads[adt_col] > 1000, :]


# ========================== INDÚSTRIAS ===============================
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


# ============ ESTAÇÕES DE MONITORAMENTO DA QUALIDADE DO AR =============
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


# # ==================== SALVANDO OUTPUTS ====================
# # Vias com valores de ADT
# roads.to_parquet(outputs_path + '/roads.parquet')

# # Indústrias
# industrial_gdf.to_parquet(outputs_path + '/industrial_gdf.parquet')

# # Estações 
# stations.to_parquet(outputs_path + '/stations.parquet')


