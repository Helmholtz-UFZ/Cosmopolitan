import datetime
import os

DEV_MODE = True
# 0 means silence, 3 is highest level of verbosity
VERBOSE_LEVEL = 3
WORK_DIR = "./"
# Directory where files are first uploaded and then checked
UPLOAD_DIR = os.path.join(WORK_DIR, "upload")
# The directory for the input files that have been validated.
INPUT_DIR = os.path.join(WORK_DIR, "input")


def check_verbose_level(verbose_level):
    """Check if verbose level is in correct form."""
    if not isinstance(verbose_level, int):
        raise ValueError("verbose level must be an integer")
    if 0 > verbose_level > 3:
        raise ValueError("verbose level must be between 0 and 3")


def vprint(msg, verbose_level=0):
    """Print to verbose."""
    check_verbose_level(verbose_level)
    msg = datetime.datetime.today().strftime("[%d/%b/%Y %H:%M:%S] - - ") + str(msg)
    if verbose_level <= VERBOSE_LEVEL:
        if DEV_MODE:
            print(msg)
        else:
            # TODO Logging
            raise NotImplementedError
