#!/usr/bin/env python

import os
import subprocess
import logging

class Error(RuntimeError): pass

def get_url(config, pkg):
    tmpl = config.git.url.overrides.get(pkg, None)
    if tmpl is None:
        tmpl = "{root}/{pkg}"
    return tmpl.format(root=config.git.url.root, pkg=pkg)

def link(config, base_path, pkg_path):
    cmd = (config.git.link.cmd, base_path, pkg_path)
    if config.git.quiet:
        git_stderr = open("/dev/null", "w")
    else:
        git_stderr = None
    if config.git.echo:
        logging.debug("Running '{0}'...".format(" ".join(cmd)))
    try:
        subprocess.check_output(cmd)
    except subprocess.CalledProcessError:
        raise Error("'{0}' failed".format(" ".join(cmd)))

def run(config, path, *args):
    olddir = os.path.abspath(os.getcwd())
    os.chdir(path)
    if config.git.quiet:
        git_stderr = open("/dev/null", "w")
    else:
        git_stderr = None
    git_cmd = ("git",) + args
    if config.git.echo:
        logging.debug("Running '{0}'...".format(" ".join(git_cmd)))
    try:
        output = subprocess.check_output(git_cmd, stderr=git_stderr)
    except subprocess.CalledProcessError:
        raise Error("'{0}' failed".format(" ".join(git_cmd)))
    finally:
        os.chdir(olddir)
    return output
