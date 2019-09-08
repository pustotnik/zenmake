
import sys
from os import path

ZENMAKE_ROOTDIR = path.dirname(path.abspath(__file__))
ZENMAKE_ROOTDIR = path.normpath(path.join(ZENMAKE_ROOTDIR, path.pardir, 'zenmake'))

if ZENMAKE_ROOTDIR not in sys.path:
    sys.path.insert(1, ZENMAKE_ROOTDIR)