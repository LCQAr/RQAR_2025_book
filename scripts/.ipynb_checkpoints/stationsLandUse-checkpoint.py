#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep 11 10:45:33 2024

@author: leohoinaski
"""

import os
import pandas as pd
from shapely.geometry import Point
import geopandas as gpd
#import matplotlib.pyplot as plt
import rasterio as rs
import rasterio.mask
import numpy as np
import ismember


def stationBuffers(station_path,bufferSize): 
    #inputFolder = rootDir+'/inputs/MonitoramentoQAr'
    df = pd.read_csv(station_path)
    geometry = [Point(xy) for xy in zip(df.LONGITUDE, df.LATITUDE)]
    gdf = gpd.GeoDataFrame(df, crs="EPSG:4326", geometry=geometry)
    gdf = gdf.set_crs(4326, allow_override=True)
    gdfMeter = gpd.GeoDataFrame(gdf, crs=4326).to_crs('EPSG:3857')
    gdfBuffer = gdfMeter.buffer(bufferSize)
    gdfBuffer = gdfBuffer.to_crs('EPSG:4326')
    gdf['buffer'] = gdfBuffer
    gdf = gdf.drop_duplicates(subset=['geometry'])
    return gdf

def stationUnionByUF(gdf):
    stationInUF=[]
    for index, uf in enumerate(gdf['UF'].unique()):
       stationInUF.append(gdf['buffer'][gdf['UF']==uf].unary_union)
       
    stationInUF = pd.DataFrame(stationInUF,columns=["geometry"])   
    stationInUF = gpd.GeoDataFrame(stationInUF, geometry=stationInUF['geometry'],
                                   crs="EPSG:4326")
    stationInUF['ID_OEMA'] = gdf['UF'].unique()
    stationInUF['buffer'] = stationInUF['geometry'].copy() 
    
    return stationInUF

def cutMapbiomas(inputFolder,gdf,year,prefix,pixelSize):
    """
    Esta função é utilizada para cortar o arquivo do Mapbiomas para o domínio 
    de modelagem. Se o domínio for muito grande, ela simplesmente lê o arquivo
    original sem cortar. 
    
    FUNÇÃO NÃO ESTÁ SENDO UTILIZADA NA VERSÃO ATUAL

    Parameters
    ----------
    domainShp : geodataframe
        Geodataframe com a geometria do domínio de modelagem.
    inputFolder : path
        Caminho para a pasta de inputs.
    outfolder : path
        Caminho para a pasta de outputs.
    year : int
        Ano de referência para a modelagem.
    GRDNAM : str
        Nome da grade de modelagem de acordo com o MCIP.

    Returns
    -------
    out_meta : rasterio
        Detalhes do raster.
    arr : rasterio
        Array do raster.

    """
    #rootDir = os.path.dirname(os.getcwd())
    #inputFolder = rootDir+'/MAPBIOMAS'
    outfolder =inputFolder+'/outputs'
    os.makedirs(outfolder, exist_ok=True)
    
    dfLegend = pd.read_csv(inputFolder+'/mapbiomasLegend.csv')
    
    for dl in dfLegend['Code ID']:
        gdf[str(dl)] = np.nan  


    for index, row in gdf.iterrows():
        # Abrindo o arquivo do MAPBIOMAS
        with rs.open(inputFolder+'/brazil_coverage_'+str(year)+'.tif') as src:
    
            # Tenta abrir e cortar o arquivo. Se for muito grande, não cortará e passará
            # para o except
            #  Abrindo raster e cortando
            try:
                out_image, out_transform = rasterio.mask.mask(src,[row.buffer],
                                                              crop=True)
            except:
                out_image, out_transform = rasterio.mask.mask(src,[row.geometry],
                                                              crop=True)
            # Extraindo propriedades do raster
            out_meta = src.meta
            out_meta.update({"driver": "GTiff",
                         "height": out_image.shape[1],
                         "width": out_image.shape[2],
                         "transform": out_transform})
            # Se conseguir recortar...
            if out_meta:   
                # Abre um novo arquvio e salva na pasta de outputs recortado
                with rs.open(outfolder+'/mapbiomas_'+row['ID_OEMA'].replace('/','')+'.tif', "w", **out_meta) as dest:
                    dest.write(out_image)

     
            values, counts = np.unique(out_image.flatten(), return_counts=True)
            counts = counts*pixelSize
            for ii,val in enumerate(values):
                if val!=0:
                    gdf.loc[index,gdf.columns[gdf.columns==str(val)]] = counts[ii]
    gdf = majorLandUse(gdf,inputFolder)
    #gdf.to_csv(outfolder+'/stationsLandUse.csv') 
    gdf = gdf.drop(columns=['geometry'])         
    gdf.to_csv(outfolder+'/'+prefix+'stationsLandUse.csv',)
    gdf = gdf.drop(columns=['buffer']) 
    gdf.to_csv(outfolder+'/'+prefix+'stationsLandUseNoGeometry.csv') 
    return gdf

def cutMapbiomasSimple(inputFolder, gdf,year,pixelSize):
    """
    Esta função é utilizada para cortar o arquivo do Mapbiomas para o domínio 
    de modelagem. Se o domínio for muito grande, ela simplesmente lê o arquivo
    original sem cortar. 
    
    FUNÇÃO NÃO ESTÁ SENDO UTILIZADA NA VERSÃO ATUAL

    Parameters
    ----------
    domainShp : geodataframe
        Geodataframe com a geometria do domínio de modelagem.
    inputFolder : path
        Caminho para a pasta de inputs.
    outfolder : path
        Caminho para a pasta de outputs.
    year : int
        Ano de referência para a modelagem.
    GRDNAM : str
        Nome da grade de modelagem de acordo com o MCIP.

    Returns
    -------
    out_meta : rasterio
        Detalhes do raster.
    arr : rasterio
        Array do raster.

    """
    rootDir = os.path.dirname(os.getcwd())
    #inputFolder = rootDir+'/inputs'
    outfolder =inputFolder+'/outputs'
    os.makedirs(outfolder, exist_ok=True)
    
    dfLegend = pd.read_csv(inputFolder+'/mapbiomasLegend.csv')
    
    for dl in dfLegend['Code ID']:
        gdf[str(dl)] = np.nan  


    for index, row in gdf.iterrows():
        # Abrindo o arquivo do MAPBIOMAS
        with rs.open(inputFolder+'/brazil_coverage_'+str(year)+'.tif') as src:
    
            # Tenta abrir e cortar o arquivo. Se for muito grande, não cortará e passará
            # para o except
            #  Abrindo raster e cortando
            try:
                out_image, out_transform = rasterio.mask.mask(src,[row.buffer],
                                                              crop=True)
            except:
                out_image, out_transform = rasterio.mask.mask(src,[row.geometry],
                                                              crop=True)
            # Extraindo propriedades do raster
            out_meta = src.meta
            out_meta.update({"driver": "GTiff",
                         "height": out_image.shape[1],
                         "width": out_image.shape[2],
                         "transform": out_transform})

            values, counts = np.unique(out_image.flatten(), return_counts=True)
            counts = counts*pixelSize
            for ii,val in enumerate(values):
                if val!=0:
                    gdf.loc[index,gdf.columns[gdf.columns==str(val)]] = counts[ii]      
    gdf.to_csv(outfolder+'/UFLandUse.csv') 
    return gdf

def statsByUF(inputFolder,gdfUFstations,year):
    #rootDir = os.path.dirname(os.getcwd())
    #inputFolder = rootDir+'/inputs'
    outfolder =inputFolder+'/outputs'

    #outfolder = rootDir+'/outputs/mapbiomas'
    
    mapbioStats = pd.read_csv(outfolder+'/mapbiomasStatisticsByUF.csv')
    dfLegend = pd.read_csv(inputFolder+'/mapbiomasLegend.csv')
    for dl in dfLegend['Code ID']:
        gdfUFstations['AREAUF_'+str(dl)] = np.nan  
    
    gdfUFstations['AREA_TOTAL']=np.nan
    
    for index, row in gdfUFstations.iterrows():
        gdfUFstations['AREA_TOTAL'][index] = np.sum(mapbioStats[str(year)][mapbioStats.UF==row['ID_OEMA']])*pixelSize
        for dl in dfLegend['Code ID']:
            gdfUFstations['AREAUF_'+str(dl)][index]= np.sum(
                mapbioStats[str(year)][(mapbioStats.UF==row['ID_OEMA']) & 
                                       (mapbioStats['class']==dl)])*10000
    #gdfUFstations = gdf.drop(columns=['geometry']) 
    #gdfUFstations = gdf.drop(columns=['buffer']) 
    gdfUFstations.to_csv(outfolder+'/UFstationsLandUseStats.csv')        
    return gdfUFstations
    
def majorLandUse(gdf,inputFolder):
    dfLegend = pd.read_csv(inputFolder+'/mapbiomasLegend.csv')
    cols=[]
    for dl in dfLegend['Code ID']:
        cols.append(dl) 
    cols = np.array(cols)
    
    lia,loc = ismember.ismember(gdf.columns, cols)
    majorLU = gdf.columns[lia][np.nanargmax(np.array(gdf[gdf.columns[lia]]).transpose(),axis=0)]
    gdf['majorLandUse'] = majorLU
    return gdf

