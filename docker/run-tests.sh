#!/bin/bash

######################################
# One of the simplest way to use remote docker server over ssh is to use it:
# export DOCKER_HOST=ssh://user@remote-host
# Also see PYTEST_ARGS env var

set -e

usage()
{
	echo "Usage: run-tests.sh <LINUX DISTRIBUTIVE NAME> [\"list of python versions\"]"
	echo "Examples:"
	echo "   run-tests.sh debian"
	echo "   run-tests.sh debian \"3.6 3.7\""
}

if (( $# == 0 )); then
	usage
	exit
fi

USERNAME=zenmake

declare -A PYVERS_MAP=(
    ["3.6"]="3.6.15"
    ["3.7"]="3.7.13"
    ["3.8"]="3.8.14"
    ["3.9"]="3.9.14"
    ["3.10"]="3.10.10"
    ["3.11"]="3.11.6"
    ["3.12"]="3.12.0"
)

DIST="$1"
PY_TO_TEST="$2"
if [[ -z $PY_TO_TEST ]]; then
    PY_TO_TEST="system"
fi
PY_TO_TEST=($PY_TO_TEST)

case $DIST in
    debian)
        BASE_DIST_NAME="debian"
        #BASE_IMAGE="debian:buster-20210511-slim"
        BASE_IMAGE="debian:bullseye-20230320-slim"
        # debian buster has system python 3.7
        #SYSTEM_PY_VER="3.7"
        # debian bullseye has system python 3.9
        SYSTEM_PY_VER="3.9"
    ;;
    ubuntu)
        BASE_DIST_NAME="debian"
        #BASE_IMAGE="ubuntu:20.04"
        #BASE_IMAGE="ubuntu:focal-20210416"
        BASE_IMAGE="ubuntu:jammy-20230308"
        # ubuntu:20.04 has system python 3.8
        #SYSTEM_PY_VER="3.8"
        # ubuntu:22.04 has system python 3.10
        SYSTEM_PY_VER="3.10"
    ;;
    centos)
        BASE_DIST_NAME="centos"
        BASE_IMAGE="centos:centos8.4.2105"
        # centos 8 has system python 3.6
        SYSTEM_PY_VER="3.6"
    ;;

    *)
    echo "Unknown/unsupported linux name \"$DIST\""
    exit 1
    ;;
esac

unset PYVERS_MAP["$SYSTEM_PY_VER"]

# It better to have sorted list otherwise cache of docker can be invalidated unexpectedly
PYENV_VERS=( $(for ver in ${PYVERS_MAP[@]}; do echo $ver; done | sort) )
PYENV_VERS="${PYENV_VERS[@]}"

PROJECT_ROOT=".."
CI_IMAGE_TAG="zenmake/${DIST}-ci:latest"

# a value greater or less than the default of 1024 to increase or reduce the container’s weight
# this is a soft limit
#BUILD_CPU_SHARES=${BUILD_CPU_SHARES:-1024}
BUILD_CPU_SHARES=${BUILD_CPU_SHARES:-500}

#docker build --cpu-shares=$BUILD_CPU_SHARES --target full-package \
#            -f ./"${BASE_DIST_NAME}-ci.Dockerfile" \
#            --build-arg USERNAME="${USERNAME}" \
#            --build-arg BASE_IMAGE="${BASE_IMAGE}" \
#            --build-arg PYENV_VERS="${PYENV_VERS}" \
#            -t $CI_IMAGE_TAG $PROJECT_ROOT

docker build --cpu-shares=$BUILD_CPU_SHARES \
            -f ./"${BASE_DIST_NAME}-ci.Dockerfile" \
            --build-arg USERNAME="${USERNAME}" \
            --build-arg BASE_IMAGE="${BASE_IMAGE}" \
            --build-arg PYENV_VERS="${PYENV_VERS}" \
            -t $CI_IMAGE_TAG $PROJECT_ROOT

#if (( $? != 0 )); then
#    echo "docker build failed or interrupted"
#    exit
#fi

# https://github.com/fabric8io/docker-maven-plugin/issues/501
docker image prune -f

# a value greater or less than the default of 1024 to increase or reduce the container’s weight
# this is a soft limit
RUN_CPU_SHARES=${RUN_CPU_SHARES:-500}

PYTEST_ARGS_EXTRA=${PYTEST_ARGS_EXTRA:-""}
#PYTEST_ARGS=${PYTEST_ARGS:-"tests -v --maxfail=1 -k "codegen""}
PYTEST_ARGS=${PYTEST_ARGS:-"tests -v --maxfail=1 $PYTEST_ARGS_EXTRA"}

for ver in ${PY_TO_TEST[@]}; do
    if [[ $ver == $SYSTEM_PY_VER ]]; then
        ver="system"
    fi
    actualver="system"
    if [[ $ver != "system" ]]; then
        actualver=${PYVERS_MAP["$ver"]}
        if [[ -z "$actualver" ]]; then
            echo "Unknown/unsupported python version \"$ver\""
            exit
        fi
    fi

    docker run -it --rm \
        --cpu-shares=$RUN_CPU_SHARES \
        --env PYENV_VERSION=$actualver \
        --env PYTEST_ARGS="${PYTEST_ARGS}" \
        $CI_IMAGE_TAG # docker/run-tests-from-inside.sh
done
