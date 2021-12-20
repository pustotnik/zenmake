# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import json

from zm.waf.task import WafTask
from zm.waf.ccroot import wafccroot
from zm.waf import wscriptimpl as wscript

class JSONEncoder(json.JSONEncoder):
    """
    Custom encoder to have ability to encode some Waf types
    """

    def default(self, o):
        # pylint: disable = method-hidden
        try:
            return json.JSONEncoder.default(self, o)
        except TypeError:
            return str(o)

def dumpToJson(data):
    """
    Serialize obj to a JSON formatted str.
    Returns json data
    """

    indent = 2
    separators = (',', ': ')
    return json.dumps(data, indent = indent, cls = JSONEncoder,
                      separators = separators, sort_keys = True)

def loadFromJson(data):
    """
    Deserialize obj from the JSON formatted str.
    """

    return json.loads(data)

def nobuildTaskRun(task):
    """
    Do dump to output files in json format instead of real building
    """

    tgen = task.generator
    bld = tgen.bld
    for node in task.outputs:
        data = {}
        data['tgen-name'] = tgen.name
        data['is-link'] = isinstance(task, wafccroot.link_task)
        data['inputs'] = task.inputs
        env = task.env.get_merged_dict()
        data['env'] = env
        data['zmtasks'] = bld.zmtasks
        data = dumpToJson(data)
        node.write(data, encoding = 'utf-8')

def _wrapBuild(method):
    def execute(ctx):
        for cls in WafTask.classes.values():
            cls.run = nobuildTaskRun
        method(ctx)
    return execute

setattr(wscript, 'build', _wrapBuild(getattr(wscript, 'build')))
