# Generate all scores layers from the DTx layers, slope, aspect, and landcover.

import tifffile as tiff
import numpy as np
from scipy import stats
from search import sizeCheck
import os
import cv2
import operator
import matplotlib.pyplot as plt
import random
import itertools

# Avoid errors for division by 0.
np.seterr(divide='ignore', invalid='ignore')
np.warnings.filterwarnings('ignore')

# Responsible for returning county directory within the state.
# Currently, the state must be edited here. This must be changed.
def getSourceDir(county):
    srcDir = 'D://new_york/{}'.format(county)
    return srcDir

# Returns the list of available tiffs, sorted from largest to smallest
# Sorting is used to make the best use of multiprocessing
def getImgList(directory,county):
    tifList = {}

    # List is derived from the tiffs in the county directory
    landcoverPath = os.path.join(directory,'{}_aspect'.format(county))
    for file in os.listdir(landcoverPath):
        if file.endswith(".tif"):
            path = os.path.join(landcoverPath,file)
            size = os.path.getsize(path)

            # Write to dictionary with file name and size
            tifList.update({file:size})

    # Remove TIFFs over a certain size; too big to work efficiently in local memory
    tifList = {key: val for key, val in tifList.items() if val <= 222767406}

    # Test random sample of parcels, uncomment the line below to use
    # tifList = dict(random.sample(tifList.items(),100))

    # Test ordered sample of parcels, uncomment the line below to use
    # tifList = dict(list(tifList.items())[0:100])

    # Sort dictionary from largest file size to smallest
    tifList = dict(sorted(tifList.items(),key=operator.itemgetter(1),reverse=True))

    # Sort dictionary from smallest size to largest
    # tifList = dict(sorted(tifList.items(),key=operator.itemgetter(1)))

    # Return ordered list of file names.
    tifList = tifList.keys()
    return tifList

# Input landcover classes tiff from DeepUNET,reclassify into scores.
def landcoverScore(landcover):
    LCs = landcover

    #Standard landcover scoring
    LCs[LCs>7]=0  # Read all errors as nodata
    LCs[LCs==1]=-1000  # Water
    LCs[LCs==2]=-1000  # Wetlands
    LCs[LCs==3]=90    # Trees
    LCs[LCs==4]=100   # Grass
    LCs[LCs==5]=100   # Barren
    LCs[LCs==6]=-1750  # Buildings
    LCs[LCs==7]=-1750   # Impervious
    return LCs

# Input Distance to Roads (DTR) tiff, return a score.
def roadScore(dtr):
    DTRs = dtr

    # Invert score to make the area closest to roads more desirable.
    DTRs = (100-(DTRs/DTRs.max())*100)

    # Reclassify out-of-bounds pixels.
    DTRs[DTRs>99.9]=-10
    return DTRs

# Input Distance to Buildings (DTB), return a score.
def buildingScore(dtb):
    DTBs = dtb

    #Reclassify out-of-bounds
    DTBs[DTBs<0]=-10

    #Positive values only start 50m away from buildings
    DTBs[DTBs>=0] -=50

    #Greatly weight areas within 20m of buildings
    DTBs[DTBs<-30]=-1000

    #Anything greater than 50m is just as good as 50m
    DTBs[DTBs>=0]=0
    return DTBs

# Input Distance to 3phase (DT3P), return a score.
def phaseScore(dt3p):
    DT3Ps = dt3p

    # Invert score to make the are closest to 3phase more desireable.
    DT3Ps = (100-(DT3Ps/DT3Ps.max())*100)

    # Reclassify out-of-bounds.
    DT3Ps[DT3Ps>99.9]=-10
    return DT3Ps

# Input Distance to Water (DTW), return a score.
def waterScore(dtw):
    DTWs = dtw

    # Reclassify out-of-bounds.
    DTWs[DTWs<0]=-10

    # Water is very bad.
    DTWs[DTWs==0]=-5000

    # If outside 9m of water, considered viable.
    DTWs[DTWs>=9]=0

    # If within 9m of water, considered inviable.
    DTWs[DTWs>0]=-5000
    return DTWs

# Input Distance to Parcel boundaries (DTP), return a score.
def boundaryScore(dtp):
    DTPs = dtp

    # Invert score to make the area closest to boundaries more desirable.
    DTPs = (100-(DTPs/DTPs.max())*100)

    # Reclassify out-of-bounds.
    DTPs[DTPs>99.9]=-10
    return DTPs

# Input Distance to Rail Roads (DTRR), return a score.
def railScore(dtrr):
    DTRRs = dtrr

    # Reclassify out-of-bounds.
    DTRRs[DTRRs<0]=-10

    # If outside 10m of rails, considered viable.
    DTRRs[DTRRs>10]=0

    # If within 10m of rails, considered inviable.
    DTRRs[DTRRs>0]=-1000
    return DTRRs

# Input Distance to Driveways (DTD), return a score.
def drivewayScore(dtd):
    DTDs = dtd

    # Reclassify out-of-bounds.
    DTDs[DTDs<0]=-10

    # If outside 10m of driveway, consider viable.
    DTDs[DTDs>10]=0

    # If within 10m of driveway, consider inviable.
    DTDs[DTDs>0]=-1000
    return DTDs

# Input Water Accumulation (ACC), return a score.
def accScore(acc):
    ACCs = acc

    # Reclassify out-of-bounds.
    ACCs[ACCs<0]=-10

    # If cell accumulates over 1000 units, consider inviable.
    ACCs[ACCs>1000]=-1000

    # If cell sccumulates less than 1000 units, consider viable.
    ACCs[ACCs>0]=0
    return ACCs

# Return a binary array of North-facing slopes.
def findNorth(asp):
    AS = asp
    north = (AS<37.5).astype(int) +  (AS>0).astype(int)
    north = (north==2).astype(int) + (AS>325.5).astype(int)
    return north

# Return a binary array of East-facing slopes.
def findEast(asp):
    AS = asp
    east = (AS>37.5).astype(int) + (AS<127.5).astype(int)
    east = (east==2).astype(int)
    return east

# Return a binary array of West-facing slopes.
def findWest(asp):
    AS = asp
    west = (AS>235.5).astype(int) + (AS<325.5).astype(int)
    west = (west==2).astype(int)
    return west

# Return a binary array of South-facing slopes.
def findSouth(asp):
    AS = asp

    #Eliminate -1 (flat) in aspect
    AS[AS<0]=180
    south = (AS<=235.5).astype(int) + (AS>=127.5).astype(int)
    south = (south==2).astype(int)
    return south

# Return a binary array of slopes under 5 degrees.
def findShallow(sl):
    SL = sl
    flat = (SL<=2.86).astype(int) + (SL>0.0).astype(int)
    flat = (flat==2).astype(int)
    return flat

# Return a binary array of slopes between 5 and 10 degrees.
def findMedium(sl):
    SL = sl
    medium = (SL<=6.84).astype(int) + (SL>2.86).astype(int)
    medium = (medium==2).astype(int)
    return medium

# Return a binary array of slopes over 10 degrees.
def findSteep(sl):
    SL = sl
    steep = (SL>6.84).astype(int)
    return steep

# Find North-facing slopes over 5, assign a negative score.
def steepNorth(north,medium,steep):
    target = north+medium+steep
    target = ((target==2).astype(int))*-5000
    return target

# Find North-facing slopes under 5, assign a moderate value.
def flatNorth(north,flat):
    target = north+flat
    target = ((target==2).astype(int))*75
    return target

# Find East and West facing slopes over 10, assign a negative value.
def steepLateral(east, west, steep):
    target = east+west+steep
    target = ((target==2).astype(int))*-5000
    return target

# Find East and West facing slopes between 5 and 10, assign a moderate value.
def mediumLateral(east,west,medium):
    target = east+west+medium
    target = ((target==2).astype(int))*75
    return target

# Find East and West facing slopes under 5, assign a strong value.
def flatLateral(east,west,medium):
    target = east+west+medium
    target = ((target==2).astype(int))*90
    return target

# Find South facing slopes over 10, assign a weak value.
def steepSouth(south,steep):
    target = south+steep
    target = ((target==2).astype(int))*-5000
    return target

# Find South facing slopes between 5 and 10, assign a strong value.
def mediumSouth(south,medium):
    target = south+medium
    target = ((target==2).astype(int))*100
    return target

# Find South facing slopes under 5, assign a strong value.
def flatSouth(south,flat):
    target = south+flat
    target = ((target==2).astype(int))*95
    return target

# Run all topo functions and combine outputs.
def topoScore(asp,sl):
    north = findNorth(asp)
    east = findEast(asp)
    west = findWest(asp)
    south = findSouth(asp)

    shallow = findShallow(sl)
    medium = findMedium(sl)
    steep = findSteep(sl)

    # Combine scores into new array portraying all topo data.
    topo=(
        steepNorth(north,medium,steep)+
        flatNorth(north,shallow)+
        steepLateral(east,west,steep)+
        mediumLateral(east,west,medium)+
        flatLateral(east,west,shallow)+
        steepSouth(south,steep)+
        mediumSouth(south,medium)+
        flatSouth(south,shallow)
        )

    #Reclassify out-of-bounds
    topo[topo==0]=-10
    return topo

#Opens tiff and checks if 'landcover' is a useable size
def openTiffs(county,imgName,minAcres,maxAcres):
    src = getSourceDir(county)

    # Rail-roads, driveways, and precipitation accumulation no longer used.
    dataDict = {
                '{}_landcover'.format(county):'',
                '{}_slope'.format(county):'',
                '{}_aspect'.format(county):'',
                'dtr':'',
                'dtb':'',
                'dt3p':'',
                'dtw':'',
                'dtp':''
                # 'dtrr':''
                # ,'dtd':''
                # ,'acc':''
                }

    # Empty lists to record any size variance among input tiffs.
    dim0 = []
    dim1 = []

    # Check if parcel contains enough viable area for an AOI
    for d in dataDict:
        dPath = os.path.join(src,'{}/{}'.format(d,imgName))
        dImg = tiff.imread(dPath).astype('float64')

        # If viable area is insufficient, return all 0's.
        if d == '{}_landcover'.format(county):
            useable,minM,maxM = sizeCheck(minAcres,maxAcres,dImg)
            if useable == False:
                return 0,0,0

        dim0.append(dImg.shape[0])
        dim1.append(dImg.shape[1])
        dataDict[d]=dImg
    dim0 = min(dim0)
    dim1 = min(dim1)
    # If viable area is sufficient, return array size.
    return dataDict,dim0,dim1

# Master function that runs previous scoring functions, resizes arrays, and combines after weighting.
def scoreParcel(county,imgName,minAcres,maxAcres):

    # Calls openTiffs to check the viable area within parcel.
    # If insufficient, scores are not calculated.
    dataDict,dim0,dim1 = openTiffs(county,imgName,minAcres,maxAcres)
    if dataDict == 0:
        totalScore = np.zeros((1,1))
        dividers = np.zeros((1,1))
        return totalScore, dividers

    # Calls scoring functions
    # Resizes by array indexing to size of smallest tiff
    # Multiplies by weight
    LC = landcoverScore(dataDict['{}_landcover'.format(county)][0:dim0,0:dim1])*0.8
    TOPO = topoScore(dataDict['{}_aspect'.format(county)][0:dim0,0:dim1],dataDict['{}_slope'.format(county)][0:dim0,0:dim1])*1.0
    DTR = roadScore(dataDict['dtr'][0:dim0,0:dim1])*0.5
    DTB = buildingScore(dataDict['dtb'][0:dim0,0:dim1])*1.5
    DT3P = phaseScore(dataDict['dt3p'][0:dim0,0:dim1])*0.8
    DTW = waterScore(dataDict['dtw'][0:dim0,0:dim1])*1.0
    DTP = boundaryScore(dataDict['dtp'][0:dim0,0:dim1])*1.0
    # rails = railScore(dataDict['dtrr'][0:dim0,0:dim1])*1.0
    # drives = drivewayScore(dataDict['dtd'][0:dim0,0:dim1])*1.0
    # acc = accScore(dataDict['acc'][0:dim0,0:dim1])*1.0

    # All scores combined
    totalScore = LC + TOPO + DTR + DTB + DT3P + DTP + DTW

    # Undesirable areas masked with negative values
    dividers = DTW + DTR
    dividers[dividers<0]=-1000
    dividers[dividers>=0]=100

    # To run with no dividers, uncomment below.
    # dividers = np.ones((dividers.shape))

    #Replace all out of bound with unique value
    totalScore[totalScore==(stats.mode(totalScore,axis=None))[0]] = -1

    # Options for sample viewing.
    # fig,ax = plt.subplots(1)
    # ax.imshow(totalScore)
    # plt.show()
    # fig,ax = plt.subplots(1)
    # ax.imshow(dividers)
    # plt.show()
    # print('\n\n\nimg shape',totalScore.shape,'dividers shape',dividers.shape)

    return totalScore,dividers
