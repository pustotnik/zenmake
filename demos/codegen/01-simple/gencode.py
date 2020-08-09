#!/usr/bin/env python
# encoding: utf-8

import sys
import os
import random

FILE_BODY_ALL_H = """
#ifndef __ZENMAKE_TEST_GENERATED_H__
#define __ZENMAKE_TEST_GENERATED_H__

extern void foo1();
extern void foo2();
extern void foo3();
extern void foo4();

#endif
"""

FILE_BODY_FOO_C = """
#include <stdio.h>

void foo%d()
{
    printf("function foo%d\\n");
}
"""

if len(sys.argv) > 1:
    destdir = os.path.abspath(sys.argv[1])
else:
    destdir = os.getcwd()

stage = 'step1'
if len(sys.argv) > 2:
    stage = sys.argv[2]

try:
    os.makedirs(destdir)
except OSError:
    pass

def writeFooC(idx):
    num = random.randint(0, 256)
    filePath = os.path.join(destdir, 'foo_%d_%d.c' % (idx, num))
    if not os.path.isfile(filePath):
        with open(filePath, 'w') as file:
            file.write(FILE_BODY_FOO_C % (idx, idx))

if stage == 'step1':
    headerFilePath = os.path.join(destdir, 'all.h')
    if not os.path.isfile(headerFilePath):
        with open(headerFilePath, 'w') as file:
            file.write(FILE_BODY_ALL_H)
    for i in (1, 2):
        writeFooC(i)
else:
    for i in (3, 4):
        writeFooC(i)

