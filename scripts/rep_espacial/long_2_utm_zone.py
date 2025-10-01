#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue May 13 18:19:16 2025

@author: brunojalowski
"""
import numpy as np


def long_2_utm_zone(long: float | np.ndarray) -> np.ndarray:
    """ This function gets the UTM Zone from the latitude value.

    Parameters
    ----------
    long : float | np.array
        Longitude in WGS84. If numpy array, must be (N,1) with dtype float.

    Returns
    -------
    np.array
        UTM Zone os UTM zones. If numpy array, the dimension will be the same
        of the input.
    """
    zone = (np.floor((long + 180) / 6) % 60) + 1

    return np.nan_to_num(zone, nan=0).astype('uint8')
