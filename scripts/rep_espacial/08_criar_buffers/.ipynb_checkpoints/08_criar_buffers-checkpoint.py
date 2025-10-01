
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
inputs_path = root_path + '/08_criar_buffers/inputs'

# Caminho da pasta de outputs
outputs_path = root_path + '/08_criar_buffers/outputs'

# Caminhos dos subsets
co_path = ('/home/nobre/Notebooks/' + os.readlink(inputs_path + '/subset_co.txt'))
no2_path = ('/home/nobre/Notebooks/' + os.readlink(inputs_path + '/subset_no2.txt'))
o3_path = ('/home/nobre/Notebooks/' + os.readlink(inputs_path + '/subset_o3.txt'))
pm_path = ('/home/nobre/Notebooks/' + os.readlink(inputs_path + '/subset_pm.txt'))
so2_path = ('/home/nobre/Notebooks/' + os.readlink(inputs_path + '/subset_so2.txt'))


# ========================== CARREGANDO SUBSETS =====================================
subset_co = gpd.read_parquet(co_path)
subset_no2 = gpd.read_parquet(no2_path)
subset_o3 = gpd.read_parquet(o3_path)
subset_pm = gpd.read_parquet(pm_path)
subset_so2 = gpd.read_parquet(so2_path)


# ====================== FUNÇÃO DE CRIAÇÃO DE BUFFERS ===============================
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



# =============================== APLICANDO FUNÇÃO ============================
# Dicionário de tamanhos de buffer de acordo com REP_ESPACIAL_NAME
""" Buffers de representatividade:
   microscale: < 100 m
   mesoscale: 100 m < x < 500 m
   escala de bairro: 500 m < x < 4000 m
   escala urbana: 4000 m < x < 50000 m
"""
buffer_sizes = {
    'urbana': 50000,
    'bairro': 4000,
    'meso': 500,
    'micro': 100,
}

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

# ================= SALVANDO OUTPUTS ==============================
buffered_subset_co.to_parquet(outputs_path + '/buffered_subset_co.parquet')
buffered_subset_no2.to_parquet(outputs_path + '/buffered_subset_no2.parquet')
buffered_subset_o3.to_parquet(outputs_path + '/buffered_subset_o3.parquet')
buffered_subset_pm.to_parquet(outputs_path + '/buffered_subset_pm.parquet')
buffered_subset_so2.to_parquet(outputs_path + '/buffered_subset_so2.parquet')
