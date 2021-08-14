# coding=utf-8
#

# pylint: disable = missing-docstring, invalid-name, no-member

"""
 Copyright (c) 2021, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import pytest
from zm.error import ZenMakeConfError
from zm.buildconf import yaml

@pytest.mark.usefixtures("unsetEnviron")
def testLoadFailed(tmpdir):

    confFile = tmpdir.mkdir("load.yaml").join("buildconf.yml")

    confFile.write("")
    with pytest.raises(ZenMakeConfError):
        yaml.load(str(confFile.realpath()))

    confFile.write("---")
    with pytest.raises(ZenMakeConfError):
        yaml.load(str(confFile.realpath()))

    confFile.write("invalid data = {")
    with pytest.raises(ZenMakeConfError):
        yaml.load(str(confFile.realpath()))

def _checkLoad(tmpdir, monkeypatch, substmode):
    confFile = tmpdir.mkdir("load.yaml").join("buildconf.yml")

    validConfig = ""

    if substmode:
        validConfig += "\nsubstmode: %s\n" % substmode
        noEnvMode = substmode.endswith('-noenv')
    else:
        substmode = 'yaml-tag'
        noEnvMode = False

    validConfig += \
"""

fragment: |
    program
    end program

PATH_PART: /ddd
PATH_PART2: /GBV
GCC_BASE_CXXFLAGS: -std=c++11 -fPIC
MYFLAGS2: -O2 -Wall -Wextra

---

foo: 123

path1: ${{ PATH_PART }}/one/two/three
path2: ${{PATH_PART}}/one/two/three
path3: $PATH_PART/one/two/three
path4: /one${{PATH_PART}}/two/three
path5: /one$PATH_PART/two/three
path6: /one${{PATH_PART}}${{PATH_PART2}}/two/three
path7: /one${{PATH_PART}}/sss/${{PATH_PART2}}/two$PATH_PART/three
path8: /one/two/$UNKNOWN_VAR/three

text1: ${{ fragment }}

tasks:
  test:
    - do: check-code
      text: ${{fragment}}

release1: { cxxflags: -O2 $MYFLAGS }
release2: { cxxflags: -O2 $MYFLAGS2 }

"""

    configSpecificYamlTag = \
"""
debug1: { cxxflags: $GCC_BASE_CXXFLAGS -O0 -g }
debug2: { cxxflags: !subst "$GCC_BASE_CXXFLAGS -O0 -g" }
debug3: { cxxflags: !subst '$GCC_BASE_CXXFLAGS -O0 -g' }
debug4: { cxxflags: !subst "${{GCC_BASE_CXXFLAGS}} -O0 -g" }
debug5:
    cxxflags: $GCC_BASE_CXXFLAGS -O0 -g
debug6:
    cxxflags: ${{GCC_BASE_CXXFLAGS}} -O0 -g
"""

    configSpecificPreparse = \
"""
debug1: { cxxflags: $GCC_BASE_CXXFLAGS -O0 -g }
debug2: { cxxflags: "$GCC_BASE_CXXFLAGS -O0 -g" }
debug3: { cxxflags: '$GCC_BASE_CXXFLAGS -O0 -g' }
debug4: { cxxflags: "${{GCC_BASE_CXXFLAGS}} -O0 -g" }
debug5:
    cxxflags: $GCC_BASE_CXXFLAGS -O0 -g
debug6:
    cxxflags: ${{GCC_BASE_CXXFLAGS}} -O0 -g
"""

    if substmode.startswith('yaml-tag'):
        validConfig += configSpecificYamlTag
    else:
        validConfig += configSpecificPreparse

    monkeypatch.setenv('MYFLAGS', '-O3 -Wall')
    monkeypatch.setenv('MYFLAGS2', '-O1 -Wall')

    confFile.write(validConfig)
    buildconf = yaml.load(str(confFile.realpath()))

    assert buildconf.path1 == "/ddd/one/two/three"
    assert buildconf.path2 == "/ddd/one/two/three"
    assert buildconf.path3 == "/ddd/one/two/three"
    assert buildconf.path4 == "/one/ddd/two/three"
    assert buildconf.path5 == "/one/ddd/two/three"
    assert buildconf.path6 == "/one/ddd/GBV/two/three"
    assert buildconf.path7 == "/one/ddd/sss//GBV/two/ddd/three"
    assert buildconf.path8 == "/one/two/$UNKNOWN_VAR/three"

    assert buildconf.text1 == "program\nend program\n"
    assert buildconf.tasks['test'][0]['text'] == "program\nend program\n"

    for idx in range(1, 6):
        param = getattr(buildconf, 'debug' + str(idx))
        assert param['cxxflags'] == "-std=c++11 -fPIC -O0 -g"

    if noEnvMode:
        assert buildconf.release1['cxxflags'] == "-O2 $MYFLAGS"
        assert buildconf.release2['cxxflags'] == "-O2 -O2 -Wall -Wextra"
    else:
        assert buildconf.release1['cxxflags'] == "-O2 -O3 -Wall"
        assert buildconf.release2['cxxflags'] == "-O2 -O1 -Wall"

@pytest.mark.usefixtures("unsetEnviron")
def testLoadDefault(tmpdir, monkeypatch):
    _checkLoad(tmpdir, monkeypatch, substmode = None)

@pytest.mark.usefixtures("unsetEnviron")
def testLoadYamlTag(tmpdir, monkeypatch):
    _checkLoad(tmpdir, monkeypatch, substmode = 'yaml-tag')

@pytest.mark.usefixtures("unsetEnviron")
def testLoadYamlTagNoEnv(tmpdir, monkeypatch):
    _checkLoad(tmpdir, monkeypatch, substmode = 'yaml-tag-noenv')

@pytest.mark.usefixtures("unsetEnviron")
def testLoadPreparse(tmpdir, monkeypatch):
    _checkLoad(tmpdir, monkeypatch, substmode = 'preparse')

@pytest.mark.usefixtures("unsetEnviron")
def testLoadPreparseNoEnv(tmpdir, monkeypatch):
    _checkLoad(tmpdir, monkeypatch, substmode = 'preparse-noenv')
