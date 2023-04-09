#!/bin/bash

set -ex

dnf --nodocs -y install \
    make gcc zlib-devel bzip2 bzip2-devel readline-devel sqlite \
    sqlite-devel openssl-devel tk-devel libffi-devel xz-devel git patch
