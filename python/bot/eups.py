#!/usr/bin/env python
from __future__ import absolute_import
import eups.table
import os
import logging

__all__ = "get_dependencies"

def get_dependencies(config, path, pkg, recursive=False):
    """Return immediate dependencies from inspecting a table file.

    NOTE: recursive=True has not been tested.
    """
    e = eups.Eups()
    t = eups.table.Table(os.path.join(path, "ups", pkg + ".table"))
    dependencies = t.dependencies(e, recursive=recursive)
    if recursive:
        dependencies.sort(key=lambda x: x[2])
    for product, optional, depth in dependencies:
        yield product.name, optional

def declare(config, path, pkg, version, tag_only=False):
    e = eups.Eups()
    if not tag_only:
        logging.debug("Declaring {pkg} {version}.".format(pkg=pkg, version=version))
        e.declare(productName=pkg, versionName=version, productDir=path)
    for tmp in config.eups.tags:
        tag = tmp.format(eups=config.eups)
        logging.debug("Assigning tag {tag} to {pkg}.".format(pkg=pkg, tag=tag))
        e.assignTag(tag, productName=pkg, versionName=version)

def undeclare(config, pkg, version):
    e = eups.Eups()
    e.undeclare(productName=pkg, versionName=version)

def setup(pkg, version, nodepend=False):
    e = eups.Eups(max_depth=(0 if nodepend else -1))
    e.setup(productName=pkg, versionName=version)

def tag(pkg, version, tag):
    e = eups.Eups()
    logging.debug("Assigning tag {tag} to {pkg}.".format(pkg=pkg, tag=tag))
    e.assignTag(tag, productName=pkg, versionName=version)
    
