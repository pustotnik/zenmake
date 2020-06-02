#!/usr/bin/env python3
# coding=utf-8
#

# pylint: disable = invalid-name, missing-function-docstring

"""
Copyright (c) 2020, Alexander Magola
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import sys
import os
import subprocess
import tempfile
import shutil
import atexit
import mimetypes
import requests
import keyring

ZMDIR = os.path.dirname(os.path.abspath(__file__))
ZMDIR = os.path.abspath(os.path.join(ZMDIR, os.path.pardir))
os.chdir(ZMDIR)

REPO_OWNER = 'pustotnik'
REPO_NAME  = 'zenmake'
REPO_RELEASES_URL = 'https://api.github.com/repos/{0}/{1}/releases'.format(REPO_OWNER, REPO_NAME)

ZENMAKE_BIN_DIR = os.path.join(ZMDIR, 'src', 'zenmake')
PYTHON_EXE = sys.executable
TMP_DIR = tempfile.mkdtemp()

sys.path.append(ZENMAKE_BIN_DIR)

@atexit.register
def _removeTmpDir():
    shutil.rmtree(TMP_DIR)

def prepareAssets():
    files = []

    cmd = [PYTHON_EXE, ZENMAKE_BIN_DIR, 'zipapp', '--destdir', TMP_DIR]
    devnull = open(os.devnull, 'w')
    subprocess.call(cmd, stdout = devnull)

    from zm.zipapp import ZIPAPP_NAME
    files.append(os.path.join(TMP_DIR, ZIPAPP_NAME))
    return files

def makeAuthHeader(token):
    return { 'Authorization': 'token {0}'.format(token) }

def makeRelease(tag, token):

    ver = tag[1:] if tag[0] == 'v' else tag
    response = requests.post(
        REPO_RELEASES_URL,
        json = {
            'tag_name': tag,
            #'target_commitish': 'master',
            'name': tag,
            'body': 'version {0}'.format(ver),
            'prerelease': False,
            'draft': False,
        },
        headers = makeAuthHeader(token)
    )

    return response

def getRelease(tag, token):

    url = '{0}/tags/{1}'.format(REPO_RELEASES_URL, tag)
    response = requests.get(url, headers = makeAuthHeader(token))

    return response

def getReleaseAssets(releaseId, token):

    url = '{0}/{1}/assets'.format(REPO_RELEASES_URL, releaseId)
    response = requests.get(url, headers = makeAuthHeader(token))

    response.raise_for_status()
    return response

def deleteReleaseAsset(assetId, token):

    url = '{0}/assets/{1}'.format(REPO_RELEASES_URL, assetId)
    response = requests.delete(url, headers = makeAuthHeader(token))

    return response

def uploadReleaseAsset(path, uploadUrl, token):

    contentType, _ = mimetypes.guess_type(path)
    if contentType is None:
        contentType = 'application/octet-stream'

    headers = makeAuthHeader(token)
    headers['Content-Type'] = contentType

    params = { 'name': os.path.basename(path) }

    with open(path, "rb") as file:
        response = requests.post(
            uploadUrl,
            data = file,
            params = params,
            headers = headers
        )

    response.raise_for_status()
    return response

def obtainRelease(tag, token):

    response = makeRelease(tag, token)
    responseJson = response.json()
    errors = responseJson.get('errors', [])
    created = not any(err.get('code') == 'already_exists' for err in errors)

    if created:
        response.raise_for_status()
    else:
        response = getRelease(tag, token)
        response.raise_for_status()
        responseJson = response.json()

    return responseJson

def uploadAssets(releaseJson, files, token):

    releaseId = releaseJson['id']
    assets = getReleaseAssets(releaseId, token).json()
    for asset in assets:
        deleteReleaseAsset(asset['id'], token)

    uploadUrl = releaseJson['upload_url']
    uploadUrl = uploadUrl[0:uploadUrl.index('{')]

    for file in files:
        path = os.path.join(ZMDIR, file)
        uploadReleaseAsset(path, uploadUrl, token)

def main():
    """ do main work """

    cmdArgs = sys.argv[1:]
    if not cmdArgs:
        print("There is no tag version in args")
        return 1

    tagVer = cmdArgs[0]
    if tagVer[0] != 'v':
        tagVer = 'v' + tagVer
    #print("Publishing release {0} to github ...".format(tagVer))

    files = prepareAssets()

    #keyring.set_password("github-zenmake", "deploy-token", "token value")
    token = keyring.get_password("github-zenmake", "deploy-token")

    releaseJson = obtainRelease(tagVer, token)
    uploadAssets(releaseJson, files, token)

    return 0

if __name__ == '__main__':
    sys.exit(main())
