#!/usr/bin/env python

import os
import subprocess
from .utils import echo

class Error(RuntimeError): pass

def get_url(config, pkg):
    tmpl = config.hg.url.overrides.get(pkg, None)
    if tmpl is None:
        tmpl = "{root}/{pkg}"
    return tmpl.format(root=config.hg.url.root, pkg=pkg)

def run(config, path, *args):
    olddir = os.path.abspath(os.getcwd())
    os.chdir(path)
    hg_cmd = ("hg",) + args
    echo(config.hg, "In {0}, running '{1}'.".format(path, " ".join(hg_cmd)))
    try:
        subprocess.check_call(hg_cmd, stderr=config.hg.stderr, stdout=config.hg.stdout)
    except subprocess.CalledProcessError:
        raise Error("'{0}' in path '{1}' failed".format(" ".join(hg_cmd), path))
    finally:
        os.chdir(olddir)
