# coding=utf-8
#

"""
 Copyright (c) 2020, Alexander Magola. All rights reserved.
 license: BSD 3-Clause License, see LICENSE for more details.
"""

import json

from waflib import Task
from waflib.Tools import ccroot
from zm.pyutils import PY2, texttype
import zm.waf.wscriptimpl as wscript

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

    hook = None
    if PY2:
        def convert(value):
            if isinstance(value, list):
                return [convert(x) for x in value]
            if isinstance(value, texttype):
                return str(value)
            return value

        def pairs(pairs):
            return { str(pair[0]): convert(pair[1]) for pair in pairs}

        hook = pairs

    return json.loads(data, object_pairs_hook = hook)

def nobuildTaskRun(task):
    """
    Do dump to output files in json format instead of real building
    """

    tgen = task.generator
    for node in task.outputs:
        data = {}
        data['tgen-name'] = tgen.name
        data['is-link'] = isinstance(task, ccroot.link_task)
        data['inputs'] = task.inputs
        env = task.env.get_merged_dict()
        data['env'] = env
        data = dumpToJson(data)
        node.write(data, encoding = 'utf-8')

def _wrapBuild(method):
    def execute(ctx):
        for cls in Task.classes.values():
            cls.run = nobuildTaskRun
        method(ctx)
    return execute

setattr(wscript, 'build', _wrapBuild(getattr(wscript, 'build')))
