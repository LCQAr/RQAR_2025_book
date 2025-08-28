#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Script para rodar a iterative_timeseries para todas as estações. 
Arquivos serão salvos na pasta _static/plotly_figures com o código ID_MMA_COMPLETO

Created on Wed Sep 11 10:45:33 2024

@author: leohoinaski
"""

#-----------------------------Importação de pacotes ------------------------------------


import os
import scripts.timeSeriesFigures as tsf
import pandas as pd

rootPath = os.path.dirname(os.getcwd())
aqmdata = pd.read_csv(rootPath+'/data/Monitoramento_QAr_BR.csv')

for index, row in aqmdata.iterrows(): 
    ID_MMA_COMPLETO = row.ID_MMA_COMPLETO
    pollutant = row.POLUENTE
    # COLOCAR CAMINHO CORRETO
    df = pd.read_csv(rootPath+'/data/MQAr/'+pollutant+'/'+ID_MMA_COMPLETO+'.csv')
    
    #ID_MMA_COMPLETO = 'RS0009_MP10'
    tsf.iterative_timeseries(df,ID_MMA_COMPLETO)