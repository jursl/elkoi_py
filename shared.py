import logging
import contextlib
import sys
import datetime


@contextlib.contextmanager
def logging_context():
    """A context manager that makes sure the enter and exit message is
    logged in any circumstance."""
    try:
        logging.basicConfig(filename='log', level='DEBUG')
        logging.info("=" * 10 + " STARTING " + sys.argv[0] + " ON " + str(datetime.datetime.now())
                     + " " + "=" * 10)
        yield
    finally:
        exit_value = 0
        exc_type, exc_val, exc_traceback = sys.exc_info()
        if exc_type is not None:
            exit_value = 1
            if exc_type is not SystemExit:
                logging.debug("Unhandled exception occurred",
                              exc_info=(exc_type, exc_val, exc_traceback))
        logging.info("=" * 10 + " ENDING " + sys.argv[0] + " ON " + str(datetime.datetime.now())
                     + " " + "=" * 10)
        sys.exit(exit_value)