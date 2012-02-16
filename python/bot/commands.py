from . import repo
from . import config

import argparse
import os

class Command(object):

    def add_arguments(self, subparsers):
        subparser = subparsers.add_parser(self.name, help=self.__doc__)
        self.setup(subparser)
        subparser.set_defaults(func=self.run)

    def setup(self, parser):
        pass

    def run(self, args):
        self.config = config.load(path=args.path)
        self.repos = repo.RepoSet(self.config)

class InitCommand(Command):
    """Initialize a repo set by creating a directory with a botconfig file.
    """

    name = "init"

    def setup(self, parser):
        parser.add_argument("path", metavar="PATH", type=str, nargs='?',
                            help="directory that will contain managed repositories.")
        parser.add_argument("--name", metavar="NAME", type=str, required=True,
                            help="sets eups.name in the generated config file")
        parser.add_argument("--top", metavar="PKG", type=str, required=True, action="append",
                            help="top-level package(s) to manage (at least one must be given)")
        parser.add_argument("--branch", metavar="REF", type=str,
                            help="git branch or cross-package tag to checkout by default")

    def run(self, args):
        if args.path is None:
            raise RuntimeError("path argument is required for init")
        if os.path.exists(args.path):
            raise RuntimeError("{0} already exists; it must be removed before running init".format(args.path))
        os.makedirs(args.path)
        with open(os.path.join(args.path, "botconfig"), "w") as f:
            f.write("# -*- python -*-\n\n")
            f.write("packages.top = {0}\n".format(repr(list(args.top))))
            f.write("eups.name = '{0}'\n".format(args.name))
            if args.branch is not None:
                f.write("packages.refs.default.insert(0, '{0}')\n".format(args.branch))
        print "Initialized config for new repo set at {0}".format(args.path)

class SyncCommand(Command):
    """Clone repositories from the server as needed and checkout the appropriate
    git refs to match the definition in the config files.
    """

    name = "sync"

    def setup(self, parser):
        parser.add_argument("path", metavar="PATH", type=str, nargs='?',
                            help="directory that will contain managed repositories.  "
                            "If not given, the first parent directory with a botconfig file will be used.")
        parser.add_argument("--fetch", action="store_true", default=False,
                            help="fetch new changes from origin before checking out")
        parser.add_argument("--no-declare", action="store_false", default=True, dest="declare",
                            help="do not declare products to EUPS")
        parser.add_argument("--no-table", action="store_false", default=True, dest="write_table",
                            help="do not write the metapackage table file")
        parser.add_argument("--no-list", action="store_false", default=True, dest="write_list",
                            help="do not write the package list file")

    def run(self, args):
        Command.run(self, args)
        self.repos.sync(fetch=args.fetch, declare=args.declare, write_table=args.write_table,
                        write_list=args.write_list)

class BuildCommand(Command):
    """Build all managed packages with scons.
    """

    name = "build"

    def setup(self, parser):
        parser.add_argument("path", metavar="PATH", type=str,
                            help="directory that contains managed repositories.  "
                            "This is mandatory to distinguish it from scons arguments.")
        parser.add_argument("scons_args", metavar="SCONS_ARGS", nargs=argparse.REMAINDER, 
                            help="additional arguments and options will be passed to scons")

    def run(self, args):
        Command.run(self, args)
        self.repos.read_list()
        self.repos.build(*args.scons_args)

class SimpleCommand(Command):

    def setup(self, parser):
        parser.add_argument("path", metavar="PATH", type=str, nargs='?',
                            help="directory that contains managed repositories.  "
                            "If not given, the first parent directory with a botconfig file will be used.")

    def run(self, args):
        Command.run(self, args)
        self.repos.read_list()
        getattr(self.repos, self.name)()

commands = [InitCommand(), SyncCommand(), BuildCommand()]

def addSimpleCommand(name):
    cmd = type(name, (SimpleCommand,), {"name": name, "__doc__": getattr(repo.RepoSet, name).__doc__})
    commands.append(cmd())

addSimpleCommand("list")
addSimpleCommand("pull")
addSimpleCommand("declare")
addSimpleCommand("undeclare")

def main(argv):
    parser = argparse.ArgumentParser(
        description="Manage a collection of LSST git repositories."
        )
    parser.add_argument("--traceback", action="store_true", default=False,
                        help="show full exception traceback when errors occur")
    subparsers = parser.add_subparsers(title="subcommands",
                                       description="use 'bot {subcommand} --help' for more information")
    for cmd in commands:
        cmd.add_arguments(subparsers)
    args = parser.parse_args(argv)
    if args.traceback:
        args.func(args)
    else:
        try:
            args.func(args)
        except Exception as err:
            parser.error(str(err))
