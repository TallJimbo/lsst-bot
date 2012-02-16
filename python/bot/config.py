import collections
import os
import logging

__all__ = "load", "default_categories"

class AttributeDict(object):

    def __init__(self):
        object.__setattr__(self, "_dict", collections.defaultdict(AttributeDict))

    def __getattr__(self, name):
        return self._dict[name]

    def __setattr__(self, name, value):
        self._dict[name] = value

    def merge(self, other):
        self._dict.update(other._dict)

    def _write(self, output, prefix=""):
        for k, v in self._dict.iteritems():
            if isinstance(v, AttributeDict):
                v._write(output, prefix="{0}{1}.".format(prefix, k))
            else:
                output.append("{0}{1} = {2}".format(prefix, k, repr(v)))

    def __repr__(self):
        output = []
        self._write(output, "")
        return "\n".join(output)

    __str__ = __repr__

default_categories = ["git", "packages", "eups", "scons"]

def load(path=None, categories=None):
    if path is None:
        path = os.getcwd()
        while not os.path.exists(os.path.join(path, "botconfig")):
            path = os.path.abspath(os.path.join(path, ".."))
            if path == "/":
                raise RuntimeError("No botconfig found in a parent directory and no path specified.")
    if categories is None:
        categories = default_categories
    config = AttributeDict()
    config.path = path
    context = {}
    for category in categories:
        context[category] = config._dict.setdefault(category, AttributeDict())
    files = []
    while os.path.exists(os.path.join(path, "botconfig")):
        files.append(os.path.abspath(os.path.join(path, "botconfig")))
        path = os.path.abspath(os.path.join(path, ".."))
        if path == "/":
            break
    directory, modfile = os.path.split(__file__)
    base = os.path.abspath(os.path.join(directory, "..", "..", "botconfig"))
    if not os.path.exists(base):
        logging.warn("Default botconfig file not found; all options must be set in user botconfigs!")
    if base not in files:
        files.append(base)
    for f in reversed(files):
        execfile(f, context)
    return config
