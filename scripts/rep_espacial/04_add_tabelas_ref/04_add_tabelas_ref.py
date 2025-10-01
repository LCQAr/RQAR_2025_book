


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
inputs_path = root_path + '/04_add_tabelas_ref/inputs'

# Caminho da pasta de outputs
outputs_path = root_path + '/04_add_tabelas_ref/outputs'

# Caminhos dos subsets
subset_co_path = '/home/nobre/Notebooks/' + os.readlink(inputs_path + '/subset_co.txt')
subset_no2_path = '/home/nobre/Notebooks/' + os.readlink(inputs_path + '/subset_no2.txt')
subset_o3_path = '/home/nobre/Notebooks/' + os.readlink(inputs_path + '/subset_o3.txt')
subset_pm_path = '/home/nobre/Notebooks/' + os.readlink(inputs_path + '/subset_pm.txt')
subset_so2_path = '/home/nobre/Notebooks/' + os.readlink(inputs_path + '/subset_so2.txt')

# Caminhos das tabelas de referencia interpoladas
interpolated_co_path = '/home/nobre/Notebooks/' + os.readlink(inputs_path +
                                                              '/interpolated_co.txt')
interpolated_no2_path = '/home/nobre/Notebooks/' + os.readlink(inputs_path + 
                                                               '/interpolated_no2.txt')
interpolated_o3_path = '/home/nobre/Notebooks/' + os.readlink(inputs_path + 
                                                              '/interpolated_o3.txt')
interpolated_pm_path = '/home/nobre/Notebooks/' + os.readlink(inputs_path + 
                                                              '/interpolated_pm.txt')
interpolated_so2_path = '/home/nobre/Notebooks/' + os.readlink(inputs_path +
                                                               '/interpolated_so2.txt')


# ======================= CARREGANDO SUBSETS ====================================
subset_co = gpd.read_parquet(subset_co_path)
subset_no2 = gpd.read_parquet(subset_no2_path)
subset_o3 = gpd.read_parquet(subset_o3_path)
subset_pm = gpd.read_parquet(subset_pm_path)
subset_so2 = gpd.read_parquet(subset_so2_path)

interpolated_co = pd.read_parquet(interpolated_co_path)
interpolated_no2 = pd.read_parquet(interpolated_no2_path)
interpolated_o3 = pd.read_parquet(interpolated_o3_path)
interpolated_pm = pd.read_parquet(interpolated_pm_path)
interpolated_so2 = pd.read_parquet(interpolated_so2_path)

# ======================== ADICIONANDO LIMITES DE DISTANCIAS PARA CADA VIA ===================
# Iterando sobre os poluentes e seus subconjuntos
def add_limites_nas_vias(subset:gpd.GeoDataFrame,
                         interpolated: pd.DataFrame,
                         poluente:str):
    
    # Dicionário de faixas de ADT (real = valor * 1000)
    pollutants_adt_dict = {'co':[1, 10, 20, 30, 40, 50, 60, np.inf],
                           'so2':[1, 10, 20, 30, 40, 50, 60, np.inf],
                           'no2':[1, 10, 15, 20, 40, 70, 110, np.inf],
                           'pm': [1, 15, 20, 30, 40, 50, 60, 70, 80, np.inf],
                           'o3':[10, 15, 20, 40, 70, 110, np.inf]}
    
    # Iterando sobre os valores de ADT da ref_table para cada poluente
    for idx, adt_band in enumerate(pollutants_adt_dict[poluente][:-1]):
        col_name = f'average_daily_vehicle_count_{adt_band}k'
        
        # Registrando valores de ADT sem vias para cada poluente
        if col_name not in subset.columns:
            print(f"[AVISO] '{col_name}' não existe no subset_{poluente}")
            continue

        # Obtendo a tabela do lado direito (para o merge)
        interp_df = interpolated.copy()
        
        # Renomeando a primeira coluna, para que a função merge não adicione sufixo
        suffix = f"_{adt_band}k"
        interp_df = interp_df.rename(columns={
            col: f"{col}{suffix}" 
            for col
            in interp_df.columns
            if col != 'avg_adt'
        })
        
        # Mesclando colunas com limites de distância para cada ADT e classe representativa
        subset = subset.merge(
            right= interp_df,
            how='left',
            left_on= col_name,
            right_on='avg_adt',
            suffixes=(None, f"_{adt_band}k")
            )
        
        # Removendo colunas 'avg_adt_{}k' adicionadas anteriormente
        if (idx != 0) and (f'avg_adt_{adt_band}k' in subset.columns):
            subset.drop(columns=[f'avg_adt_{adt_band}k'],
                        inplace=True)
    
    # Remove a primeira coluna 'avg_adt' adicionada
    subset.drop(columns=['avg_adt'], inplace=True)
        
    # Preenchendo valores nulos com np.inf (somente colunas 
    # {micro/meso/bairro/urb}_max podem ter nulos)
    cols = list(subset.filter(like='k').columns)
    subset.loc[:,cols] = (
        subset
        .loc[:,cols]
        .astype(float)
        .fillna(np.inf)
    )

    return subset


# ================== APLICANDO A FUNÇÃO =====================================
subset_co = add_limites_nas_vias(subset_co,
                                 interpolated_co,
                                 "co")
subset_no2 = add_limites_nas_vias(subset_no2,
                                 interpolated_no2,
                                 "no2")
subset_o3 = add_limites_nas_vias(subset_o3,
                                 interpolated_o3,
                                 "o3")
subset_pm = add_limites_nas_vias(subset_pm,
                                 interpolated_pm,
                                 "pm")
subset_so2 = add_limites_nas_vias(subset_so2,
                                 interpolated_so2,
                                 "so2")

# ====================== SALVANDO OUTPUTS ====================================
subset_co.to_parquet(outputs_path + '/subset_co.parquet')
subset_no2.to_parquet(outputs_path + '/subset_no2.parquet')
subset_o3.to_parquet(outputs_path + '/subset_o3.parquet')
subset_pm.to_parquet(outputs_path + '/subset_pm.parquet')
subset_so2.to_parquet(outputs_path + '/subset_so2.parquet')




