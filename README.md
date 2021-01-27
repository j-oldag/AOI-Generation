# AOI-Generation
Find optimal area within parcel.

### Required Input Rasters
- Landcover
- Slope, in degrees
- Aspect
- Proximity to Building Footprints (DTB)
- Proximity to 3-Phase Lines (DT3P)
- Proximity to Roads (DTR)
- Proximity to Water/Wetlands (DTW)
- Proximity to Parcel Boundaries (DTP)

Proximity rasters are best created with GDAL_Proximize.


### To Execute
- Create raster inputs from vector data; use gdal_funcs.py
- Split raster inputs into passabel parcels; use rasterSplit.py
- Score and search parcels, output viable AOIs; use combfunc.py
