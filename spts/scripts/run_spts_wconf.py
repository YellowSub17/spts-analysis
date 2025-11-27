#!/usr/bin/env python 
import numpy as np
import argparse
import os, sys, shutil
import time

# filenames = [f for f in os.listdir(".") if f.endswith(".cxi")]

# if len(sys.argv) > 1:
    # timestamp = sys.argv[1]
    # filenames = [filename for filename in filenames if timestamp in filename]

# for f in filenames:

c = sys.argv[1]
f = sys.argv[2]

assert c[-5:]=='.conf', 'second input should be *.conf'
assert f[-4:]=='.cxi', 'first input should be *.cxi'

n = f[:-4]


d = "./"+n+"_analysis"
if not os.path.exists(d):
    os.mkdir(d)

cmds = ["cp %s %s/spts.conf" % (c, d), "ln -s ../%s %s/frames.cxi" % (f,d), "cd %s; run_spts.py -v; cd .." % (d)]
for cmd in cmds:
    print(cmd)
    os.system(cmd)
