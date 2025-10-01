

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
inputs_path = root_path + '/05_verif_vias_e_limites/inputs'

# Caminho da pasta de outputs
outputs_path = root_path + '/05_verif_vias_e_limites/outputs'

# Caminhos dos subsets
co_path = '/home/nobre/Notebooks/' + os.readlink(inputs_path + '/subset_co.txt')
no2_path = '/home/nobre/Notebooks/' + os.readlink(inputs_path + '/subset_no2.txt')
o3_path = '/home/nobre/Notebooks/' + os.readlink(inputs_path + '/subset_o3.txt')
pm_path = '/home/nobre/Notebooks/' + os.readlink(inputs_path + '/subset_pm.txt')
so2_path = '/home/nobre/Notebooks/' + os.readlink(inputs_path + '/subset_so2.txt')

# ========================== CARREGANDO SUBSETS =====================================
subset_co = gpd.read_parquet(co_path)
subset_no2 = gpd.read_parquet(no2_path)
subset_o3 = gpd.read_parquet(o3_path)
subset_pm = gpd.read_parquet(pm_path)
subset_so2 = gpd.read_parquet(so2_path)


# ========================= FUNÇÃO DE VERIFICAÇÃO ===================================

def verif_vias_dentro_dos_limites(subset:gpd.GeoDataFrame,
                                  poluente:str):
    """
    
    """

    # Dicionário de faixas de ADT (value * 1000)
    pollutants_adt_dict = {'co':[1, 10, 20, 30, 40, 50, 60, np.inf],
                           'so2':[1, 10, 20, 30, 40, 50, 60, np.inf],
                           'no2':[1, 10, 15, 20, 40, 70, 110, np.inf],
                           'pm': [1, 15, 20, 30, 40, 50, 60, 70, 80, np.inf],
                           'o3':[10, 15, 20, 40, 70, 110, np.inf]}
    
    if poluente != 'pm':
        
        # Iterando sobre os valores de ADT da ref_table para cada poluente
        for idx, adt_band in enumerate(pollutants_adt_dict[poluente][:-1]):
            distance = f'distance_{adt_band}k'
            cols = subset.columns
        
            # MICRO
            col_micro_min = f'micro_min_{adt_band}k'
            col_micro_max = f'micro_max_{adt_band}k'
            if col_micro_min in cols and col_micro_max in cols:
                subset[f'rep_micro_{adt_band}k'] = np.where(
                    (subset[distance] > subset[col_micro_min]) &
                    (subset[distance] < subset[col_micro_max]),
                    True,
                    False)
        
            # MESO
            col_meso_min = f'meso_min_{adt_band}k'
            col_meso_max = f'meso_max_{adt_band}k'
            if col_meso_min in cols and col_meso_max in cols:
                subset[f'rep_meso_{adt_band}k'] = np.where(
                    (subset[distance] > subset[col_meso_min]) &
                    (subset[distance] < subset[col_meso_max]),
                    True,
                    False)
        
            # BAIRRO
            col_bairro_min = f'bairro_min_{adt_band}k'
            col_bairro_max = f'bairro_max_{adt_band}k'
            if col_bairro_min in cols and col_bairro_max in cols:
                subset[f'rep_bairro_{adt_band}k'] = np.where(
                    (subset[distance] > subset[col_bairro_min]) &
                    (subset[distance] < subset[col_bairro_max]),
                    True,
                    False)
        
            # URBANO
            col_urb_min = f'urb_min_{adt_band}k'
            col_urb_max = f'urb_max_{adt_band}k'
            if col_urb_min in cols and col_urb_max in cols:
                subset[f'rep_urb_{adt_band}k'] = np.where(
                    (subset[distance] > subset[col_urb_min]) &
                    (subset[distance] < subset[col_urb_max]),
                    True,
                    False)
            
            
    else:
        for idx, adt_band in enumerate(pollutants_adt_dict[poluente][:-1]):
            distance = f'distance_{adt_band}k'
            cols = subset.columns
        
            # MICRO
            col_micro_min = f'micro_min_{adt_band}k'
            col_micro_max = f'micro_max_{adt_band}k'
            if col_micro_min in cols and col_micro_max in cols:
                subset[f'rep_micro_{adt_band}k'] = np.where(
                    (subset[distance] > subset[col_micro_min]) &
                    (subset[distance] < subset[col_micro_max]),
                    True,
                    False)
        
            # MESO
            col_meso_min = f'meso_min_{adt_band}k'
            col_meso_max = f'meso_max_{adt_band}k'
            # Exclui banda 1k do cálculo meso para PM
            if col_meso_min in cols and col_meso_max in cols and adt_band != 1:
                subset[f'rep_meso_{adt_band}k'] = np.where(
                    (subset[distance] > subset[col_meso_min]) &
                    (subset[distance] < subset[col_meso_max]),
                    True,
                    False)
        
            # BAIRRO
            col_bairro_min = f'bairro_min_{adt_band}k'
            col_bairro_max = f'bairro_max_{adt_band}k'
            if col_bairro_min in cols and col_bairro_max in cols:
                subset[f'rep_bairro_{adt_band}k'] = np.where(
                    (subset[distance] > subset[col_bairro_min]) &
                    (subset[distance] < subset[col_bairro_max]),
                    True,
                    False)
        
            # URBANO
            col_urb_min = f'urb_min_{adt_band}k'
            col_urb_max = f'urb_max_{adt_band}k'
            # Exclui banda 80k do cálculo urbano para PM
            if col_urb_min in cols and col_urb_max in cols and adt_band != 80:
                subset[f'rep_urb_{adt_band}k'] = np.where(
                    (subset[distance] > subset[col_urb_min]) &
                    (subset[distance] < subset[col_urb_max]),
                    True,
                    False)
    
    return subset

# ======================== APLICANDO FUNÇÃO ===============================
subset_co = verif_vias_dentro_dos_limites(subset_co,"co")
subset_no2 = verif_vias_dentro_dos_limites(subset_no2,"no2")
subset_o3 = verif_vias_dentro_dos_limites(subset_o3,"o3")
subset_pm = verif_vias_dentro_dos_limites(subset_pm,"pm")
subset_so2 = verif_vias_dentro_dos_limites(subset_so2,"so2")


# ==================== SALVANDO OUTPUTS ==================================
subset_co.to_parquet(outputs_path + '/subset_co.parquet')
subset_no2.to_parquet(outputs_path + '/subset_no2.parquet')
subset_o3.to_parquet(outputs_path + '/subset_o3.parquet')
subset_pm.to_parquet(outputs_path + '/subset_pm.parquet')
subset_so2.to_parquet(outputs_path + '/subset_so2.parquet')

