import logging
import sys

def echo(config, message):
    logging.log(config.echo, message)
    if config.stderr != sys.stderr and config.stderr != sys.stdout:
        config.stderr.write("\n#---- bot: {0} ----\n".format(message))
        config.stderr.flush()
    if config.stdout != sys.stderr and config.stdout != sys.stdout and config.stdout != config.stderr:
        config.stdout.write("\n#---- bot: {0} ----\n".format(message))
        config.stdout.flush()
