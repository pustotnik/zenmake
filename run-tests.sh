#!/bin/bash

# detect current directory
BASEDIR=`realpath "$0"`
BASEDIR=`dirname "$BASEDIR"`
cd $BASEDIR

python -m pytest tests -svv --maxfail=1
