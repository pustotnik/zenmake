#!/bin/bash

set -ex

if [[ $CACHE_INDY_HIT == "true" ]]; then
    echo "Qt is already installed"
    exit
fi

python -m pip install --upgrade pip
python -m pip install --upgrade aqtinstall
# there is no win64_msvc2019_64 for Qt 5.12.12
aqt install-qt --outputdir C:/Qt windows desktop 5.15.2 win64_msvc2019_64
aqt install-qt --outputdir C:/Qt windows desktop 5.15.2 win64_mingw81
# aqt install-qt --outputdir C:/Qt windows desktop 5.12.12 win64_msvc2017_64
