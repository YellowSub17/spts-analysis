#!/usr/bin/env python
import argparse
import os
import sys
import olefile
import numpy as np

from scipy.ndimage import percentile_filter
import scipy.ndimage


import os
import h5writer
import h5py
import spts
import spts.camera
from spts.camera import CXDReader
import matplotlib.pyplot as plt
import matplotlib.cm
import matplotlib.patches
from matplotlib.colors import LogNorm


def estimate_background(filename_bg_cxd, bg_frames_max, filename, read_cache=True):
    print("*************************************")
    print("*   Background correction section   *")
    print("*************************************")
    if(filename_bg_cxd is None):
        filename_bg_cxd = filename[:-4] + "_bg.cxd"
        if not os.path.isfile(filename_bg_cxd):
            print("Background file missing!")
            return None, None, None

    f_cache = filename_bg_cxd[:-4] + '_bg_' + str(bg_frames_max) + ".h5"

    if read_cache and os.path.isfile(f_cache):
        print("Reading cached background from %s" % (f_cache))
        with h5py.File(f_cache, 'r') as f:
            bg = f['bg'][:]
            bg_std = f['bg_std'][:]
            good_pixels = f['good_pixels'][:]
        print("Mean over mean background = %.0f" % (np.mean(bg)))
        print("Std dev over mean background = %.0f" % (np.std(bg)))
        return bg, bg_std, good_pixels
    print('No cached background found. Generating new cache.')

    Rbg = CXDReader(filename_bg_cxd)
    N = min([bg_frames_max, Rbg.get_number_of_frames()])
    print("Collecting %d background frames..." % (N), end='')

    frames_map = map(Rbg.get_frame, [i for i in range(N)])

    bg_stack = np.array(list(frames_map), dtype=np.uint16)

    bg_stack = bg_stack.transpose((1,2,0))
    print("done.")

    print("Calculating background estimate by mean of buffer...", end='')
    bg = np.mean(bg_stack, axis=2)
    bg_std = np.std(bg_stack, axis=2)

    # Use the standard deviation of the 50% middle values to find
    # bad pixels
    sort_bg = np.sort(bg.flatten())
    middle_bg = sort_bg[round(len(sort_bg)/4):-round(len(sort_bg)/4)]
    middle_std = np.std(middle_bg)
    good_pixels = bg < np.mean(middle_bg)+middle_std*6
    bg *= good_pixels
    print("done.")
    print("Found %d bad pixels" % (good_pixels == 0).sum())

    print("Mean over mean background = %.0f" % (np.mean(bg)))
    print("Std dev over mean background = %.0f" % (np.std(bg)))


    print("Writing out h5...", end='')

    with h5py.File(f_cache, 'w') as f:
        f.create_dataset('bg_stack', data=bg_stack)
        f.create_dataset('bg', data=bg)
        f.create_dataset('bg_std', data=bg_std)
        f.create_dataset('good_pixels', data=good_pixels)

    print("done.")




    return bg, bg_std, good_pixels


def estimate_flatfield(flatfield_filename, ff_frames_max, bg, good_pixels, read_cache=True):
    print("*************************************")
    print("*   Flat field correction section   *")
    print("*************************************")
    if(flatfield_filename is None):
        flatfield_filename = flatfield_filename[:-4] + "_ff.cxd"
        if not os.path.isfile(flatfield_filename):
            print("Flat field file missing!")
            return None, None

    f_cache = flatfield_filename[:-4] + '_ff_' + str(ff_frames_max) + ".h5"

    if read_cache and os.path.isfile(f_cache):
        print("Reading cached flat field from %s" % (f_cache))
        with h5py.File(f_cache, 'r') as f:
            ff = f['ff'][:]
            ff_std = f['ff_std'][:]

        print("Mean over median flatfield = %.0f" % (np.mean(ff)))
        print("Std dev over median flatfield = %.0f" % (np.std(ff)))
        return ff, ff_std

    print('No cached flatfield found. Generating new cache.')




    print("Collecting flat-field frames...", end='')

    R = CXDReader(flatfield_filename)
    N = min([ff_frames_max, R.get_number_of_frames()])
    frame = R.get_frame(0)  # dtype: uint16
    if(good_pixels is None):
        print("Warning: Good pixels information is missing. Using all the pixels.")
        good_pixels = np.ones_like(frame)

    if bg is None:
        print("Warning: Background information is missing. Using median of the 1st frame as background.")
        bg = np.median(frame.flatten())


    ff_map = map(R.get_frame, [i for i in range(N)])
    ff_stack = np.array(list(ff_map), dtype=np.float32)
    # ff_stack = ff_stack.transpose((1,2,0))

    ff_stack -=bg
    ff_stack *= good_pixels

    com_map = map(scipy.ndimage.center_of_mass, ff_stack)
    com_stack = np.array(list(com_map))




    print("done")



    print("Calculating flatfield correction estimate by median of buffer... ", end='')
    ff = np.median(ff_stack, axis=0)
    ff_std = np.std(ff_stack, axis=0)
    ff_mean = np.mean(ff)
    print("done")
    print("Mean of all pixels in median flatfield = %.0f" % (ff_mean))
    print("Std dev of all pixels in median flatfield = %.0f" % (np.std(ff)))
    ff_mean_std = np.std(np.mean(ff_stack, axis=(1, 2)))
    print("Std dev across frames of flatfield mean intensity = %.0f (%.1f%%)" %
          (ff_mean_std, 100.0 * ff_mean_std/ff_mean))
    if(100.0 * ff_mean_std/ff_mean > 10):
        print("Warning: Flatfield intensity is fluctuating more than 10% across frames!")
    com_mean = scipy.ndimage.center_of_mass(ff)
    print("Center of mass of median flatfield = %.0f,%.0f" %
          (com_mean[0], com_mean[1]))
    com_std = np.std(com_stack, axis=0)
    print("Center of mass std dev of flatfield = %.0f,%.0f" %
          (com_std[0], com_std[1]))

    with h5py.File(f_cache, 'w') as f:
        f.create_dataset('ff', data=ff) #median through image axis: shape=2048x2048
        f.create_dataset('ff_std', data=ff_std) #std through image axis: shape=2048x2048



    return ff, ff_std


def guess_ROI(ff, flatfield_filename, ff_low_limit, roi_fraction):
    if(ff is None):
        print("Cannot guess ROI: flat field information missing!")
        return (slice(None), slice(None))

    ff_thres = ff.copy()
    ff_thres[ff < ff_low_limit] = 0

    ff_y = np.sum(ff_thres, axis=1)
    ff_x = np.sum(ff_thres, axis=0)

    # We'll try to include roi_fraction of the intensity in our ROI
    com = scipy.ndimage.center_of_mass(ff_y)
    com_y = round(com[0])
    y_width = 1
    while(ff_y.sum()*roi_fraction > ff_y[com_y-y_width:com_y+y_width].sum()):
        y_width += 1
    # And now we'll add some padding around
    pad = 20  # 20 px padding
    ymin = com_y - y_width - pad
    if(ymin < 0):
        ymin = 0
    ymax = com_y + y_width + pad
    if(ymax > ff.shape[0]):
        ymax = ff.shape[0]

    com = scipy.ndimage.center_of_mass(ff_x)
    com_x = round(com[0])
    x_width = 1
    while(ff_x.sum()*roi_fraction > ff_x[com_x-x_width:com_x+x_width].sum()):
        x_width += 1

    # And now we'll add some padding around
    pad = 20  # 20 px padding
    xmin = com_x - x_width - pad
    if(xmin < 0):
        xmin = 0
    xmax = com_x + x_width + pad
    if(xmax > ff.shape[1]):
        xmax = ff.shape[1]

    print("Auto cropping to y = %d:%d x = %d:%d" % (ymin, ymax, xmin, xmax))
    roi = (slice(ymin, ymax, None), slice(xmin, xmax, None))


    return roi


def cxd_to_h5(filename_cxd,  bg, ff, roi, good_pixels, filename_cxi, do_percent_filter, filt_percent, filt_frames, cropping, minx, maxx, miny, maxy, skip_raw = False):
    print("*************************************")
    print("*   Particle conversion section     *")
    print("*************************************")
    # Initialise reader(s)
    # Data
    print("Opening %s" % filename_cxd)
    R = CXDReader(filename_cxd)

    frame = R.get_frame(0)  # dtype: uint16

    if(cropping):
        roi = (slice(miny, maxy, None), slice(minx, maxx, None))
    if(good_pixels is None):
        print("Warning: Good pixels information is missing. Using all the pixels.")
        good_pixels = np.ones_like(frame)

    N = R.get_number_of_frames()
    shape = (N, frame[roi].shape[0], frame[roi].shape[1])

    if(do_percent_filter):
        four_gigabytes = 4*(1 << 30)
        if np.prod(shape)*frame.dtype.itemsize > four_gigabytes:
            gigs = np.prod(shape)*np.dtype(np.float16).itemsize/(1 << 30)
            print(
                "Warning: reading data for percentile filter will require more than %.1fG of RAM!" % gigs)

        print("Calculating percentile filter...", end='')
        data_stack = np.zeros(shape, dtype=frame.dtype)  # percent_filter stack
        for i in range(N):
            frame = R.get_frame(i)
            data_stack[i] = frame[roi]*good_pixels[roi]
        filtered_stack = percentile_filter(
            data_stack, filt_percent, size=(filt_frames, 1, 1))
        print('done.')

    # Initialise integration variables
    integrated_raw = None
    integrated_image = None
    integratedsq_raw = None
    integratedsq_image = None


    print('Generateing frames map...', end='')
    frames = map(R.get_frame, [i for i in range(N)])
    print('done.')
    for i, frame in enumerate(frames):
    # Write frames
    # for i in range(N):




        bg_corr = None
        if(do_percent_filter):
            # Replace background with percentile filter
            # Applying both a constant background correction after a percentile filter is redundant
            bg_corr = filtered_stack[i]
        elif(bg is not None):
            bg_corr = bg[roi]

        print('(%d/%d) Writing frames...' % (i+1, N), end='\r')

        # frame = R.get_frame(i)
        image_raw = frame[roi]*good_pixels[roi]

        out = {}
        out["entry_1"] = {}

        # Raw data
        if(not skip_raw):
            out["entry_1"]["data_1"] = {"data": image_raw}

        # Background-subtracted image
        if(bg_corr is not None):
            image_bgcor = ((image_raw.astype(np.float32) -
                           bg_corr.astype(np.float32)).astype(np.float32))*good_pixels[roi]
            # Save corrected data as float16 to save on space
            out["entry_1"]["image_1"] = {"data": image_bgcor.astype(np.float16)}

        # Write to disc
        W.write_slice(out)

        if integrated_raw is None:
            integrated_raw = np.zeros(shape=image_raw.shape, dtype='float32')
        if integratedsq_raw is None:
            integratedsq_raw = np.zeros(shape=image_raw.shape, dtype='float32')
        integrated_raw += np.asarray(image_raw, dtype='float32')
        integratedsq_raw += np.asarray(image_raw, dtype='float32')**2

        if(bg_corr is not None):
            if integrated_image is None:
                integrated_image = np.zeros(
                    shape=image_bgcor.shape, dtype='float32')
            if integratedsq_image is None:
                integratedsq_image = np.zeros(
                    shape=image_bgcor.shape, dtype='float32')
            integrated_image += image_bgcor
            integratedsq_image += np.asarray(image_bgcor, dtype='f')**2

    # Print newline
    print('(%d/%d) Writing frames...done.' % (N, N))
    # Write integrated images
    print('Writing integrated images...', end='')
    out = {"entry_1": {"data_1": {}, "image_1": {}}}
    if integrated_raw is not None:
        out["entry_1"]["data_1"]["data_mean"] = integrated_raw / float(N)
    if integrated_image is not None:
        out["entry_1"]["image_1"]["data_mean"] = integrated_image / float(N)
    if integratedsq_raw is not None:
        out["entry_1"]["data_1"]["datasq_mean"] = integratedsq_raw / float(N)
    if integratedsq_image is not None:
        out["entry_1"]["image_1"]["datasq_mean"] = integratedsq_image / \
            float(N)

    if bg is not None:
        out["entry_1"]["image_1"]["bg_fullframe"] = bg
        out["entry_1"]["image_1"]["bg"] = bg[roi]
    if ff is not None:
        out["entry_1"]["image_1"]["ff_fullframe"] = ff
        out["entry_1"]["image_1"]["ff"] = ff[roi]

    out["entry_1"]["image_1"]["good_pixels_fullframe"] = good_pixels
    out["entry_1"]["image_1"]["good_pixels"] = good_pixels[roi]
    out["entry_1"]["image_1"]["roi"] = [
        roi[0].start, roi[0].stop, roi[1].start, roi[1].stop]
    W.write_solo(out)
    # Close readers
    R.close()

    print("done.")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description='Conversion of CXD (Hamamatsu file format) to HDF5')
    parser.add_argument('filename', type=str, nargs='?',
                        help='CXD filename of the particle scattering data.')
    parser.add_argument('-b', '--background-filename', type=str,
                        help='CXD filename with photon background data (no injection).')
    parser.add_argument('-bn', '--bg-frames-max', type=int,
                        help='Maximum number of frames used for background calculation.', default=100)

    parser.add_argument('-f', '--flatfield-filename', type=str,
                        help='CXD filename with flat field correction (laser on paper) data.')
    parser.add_argument('-fn', '--ff-frames-max', type=int,
                        help='Maximum number of frames used for flatfield calculation.', default=100)

    parser.add_argument('-rl', '--roi-low-limit', type=int,
                        help='Miminum intensity threshold for ROI calculations from flatfield.', default=10)
    parser.add_argument('-rf', '--roi-fraction', type=int,
                        help='Fraction of intensity above threshold to include in ROI.', default=0.999)

    parser.add_argument('-m', '--percentile-filter', action='store_true',
                        help='Apply a percentile filter to output images.')
    parser.add_argument('-p', '--percentile-number', type=int,
                        help='Percentile value for percentile filter.', default=50)
    parser.add_argument('-pf', '--percentile-frames', type=int,
                        help='Number of frames in kernel for percentile filter.', default=4)

    parser.add_argument('-crop', '--crop-raw', action='store_true',
                        help='Enable manual cropping of output images. Disables auto cropping')
    parser.add_argument('-minx', '--min-x', type=int,
                        help='Minimum x-coordinate of cropped raw data.', default=0)
    parser.add_argument('-maxx', '--max-x', type=int,
                        help='Maximum x-coordinate of cropped raw data.', default=2048)
    parser.add_argument('-miny', '--min-y', type=int,
                        help='Minimum y-coordinate of cropped raw data.', default=0)
    parser.add_argument('-maxy', '--max-y', type=int,
                        help='Maximum y-coordinate of cropped raw data.', default=2048)
    parser.add_argument('-o', '--out-filename', type=str,
                        help='destination file')
    parser.add_argument('-s', '--skip-raw', action='store_true',
                        help='Skip saving the raw data, instead linking to processed data')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help="Don't show plots interactively")

    args = parser.parse_args()

    bg, bg_std, good_pixels = estimate_background(
        args.background_filename, args.bg_frames_max, args.filename)
    ff, ff_std = estimate_flatfield(
        args.flatfield_filename, args.ff_frames_max, bg, good_pixels)
    roi = guess_ROI(ff, args.flatfield_filename,
                    args.roi_low_limit, args.roi_fraction)

    if(args.filename is None):
        sys.exit(0)

    if not args.filename.endswith(".cxd"):
        print("ERROR: Given filename %s does not end with \".cxd\". Wrong format!" %
              args.filename)
        sys.exit(-1)

    if args.out_filename:
        f_out = args.out_filename
    else:
        f_out = args.filename[:-4] + ".cxi"

    # Initialise output CXI file
    W = h5writer.H5Writer(f_out)

    cxd_to_h5(args.filename, bg, ff, roi, good_pixels, W, args.percentile_filter, args.percentile_number,
              args.percentile_frames, args.crop_raw, args.min_x, args.max_x, args.min_y, args.max_y, args.skip_raw)

    # Write out information on the command used
    out = {"entry_1": {"process_1": {}}}
    out["entry_1"]["process_1"] = {"command": str(sys.argv)}
    out["entry_1"]["process_1"] = {"cwd": str(os.getcwd())}
    W.write_solo(out)
    # Close CXI file
    W.close()
    if args.skip_raw:
        h5py.File(f_out,'r+')['entry_1']['data_1']['data'] = h5py.SoftLink('/entry_1/image_1/data')
