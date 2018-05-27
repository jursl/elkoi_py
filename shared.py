import logging
import contextlib
import sys
import datetime
from collections import namedtuple


# saved as a constant because names of tables my change
FLASHCARDS_TABLE_NAME = 'flashcards'
PWCENTRIES_TABLE_NAME = 'pwcentries'


# NOTE: The difference between this tuple and a row in table FLASHCARDS_TABLE_NAME
# is 'PWCENTRY'. Here it's PWCENTRY, there it's PWCE_ID
# The order of the elements of this tuple is the same as attributes in table FLASHCARDS_TABLE_NAME
Flashcard = namedtuple("Flashcard", ('ID', 'SCHEDULED', 'FRONT', 'BACK', 'DRILL_LAST_INTERVAL',
                                     'DRILL_REPEATS_SINCE_FAIL',
                                     'DRILL_TOTAL_REPEATS',
                                     'DRILL_FAILURE_COUNT',
                                     'DRILL_AVERAGE_QUALITY',
                                     'DRILL_EASE',
                                     'DRILL_LAST_QUALITY', 'DRILL_LAST_REVIEWED',
                                     'PWCENTRY'))

# # like Flashcard but without FRONT, BACK
# the order of the elements of this tuple is the same as the properties in an org-mode file
Properties = namedtuple('Properties', ('SCHEDULED', 'ID', 'DRILL_LAST_INTERVAL',
                                       'DRILL_REPEATS_SINCE_FAIL',
                                       'DRILL_TOTAL_REPEATS',
                                       'DRILL_FAILURE_COUNT',
                                       'DRILL_AVERAGE_QUALITY',
                                       'DRILL_EASE',
                                       'DRILL_LAST_QUALITY', 'DRILL_LAST_REVIEWED'))

@contextlib.contextmanager
def logging_context():
    """A context manager that makes sure the enter and exit message is
    logged in any circumstance."""
    try:
        logging.basicConfig(filename='log', level='DEBUG')
        logging.info("\n\n" + "=" * 10 + " STARTING " + sys.argv[0] + " ON "
                     + str(datetime.datetime.now())
                     + " " + "=" * 10 + "\n\n")
        yield
    finally:
        exit_value = 0
        exc_type, exc_val, exc_traceback = sys.exc_info()
        if exc_type is not None:
            exit_value = 1
            if exc_type is not SystemExit:
                logging.debug("Unhandled exception occurred",
                              exc_info=(exc_type, exc_val, exc_traceback))
        logging.info("\n\n" + "=" * 10 + " ENDING " + sys.argv[0] + " ON "
                     + str(datetime.datetime.now())
                     + " " + "=" * 10 + "\n\n")
        sys.exit(exit_value)