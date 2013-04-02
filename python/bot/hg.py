#!/usr/bin/env python

import os
import subprocess
from .utils import echo

class Error(RuntimeError): pass

def get_remotes(config, pkg):
    d = config.hg.url.overrides.get(pkg, config.hg.url.remotes)
    if not isinstance(d, dict):
        pkg = d
        d = config.hg.url.remotes
    return {k: v.format(pkg=pkg) for k,v in d.iteritems()}

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
    and add corresponding gitifyhg:: URLs to "git.url.overrides" instead."""
    if not config.hg.use_git:
        return
    while config.hg.packages:
        pkg = config.hg.packages.pop()
        remotes = get_remotes(config, pkg)
        for k in remotes:
            remotes[k] = "gitifyhg::" + remotes[k]
        config.git.url.overrides[pkg] = remotes
