##########################################################################
#########  Base image
# It is better not to use official python images because default python is
# configured (symlinked) to python3 in these images while in original debian/ubuntu
# it is not so by default and such compatibility feature will not be tested.
# Another reason not to use official python images is because there are no
# python images based on ubuntu at the moment of writing.

ARG DMD_VER="2.096.1"
ARG DMD_VERNAME="dmd-$DMD_VER"
#ARG PYENV_VERS="3.5.9 3.6.10 3.7.9 3.8.8 3.9.2"

ARG BASE_IMAGE=debian:10
FROM $BASE_IMAGE AS base

ARG USERNAME=zenmake

ENV DEBIAN_FRONTEND noninteractive
ENV LANG='C.UTF-8'

ENV PYENV_ROOT="/home/$USERNAME/.pyenv"
ENV PATH="$PYENV_ROOT/bin:$PATH"

ARG DMD_PATH="/home/$USERNAME/dmd"

SHELL ["/bin/bash", "-c"]

RUN useradd -m -G users $USERNAME

##########################################################################
#########  Make image with pyenv and selected python versions
FROM base AS pyenv-pythons

ENV PYBUILD_DEPS="build-essential libssl-dev zlib1g-dev libbz2-dev \
            libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev \
            xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev \
            libncursesw5-dev python-openssl git ca-certificates"

RUN apt-get -y update \
    && apt-get -y --no-install-recommends install $PYBUILD_DEPS \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /usr/share/doc/* \
    && rm -rf /tmp/* /var/tmp/* \
    && true

# global var
ARG PYENV_VERS

USER $USERNAME
RUN curl https://pyenv.run | bash \
    #&& export PYTHON_CONFIGURE_OPTS="--enable-optimizations --enable-shared \
    #                     -enable-option-checking=fatal --without-ensurepip" \
    #&& export PYTHON_MAKE_OPTS="LDFLAGS=\"-Wl,--strip-all\"" \
    && echo $PYENV_VERS | xargs -n 1 pyenv install -s -v \
    && find "$PYENV_ROOT/versions" -depth \
        \( \
            \( -type d -a \( -name test -o -name tests -o -name idle_test \) \) \
            -o \( -type f -a \( -name '*.pyc' -o -name '*.pyo' -o -name '*.a' \) \) \
        \) -exec rm -rf '{}' + \
    \
    && true

USER root

##########################################################################
#########  Make image with DMD
FROM base AS dmd

# global var
ARG DMD_VERNAME

ENV DMD_INSTALL_PKG_DEPS="ca-certificates gpg xz-utils curl"

RUN apt-get -y update \
    && apt-get -y --no-install-recommends install $DMD_INSTALL_PKG_DEPS \
    && curl -fsS https://dlang.org/install.sh | bash -s $DMD_VERNAME -p $DMD_PATH \
    && apt-get --purge -y remove $DMD_INSTALL_PKG_DEPS \
    && rm -fr $DMD_PATH/$DMD_VERNAME/{html,man,samples} \
    && rm -fr $DMD_PATH/$DMD_VERNAME/linux/{bin32,lib32} \
    # hack to solve the problem with very slow chmod/chown in docker
    && find $DMD_PATH/$DMD_VERNAME/ -not -user $USERNAME -print0 | \
        xargs -P 0 -0 --no-run-if-empty chown --no-dereference $USERNAME:$USERNAME \
    \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /usr/share/doc/* \
    && rm -rf /tmp/* /var/tmp/* \
    && true

##########################################################################
#########  Final configuration for all python environments
FROM base AS full-package

WORKDIR /home/$USERNAME/
COPY --from=pyenv-pythons --chown=$USERNAME:$USERNAME $PYENV_ROOT $PYENV_ROOT
COPY --from=dmd --chown=$USERNAME:$USERNAME $DMD_PATH $DMD_PATH
COPY ./tests/deb-deps.txt .

# install zenmake deps for tests on system python and toolchain system packages

RUN apt-get -y update \
    \
    && apt-get -y --no-install-recommends install python3 python3-pip \
#    && update-alternatives --install /usr/bin/python python /usr/bin/python3 1 \
#    && pip3 install --no-cache-dir --upgrade pip \
    && find "/usr/lib" -depth \
        \( \
            \( -type d -a \( -name test -o -name tests -o -name idle_test \) \) \
            -o \( -type f -a \( -name '*.pyc' -o -name '*.pyo' -o -name '*.a' \) \) \
        \) -exec rm -rf '{}' + \
    \
    # just to test with installed system pyyaml
    && apt-get -y --no-install-recommends install python3-yaml \
    \
    # install toolchains
    && ZMTESTS_PKG_DEPS=`cat deb-deps.txt` \
    && apt-get -y --no-install-recommends install $ZMTESTS_PKG_DEPS \
    \
    && apt-get --purge -y autoremove \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /usr/share/doc/* \
    && rm -rf /tmp/* /var/tmp/* \
    && true

COPY ./tests/requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# global var
ARG PYENV_VERS

# finish setup of pyenv and install zenmake python deps for tests on pyenv pythons
USER $USERNAME
RUN true \
    #&& echo "eval \"\$(pyenv init --path)\"" >> ~/.bashrc \
    #&& eval "$(pyenv init --path)" \
    && PATH="$PYENV_ROOT/shims:$PATH"; for ver in "$PYENV_VERS"; do \
           pyenv global $ver; \
           pip3 install --no-cache-dir -r requirements.txt; \
       done \
    && pyenv global system \
    && true

USER root

# apply DMD paths

# global var
ARG DMD_VERNAME
ENV PATH="$DMD_PATH/$DMD_VERNAME/linux/bin64:$PATH"
ENV LIBRARY_PATH="$DMD_PATH/$DMD_VERNAME/linux/lib64:$LIBRARY_PATH"
ENV LD_LIBRARY_PATH="$DMD_PATH/$DMD_VERNAME/linux/lib64:$LD_LIBRARY_PATH"

##########################################################################
########## Test all

FROM full-package AS zenmake-tests
USER $USERNAME
WORKDIR /home/$USERNAME/prj
# copy all the files to the container
COPY --chown=$USERNAME:$USERNAME . .

ENV PYENV_VERSION="system"
#CMD ["./docker/run-tests-from-inside.sh"]
#CMD ["pytest", "tests", "-v", "--maxfail=1"]