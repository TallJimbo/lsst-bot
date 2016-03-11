#!/usr/bin/env python
import os
import sys
import argparse
import subprocess
import eups

def findDir(relatives):
    for eupsPath in os.environ["EUPS_PATH"].split(":"):
        for subPath in ("../external", "external"):
            result = os.path.join(eupsPath, subPath)
            if os.path.isdir(result):
                return result
    return None

def main(argv):
    parser = argparse.ArgumentParser(
        description="Install a setuptools module in the current directory and declare it to EUPS",
    )
    parser.add_argument("name", metavar="NAME", type=str, help="name of the EUPS product to declare")
    parser.add_argument("version", nargs="?", type=str, default="system", help="EUPS version 'number'")

    parser.add_argument("--productDir", "-r", metavar="DIR", help="root directory for installed product",
                        default=None)
    parser.add_argument("--dep", "-d", action="append", metavar="PRODUCTS", dest="deps", default=["python"],
                        help="names of EUPS products on which this package depends (must be setup)")
    args = parser.parse_args(argv)

    eupsObj = eups.Eups()

    if args.productDir is None:
        productDir = os.path.join(eupsObj.path[0], eupsObj.flavor, args.name, args.version)
    else:
        productDir = args.productDir

    subprocess.call("python setup.py install --home=" + productDir, shell=True)

    depDict = {}

    tableFile = os.path.join(productDir, "ups", "{}.table".format(args.name))

    with open(tableFile, "w") as table:
        for dep in args.deps:
            table.write("setupRequired({})\n".format(dep))
        table.write("envPrepend(PYTHONPATH, {})".format(os.path.join("${PRODUCT_DIR}", "lib", "python")))
        if os.path.isdir(os.path.join(productDir, "bin")):
            table.write("envPrepend(PATH, {})".format(oos.path.join("${PRODUCT_DIR}", "bin")))

    try:
        os.makedirs(os.path.join(productDir, "ups"))
    except OSError:
        pass

    subprocess.call("eups expandtable -i " + tableFile, shell=True)

    eups.declare(productName=args.name, versionName=args.version, productDir=productDir,
                 tablefile=tableFile)


if __name__ == "__main__":
    main(sys.argv[1:])
