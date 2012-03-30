#!/usr/bin/env python

import os
import subprocess
from .utils import echo

class Error(RuntimeError): pass

def run(config, path, *args):
    olddir = os.path.abspath(os.getcwd())
    os.chdir(path)
    try:
        scons_cmd = ("scons",) + args
        echo(config.scons, "In {0}, running '{1}'".format(path, " ".join(scons_cmd)))
        subprocess.check_call(scons_cmd, stderr=config.scons.stderr, stdout=config.scons.stdout)
    except subprocess.CalledProcessError:
        raise Error("'{0}' in path '{1}' failed".format(" ".join(scons_cmd), path))
    finally:
        os.chdir(olddir)
