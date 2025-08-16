#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul  6 13:43:18 2023

@author: leohoinaski
"""

import elevation
import pandas as pd
import utm
import rasterio
from shapely.geometry import Polygon
import geopandas as gpd
import numpy as np
from rasterio.merge import merge


def getSRTMdomain(folder,Xcenter,Ycenter,UTM_zone,Northern):
    xi = Xcenter-50000
    xf = Xcenter+50000
    yi = Ycenter-50000
    yf = Ycenter+50000
    # melhorar esta parte do northern false
    lati,loni = utm.to_latlon(xi, yi, UTM_zone, northern=Northern)
    latf,lonf = utm.to_latlon(xf, yf, UTM_zone, northern=Northern)
    elevation.clip(bounds=(loni, lati, lonf, latf), output=folder+'/SRTM.tif')
    elevation.clean()
    return elevation

def getSRTMforCoord(folder,srcFile):
    coord = pd.read_csv(srcFile)
    lati = coord['Latitude'].min()-0.5
    latf = coord['Latitude'].max()+0.5
    loni = coord['Longitude'].min()-0.5
    lonf = coord['Longitude'].max()+0.5
    elevation.clip(bounds=(loni, lati, lonf, latf), output=folder+'/SRTM.tif')
    elevation.clean()
    return elevation

#%% userDomain
def center2domain(Xcenter,Ycenter,UTM_zone,nreceptX,nreceptY,
                  deltaX,deltaY):
    # Creating domain window
    xi = Xcenter-deltaX*(nreceptX+4)
    xf = Xcenter+deltaX*(nreceptX+4)
    yi = Ycenter-deltaY*(nreceptY+4)
    yf = Ycenter+deltaY*(nreceptY+4)

    # melhorar esta parte do northern false
    lati,loni = utm.to_latlon(xi, yi, UTM_zone, northern=False)
    latf,lonf = utm.to_latlon(xf, yf, UTM_zone, northern=False)

    return lati,latf,loni,lonf

#%% userDomain
def modelDomain(lati,latf,loni,lonf):
    # Creating domain window
    domain = Polygon(zip([loni,loni,lonf,lonf],[lati,latf,latf,lati])) 
    domain = gpd.GeoDataFrame(index=[0],geometry=[domain])
    domain.crs = "EPSG:4326"
    return domain,lati,latf,loni,lonf


def SRTM_selectGetElev(FOLDER_PATH,outfolder,srcFile):  
    
    coord = pd.read_csv(srcFile)
    lati = coord['Latitude'].min()-0.1
    latf = coord['Latitude'].max()+0.1
    loni = coord['Longitude'].min()-0.1
    lonf = coord['Longitude'].max()+0.1

    domain,lati,latf,loni,lonf = modelDomain(lati,latf,loni,lonf)
    
    lati = int(np.floor(lati))
    latf = int(np.ceil(latf))
    loni = int(np.floor(loni))
    lonf = int(np.ceil(lonf))
    
    latFiles = np.linspace(lati,latf,abs(latf-lati)+1)
    lonFiles = np.linspace(loni,lonf,abs(lonf-loni)+1)
    
    x,y=np.meshgrid(lonFiles,latFiles)
    files = []
    for xl in lonFiles[:-1]:
        for yl in latFiles[:-1]:
            file = 's'+str(abs(int(yl))).zfill(2)+'_w'+str(abs(int(xl))).zfill(3)+'_1arc_v3.tif'
            files.append(file)
                       
    raster_to_mosiac=[]        
    for file in files:
        try:
            raster = rasterio.open(FOLDER_PATH+file)
            raster_to_mosiac.append(raster)
        except:
            print('File '+file+ ' does not exist')
        
    mosaic, output = merge(raster_to_mosiac)
    output_meta = raster.meta.copy()
    output_meta.update(
        {"driver": "GTiff",
            "height": mosaic.shape[1],
            "width": mosaic.shape[2],
            "transform": output,
        })
    

    with rasterio.open(outfolder+'mergedSRTM.tif', 'w', **output_meta) as m:
        m.write(mosaic)
        
    with rasterio.open(outfolder+'mergedSRTM.tif') as src:
        out_image, out_transform = rasterio.mask.mask(src,domain.geometry, crop=True)
        output_meta = src.meta
        output_meta.update({"driver": "GTiff",
                         "height": out_image.shape[1],
                         "width": out_image.shape[2],
                         "transform": out_transform})
    if output_meta:   
        with rasterio.open(outfolder+'/mergedSRTM.tif', "w", **output_meta) as dest:
            dest.write(out_image)
    return out_image


def getElevSRTM(folder,srcFile):
    coord = pd.read_csv(srcFile)
    path = folder+'/mergedSRTM.tif'
    dem_data = rasterio.open(path)
    dem_array = dem_data.read(1)
    elevations=[]
    for ii,coords in coord.iterrows():
        elev = dem_array[dem_data.index(coords.Longitude, coords.Latitude)]
        elevations.append(elev)
    coord['elev'] = elevations 
    coord.to_csv(folder+'/getElev.csv', index=False)
    return coords

def getElevSRTMfromCoords(folder,fileName,lat,lon):
    path = folder+'/'+fileName+'.tif'
    dem_data = rasterio.open(path)
    dem_array = dem_data.read(1)
    print('Raster boundary')
    print(dem_data.bounds)
    print(str(lat) + ' ' + str(lon))
    print(dem_data.index(lon, lat))
    print(dem_array.shape)
    elev = dem_array[dem_data.index(lon, lat)]
    return elev