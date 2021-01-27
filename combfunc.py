# Combine all functions for AOI generation
import score
import search
import write
import time
import tifffile as tiff
import os
from multiprocessing import Pool
import pandas as pd
import tqdm
import sys

# Timer
t0 = time.time()

county = sys.argv[1]


def main(i):
    # Minimum acceptable AOI acreage
    minAcres = 20
    # Maximum acceptable AOI acreage
    maxAcres = 40

    # Retrieve directory holding input rasters from score.getSourceDir.
    srcDir = score.getSourceDir('{}'.format(county))

    # Set/create output directory for resulting .shp file and .csv.
    resultsDir = os.path.join(srcDir, 'results')
    if os.path.isdir(resultsDir) == False:
        os.mkdir(resultsDir)
    outDir = os.path.join(srcDir, 'results/dir/')

    # Retrieve composite score and water mask raster from score.scoreParcel.
    scoreIMG, dtw = score.scoreParcel('{}'.format(county), i, minAcres, maxAcres)


    try:
        # Retrieve best AOI score sum, bounds, and rotation from search.parcelSearch.
        sum, TLc, TLr, BRc, BRr, rotation, placeMatrix = search.parcelSearch(scoreIMG, dtw, minAcres, maxAcres)

        if sum > 0: # Viable AOI exists.
            # Use non-negative raster for .shp creation.
            img = tiff.imread(os.path.join(srcDir, '{}_slope/{}'.format(county, i)))
            overlay = write.overlay(img, TLc, TLr, BRc, BRr, rotation, placeMatrix)
            masked = write.mask(img, write.convolve(write.reshape(img, overlay)))
            write.projectWrite(outDir, masked, srcDir, i, sum, county)
            return [i, sum, TLc, TLr, BRc, BRr, rotation]

        else:   # No viable AOI exists.
            return [i, 0, 0, 0, 0, 0, 0]

    except: # Parcel is of unsuitable size.
        return [i, 0, 0, 0, 0, 0, 0]


if __name__ == '__main__':
    srcDir = score.getSourceDir('{}'.format(county))
    imgList = score.getImgList(srcDir, county)
    pool = Pool(processes=9)
    r = list(tqdm.tqdm(pool.imap(main, imgList), total=len(imgList)))
    df = pd.DataFrame(r, columns=['Name', 'Sum', 'TLc', 'TLr', 'BRc', 'BRr', 'Rotation'])
    df.to_csv(r'C:\AOI_Gen\pennsylvania\{}\results\dir.csv'.format(county), index=None, header=True)
    t1 = time.time()
    print('Time elapsed:', t1 - t0)
