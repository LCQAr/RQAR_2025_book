
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
inputs_path = root_path + '/09_format_e_salv_outputs/inputs'

# Caminho da pasta de outputs
outputs_path = root_path + '/09_format_e_salv_outputs/outputs'

# Caminhos dos subsets
co_path = '/home/nobre/Notebooks/' + os.readlink(inputs_path + '/buffered_subset_co.txt')
no2_path = '/home/nobre/Notebooks/' + os.readlink(inputs_path + '/buffered_subset_no2.txt')
o3_path = '/home/nobre/Notebooks/' + os.readlink(inputs_path + '/buffered_subset_o3.txt')
pm_path = '/home/nobre/Notebooks/' + os.readlink(inputs_path + '/buffered_subset_pm.txt')
so2_path = '/home/nobre/Notebooks/' + os.readlink(inputs_path + '/buffered_subset_so2.txt')


# ========================== CARREGANDO SUBSETS =====================================
subset_co = gpd.read_parquet(co_path)
subset_no2 = gpd.read_parquet(no2_path)
subset_o3 = gpd.read_parquet(o3_path)
subset_pm = gpd.read_parquet(pm_path)
subset_so2 = gpd.read_parquet(so2_path)

# ========================== FORMATANDO OUTPUTS =====================================
# 1) estacoes_completa --------------------------------------------------------------
# Unindo poluentes em um gdf final completo
buffered_stations = pd.concat([buffered_subset_co,
                               buffered_subset_no2,
                               buffered_subset_o3,
                               buffered_subset_pm,
                               buffered_subset_so2])


# 2) rep_espacial -------------------------------------------------------------------
"""
Planilha original de estações de monitoramento + colunas [REP_ESPACIAL_NAME] e [REP_ESPACIAL]
    - REP_ESPACIAL_NAME: nome da classe de representatividade espacial (micro, meso, 
    bairro, urbana)
    - REP_ESPACIAL: tamanho do raio do buffer de representatividade em metros
"""
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

# =========================== SALVANDO OUTPUTS =========================================
# Salvando o GeoDataFrame com a indústria mais próxima de cada estação
buffered_stations.to_parquet(outputs_path + '/estacoes_completa.parquet')

# Salvando o GeoDataFrame de input com as estações, sua classificação de 
# representatividade espacial e o tamanho do buffer
filtered_stations.to_csv(outputs_path + '/rep_espacial.csv')

