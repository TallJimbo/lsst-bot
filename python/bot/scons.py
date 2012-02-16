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
        if config.scons.echo:
            logging.debug("Running '{0}'...".format(" ".join(scons_cmd)))
        output = subprocess.check_output(scons_cmd, stderr=scons_stderr)
    except subprocess.CalledProcessError:
        raise Error("'{0}' failed".format(" ".join(scons_cmd)))
    finally:
        os.chdir(olddir)
    return output
