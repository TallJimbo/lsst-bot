#!/usr/bin/env python

import os
import re
import sys
import argparse
import eups

def main(argv):
    parser = argparse.ArgumentParser(
        description="Declare a dummy EUPS product for a package already available in /usr or /usr/local",
    )
    parser.add_argument("name", metavar="NAME", type=str, help="name of the EUPS product to declare")
    parser.add_argument("version", nargs="?", type=str, default="system", help="EUPS version 'number'")
    parser.add_argument("--remap", metavar="FILE", type=str,
                        help="Full path to the 'manifest.remap' file, to ensure usage by eups distrib",
                        default=os.path.join(os.environ["EUPS_PATH"].split(":")[0], "site", "manifest.remap"))
    parser.add_argument("--buildFiles", metavar="DIR", type=str,
                        help="Full path to a local clone of the 'buildFiles' package",
                        default=None)
    parser.add_argument("--productDir", "-r", metavar="DIR", help="directory to associate with the product",
                        default='none')
    args = parser.parse_args(argv)

    if args.buildFiles is None:
        for eupsPath in os.environ["EUPS_PATH"].split(":"):
            for subPath in ("../buildFiles", "../devenv/buildFiles", "buildFiles", "devenv/buildFiles"):
                args.buildFiles = os.path.join(eupsPath, subPath)
                if os.path.isdir(args.buildFiles):
                    print "Using buildFiles at %s" % args.buildFiles
                    break
                args.buildFiles = None
    if args.buildFiles is None:
        parser.error("--buildFiles must be specified, or present in or just above EUPS_PATH")

    tableFile = os.path.join(args.buildFiles, "%s.table" % args.name)
    extrasDir = os.path.join(args.buildFiles, args.name)
    if not os.path.isfile(tableFile):
        tableFile = None
    else:
        tableFile = open(tableFile, 'r')
    if not os.path.isdir(extrasDir):
        extraFiles = []
    else:
        extraFiles = [(os.path.join(extrasDir, f), f) for f in os.listdir(extrasDir)]
    print ("Declaring %s %s with productDir %s and %d extra files"
           % (args.name, args.version, args.productDir, len(extraFiles)))
    eups.declare(productName=args.name, versionName=args.version, productDir=args.productDir,
                 tablefile=tableFile, externalFileList=extraFiles)

    if os.path.isfile(args.remap):
        remapRegex = re.compile("^\s*%s\s*(\s+(?P<version>\S+))$" % args.name)
        remapFile = open(args.remap, "r")
        for line in remapFile:
            m = remapRegex.match(line.split("#")[0])
            if m:
                if m.group("version") == args.version:
                    print "manifest.remap already includes an entry for this version; leaving unchanged"
                    return
                else:
                    parser.error("manifest.remap already includes an entry for this product with version %s"
                                 % m.group("version"))
    try:
        with open(args.remap, "a") as remapFile:
            remapFile.write("%s %s\n" % (args.name, args.version))
    except Exception as err:
        parser.error("remap file %s cannot be opened for appending: %s" % (args.remap, err))


if __name__ == "__main__":
    main(sys.argv[1:])
