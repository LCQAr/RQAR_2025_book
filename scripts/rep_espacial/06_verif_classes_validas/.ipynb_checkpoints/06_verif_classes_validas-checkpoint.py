
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
inputs_path = root_path + '/06_verif_classes_validas/inputs'

# Caminho da pasta de outputs
outputs_path = root_path + '/06_verif_classes_validas/outputs'

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


# =================== VERIFICANDO CLASSES VÁLIDAS PARA CADA ESTAÇÃO=================

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
subset_no2['rep_micro_any'] = safe_any(subset_no2, 'rep_micro')
subset_no2['rep_bairro_any'] = safe_any(subset_no2, 'rep_bairro')
subset_no2['rep_urb_any'] = safe_any(subset_no2, 'rep_urb')

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


# ============================== SALVANDO OUTPUTS =============================
subset_co.to_parquet(outputs_path + '/subset_co.parquet')
subset_no2.to_parquet(outputs_path + '/subset_no2.parquet')
subset_o3.to_parquet(outputs_path + '/subset_o3.parquet')
subset_pm.to_parquet(outputs_path + '/subset_pm.parquet')
subset_so2.to_parquet(outputs_path + '/subset_so2.parquet')