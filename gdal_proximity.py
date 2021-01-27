# Create raster measuring pixel distance to objects within .shp file.
# Modified from https://github.com/kubaszostak
import os.path
import sys
from osgeo import gdal

# Find current filetype of input raster.
def GetExtension(filename):
    ext = os.path.splitext(filename)[1]
    if ext.startswith('.'):
        ext = ext[1:]
    return ext

# Check if filetype is within GDAL driver library.
def DoesDriverHandleExtension(drv, ext):
    exts = drv.GetMetadataItem(gdal.DMD_EXTENSIONS)
    return exts is not None and exts.lower().find(ext.lower()) >= 0

# Uses above helper functions.
# Returns list of possible dirvers for output raster.
def GetOutputDriversFor(filename):
    drv_list = []
    ext = GetExtension(filename)
    for i in range(gdal.GetDriverCount()):
        drv = gdal.GetDriver(i)
        if (drv.GetMetadataItem(gdal.DCAP_CREATE) is not None or
            drv.GetMetadataItem(gdal.DCAP_CREATECOPY) is not None) and \
           drv.GetMetadataItem(gdal.DCAP_RASTER) is not None:
            if ext and DoesDriverHandleExtension(drv, ext):
                drv_list.append(drv.ShortName)
            else:
                prefix = drv.GetMetadataItem(gdal.DMD_CONNECTION_PREFIX)
                if prefix is not None and filename.lower().startswith(prefix.lower()):
                    drv_list.append(drv.ShortName)

    # GMT is registered before netCDF for opening reasons, but we want
    # netCDF to be used by default for output.
    if ext.lower() == 'nc' and not drv_list and \
       drv_list[0].upper() == 'GMT' and drv_list[1].upper() == 'NETCDF':
        drv_list = ['NETCDF', 'GMT']

    return drv_list

# Uses above function
# If viable driver is found, set to return output raster as geotiff.
def GetOutputDriverFor(filename):
    drv_list = GetOutputDriversFor(filename)
    ext = GetExtension(filename)
    if not drv_list:
        if not ext:
            return 'GTiff'
        else:
            raise Exception("Cannot guess driver for %s" % filename)
    elif len(drv_list) > 1:
        print("Several drivers matching %s extension. Using %s" % (ext if ext else '', drv_list[0]))
    return drv_list[0]


# Combine above helper functions.
# Creates proximized raster.
def proximityMain(source,destination):
    # Set modified function variables.
    frmt = None
    creation_options = []
    options = ['VALUES=1','NODATA=-1']
    src_filename = source
    src_band_n = 1
    dst_filename = destination
    dst_band_n = 1
    creation_type = 'Float32'
    quiet_flag = 1

    gdal.AllRegister()

    # Open source file
    src_ds = gdal.Open(src_filename)
    # Error if source file does not exist.
    if src_ds is None:
        print('Unable to open %s' % src_filename)
        sys.exit(1)

    srcband = src_ds.GetRasterBand(src_band_n)

    # Try opening the destination file as an existing file.
    try:
        driver = gdal.IdentifyDriver(dst_filename)
        if driver is not None:
            dst_ds = gdal.Open(dst_filename, gdal.GA_Update)
            dstband = dst_ds.GetRasterBand(dst_band_n)
        else:
            dst_ds = None
    except:
        dst_ds = None

    # Create output file.
    if dst_ds is None:
        if frmt is None:
            frmt = GetOutputDriverFor(dst_filename)

        drv = gdal.GetDriverByName(frmt)
        dst_ds = drv.Create(dst_filename,
                            src_ds.RasterXSize, src_ds.RasterYSize, 1,
                            gdal.GetDataTypeByName(creation_type), creation_options)

        dst_ds.SetGeoTransform(src_ds.GetGeoTransform())
        dst_ds.SetProjection(src_ds.GetProjectionRef())

        dstband = dst_ds.GetRasterBand(1)

    # Set progress echo preferences.
    if quiet_flag:
        prog_func = None
    else:
        prog_func = gdal.TermProgress_nocb

    # Run GDAL algorithm.
    gdal.ComputeProximity(srcband, dstband, options,
                          callback=prog_func)
    srcband = None
    dstband = None
    src_ds = None
    dst_ds = None
