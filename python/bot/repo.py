#!/usr/bin/env python

from . import git
from . import hg
from . import eups
from . import scons
from . import config

import os
import sys
import shutil
import logging

class RepoSet(object):

    def __init__(self, cfg):
        self.config = cfg
        self.packages = None
        self.refs = None
        self.external = None
        self.inherited = None
        if self.config.packages.inherit.base:
            base_path = os.path.normpath(os.path.join(self.config.path, self.config.packages.inherit.base))
            base_config = config.load(base_path)
            self.base = RepoSet(base_config)
            try:
                self.base.read_list()
            except RuntimeError:
                raise RuntimeError("Please run 'bot sync' on the base repo at '{path}'".format(base_path))
        else:
            self.base = None

    def path(self, pkg):
        """Return the source path for the given package."""
        assert self.inherited is not None
        if pkg in self.inherited:
            return self.base.path(pkg)
        else:
            return os.path.join(self.config.path, pkg)

    def version(self, pkg):
        """Return the eups version for the given package."""
        assert self.inherited is not None
        if pkg in self.inherited:
            return self.base.version(pkg)
        else:
            return self.config.eups.version(ref=self.refs[pkg], eups=self.config.eups)

    def write_table(self):
        """Write the EUPS table file for the metapackage."""
        assert self.packages is not None
        assert self.refs is not None
        assert self.external is not None
        assert self.inherited is not None
        ups = os.path.join(self.config.path, "ups")
        if not os.path.exists(ups): os.makedirs(ups)
        meta = self.config.eups.meta.format(eups=self.config.eups)
        with open(os.path.join(ups, "{0}.table".format(meta)), "w") as file:
            for pkg, required in self.external.iteritems():
                if required:
                    file.write("setupRequired({pkg})\n".format(pkg=pkg))
                else:
                    file.write("setupOptional({pkg})\n".format(pkg=pkg))
            for pkg in self.packages:
                file.write("setupRequired({pkg} -j {version})\n".format(pkg=pkg, version=self.version(pkg)))

    def write_list(self):
        """Write a text file containing a dependency sorted list with package name and version columns.
        """
        assert self.packages is not None
        assert self.refs is not None
        assert self.inherited is not None
        with open(os.path.join(self.config.path, "packages"), "w") as file:
            for pkg in self.packages:
                if pkg in self.inherited:
                    file.write("{pkg} [{ref}]\n".format(pkg=pkg, ref=self.refs[pkg]))
                else:
                    file.write("{pkg} {ref}\n".format(pkg=pkg, ref=self.refs[pkg]))

    def read_list(self):
        """Read the package list file into the RepoSet object to allow other operations
        to be performed without a sync.
        """
        self.packages = []
        self.refs = {}
        self.inherited = set()
        try:
            with open(os.path.join(self.config.path, "packages"), "r") as file:
                for line in file:
                    pkg, ref = line.split()
                    if ref.startswith("[") and ref.endswith("]"):
                        ref = ref[1:-1]
                        self.inherited.add(pkg)
                    self.packages.append(pkg)
                    self.refs[pkg] = None if ref == 'None' else ref
        except IOError as err:
            raise RuntimeError("packages file not found - repo set is not synced or path not given")

    def declare(self):
        """Declare all managed packages with EUPS."""
        assert self.packages is not None
        assert self.refs is not None
        assert self.inherited is not None
        for pkg in self.packages:
            version = self.version(pkg)
            if pkg in self.inherited:
                logging.info("Assigning tags for inherited package '{pkg}'.".format(pkg=pkg))
                eups.declare(self.config, self.path(pkg), pkg, version, tag_only=True)
            else:
                logging.info("Declaring {pkg} {version}.".format(pkg=pkg, version=version))
                eups.declare(self.config, self.path(pkg), pkg, version)

    def undeclare(self):
        """Undeclare all managed packages with EUPS."""
        assert self.packages is not None
        assert self.refs is not None
        assert self.inherited is not None
        for pkg in self.packages:
            if pkg in self.inherited:
                logging.info("Skipping inherited package '{pkg}'.".format(pkg=pkg))
            else:
                version = self.version(pkg)
                logging.info("Undeclaring {pkg} {version}.".format(pkg=pkg, version=version))
                eups.undeclare(self.config, pkg, version)

    def list(self):
        """List all managed packages in dependency order."""
        assert self.packages is not None
        assert self.inherited is not None
        for pkg in self.packages:
            print pkg

    def build(self, *args, **kw):
        """Build all managed packages with scons.  They must already be setup.
        """
        assert self.packages is not None
        assert self.inherited is not None
        for pkg in self.packages:
            if pkg not in self.inherited or kw.get("inherited"):
                logging.info("Building '{pkg}'...".format(pkg=pkg))
                try:
                    scons.run(self.config, self.path(pkg), *args)
                except scons.Error as err:
                    if kw.get("ignore_failed"):
                        logging.warning("Build for '{pkg}' failed; continuing...".format(pkg=pkg))
                        continue
                    raise err
            else:
                logging.info("Skipping inherited package '{pkg}'...".format(pkg=pkg))

    def run_git(self, *args, **kw):
        """Run the same git command on each package, excluding 'manual' and hg-controlled packages.
        """
        assert self.packages is not None
        assert self.refs is not None
        assert self.inherited is not None
        for pkg in self.packages:
            if self.refs[pkg] is None:
                logging.info("Skipping package '{pkg}' with ref==None...".format(pkg=pkg))
            elif pkg in self.config.hg.packages:
                logging.info("Skipping hg package '{pkg}'...".format(pkg=pkg))
            elif pkg not in self.inherited or kw.get("inherited"):
                logging.info("Processing '{pkg}'...".format(pkg=pkg))
                expanded = [arg.format(pkg=pkg) for arg in args]
                try:
                    git.run(self.config, self.path(pkg), *expanded)
                except git.Error as err:
                    if kw.get("ignore_failed"):
                        logging.info("Failure on '{pkg}'; continuing...".format(pkg=pkg))
                    else:
                        raise err
            else:
                logging.info("Skipping inherited package '{pkg}'...".format(pkg=pkg))

    def run_hg(self, *args, **kw):
        """Run the same hg command on each hg-controlled package.
        """
        assert self.packages is not None
        assert self.refs is not None
        assert self.inherited is not None
        for pkg in self.packages:
            if self.refs[pkg] is None:
                logging.info("Skipping package '{pkg}' with ref==None...".format(pkg=pkg))
            elif pkg not in self.config.hg.packages:
                logging.info("Skipping git package '{pkg}'...".format(pkg=pkg))
            elif pkg not in self.inherited or kw.get("inherited"):
                logging.info("Processing '{pkg}'...".format(pkg=pkg))
                expanded = [arg.format(pkg=pkg) for arg in args]
                try:
                    hg.run(self.config, self.path(pkg), *expanded)
                except hg.Error as err:
                    if kw.get("ignore_failed"):
                        logging.info("Failure on '{pkg}'; continuing...".format(pkg=pkg))
                    else:
                        raise err
            else:
                logging.info("Skipping inherited package '{pkg}'...".format(pkg=pkg))

    def install(self, *args, **kw):
        """Install and declare all managed packages with scons.  They must already be setup.
        """
        assert self.packages is not None
        assert self.inherited is not None
        to_tag = []
        for pkg in self.packages:
            if pkg not in self.inherited or kw.get("inherited"):
                version = kw["version"].format(pkg=pkg)
                full_args = args + ("install", "declare", "version=" + version)
                logging.info("Installing '{pkg}'...".format(pkg=pkg))
                try:
                    scons.run(self.config, self.path(pkg), *full_args)
                    eups.setup(pkg, version, nodepend=True)
                    to_tag.append((pkg, version))
                except scons.Error as err:
                    if kw.get("ignore_failed"):
                        logging.warning("Build for '{pkg}' failed; continuing...".format(pkg=pkg))
                        continue
                    raise err
            else:
                logging.warn("Skipping inherited package '{pkg}'...".format(pkg=pkg))
        tag = kw.get("tag")
        if tag:
            for pkg, version in to_tag:
                eups.tag(pkg, version, tag)

    def sync(self, fetch=False, declare=True, write_table=True, write_list=True):
        """Clone and/or checkout git and/or hg repositories to match the package list defined
        by the configuration, and declare them to EUPS and write the
        EUPS metapackage table file.

        If fetch is True, run 'git fetch' or 'hg pull' on repos to ensure we have access to the
        branches/tags we need before trying to check them out (only applies when
        an existing repo is found).
        """
        allExternal = set(self.config.packages.external)
        if isinstance(self.config.packages.top, basestring):
            todo = [self.config.packages.top]
        else:
            todo = list(self.config.packages.top)
        done = set()
        required = set(todo)
        external = set()
        self.refs = {}
        self.inherited = set()
        new_clones = set()
        dependencies = {}
        while todo:
            pkg = todo.pop(0)
            if pkg in done:
                continue
            done.add(pkg)
            # clone or fetch the git/hg repo as needed
            if not self._ensure_repo(pkg, fetch, new_clones):
                if pkg in dependencies:
                    del dependencies[pkg]
                for deps in dependencies.itervalues():
                    deps.discard(pkg)
                allExternal.add(pkg)
                external.add(pkg)
                continue
            # checkout the desired ref in the repo, falling back to defaults as necessary
            ref = self._checkout_ref(pkg)
            self.refs[pkg] = ref
            # lookup dependencies by reading the table file we just checked out
            pkg_deps = dependencies.setdefault(pkg, set()) # each value is a set of nonrecursive deps
            for dependency, optional in eups.get_dependencies(self.config, self.path(pkg), 
                                                              pkg, recursive=False):
                if not optional:
                    required.add(dependency)
                if dependency in allExternal:
                    external.add(dependency)
                    continue
                if dependency in self.config.packages.ignore:
                    continue
                pkg_deps.add(dependency)
                if dependency not in done:
                    todo.append(dependency)
        # walk through the packages we've tried to inherit, and remove any that have non-inherited deps
        while True:
            uninheritable = set()
            for pkg in self.inherited:
                for dep in dependencies[pkg]:
                    if dep not in self.inherited or dep in uninheritable:
                        logging.info("Not inheriting '{pkg}'; depends on '{dep}'.".format(pkg=pkg, dep=dep))
                        uninheritable.add(pkg)
                        break
            if not uninheritable:
                break
            self.inherited -= uninheritable
        # use the dependency dict-of-sets to make a dependency-sorted list of managed packages
        self.packages = self._make_sorted_list(dependencies)
        # go through all the packages, and add repos for things we thought we could inherit but can't
        for pkg in self.packages:
            if not self._ensure_repo(pkg, False, new_clones, inherit=False):
                raise RuntimeError("Could not clone new repo for '{pkg}'".format(pkg))
            checked_out_ref = self._checkout_ref(pkg, inherit=False)
        # remove any new clones we are inheriting; note that we don't remove repos we didn't just make
        for pkg in new_clones:
            if pkg in self.inherited:
                logging.info("Pruning repo for inherited package '{pkg}'.".format(pkg=pkg))
                # can't use self.path here, because that points to the inherited location
                shutil.rmtree(os.path.join(self.config.path, pkg))
        # make a dict of unmanaged packages, where value is True if it's required
        self.external = dict((pkg, pkg in required) for pkg in external)
        # other optional tasks
        if declare: self.declare()
        if write_table: self.write_table()
        if write_list: self.write_list()

    def _ensure_repo(self, pkg, fetch, new_clones, inherit=True):
        """Worker function for sync - clones a git/hg repo as needed and optionally fetches
        new changes if one is already present.
        """
        if os.path.isdir(self.path(pkg)):
            if fetch:
                assert pkg not in self.inherited 
                if self.config.packages.refs.overrides.get(pkg, False) is None:
                    logging.info("Not fetching manual package '{pkg}'".format(pkg=pkg))
                elif pkg in self.config.hg.packages:
                    logging.info("Fetching (but not merging) from hg '{pkg}'.".format(pkg=pkg))
                    hg.run(self.config, self.path(pkg), "pull")                    
                else:
                    logging.info("Fetching (but not merging) from git '{pkg}'.".format(pkg=pkg))
                    git.run(self.config, self.path(pkg), "fetch")
        else:
            ref = self.config.packages.refs.overrides.get(pkg, False)
            if inherit and self.base is not None and ref in self.config.packages.inherit.refs:
                assert self.base.packages is not None
                assert self.base.refs is not None
                try:
                    base_ref = self.base.refs[pkg]
                    if base_ref == ref:
                        logging.info("Provisionally inheriting '{pkg}' from base repo.".format(pkg=pkg))
                        self.inherited.add(pkg)
                        return True
                except KeyError:
                    logging.info("'{pkg}' could not be found in the base repo.".format(pkg=pkg))
            if ref is None:
                logging.info("Unmanaged source for '{pkg}' not found; treating as external.".format(pkg=pkg))
                return False
            if pkg in self.config.packages.hg:
                logging.info("Cloning '{pkg}' with hg.".format(pkg=pkg))
                hg_url = hg.get_url(self.config, pkg)
                try:
                    hg.run(self.config, self.config.path, "clone", hg_url)
                    new_clones.add(pkg)
                except hg.Error:
                    logging.info("hg repo at '{0}' not found; treating as external.".format(hg_url))
                    return False
            else:
                if self.config.git.link.base is not None:
                    base_path = os.path.join(self.config.path, self.config.git.link.base, pkg)
                    if os.path.exists(base_path):
                        git.link(self.config, base_path, self.path(pkg))
                        new_clones.add(pkg)
                        return True
                logging.info("Cloning '{pkg}' with git.".format(pkg=pkg))
                git_url = git.get_url(self.config, pkg)
                try:
                    git.run(self.config, self.config.path, "clone", git_url)
                    new_clones.add(pkg)
                except git.Error:
                    logging.info("hg repo at '{0}' not found; treating as external.".format(git_url))
                    return False
        return True

    def _checkout_ref(self, pkg, inherit=True):
        """Worker function for sync - checks out the first available ref from config.packages.refs
        for a single package.
        """
        ref = self.config.packages.refs.overrides.get(pkg, False)
        if pkg in self.inherited:  # we already marked it provisionally inherited in _ensure_repo
            return ref
        if ref:
            trueref = ref
            # let exceptions propagate up; we don't want to fall back if the ref is in overrides
            if pkg in self.config.hg.packages:
                hgref = self.config.hg.refs.replace.get(ref, ref)
                logging.debug("Trying to checkout ref '{hgref}' for '{pkg}'.".format(hgref=hgref, pkg=pkg))
                hg.run(self.config, self.path(pkg), "update", hgref)
                trueref = hgref
            else:
                logging.debug("Trying to checkout ref '{ref}' for '{pkg}'.".format(ref=ref, pkg=pkg))
                git.run(self.config, self.path(pkg), "checkout", ref)
        elif ref is False:  # don't want to match 'ref is None' here
            for ref in self.config.packages.refs.default:
                trueref = ref
                if pkg in self.config.hg.packages:
                    hgref = self.config.hg.refs.replace.get(ref, ref)
                    logging.debug("Trying to checkout ref '{hgref}' for '{pkg}'."
                                  .format(hgref=hgref, pkg=pkg))
                    try:
                        hg.run(self.config, self.path(pkg), "update", hgref)
                        trueref = hgref
                        break
                    except hg.Error:
                        pass
                else:
                    logging.debug("Trying to checkout ref '{ref}' for '{pkg}'.".format(ref=ref, pkg=pkg))
                    try:
                        git.run(self.config, self.path(pkg), "checkout", ref)
                        break
                    except git.Error:
                        pass
            else:
                raise RuntimeError(
                    "Could not checkout any of ({refs}) for package '{pkg}'".format(
                        refs=", ".join(self.config.packages.refs.default), pkg=pkg)
                    )
        logging.info("Using ref '{ref}' for '{pkg}'.".format(ref=trueref, pkg=pkg))
        if inherit and self.base is not None and ref in self.config.packages.inherit.refs:
            assert self.base.packages is not None
            assert self.base.refs is not None
            try:
                base_ref = self.base.refs[pkg]
                if base_ref == ref:
                    logging.info("Provisionally inheriting '{pkg}' from base repo.".format(pkg=pkg))
                    self.inherited.add(pkg)
            except KeyError:
                logging.info("'{pkg}' could not be found in the base repo.".format(pkg=pkg))    
        return ref

    def _make_sorted_list(self, data):
        """Given a dict of package names and sets of immediate dependencies, generate
        a dependency-sorted list of package names.
        """
        result = []
        todo = set(data.iterkeys())
        finished = set()
        while todo:
            for name in todo:
                dependencies = data[name]
                dependencies -= finished
                logging.debug("Updating dependencies for '{0}': {1}".format(name, dependencies))
                if not dependencies:
                    break
            else:
                raise ValueError("Circular dependency detected: {0}".format(todo))
            logging.debug("Finished all dependencies for '{0}'".format(name))
            finished.add(name)
            result.append(name)
            todo.remove(name)
        return result
