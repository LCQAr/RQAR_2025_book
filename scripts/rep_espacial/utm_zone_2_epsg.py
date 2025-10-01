#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon May 19 11:09:28 2025

@author: brunojalowski
"""
import numpy as np


def utm_zone_2_epsg(zone, lat) -> np.array:
    """This function assigns an EPSG code for the projected datum SIRGAS
    2000/UTM Zone XX N/S, according to the UTM zone and latitude.

    Parameters
    ----------
    zone : np.array | int
        UTM Zone.
        If numpy array, must be (N,1) with dtype int.
    lat : np.array | float
        Latitude in WGS84. If numpy array, must be (N,1) with dtype float.

    Returns
    -------
    np.array
        The EPSG code or codes. If numpy array, the dimension will be the same
        of the input.
    """
    epsg_south = 'EPSG:319' + (60 + zone).astype(int).astype(str)
    epsg_north = 'EPSG:319' + (54 + zone).astype(int).astype(str)

    epsg_code = np.where(lat > 0, epsg_north, epsg_south)

    return epsg_code
