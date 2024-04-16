import sys

from termcolor import colored


def die(message, code=1):
    sys.stderr.write(colored(message, "red") + "\n")
    exit(code)


def warn(message, silent=False):
    if not silent:
        sys.stderr.write(colored(message, "yellow") + "\n")
