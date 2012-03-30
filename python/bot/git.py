#!/usr/bin/env python

import os
import subprocess
from .utils import echo

class Error(RuntimeError): pass

def get_url(config, pkg):
    tmpl = config.git.url.overrides.get(pkg, None)
    if tmpl is None:
        tmpl = "{root}/{pkg}"
    return tmpl.format(root=config.git.url.root, pkg=pkg)

def link(config, base_path, pkg_path):
    cmd = (config.git.link.cmd, base_path, pkg_path)
    echo(config.git, "Running '{0}'".format(" ".join(cmd)))
    try:
        subprocess.check_call(cmd, stderr=config.git.stderr, stdout=config.git.stdout)
    except subprocess.CalledProcessError:
        raise Error("'{0}' failed".format(" ".join(cmd)))

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
