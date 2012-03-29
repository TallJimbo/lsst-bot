#!/usr/bin/env python

from . import git
from . import eups
from . import scons

import os
import logging

class RepoSet(object):

    def __init__(self, config):
        self.config = config
        self.packages = None
        self.refs = None
        self.external = None

    def path(self, pkg):
        return os.path.join(self.config.path, pkg)

    def write_table(self):
        """Write the EUPS table file for the metapackage."""
        assert(self.packages is not None)
        assert(self.refs is not None)
        assert(self.external is not None)
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
                version = self.config.eups.version(ref=self.refs[pkg], eups=self.config.eups)
                file.write("setupRequired({pkg} -j {version})\n".format(pkg=pkg, version=version))

    def write_list(self):
        """Write a text file containing a dependency sorted list with package name and version columns.
        """
        assert(self.packages is not None)
        assert(self.refs is not None)
        with open(os.path.join(self.config.path, "packages"), "w") as file:
            for pkg in self.packages:
                file.write("{pkg} {ref}\n".format(pkg=pkg, ref=self.refs[pkg]))

    def declare(self):
        """Declare all managed packages with EUPS."""
        assert(self.packages is not None)
        assert(self.refs is not None)
        for pkg in self.packages:
            version = self.config.eups.version(ref=self.refs[pkg], eups=self.config.eups)
            logging.info("Declaring {pkg} {version}.".format(pkg=pkg, version=version))
            eups.declare(self.config, self.path(pkg), pkg, version)

    def undeclare(self):
        """Undeclare all managed packages with EUPS."""
        assert(self.packages is not None)
        assert(self.refs is not None)
        for pkg in self.packages:
            version = self.config.eups.version(ref=self.refs[pkg], eups=self.config.eups)
            logging.info("Undeclaring {pkg} {version}.".format(pkg=pkg, version=version))
            eups.undeclare(self.config, pkg, version)

    def pull(self):
        """Pull the latest changes into the managed git repositories."""
        assert(self.packages is not None)
        for pkg in self.packages:
            if pkg in self.config.packages.manual:
                logging.info("Skipping manual package '{pkg}'...".format(pkg=pkg))
            else:
                logging.info("Pulling changes for '{pkg}'.".format(pkg=pkg))
                git.run(self.config, self.path(pkg), "pull")

    def list(self):
        """List all managed packages in dependency order."""
        assert(self.packages is not None)
        for pkg in self.packages:
            print pkg

    def build(self, *args):
        """Build all managed packages with scons.  They must already be setup.
        """
        assert(self.packages is not None)
        for pkg in self.packages:
            logging.info("Building '{pkg}'...".format(pkg=pkg))
            scons.run(self.config, self.path(pkg), *args)

    def run_git(self, *args, **kwargs):
        """Run the same git command on each package, excluding 'manual' packages.
        """
        ignore_failed = kwargs.get("ignore_failed", False)
        assert(self.packages is not None)
        for pkg in self.packages:
            if pkg in self.config.packages.manual:
                logging.info("Skipping manual package '{pkg}'...".format(pkg=pkg))
            else:
                logging.info("Processing '{pkg}'...".format(pkg=pkg))
                expanded = [arg.format(pkg=pkg) for arg in args]
                try:
                    git.run(self.config, self.path(pkg), *expanded)
                except git.Error as err:
                    if ignore_failed:
                        logging.info("Failure on '{pkg}'; continuing...".format(pkg=pkg))
                    else:
                        raise err

    def read_list(self):
        """Read the package list file into the RepoSet object to allow other operations
        to be performed without a sync.
        """
        self.packages = []
        self.refs = {}
        try:
            with open(os.path.join(self.config.path, "packages"), "r") as file:
                for line in file:
                    pkg, ref = line.split()
                    self.packages.append(pkg)
                    self.refs[pkg] = ref
        except IOError as err:
            raise RuntimeError("packages file not found - repo set is not synced or path not given")

    def sync(self, fetch=False, declare=True, write_table=True, write_list=True, pull=False):
        """Clone and/or checkout git repositories to match the package list defined
        by the configuration, and declare them to EUPS and write the
        EUPS metapackage table file.

        If fetch is True, run 'git fetch' on repos to ensure we have access to the
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
        dependencies = {}
        while todo:
            pkg = todo.pop(0)
            if pkg in done:
                continue
            done.add(pkg)
            # clone or fetch the git repo as needed
            if not self._ensure_repo(pkg, fetch):
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
        # use the dependency dict-of-sets to make a dependency-sorted list of managed packages
        self.packages = self._make_sorted_list(dependencies)
        # make a dict of unmanaged packages, where value is True if it's required
        self.external = dict((pkg, pkg in required) for pkg in external)
        # other optional tasks
        if declare: self.declare()
        if write_table: self.write_table()
        if write_list: self.write_list()
        if pull: self.pull()

    def _ensure_repo(self, pkg, fetch):
        """Worker function for sync - clones a git repo as needed and optionally fetches
        new changes if one is already present.
        """
        if os.path.isdir(self.path(pkg)):
            if fetch:
                if self.config.packages.refs.overrides.get(pkg, False) is None:
                    logging.info("Not fetching manual package '{pkg}'".format(pkg=pkg))
                else:
                    logging.info("Fetching (but not merging) '{pkg}'.".format(pkg=pkg))
                    git.run(self.config, self.path(pkg), "fetch")
        else:
            if self.config.packages.refs.overrides.get(pkg, False) is None:
                logging.info("Unmanaged source for '{pkg}' not found; treating as external.".format(pkg=pkg))
                return False
            if self.config.git.link.base is not None:
                base_path = os.path.join(self.config.path, self.config.git.link.base, pkg)
                if os.path.exists(base_path):
                    git.link(self.config, base_path, self.path(pkg))
                    return True
            logging.info("Cloning '{pkg}'.".format(pkg=pkg))
            git_url = git.get_url(self.config, pkg)
            try:
                git.run(self.config, self.config.path, "clone", git_url)
            except git.Error:
                logging.info("Git repo at '{0}' not found; treating as external.".format(git_url))
                return False
        return True

    def _checkout_ref(self, pkg):
        """Worker function for sync - checks out the first available ref from config.packages.refs
        for a single package.
        """
        ref = self.config.packages.refs.overrides.get(pkg, False)
        if ref:
            logging.debug("Trying to checkout ref '{ref}' for '{pkg}'.".format(ref=ref, pkg=pkg))
            git.run(self.config, self.path(pkg), "checkout", ref)
        elif ref is False:  # don't want to match 'ref is None' here
            for ref in self.config.packages.refs.default:
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
        logging.info("Using ref '{ref}' for '{pkg}'.".format(ref=ref, pkg=pkg))
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
