
import sys
from os import path

ZENMAKE_DIR = path.dirname(path.abspath(__file__))
ZENMAKE_DIR = path.normpath(path.join(ZENMAKE_DIR, path.pardir, 'src', 'zenmake'))

if ZENMAKE_DIR not in sys.path:
    sys.path.insert(1, ZENMAKE_DIR)

# for test 'testLoadPyModule()'
something = 'qaz'