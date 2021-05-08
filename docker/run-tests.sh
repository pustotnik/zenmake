#!/bin/bash

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

declare -A PYVERS=(
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

case $DIST in
    debian)
        DOCKERF_PREFIX="debian"
        #BASE_IMAGE="debian:buster"
        BASE_IMAGE="debian:buster-slim"
        # debian buster has system python 3.7
        unset PYVERS["3.7"]
    ;;
    ubuntu)
        DOCKERF_PREFIX="debian"
        BASE_IMAGE="ubuntu:20.04"
        # ubuntu:20.04 has system python 3.8
        unset PYVERS["3.8"]
    ;;

    *)
    echo -n "Unknown/unsupported linux name \"$DIST\""
    exit
    ;;
esac

# It better to have sorted list otherwise cache of docker can be invalidated unexpectedly
PYENV_VERS=( $(for ver in ${PYVERS[@]}; do echo $ver; done | sort) )
PYENV_VERS="${PYENV_VERS[@]}"

PROJECT_ROOT=".."
BASE_IMAGE_TAG="zenmake/${DIST}-ci:latest"

#docker build --target full-package \
#            -f ./"${DOCKERF_PREFIX}-ci.Dockerfile" \
#            --build-arg BASE_IMAGE="${BASE_IMAGE}" \
#            --build-arg PYENV_VERS="${PYENV_VERS}" \
#            -t $BASE_IMAGE_TAG $PROJECT_ROOT

docker build \
            -f ./"${DOCKERF_PREFIX}-ci.Dockerfile" \
            --build-arg BASE_IMAGE="${BASE_IMAGE}" \
            --build-arg PYENV_VERS="${PYENV_VERS}" \
            -t $BASE_IMAGE_TAG $PROJECT_ROOT

if [[ $? -ne 0 ]]; then
    echo "docker build failed or interrupted"
    exit
fi

# https://github.com/fabric8io/docker-maven-plugin/issues/501
docker image prune -f

PY_TO_TEST=($PY_TO_TEST)
for ver in ${PY_TO_TEST[@]}; do
    if [[ "$ver" != "system" ]]; then
        actualver=${PYVERS["$ver"]}
        if [[ -z "$actualver" ]]; then
            echo "Unknown/unsupported python version \"$ver\""
            exit
        fi
    fi

    docker run -it --rm \
        --env PYENV_VERSION=$actualver \
        $BASE_IMAGE_TAG docker/run-tests-from-inside.sh
done
