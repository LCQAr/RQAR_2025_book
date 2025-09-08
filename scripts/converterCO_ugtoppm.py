#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""


Criado por Leonardo Hoinaski
"""

# ---------------------------------- Importação de pacotes ----------------------------------

import os 
import pandas as pd
import numpy as np
import glob

def converter_ug_to_ppm(df):

    df['UNIDADE'] = 'ppm'
    df['VALOR'] = df['VALOR']/1163.517

    return df

path = '/home/nobre/Notebooks/RQAR_2025_book/data/MQAr/CO/'
files = os.listdir(path)

for file in files:

    if file.endswith('.csv'):
    
        df = pd.read_csv(path+file)
    
        if df['UNIDADE'][0] != 'ppm':
    
            df = converter_ug_to_ppm(df)
    
            df.to_csv(path+file)

