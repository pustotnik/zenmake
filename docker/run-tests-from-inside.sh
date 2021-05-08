#!/bin/bash

# detect right directory and go into it
cd "$( dirname "$(realpath ${BASH_SOURCE[0]:-$0})" )/.."

PYENV_VERSION=${PYENV_VERSION:-system}

if [[ "$PYENV_VERSION" != "system" ]]; then
    eval "$(pyenv init -)"
fi

pytest tests -v --maxfail=1
