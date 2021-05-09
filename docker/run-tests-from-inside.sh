#!/bin/bash

# detect right directory and go into it
cd "$( dirname "$(realpath ${BASH_SOURCE[0]:-$0})" )/.."

PYENV_VERSION=${PYENV_VERSION:-system}

if [[ "$PYENV_VERSION" != "system" ]]; then
    # "pyenv init" doesn't look as a stable thing
    # for example I got this in 2 days after creation of this script:
    # WARNING: `pyenv init -` no longer sets PATH.
    #eval "$(pyenv init --path)"
    export PATH="$PYENV_ROOT/shims:$PATH"
fi

pytest tests -v --maxfail=1
