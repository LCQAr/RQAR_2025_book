
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
inputs_path = root_path + '/07_classificar_rep_espacial/inputs'

# Caminho da pasta de outputs
outputs_path = root_path + '/07_classificar_rep_espacial/outputs'

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


# ============ CLASSIFICANDO O STATUS DE REPRESENTATIVIDADE DE CADA ESTAÇÃO ===================
def classificar_rep_espacial(subset):
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

    # Assegurando de não estar sobrescrevendo o subset original
    subset = subset.copy()
    
    # Criando lista de possíveis colunas a considerar
    # A lista foi criada do menos restritivo para mais restritivo
    rep_possibilities = {
        'rep_urb_any': 'urbana',
        'rep_bairro_any': 'bairro',
        'rep_meso_any': 'meso',
        'rep_micro_any': 'micro',
    }

    # Filtrando as que estão no subset
    rep_possibilities = {
        col: item
        for col, item in rep_possibilities.items()
        if col in subset.columns
    }

    # Definindo variável de resultado como lista vazia do tamanho de subset
    rep_spatial_name_serie = pd.Series(index=range(len(subset)), dtype='str')
    rep_spatial_name_serie.loc[:] = 'não representativo'

    # Adicionando resultados do menos restritivo pro mais restritivo
    for header, item in rep_possibilities.items():
        # Adicionando só onde os valores da coluna forem iguais a True
        rep_spatial_name_serie.loc[subset[header]] = item

    # Adicionando no subset final
    subset.loc[:, 'REP_ESPACIAL_NAME'] = rep_spatial_name_serie

    return subset

  
# ====================== APLICANDO FUNÇÃO ===================================
subset_co = classificar_rep_espacial(subset_co)
subset_no2 = classificar_rep_espacial(subset_no2)
subset_o3 = classificar_rep_espacial(subset_o3)
subset_pm = classificar_rep_espacial(subset_pm)
subset_so2 = classificar_rep_espacial(subset_so2)


# ==================== SALVANDO OUTPUTS ==================================
subset_co.to_parquet(outputs_path + '/subset_co.parquet')
subset_no2.to_parquet(outputs_path + '/subset_no2.parquet')
subset_o3.to_parquet(outputs_path + '/subset_o3.parquet')
subset_pm.to_parquet(outputs_path + '/subset_pm.parquet')
subset_so2.to_parquet(outputs_path + '/subset_so2.parquet')