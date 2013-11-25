import sys


def log(something, *args):
    if args:
        something = something % args
    print >>sys.stderr, something
