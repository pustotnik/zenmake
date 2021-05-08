#!/bin/bash

# detect right directory and go into it
cd "$( dirname "$(realpath ${BASH_SOURCE[0]:-$0})" )/docs"
rm -fr ./_build/ && make html

