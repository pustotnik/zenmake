#!/bin/bash

set -ex

apt-get -y --no-install-recommends install \
    build-essential libssl-dev zlib1g-dev libbz2-dev \
    libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev \
    xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev \
    libncursesw5-dev python-openssl git ca-certificates
