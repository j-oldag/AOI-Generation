# Module for the splitting of large raster files into parcels.

import os
import fiona
import gdal

# Set variables for main function.
state = 'pennsylvania'

countyList = ['Albemarle','Amherst','Botetourt','Buchanan','Campbell','Carroll','Dickenson','Floyd','Galax','Giles',
              'Grayson','Henry','Lynchburg','Martinsville','Montgomery','Nelson','Patrick','Pittsylvania','Pulaski',
              'Radford','Roanoke','Russell','Scott','Tazewell','Wise']

# Execute main function.
for c in countyList:
    mainSplit(c)






def mainSplit(state,county):

    # List of rasters to be split.
    tifList =['{}_aspect.tif'.format(county),
              '{}_landcover.tif'.format(county),
              'dtp.tif','dt3p.tif',
              'dtb.tif','dtr.tif',
              'dtw.tif','{}_slope.tif'.format(county)]

    for t in tifList:

        # Echo progress updates.
        print('Working on',t)

        if t == '{}_slope.tif'.format(county):
            nodata = -1
        else:
            nodata = 0

        # Check for output directory and input .shp file.
        srcDir = 'C:/{}/{}/basedata'.format(state,county)
        print(srcDir)
        os.chdir(srcDir)
        im = os.path.join(srcDir,t)
        shp = os.path.join(srcDir,'{}_parcels.shp'.format(county))
        dstDir = os.path.splitext(t)[0]

        # Open Raster and check cell size.
        print('Opening raster')
        raster = gdal.Open(im)
        print('Raster opened')
        xSize, ySize = raster.GetGeoTransform()[1],-raster.GetGeoTransform()[5]

        # Pass if resolution is 1m.
        if xSize==1.0 and ySize==1.0:
            pass
        # Else, resample into 1m pixel resolution.
        else:
            print('Resampling',im)
            im02 = os.path.splitext(im)[0]+'02.tif'
            os.system('gdalwarp -tr 1 1 -r near -dstnodata -1 -overwrite {} {}'.format(im,im02))
            im = im02

        # Create holding lists for unique feature IDs.
        featIDs01 = []
        featIDs02 = []

        # Test that .shp file is uncorrupted and valid.
        test = fiona.open(shp)

        # Unique feature IDs written to list.
        print('Reading shp features')
        for feat in fiona.open(shp):
            featIDs01.append(str(feat['properties']['U_ID']))
        for feat in featIDs01:
            featIDs02.append('"'+feat+'"')

        # Output directory created for each input raster.
        newDir = os.path.join('C://{}/{}/'.format(state,county),dstDir)
        if os.path.isdir(newDir) == False:
            os.mkdir(newDir)
            print('Creating dir',newDir)

        os.chdir(newDir)

        # Iterative os command executed to cut raster to parcel lines.
        print('Clipping raster')
        for f in featIDs02:
            os.system('gdalwarp -tr 1 1 -r near -ot Float64 -dstnodata %s -q -overwrite -cutline %s -cwhere U_ID=%s '
                      '-crop_to_cutline --config GDALWARP_IGNORE_BAD_CUTLINE YES %s %s.tif' %(nodata,shp,f,im,f))


