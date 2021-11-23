##########################################################################
#########  Global

ARG BASE_IMAGE=centos:8

ARG DMD_VER="2.096.1"
ARG DMD_VERNAME="dmd-$DMD_VER"
ARG LDC_VER="1.26.0"
ARG LDC_VERNAME="ldc-$LDC_VER"

#########  Base image
FROM $BASE_IMAGE AS base

ARG USERNAME=zenmake

ENV LANG='C.UTF-8'

ENV PYENV_ROOT="/home/$USERNAME/.pyenv"
ENV PATH="$PYENV_ROOT/bin:$PATH"

ARG DLANG_DIRPATH="/home/$USERNAME/dlang"
ARG DMD_PATH="$DLANG_DIRPATH/dmd"
ARG LDC_PATH="$DLANG_DIRPATH/ldc"

SHELL ["/bin/bash", "-c"]

RUN useradd -m -G users $USERNAME

##########################################################################
#########  Make image with pyenv and selected python versions
FROM base AS pyenv-pythons

ENV PYBUILD_DEPS="make gcc zlib-devel bzip2 bzip2-devel readline-devel sqlite \
            sqlite-devel openssl-devel tk-devel libffi-devel xz-devel\
            git"

RUN dnf --nodocs -y install $PYBUILD_DEPS \
    && dnf clean all \
    && rm -rf /var/cache/dnf /var/cache/yum \
    && rm -rf /usr/share/doc/* \
    && rm -rf /tmp/* /var/tmp/* \
    && true

# global var
ARG PYENV_VERS

USER $USERNAME
RUN curl https://pyenv.run | bash \
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
#########  Make image with D compilers
FROM base AS dlang

# global vars
ARG DMD_VERNAME
ARG LDC_VERNAME

ENV DLANG_INSTALL_PKG_DEPS="curl"

RUN dnf --nodocs -y install $DLANG_INSTALL_PKG_DEPS \
    && mkdir $DLANG_DIRPATH \
    && curl -fsS https://dlang.org/install.sh -o $DLANG_DIRPATH/install.sh \
    && chmod +x $DLANG_DIRPATH/install.sh \
    \
    && $DLANG_DIRPATH/install.sh $DMD_VERNAME -p $DMD_PATH \
    && rm -fr $DMD_PATH/$DMD_VERNAME/{html,man,samples} \
    && rm -fr $DMD_PATH/$DMD_VERNAME/linux/{bin32,lib32} \
    \
    && $DLANG_DIRPATH/install.sh $LDC_VERNAME -p $LDC_PATH \
    \
    && dnf clean all \
    && rm -rf /var/cache/dnf /var/cache/yum \
    && rm -rf /usr/share/doc/* \
    && rm -rf /tmp/* /var/tmp/* \
    && true

##########################################################################
#########  Final configuration for all python environments
FROM base AS full-package

WORKDIR /home/$USERNAME/
COPY ./tests/rpm-deps.txt .

RUN dnf --nodocs -y install python36 \
    && find "/usr/lib" -depth \
        \( \
            \( -type d -a \( -name test -o -name tests -o -name idle_test \) \) \
            -o \( -type f -a \( -name '*.pyc' -o -name '*.pyo' -o -name '*.a' \) \) \
        \) -exec rm -rf '{}' + \
    \
    # install toolchains
    && ZMTESTS_PKG_DEPS=`cat rpm-deps.txt` \
    && dnf --nodocs -y --enablerepo=powertools install $ZMTESTS_PKG_DEPS \
    \
    && dnf clean all \
    && rm -rf /var/cache/dnf /var/cache/yum \
    && rm -rf /usr/share/doc/* \
    && rm -rf /tmp/* /var/tmp/* \
    && true

COPY ./tests/requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

### complete pyenv setup

COPY --from=pyenv-pythons --chown=$USERNAME:$USERNAME $PYENV_ROOT $PYENV_ROOT

# global var
ARG PYENV_VERS

# finish setup of pyenv and install zenmake python deps for tests on pyenv pythons
USER $USERNAME
RUN true \
    && PATH="$PYENV_ROOT/shims:$PATH"; for ver in $PYENV_VERS; do \
           pyenv global $ver; \
           python -m pip install --no-cache-dir -r requirements.txt; \
       done \
    && pyenv global system \
    && true

USER root

### complete D lang setup

COPY --from=dlang --chown=$USERNAME:$USERNAME $DLANG_DIRPATH $DLANG_DIRPATH

# global vars

# prepare to avoid implication of empty vars, otherwise empty *LIBRARY_PATH
# will be considered as current (".") path by a system.
RUN if [[ -n "$LIBRARY_PATH" ]]; then LIBRARY_PATH=":$LIBRARY_PATH"; fi;\
    if [[ -n "$LD_LIBRARY_PATH" ]]; then LD_LIBRARY_PATH=":$LD_LIBRARY_PATH"; fi

ARG DMD_VERNAME
ARG LDC_VERNAME

# dmd
ENV PATH="$DMD_PATH/$DMD_VERNAME/linux/bin64:$PATH"
ENV LIBRARY_PATH="$DMD_PATH/$DMD_VERNAME/linux/lib64$LIBRARY_PATH"
ENV LD_LIBRARY_PATH="$DMD_PATH/$DMD_VERNAME/linux/lib64$LD_LIBRARY_PATH"

# ldc
ENV PATH="$LDC_PATH/$LDC_VERNAME/bin:$PATH"
ENV LIBRARY_PATH="$LDC_PATH/$LDC_VERNAME/lib:$LIBRARY_PATH"
ENV LD_LIBRARY_PATH="$LDC_PATH/$LDC_VERNAME/lib:$LD_LIBRARY_PATH"

##########################################################################
########## Test all

FROM full-package AS zenmake-tests
USER $USERNAME
WORKDIR /home/$USERNAME/prj
# copy all the files to the container
COPY --chown=$USERNAME:$USERNAME . .

ENV PYENV_VERSION="system"

# there are some problems with installing gdc on CentOS and I decided not
# to spend time on it
ENV ZENMAKE_TESTING_DISABLE_TOOL="gdc"

CMD ["./docker/run-tests-from-inside.sh"]
#CMD ["pytest", "tests", "-v", "--maxfail=1"]