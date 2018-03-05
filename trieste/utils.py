import astropy.io.fits as fits
import trieste as tr


def metadata_to_fits_header(metadata):
    """
    Reads a trieste metadata dictionary and converts it to a FITS header. If the metadata contains a keyword called
    "fits_comments", then only the keywords stored in `metadata['fits_comments'].keys()` will be stored in the FITS
    header.
    :param metadata: A Trieste metadata dictionary
    :return: A FITS header containing the metadata.
    """
    if "fits_comments" in metadata.keys():
        # only store the FITS header information
        comments = metadata['fits_comments']
        header_entries = [(key, metadata[key], comments[key]) for key in comments.keys()]
    else:
        header_entries = [(k, metadata[k], '') for k in metadata.keys() if type(metadata[k]) in (str, int, float)]

    return fits.Header(header_entries)


def fits_header_to_metadata(header):
    """
    Reads a FITS header and converts it to a Trieste metadata dictionary.
    :param header:
    :return: a Trieste metadata dictionary.
    """
    comments = header.comments
    metadata = {item[0]: item[1] for item in header.items()}
    fits_comments = {key: comments[key] for key in header.keys()}
    metadata['fits_comments'] = fits_comments
    return metadata


def fits_to_collection(hdulist):
    """Converts a FITS HDUList containing multiple related images to a Trieste Collection"""

    if isinstance(hdulist, str):
        # the user provided the filename. Open the file:
        hdulist = fits.open(hdulist)

    if not isinstance(hdulist, fits.HDUList):
        raise TypeError("The hdulist must be either a fits.HDUlist or the name of a FITS file.")

    collection_metadata = fits_header_to_metadata(hdulist[0].header)

    objects = []
    for i, layer in enumerate(hdulist):
        if i > 0:
            metadata = fits_header_to_metadata(layer.header)
            if 'EXTNAME' in metadata.keys():
                array_name = metadata['EXTNAME']
            else:
                array_name = f"layer_{i}"
            array = tr.Array(layer.data, array_name, metadata)
            objects.append(array)

    return tr.Collection(objects, hdulist.filename(), collection_metadata)


def collection_to_fits(collection):
    """Converts a Trieste Collection of related images to a FITS HDUList."""
    fits_header = metadata_to_fits_header(collection.metadata)

    hdus = [fits.PrimaryHDU(header=fits_header)]

    for object in collection:
        header = metadata_to_fits_header(object.metadata)
        data = object.data
        hdu_image = fits.ImageHDU(data, header)
        hdus.append(hdu_image)

    return fits.HDUList(hdus)
