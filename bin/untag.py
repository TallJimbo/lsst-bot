#!/usr/bin/env python

import argparse
import sys
import eups

def main(argv):
    parser = argparse.ArgumentParser(
        description="Remove all tags from one or more EUPS products",
    )
    parser.add_argument("product", metavar="PRODUCT", type=str,
                        help="name of a EUPS product to remove tags from")
    parser.add_argument("version", nargs="?", metavar="PRODUCT", type=str, default=None,
                        help="version of the EUPS product to remove tags from")
    parser.add_argument("-t", "--tag", nargs="?", metavar="PRODUCT", type=str, default=None,
                        help="tag of the EUPS product to remove tags from")
    parser.add_argument("--keep", "-k", metavar="TAG", type=str, action="append",
                        help="Name of tag to keep; may be used multiple times.",
                        default=["current"])
    args = parser.parse_args(argv)
    if args.tag:
        version = eups.Tag(args.tag)
    else:
        version = args.version
    product = eups.findProduct(args.product, versionName=version)
    if product is None:
        raise ValueError("No product %s with version %s" % (args.product, version))
    for tag in product.tags:
        eups.undeclare(product.name, versionName=product.version, tag=tag)

if __name__ == "__main__":
    main(sys.argv[1:])