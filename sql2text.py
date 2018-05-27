import shared
import sqlite3
import sys
import logging
import configparser
import datetime
from shared import Flashcard, FLASHCARDS_TABLE_NAME, PWCENTRIES_TABLE_NAME


def write_one_flashcard(flashcard: Flashcard, org_file):
    """
    Writes a single flashcard into an org-mode file.
    :param flashcard:
    :param org_file:
    """
    org_file.write("*"*3 + " q" + " "*30 + ":drill:" + "\n")
    org_file.write(" "*4 + "SCHEDULED: " + flashcard.SCHEDULED + "\n")
    org_file.write(" "*4 + ":PROPERTIES:\n")
    org_file.write(" " * 4 + ':ID: ' + flashcard.ID + '\n')
    org_file.write(" " * 4 + ':DRILL_LAST_INTERVAL: ' + str(flashcard.DRILL_LAST_INTERVAL) + '\n')
    org_file.write(" " * 4 + ':DRILL_REPEATS_SINCE_FAIL: ' + str(flashcard.DRILL_REPEATS_SINCE_FAIL) + "\n")
    org_file.write(" " * 4 + ':DRILL_TOTAL_REPEATS: ' + str(flashcard.DRILL_TOTAL_REPEATS) + "\n")
    org_file.write(" " * 4 + ':DRILL_FAILURE_COUNT: ' + str(flashcard.DRILL_FAILURE_COUNT) + "\n")
    org_file.write(" " * 4 + ':DRILL_AVERAGE_QUALITY: ' + str(flashcard.DRILL_AVERAGE_QUALITY) + "\n")
    org_file.write(" " * 4 + ':DRILL_EASE: ' + str(flashcard.DRILL_EASE) + "\n")
    org_file.write(" " * 4 + ':DRILL_LAST_QUALITY: ' + str(flashcard.DRILL_LAST_QUALITY) + "\n")
    org_file.write(" " * 4 + ':DRILL_LAST_REVIEWED: ' + flashcard.DRILL_LAST_REVIEWED + "\n")
    org_file.write(" " * 4 + ":END:\n")
    org_file.write(flashcard.FRONT + '\n')
    org_file.write("*"*4 + " a\n")
    org_file.write(flashcard.BACK + '\n')


def write_flashcards_to_file(flashcard_dict, org_file):
    """
    Writes flashcards to org-mode file so that they're grouped by pwce entries
    (a pwcentry is a header to which flashcard headers belong).
    :param flashcard_dict: dictionary of (pwcentry, list of flashcards)
    :param org_file: file object in write mode
    :return: number of flashcards written to file correctly
    """
    count = 0
    org_file.write("* Flashcards on " + str(datetime.datetime.now()) + "\n")
    for pwcentry, flashcard_list in flashcard_dict.items():
        org_file.write("** " + pwcentry + "\n")
        for flashcard in flashcard_list:
            write_one_flashcard(flashcard, org_file)
            count += 1
    return count


def sort_flashcards_by_pwcentry(flashcard_list):
    """
    Sorts the Flashcards into a directory by their pwcentry.
    :param flashcard_list: a list of Flashcard instance objects
    :return: dictionary of Flashcard instance objects
    """
    flashcard_dict = {}
    for flashcard in flashcard_list:
        key_in_dict = flashcard_dict.get(flashcard.PWCENTRY)
        if key_in_dict is None:
            flashcard_dict[flashcard.PWCENTRY] = [flashcard]
        else:
            flashcard_dict[flashcard.PWCENTRY].append(flashcard)
    return flashcard_dict


def read_scheduled_flashcards(db_connection: sqlite3.Connection):
    """
    From the database, selects flashcards that are scheduled for review today
    or earlier, and creates Flashcard instance objects from them and returns them in a list.
    :param db_connection:
    :return: A list of Flashcard instance objects
    """
    db_connection.row_factory = sqlite3.Row
    cursor = db_connection.execute(
        """
        select {0}.ID, SCHEDULED, FRONT, BACK, DRILL_LAST_INTERVAL,
               DRILL_REPEATS_SINCE_FAIL, DRILL_TOTAL_REPEATS,
               DRILL_FAILURE_COUNT, DRILL_AVERAGE_QUALITY,
               DRILL_EASE, DRILL_LAST_QUALITY, DRILL_LAST_REVIEWED,
               NAME
        from {0} join {1} on PWCE_ID = {1}.ID
        where julianday('now') >= julianday(SCHEDULED)
        """.format(FLASHCARDS_TABLE_NAME, PWCENTRIES_TABLE_NAME)
    )
    row = cursor.fetchone()
    flashcard_list = []
    while row is not None:
        flashcard = Flashcard._make(row)
        flashcard = flashcard._replace(SCHEDULED=('<'+flashcard.SCHEDULED+'>'))
        flashcard_list.append(flashcard)
        row = cursor.fetchone()
    return flashcard_list


def read_configuration():
    """Reads from config file paths to org-file and database file.
    :return a tuple (orgfile_path, db_path)
    """
    # log critical and sys.exit if properties not found
    config_parser = configparser.ConfigParser()
    if not config_parser.read('config'):
        logging.critical("Config file not found.  Quitting.")
        sys.exit(1)
    try:
        config_dict = config_parser['file_paths']
        orgfile_path = config_dict['orgfile_worte_write_path']
        db_path = config_dict['db_path']
    except KeyError as e:
        logging.critical("Missing a config property.  KeyError was raised on " + str(e.args))
        sys.exit(1)
    return orgfile_path, db_path


def __main__():
    """
    Reads flashcards due for review from the database and writes them into
    an org-mode file in format for org-dril.
    :return:
    """
    with shared.logging_context():
        orgfile_path, db_path = read_configuration()
        try:
            db_connection = sqlite3.connect(db_path)
        except sqlite3.Error as e:
            logging.critical("An error occured while opening database " + db_path + ".",
                             exc_info=True)
            sys.exit(1)
        flashcard_list = read_scheduled_flashcards(db_connection)
        db_connection.close()
        flashcard_dict = sort_flashcards_by_pwcentry(flashcard_list)
        with open(orgfile_path, 'a', encoding='utf-8') as org_file:
            count = write_flashcards_to_file(flashcard_dict, org_file)
        logging.info("Successfully wrote " + str(count) + " flashcards into file.")
        print("Successfully wrote", count, "flashcards into file. Press RETURN to finish.")
        input()


if __name__ == "__main__":
    __main__()

# TODO (if you changed anything) update docstrings?
