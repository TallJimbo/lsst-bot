#!/usr/bin/env python

import os
import subprocess
import logging

class Error(RuntimeError): pass

def run(config, path, *args):
    olddir = os.path.abspath(os.getcwd())
    os.chdir(path)
    try:
        if config.scons.quiet:
            scons_stderr = open("/dev/null", "w")
        else:
            scons_stderr = None
        scons_cmd = ("scons",) + args
        logging.log(config.scons.echo, "In {0}, running '{1}'...".format(path, " ".join(scons_cmd)))
        output = subprocess.check_output(scons_cmd, stderr=scons_stderr)
    except subprocess.CalledProcessError:
        raise Error("'{0}' in path '{1}' failed".format(" ".join(scons_cmd), path))
    finally:
        os.chdir(olddir)
    return output
