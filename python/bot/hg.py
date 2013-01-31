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

def maybe_use_git(config):
    """Inspect 'config.hg.use_git', and if True, remove all packages from 'hg.packages'
    and add corresponding hg:: URLs to "git.url.overrides" instead."""
    if not config.hg.use_git:
        return
    while config.hg.packages:
        pkg = config.hg.packages.pop()
        url = get_url(config, pkg)
        config.git.url.overrides[pkg] = "hg::" + url
