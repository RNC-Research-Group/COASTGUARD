#!/usr/bin/env python3
import os
from glob import glob
import warnings
import pandas as pd
from tqdm.auto import tqdm
from tqdm.contrib.concurrent import process_map

warnings.filterwarnings("ignore")
from datetime import datetime
from Toolshed import (
    Download,
    Toolbox,
    VegetationLine,
    Transects,
)
import ee
import geopandas as gpd
import time
import sys
import numpy as np

start = time.time()

# Earth engine service account
service_account = 'service-account@iron-dynamics-294100.iam.gserviceaccount.com'
credentials = ee.ServiceAccountCredentials(service_account, '../CoastSat/.private-key.json')
ee.Initialize(credentials)

poly = gpd.read_file("../CoastSat/polygons.geojson")
poly = poly[poly.id.str.startswith("nzd")].to_crs(2193)
mhwl = gpd.read_file("lds-nz-coastline-mean-high-water-GPKG.zip!nz-coastline-mean-high-water.gpkg")
transects = gpd.read_file("../CoastSat/transects_extended.geojson")

print(f"{time.time() - start}: Reference polygons and transects loaded")

os.makedirs("Data/referenceLines", exist_ok=True)

sitename = "nzd0151"

try:
    os.unlink(f"Data/{sitename}/{sitename}_metadata.pkl")
    os.unlink(f"Data/{sitename}/{sitename}_output.pkl")
except Exception:
    pass

bbox = poly[poly.id == sitename].geometry.iloc[0]
clipped_mhwl = mhwl.clip(bbox)

dates = ["2010-01-01", "2010-02-01"]
sat_list = ["L5", "L7", "L8", "L9"]

cloud_thresh = 0.5
wetdry = False
max_dist_ref = 80

filepath = Toolbox.CreateFileStructure(sitename, sat_list)

if len(dates) > 2:
    daterange = "no"
else:
    daterange = "yes"
years = list(
    Toolbox.daterange(
        datetime.strptime(dates[0], "%Y-%m-%d"),
        datetime.strptime(dates[-1], "%Y-%m-%d"),
    )
)

polygon = [poly[poly.id == sitename].to_crs(4326).geometry.iloc[0]]
polygon = Toolbox.smallest_rectangle(polygon)

inputs = {
    "polygon": polygon,
    "dates": dates,
    "daterange": daterange,
    "sat_list": sat_list,
    "sitename": sitename,
    "filepath": filepath,
}

inputs = Download.check_images_available(inputs)

Sat = Download.RetrieveImages(inputs, SLC=False)
metadata = Download.CollectMetadata(inputs, Sat)

LinesPath = "Data/" + sitename + "/lines"

os.makedirs(LinesPath, exist_ok=True)

#projection_epsg, _ = Toolbox.FindUTM(polygon[0][0][1], polygon[0][0][0])
#print(projection_epsg)
#projection_epsg = 2193
projection_epsg = 32760

settings = {
    # general parameters:
    "cloud_thresh": cloud_thresh,  # threshold on maximum cloud cover
    "output_epsg": projection_epsg,  # epsg code of spatial reference system desired for the output
    "wetdry": wetdry,  # extract wet-dry boundary as well as veg
    # quality control:
    "check_detection": False,  # if True, shows each shoreline detection to the user for validation
    "adjust_detection": False,  # if True, allows user to adjust the postion of each shoreline by changing the threhold
    "save_figure": True,  # if True, saves a figure showing the mapped shoreline for each image
    # [ONLY FOR ADVANCED USERS] shoreline detection parameters:
    "min_beach_area": 200,  # minimum area (in metres^2) for an object to be labelled as a beach
    "buffer_size": 250,  # radius (in metres) for buffer around sandy pixels considered in the shoreline detection
    "min_length_sl": 500,  # minimum length (in metres) of shoreline perimeter to be valid
    "cloud_mask_issue": False,  # switch this parameter to True if sand pixels are masked (in black) on many images
    # add the inputs defined previously
    "inputs": inputs,
    "projection_epsg": projection_epsg,
    "year_list": years,
}


#referenceLine, ref_epsg = Toolbox.ProcessRefline(referenceLinePath, settings)
#print(referenceLine, ref_epsg)
settings["reference_shoreline"] = clipped_mhwl
settings["ref_epsg"] = 4326
settings["max_dist_ref"] = max_dist_ref
settings["reference_coreg_im"] = None

output, output_latlon, output_proj = VegetationLine.extract_veglines(
    metadata, settings, polygon, dates
)
output, output_latlon, output_proj = Toolbox.ReadOutput(inputs)
output = Toolbox.RemoveDuplicates(output)
print(output)