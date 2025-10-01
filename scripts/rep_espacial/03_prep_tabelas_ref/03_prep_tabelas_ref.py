

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
inputs_path = '/home/nobre/Notebooks/' + root_path + '/03_prep_tabelas_ref/inputs'

# Caminho da pasta de outputs
outputs_path = root_path + '/03_prep_tabelas_ref/outputs'

# Caminhos dos subsets
subset_co_path = os.readlink(inputs_path + '/subset_co.txt')
subset_no2_path = os.readlink(inputs_path + '/subset_no2.txt')
subset_o3_path = os.readlink(inputs_path + '/subset_o3.txt')
subset_pm_path = os.readlink(inputs_path + '/subset_pm.txt')
subset_so2_path = os.readlink(inputs_path + '/subset_so2.txt')

# ========================= CARREGANDO SUBSETS ====================================
subset_co = gpd.read_parquet(subset_co_path)
subset_no2 = gpd.read_parquet(subset_no2_path)
subset_o3 = gpd.read_parquet(subset_o3_path)
subset_pm = gpd.read_parquet(subset_pm_path)
subset_so2 = gpd.read_parquet(subset_so2_path)


# ========================== PREPARANDO TABELAS DE REFERÊNCIA ======================
# Lendo os arquivos para cada tabela -------------------------------------------------
# https://www.gov.br/mma/pt-br/assuntos/meio-ambiente-urbano-recursos-hidricos-qualidade-ambiental/qualidade-do-ar/guia-tecnico-para-o-monitoramento-e-avaliacao-da-qualidade-do-ar.pdf

ref_table_co = pd.read_csv(inputs_path + '/ref_table_so2eco.csv')
ref_table_no2 = pd.read_csv(inputs_path + '/ref_table_no2.csv')
ref_table_o3 = pd.read_csv(inputs_path + '/ref_table_o3.csv')
ref_table_pm = pd.read_csv(inputs_path + '/ref_table_pm.csv')
ref_table_so2 = pd.read_csv(inputs_path + '/ref_table_so2eco.csv')

# Nota da EPA acerca da ocorrência de valores intermediários de ADT
'''
Distance from the edge of the nearest traffic lane. The distance for 
intermediate traffic counts should be interpolated from the table values based
on the actual traffic count.

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


# ============ INTERPOLAÇÃO DOS LIMITES DAS CLASSES DE REPRESENTATIVIDADE =============

def interp_limites_rep(subset: gpd.GeoDataFrame,
                       interpolated: pd.DataFrame,
                       poluente: str) -> pd.DataFrame:
    """
    
    """
  
    # Dicionário de faixas de ADT (value * 1000)
    pollutants_adt_dict = {'co':[1, 10, 20, 30, 40, 50, 60, np.inf],
                           'so2':[1, 10, 20, 30, 40, 50, 60, np.inf],
                           'no2':[1, 10, 15, 20, 40, 70, 110, np.inf],
                           'pm': [1, 15, 20, 30, 40, 50, 60, 70, 80, np.inf],
                           'o3':[10, 15, 20, 40, 70, 110, np.inf]}
    
    # Iterando sobre os valores de adt da tabela de referencia de cada poluente
    for idx, adt_band in enumerate(pollutants_adt_dict[poluente][:-1]):
        col_name = f'average_daily_vehicle_count_{adt_band}k'
        
        if col_name not in subset.columns:
            print(f"[WARNING] '{col_name}' nonexistant in subset_{poluente}")
            continue
        
        # Iterando sobre os valores de adt para cada via do subset do poluente
        for adt_value in subset[col_name]:
            interpolated.loc[adt_value] = np.nan
                
    # Organizar pelo índice de modo ascendente
    interpolated.sort_index(inplace=True)
                
    # Interpolando os valores NaN #FIXME
    cols = [col for col in interpolated.columns if (('min' in col) | ('max' in col))]
    for col in cols:
        vals = set(interpolated[col].dropna().unique())
        if len(vals) == 1 and interpolated[col].isna().any():
            interpolated[col] = interpolated[col].dropna().unique()[0]
        else:
            interpolated[col] = pd.to_numeric(interpolated[col],
                                              errors='coerce')
            
            interpolated[col] = interpolated[col].interpolate(method='index',
                                                              limit_area='inside')
            interpolated[col] = interpolated[col].interpolate(method='spline',
                                                              order=1,
                                                              limit_direction='forward')
            interpolated[col] = interpolated[col].fillna(np.inf)

                
    # Resetando index
    interpolated.reset_index(inplace=True)

    return interpolated


# ========== APLICANDO FUNÇÃO ===========================================
interpolated_co = interp_limites_rep(subset_co,
                                     interpolated_co,
                                     'co')
interpolated_no2 = interp_limites_rep(subset_no2,
                                     interpolated_no2,
                                     'no2')
interpolated_o3 = interp_limites_rep(subset_o3,
                                     interpolated_o3,
                                     'o3')
interpolated_pm = interp_limites_rep(subset_pm,
                                     interpolated_pm,
                                     'pm')
interpolated_so2 = interp_limites_rep(subset_so2,
                                     interpolated_so2,
                                     'so2')

# ================= SALVANDO OUTPUTS ====================================
interpolated_co.to_parquet(outputs_path + '/interpolated_co.parquet')
interpolated_no2.to_parquet(outputs_path + '/interpolated_no2.parquet')
interpolated_o3.to_parquet(outputs_path + '/interpolated_o3.parquet')
interpolated_pm.to_parquet(outputs_path + '/interpolated_pm.parquet')
interpolated_so2.to_parquet(outputs_path + '/interpolated_so2.parquet')


