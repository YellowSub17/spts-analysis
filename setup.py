#!/usr/bin/env python3

import sys, os
from setuptools import setup, Extension, find_packages
import numpy

this_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(this_dir + "/spts/data")

setup(
    name='spts',
    version='0.0.2',
    description='SPTS',
    long_description='SPTS - Single Particle Tracking and Sizing',
    author='Hantke, Max Felix', 
    author_email='hantke@xray.bmc.uu.se',
    license='BSD',

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Physics',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.13',
    ],

    packages=find_packages(),

    package_data={
        '': [
            'gui/ui/*.ui',
            'gui/spts_default.conf'
        ]
    },

    install_requires=[
        'numpy',
        'scipy',
        'h5py',
        'h5writer',
        'mulpro>=0.1.3'
    ],

    extras_require={
        'mpi': 'mpi4py>=1.3.1',
        'gui': ['PyQt4', 'pyqtgraph']
    },

    ext_modules=[
        Extension(
            "spts.denoise",
            sources=["spts/denoise_module.cpp"],
            include_dirs=[numpy.get_include()],
            define_macros=[("NPY_NO_DEPRECATED_API", "NPY_1_7_API_VERSION")],
            extra_compile_args=["-std=c++14"],
        ),
        Extension(
            "spts.utils.fj",
            sources=["spts/utils/fj/fj_module.cpp"],
            include_dirs=[numpy.get_include()],
            define_macros=[("NPY_NO_DEPRECATED_API", "NPY_1_7_API_VERSION")],
            extra_compile_args=["-std=c++14"],
        ),
    ],

    scripts=[
        this_dir + "/spts/scripts/" + s
        for s in os.listdir(this_dir + "/spts/scripts/")
        if ((s.endswith(".py") or s.endswith(".sh")) and not s.startswith("."))
    ],
)
