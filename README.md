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
