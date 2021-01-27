# Module to write final AOI mask .shp from search.py.
from scipy.ndimage import rotate
import math
import numpy as np
import cv2
import rasterio
import os
import gdal_polygonize as gdp
import matplotlib.pyplot as plt

# Create empty array of size parcel, rotate to the best rotation.
# Copy the bestBlob(placeCheck) onto rotated image.
# Reverse rotation to properly align blob.
def overlay(img,TLc,TLr,BRc,BRr,rotation,placeCheck):
    final = rotate(np.zeros(img.shape),rotation,reshape=True).astype('float64')
    final[TLr:BRr,TLc:BRc]=placeCheck
    final = rotate(final,-rotation,reshape=True)
    final[final<-2]=1
    final[final<1]=0
    final[final>0]=1
    return final

# Make sure that newImg and original parcel image are the same size.
def reshape(img,final):
    # print(final.shape)
    if final.shape == img.shape:
        return final
    else:
        rowDif=((final.shape[0]-img.shape[0])/2)
        colDif=((final.shape[1]-img.shape[1])/2)
        TLr = (0+rowDif)
        TLc = (0+colDif)
        BRr = (final.shape[0]-rowDif)
        BRc = (final.shape[1]-colDif)
        reshapeFinal = final[math.floor(TLr):math.floor(BRr),
                            math.floor(TLc):math.floor(BRc)]
        return reshapeFinal

# Convolve image to smooth small errors/holes.
def convolve(reshapeFinal):
    # print(reshapeFinal.shape)
    convolved=reshapeFinal
    kernel = np.ones((3,3),np.uint8)/9
    for i in range(10):
        convolved = cv2.filter2D(convolved,-1,kernel)
    convolved[convolved>0]=1
    return convolved

# Masks image by those areas where original parcel is positive (viable).
def mask(img,convolved):
    # print(convolved.shape)
    mask = (img>=0)
    zeros = np.zeros((convolved.shape))
    np.copyto(zeros,convolved,casting='same_kind',where=mask)
    masked = (zeros[np.newaxis,...]).astype('uint8')
    # print(masked)
    # print(masked.shape,masked.sum())
    # fig,ax = plt.subplots(1)
    # ax.imshow(convolved)
    # plt.show()
    return masked

# Function to create .shp from blob mask.
# Also adds tabular info summarizing the total AOI score.
# Allows for AOI to be compared with those from other parcels.
def projectWrite(outDir,masked,srcDir,imgName,sum,county):
    if os.path.isdir(outDir) == False:
        os.mkdir(outDir)
    parcelName = os.path.splitext(imgName)[0]
    outPath = os.path.join(outDir,imgName)
    defPath = os.path.join(srcDir,'{}_landcover/{}'.format(county,imgName))
    # print(defPath)
    defSet = rasterio.open(defPath)
    projection = defSet.meta['crs']
    transformation = defSet.meta['transform']
    with rasterio.open(outPath, "w",
                        driver='GTiff',
                        crs=projection,
                        height=masked.shape[1],
                        width=masked .shape[2],
                        count=1,
                        dtype=masked.dtype,
                        nodata=0,
                        transform=transformation) as dest:
        dest.write(masked)
    shpPath = os.path.join(outDir,parcelName+'.shp')
    gdp.main(outPath,shpPath)
    os.chdir(outDir)
    os.system('ogrinfo -q {} -sql "ALTER TABLE {} ADD COLUMN parcel character(15)"'.format(shpPath,parcelName))
    os.system('ogrinfo -q {} -dialect sqlite -sql "UPDATE \'{}\' SET parcel = {}"'.format(shpPath,parcelName,parcelName))
    os.system('ogrinfo -q {} -sql "ALTER TABLE {} ADD COLUMN sum character(15)"'.format(shpPath,parcelName))
    os.system('ogrinfo -q {} -dialect sqlite -sql "UPDATE \'{}\' SET sum = {}"'.format(shpPath,parcelName,sum))
    os.system('ogr2ogr -q -f "ESRI Shapefile" -update -append merge.shp {}'.format(shpPath))

    #Cleanup
    #Deleted masked raster
    os.remove(outPath)
    #List of shp dependencies
    deps = ['.dbf','.prj','.shx','.shp']
    for d in deps:
        os.remove(os.path.join(outDir,parcelName+d))
