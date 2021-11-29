#!/bin/bash

set -e

# detect right directory and go into it
cd "$( dirname "$(realpath ${BASH_SOURCE[0]:-$0})" )"

#python3 -m pytest tests -svv --maxfail=1
python3 -m pytest tests -vv --maxfail=1
