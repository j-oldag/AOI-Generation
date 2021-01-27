# Module for holding GDAL functions for reprojection, rasterization, and computing proximity.

import os
from gdal_proximity import proximityMain


# Set function variables.
state = 'pennsylvania'

countyList = ['Albemarle','Amherst','Botetourt','Buchanan','Campbell','Carroll','Dickenson','Floyd','Galax','Giles',
              'Grayson','Henry','Lynchburg','Martinsville','Montgomery','Nelson','Patrick','Pittsylvania','Pulaski',
              'Radford','Roanoke','Russell','Scott','Tazewell','Wise']

coorSys = "32618"

# Execute main function.
for county in countyList:
    allGDAL(county,state,coorSys)







# Reproject all .shp files to desired UTM and standardize names.
# Generate os command to iterate through inputs dict.
def reprojectVector(county,path,coor):
    os.chdir(path)
    dict = {
            'water.shp':'{}_wetlands.shp'.format(county),
            '3phase.shp':'{}_3phase.shp'.format(county),
            'buildings.shp':'{}_buildings.shp'.format(county),
            'roads.shp':'{}_roads.shp'.format(county),
            'parcelLines.shp':'{}_Parcellines.shp'.format(county)
            }
    for i in dict.items():
        srcPath = os.path.join(path,i[1])
        dstPath = os.path.join(path,i[0])
        # print(srcPath,dstPath)
        print("Reprojecting",i[1])
        command = 'ogr2ogr -q -f "ESRI Shapefile" -overwrite -progress {} {} -t_srs EPSG:{}'.format(dstPath,srcPath,coor)
        # print(command)
        os.system(command)

# Rasterize all .shp files.
# Generate os command to iterate through inputs dict.
def gdal_rasterize(path):
    os.chdir(path)
    dict = {
            'water.tif':'water.shp',
            '3phase.tif':'3phase.shp',
            'buildings.tif':'buildings.shp',
            'roads.tif':'roads.shp',
            'parcels.tif':'parcelLines.shp'
            }
    for i in dict.items():
        srcPath = os.path.join(path,i[1])
        dstPath = os.path.join(path,i[0])
        print('Rasterizing',i[1])
        os.system('gdal_rasterize -q -burn 1 -a_nodata -1 -tr 1 1 -q {} {}'.format(srcPath,dstPath))

# Compute proximity of all raster mask file.
# Generate os command to iterate through inputs dict.
def gdal_proximity(path):
    os.chdir(path)
    dict = {
            'DTW.tif':'water.tif',
            'DT3P.tif':'3phase.tif',
            'DTB.tif':'buildings.tif',
            'DTR.tif':'roads.tif',
            'DTP.tif':'parcels.tif'
            }
    for i in dict.items():
        srcPath = os.path.join(path,i[1])
        dstPath = os.path.join(path,i[0])
        print('Proximizing',i[0])
        proximityMain(srcPath,dstPath)
        os.remove(srcPath)

# Combines above helper functions.
# Creates all outputs in local C:/ drive directory.
def allGDAL(county,state,coor):
    path = 'C:/aoi_gen//{}/{}/basedata'.format(state,county)
    reprojectVector(county,path,coor)
    gdal_rasterize(path)
    gdal_proximity(path)


