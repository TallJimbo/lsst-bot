#!/usr/bin/env python

import os
import subprocess
from .utils import echo

class Error(RuntimeError): pass

def get_remotes(config, pkg):
    d = config.git.url.overrides.get(pkg, config.git.url.remotes)
    if not isinstance(d, dict):
        pkg = d
        d = config.git.url.remotes
    return {k: v.format(pkg=pkg) for k,v in d.iteritems()}

def run(config, path, *args):
    olddir = os.path.abspath(os.getcwd())
    os.chdir(path)
    git_cmd = ("git",) + args
    echo(config.git, "In {0}, running '{1}'.".format(path, " ".join(git_cmd)))
    try:
        subprocess.check_call(git_cmd, stderr=config.git.stderr, stdout=config.git.stdout)
    except subprocess.CalledProcessError:
        raise Error("'{0}' in path '{1}' failed".format(" ".join(git_cmd), path))
    finally:
        os.chdir(olddir)
