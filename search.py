#Functional module for searching for best AOI in parcel
import numpy as np
import tifffile as tiff
from scipy.ndimage import rotate
import scipy
from scipy import ndimage
import time
import cv2
import matplotlib.pyplot as plt
from operator import itemgetter

# Check if target has enough positive area to fit an AOI.
def sizeCheck(minAcres,maxAcres,img):

    # Convert acres to meters-squared.
    convFactor = 0.000247105381467165
    minM = round(minAcres/convFactor)
    maxM = round(maxAcres/convFactor)

    # Return the area of positive cells from scored parcel.
    totalArea = (np.sum(img!=-1))
    areaCount = (np.sum(img>0))
    if areaCount >= maxM:
        useable = True

    # Reset maxM as the parcel size if parcel within bounds.
    elif areaCount < maxM and areaCount >= minM:
        useable = True
        maxM = areaCount
    elif areaCount < maxM and areaCount < minM:
        useable = False
    if totalArea >= 500/convFactor:
        useable = False
    return useable,minM,maxM

# Input score parcel, return the primary rotation of the parcel.
def rotationCheck(img):
    shapes = {}
    for r in range(0,90,5):
        rotated = rotate(img,r,reshape=True, mode='constant', cval=-1)
        rotated[rotated<0]=0
        rotated = rotated[~np.all(rotated==0, axis=1)]
        rotated = rotated[:,~np.all(rotated==0, axis=0)]
        size = rotated.shape[0]*rotated.shape[1]
        shapes.update({r:size})
    return min(shapes, key=shapes.get)

# Input scored parcel and degree, return rotated scored image.
def rotateImg(rotation,img,dividers):

    # All reshaped boundaries are given value of -1.
    rotated = rotate(img,rotation,reshape=True, mode='constant', cval=-1)

    # Also rotate dividers to same primary rotation value.
    rotatedDiv = rotate(dividers,rotation,reshape=True)
    rowsEnd = rotated.shape[0]
    columnsEnd = rotated.shape[1]
    columnsStart = 0  # Starting place for Top Left x
    rowsStart = 0  # Starting place for Top Left y
    return rotated,columnsStart,columnsEnd,rowsStart,rowsEnd,rotatedDiv

# Determine if rectangle contains enough usable area. Used to filter sites before processing.
def calculateSize(height,width,TLr,BRr,TLc,BRc,minM,maxM,img):

    # Shape is checked to prevent over-long AOIs.
    area = (height*width)
    if (width/height)>0.2 and (height/width)>=0.2 and area>=minM and area<=1.0*maxM:

        # Only positive pixels are counted as viable area.
        newMatrix = img[TLr:BRr,TLc:BRc]
        tempMatrix = newMatrix[~np.all(newMatrix<=0, axis=1)]
        tempMatrix = tempMatrix[:,~np.all(tempMatrix<=0, axis=0)]
        if tempMatrix.shape!=newMatrix.shape:
            return False
        useableArea = np.sum(newMatrix>0)
        if useableArea>=minM and useableArea<=maxM:
            return newMatrix
        else:
            return False
    else:
        return False

# Create an array with dividing factors(roads,water,rails,etc).
def createDivider(dividers,TLr,BRr,TLc,BRc):

    # Extract matrix from same coordinates as searching rectangle returned from iterateCorners.
    contMatrix = dividers[TLr:BRr,TLc:BRc]
    contMatrix[contMatrix==0]=-1
    contMatrix[contMatrix<-1]=-1
    contMatrix = (contMatrix!=-1).astype(float)
    # kernel = np.ones((3,3),np.uint8)/9
    # for i in range(5):
    #     contMatrix = cv2.filter2D(contMatrix,-1,kernel)
    contMatrix[contMatrix>0]=1
    return contMatrix

# Determine the number and size of usable blobs in a viable searching rectangle.
# Only return if the largest blob is of usable area.
def calculateBlobs(contMatrix,minM,maxM):

    # Create separated blobs.
    blobs,numBlobs = ndimage.label(contMatrix)

    # Create empy dict to record blob sizes.
    blobAreas = {}

    for n in range(numBlobs+1):
        blobArea = np.sum(blobs==n)
        blobAreas[n]=blobArea

    # If multiple blobs exist, the blob representing out-of-bounds or dividers pixels is removed.
    if len(blobAreas)>1:
        del blobAreas[0]

    # The blob with the highest score is checked against the AOI size parameters.
    bestBlob = max(blobAreas,key=blobAreas.get)
    if blobAreas[bestBlob]>=minM and blobAreas[bestBlob]<=maxM:
        # print(blobAreas,bestBlob)
        blobs[blobs!=bestBlob]=0
        blobs[blobs!=0]=1
        return blobs
    else:
        return False

# Checks how rectangular and whole the aoi is.
def rectCheck(checkMatrix):
    tempMatrix = checkMatrix[~np.all(checkMatrix<=0, axis=1)]
    tempMatrix = tempMatrix[:,~np.all(tempMatrix<=0, axis=0)]
    if tempMatrix.shape!=checkMatrix.shape:
        return np.zeros((1,1))
    ratio = np.sum(checkMatrix>0)/(checkMatrix.shape[0]*checkMatrix.shape[1])
    threshold = 0.30
    if ratio>=threshold:
        factor = ((ratio-threshold)/(1.0-threshold))*(1.0-0.8)+0.8
        tempMatrix[tempMatrix>0]*=factor
        return tempMatrix
    else:
        return np.zeros((1,1))

# Check the sum of the largest blob, compare against the previous best sums.
def checkSum(blobs,newMatrix,minM,maxM,placeSum,placeMatrix):
    checkMatrix = np.ma.masked_where(blobs!=1,newMatrix)
    checkMatrix = checkMatrix.filled(0)
    useableArea = np.sum(checkMatrix>1)

    checkMatrix[checkMatrix<=0]=0

    if useableArea>=minM and useableArea<=maxM:
        checkMatrix = rectCheck(checkMatrix)
        tempSum=checkMatrix.sum()
        # print(tempSum)
        if tempSum > placeSum:
            return tempSum,checkMatrix,True
        else:
            return placeSum,placeMatrix,False
    else:
        return placeSum,placeMatrix,False

# Iterate through all possible TopLeft (TL) and BottomRight (BR) corners.
def iterateCorners(rowsStart,columnsStart,rowsEnd,columnsEnd,minM,maxM,dividers,rotation,img):
    placeSum = 0
    placeMatrix = 0
    for TLr in range(rowsStart,rowsEnd-30,70):
        for TLc in range(columnsStart,columnsEnd-10,70):

            # Mandatory 30m height and 10m width to allow for minimum unit size.
            # If search area is not of viable size, blobs are not created and score is not recorded.
            for BRr in range(TLr+30,rowsEnd,70):
                for BRc in range(TLc+10,columnsEnd,70):
                    height=BRr-TLr
                    width=BRc-TLc
                    if height>=30 and width>=10:
                        newMatrix = calculateSize(height,width,TLr,BRr,TLc,BRc,minM,maxM,img)

                        # Positive pixels in search area divided into contiguous blobs for individual scoring.
                        if type(newMatrix)==np.ndarray:
                            contMatrix = createDivider(dividers,TLr,BRr,TLc,BRc)
                            blobs = calculateBlobs(contMatrix,minM,maxM)

                            # Individual blob score recorded.
                            if type(blobs)==np.ndarray:
                                # print('Valid for checking')
                                placeSum,placeMatrix,check = checkSum(blobs,newMatrix,minM,maxM,placeSum,placeMatrix)

# Combines all previous helper functions.
def parcelSearch(img,dividers,minAcres,maxAcres):

    # Check if parcel is large enough to hold AOI
    useable,minM,maxM = sizeCheck(minAcres,maxAcres,img)
    results = []

    # Check positive score of every blob, in every searching rectangle, of every rotation.
    # Optimal score, coordinates, and rotation returned for .shp file generation.
    if useable == True:
        startRot = rotationCheck(img)
        rotations = [startRot,startRot+15,startRot+30,startRot+45,startRot+60,startRot+75]
        for r in rotations:
            img01 = img
            if r == startRot:
                img01 = np.where(img01<=0,img01,1.07*img01)
            rotated,columnsStart,columnsEnd,rowsStart,rowsEnd,rotatedDiv =(rotateImg(r,img01,dividers))
            results.append(iterateCorners(rowsStart,columnsStart,rowsEnd,columnsEnd,minM,maxM,rotatedDiv,r,rotated))
        try:
            # print(max(results,key=itemgetter(0))[:])
            return max(results,key=itemgetter(0))[:]
        except TypeError:
            # print('Search return error')
            return False
    else:
        # print('Search return error')
        return False
                                                                                                                       