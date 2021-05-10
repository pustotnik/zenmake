#!/bin/bash

######################################
# One of the simplest way to use remote docker server over ssh is to use it:
# export DOCKER_HOST=ssh://user@remote-host 

usage()
{
	echo "Usage: run-tests.sh <LINUX DISTRIBUTIVE NAME> [\"list of python versions\"]"
	echo "Examples:"
	echo "   run-tests.sh debian"
	echo "   run-tests.sh debian \"3.5 3.7\""
}

if test $# = 0; then
	usage
	exit
fi

USERNAME=zenmake

declare -A PYVERS_MAP=(
    ["3.5"]="3.5.9"
    ["3.6"]="3.6.10"
    ["3.7"]="3.7.9"
    ["3.8"]="3.8.8"
    ["3.9"]="3.9.2"
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
        #BASE_IMAGE="debian:buster"
        BASE_IMAGE="debian:buster-slim"
        # debian buster has system python 3.7
        SYSTEM_PY_VER="3.7"
    ;;
    ubuntu)
        BASE_DIST_NAME="debian"
        BASE_IMAGE="ubuntu:20.04"
        # ubuntu:20.04 has system python 3.8
        SYSTEM_PY_VER="3.8"
    ;;

    *)
    echo -n "Unknown/unsupported linux name \"$DIST\""
    exit
    ;;
esac

unset PYVERS_MAP["$SYSTEM_PY_VER"]

# It better to have sorted list otherwise cache of docker can be invalidated unexpectedly
PYENV_VERS=( $(for ver in ${PYVERS_MAP[@]}; do echo $ver; done | sort) )
PYENV_VERS="${PYENV_VERS[@]}"

PROJECT_ROOT=".."
CI_IMAGE_TAG="zenmake/${DIST}-ci:latest"

#docker build --target full-package \
#            -f ./"${BASE_DIST_NAME}-ci.Dockerfile" \
#            --build-arg USERNAME="${USERNAME}" \
#            --build-arg BASE_IMAGE="${BASE_IMAGE}" \
#            --build-arg PYENV_VERS="${PYENV_VERS}" \
#            -t $CI_IMAGE_TAG $PROJECT_ROOT

# a value greater or less than the default of 1024 to increase or reduce the container’s weight
#CPU_SHARES=1024
CPU_SHARES=900
docker build --cpu-shares=$CPU_SHARES \
            -f ./"${BASE_DIST_NAME}-ci.Dockerfile" \
            --build-arg USERNAME="${USERNAME}" \
            --build-arg BASE_IMAGE="${BASE_IMAGE}" \
            --build-arg PYENV_VERS="${PYENV_VERS}" \
            -t $CI_IMAGE_TAG $PROJECT_ROOT

if [[ $? -ne 0 ]]; then
    echo "docker build failed or interrupted"
    exit
fi

# https://github.com/fabric8io/docker-maven-plugin/issues/501
docker image prune -f

for ver in ${PY_TO_TEST[@]}; do
    if [[ "$ver" == "$SYSTEM_PY_VER" ]]; then
        ver="system"
    fi
    actualver="system"
    if [[ "$ver" != "system" ]]; then
        actualver=${PYVERS_MAP["$ver"]}
        if [[ -z "$actualver" ]]; then
            echo "Unknown/unsupported python version \"$ver\""
            exit
        fi
    fi
    
    docker run -it --rm \
        --env PYENV_VERSION=$actualver \
        $CI_IMAGE_TAG docker/run-tests-from-inside.sh
done
