# AOI-Generation
Application developed to replicate and customize the ESRI Locate Regions tool (https://pro.arcgis.com/en/pro-app/latest/tool-reference/spatial-analyst/locate-regions.htm) using open source libraries. Cutting extraneous functions and enabling multiprocessing greatly decresased processing time compared to the proprietary ESRI tool.
Note - Input data layers are not provided or explicitly described. Additionally, not all key steps are provided in this repository.

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
