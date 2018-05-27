import shared
import sys
import configparser
import logging
import sqlite3
from re import compile, match
from shared import Properties, Flashcard, FLASHCARDS_TABLE_NAME, PWCENTRIES_TABLE_NAME


class FileWrapper:
    """A wrapper class around a file that keeps track of the line number
    currently being read, the latest read line and whether EOF is reached.  Every reading of a
    file in the module text2sql.py should be done using a FileWrapper
    instead of reading from a file directly.

    """
    def __init__(self, file):
        self.file = file
        self._linecounter = 0
        self._currentline = None
        self.return_current_line = False
        # return_current_line is to be used in functions that read ahead of what they are supposed
        # to, in order to find the terminator of the text they are to work with.
        # In order for other functions to work normally, those read-ahead functions must
        # notify FileWrapper to "go back" one line.

    def readline(self):
        """While reading a new line, it updates _linecounter and _currentline,
        and also checks if EOF has been reached, in which case OrgEOFError
        is raised.  Some functions will read one line forward from what they're supposed
        to process (in order to determine stopping conditions), in which case
        they must set self.return_current_line to True so that
        the next call to self.readline() gets the correct line.
        """
        if self.return_current_line and (self._currentline is not None):
            self.return_current_line = False
            return self._currentline
        self._currentline = self.file.readline()
        if self._currentline == '':
            raise OrgEOFError
        self._linecounter += 1
        return self._currentline

    def getlinecounter(self):
        return self._linecounter

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            return self.file.__exit__(exc_type, exc_val, exc_tb)
        else:
            logging.critical("Error occured while reading file " + self.file.name,
                             exc_info=True)
            self.file.__exit__(exc_type, exc_val, exc_tb)
            sys.exit(1)


class OrgEOFError(Exception):
    """An exception that is thrown when the FileWrapper is being read and
    EOF has been reached.

    """
    def __init__(self):
        pass


class OrgLineFormatError(Exception):
    """An exception that occurs when wrong/unexpected format in an org
    file is noticed.

    """
    def __init__(self, filewrp, message):
        """Expected argument is a FileWrapper object.

        """
        self.linecounter = filewrp.getlinecounter()
        self.currentline = filewrp._currentline
        self.message = message


def is_org_header(line):
    """Checks if 'line' is a header of org file.

    >>> is_org_header("* Foo")
    True
    >>> is_org_header("*Foo")
    False
    >>> is_org_header('* Foo\\n')
    True
    """
    try:
        if line[0] != '*':
            return False
    except IndexError:
        return False
    for character in line[1:]:
        if character == '*':
            continue
        elif character == ' ':
            return True
        else:
            return False


def is_drill_header(line):
    """Checks if line is a drill header.

    """
    if is_org_header(line) and line.strip().endswith(":drill:"):
        return True
    else:
        return False


def extract_properties(filewrp):
    """
    Given a FileWrapper object instances, reads lines from it that contain
    org-mode PROPERTIES (that are used in org-drill) and also the value of
    SCHEDULED in org-mode.  Creates and returns a Properties object instance.
    :param filewrp: a FileWrapper object around a file in read mode.
    :return: Properties object instance from which a Flashcard object instance
            can be created.
    """
    lineformat_re = compile(":(\\w+):([\\w\\s.\\[\\]:-]+)")
    while True:
        line = filewrp.readline().strip()
        if line == ":PROPERTIES:":
            continue
        elif line == ":END:":
            try:
                return Properties(scheduled, id, dli, drsf, dtr, dfc, daq,
                              de, dlq, dlr)
            except NameError:
                raise OrgLineFormatError(filewrp, "A property that should "
                                                  "have been defined wasn't defined.")
        elif line == '':
            continue
        elif line.startswith("SCHEDULED:"):
            (_, _, scheduled) = line.partition("SCHEDULED:")
            if scheduled == "":
                raise OrgLineFormatError(filewrp, "Error in the format"
                                         " of 'SCHEDULED'")
            scheduled = scheduled.strip()
            continue

        m = lineformat_re.match(line)
        if not m:
            raise OrgLineFormatError(filewrp, "Line doesn't contain org-mode property.")

        name = m.group(1)
        value = m.group(2).strip()

        if name == "ID":
            id = value
        elif name == "DRILL_LAST_INTERVAL":
            dli = float(value)
        elif name == "DRILL_REPEATS_SINCE_FAIL":
            drsf = int(value)
        elif name == "DRILL_TOTAL_REPEATS":
            dtr = int(value)
        elif name == "DRILL_FAILURE_COUNT":
            dfc = int(value)
        elif name == "DRILL_AVERAGE_QUALITY":
            daq = float(value)
        elif name == "DRILL_EASE":
            de = float(value)
        elif name == "DRILL_LAST_QUALITY":
            dlq = int(value)
        elif name == "DRILL_LAST_REVIEWED":
            dlr = value
        else:
            raise OrgLineFormatError(filewrp, "Unexpected property " + name)


def extract_flashcard(filewrp, pwce_name):
    """
    Given the FileWrapper object instance, reads lines from it that pertain
    to an org-drill item (a flashcard) and from this, a Flashcard object instance
    is created.
    :param filewrp: a FileWrapper object around a file in read mode.
    :param pwce_name: PWCEntry name for current flashcards
    :return: a Flashcard object instance.
    """
    front = []
    back = []
    properties = extract_properties(filewrp)
    line = filewrp.readline()
    while not is_org_header(line):
        front.append(line)
        line = filewrp.readline()
    line = filewrp.readline()
    while not is_org_header(line):
        back.append(line)
        try:
            line = filewrp.readline()
        except OrgEOFError:  # EOF is expected in this function
            break
    else:
        filewrp.return_current_line = True
    flashcard = Flashcard(SCHEDULED=properties.SCHEDULED,
                          ID=properties.ID,
                          FRONT="".join(front).strip(),
                          BACK="".join(back).strip(),
                          PWCENTRY=pwce_name,
                          DRILL_LAST_INTERVAL=properties.DRILL_LAST_INTERVAL,
                          DRILL_REPEATS_SINCE_FAIL=properties.DRILL_REPEATS_SINCE_FAIL,
                          DRILL_TOTAL_REPEATS=properties.DRILL_TOTAL_REPEATS,
                          DRILL_FAILURE_COUNT=properties.DRILL_FAILURE_COUNT,
                          DRILL_AVERAGE_QUALITY=properties.DRILL_AVERAGE_QUALITY,
                          DRILL_EASE=properties.DRILL_EASE,
                          DRILL_LAST_QUALITY=properties.DRILL_LAST_QUALITY,
                          DRILL_LAST_REVIEWED=properties.DRILL_LAST_REVIEWED)
    return flashcard


def extract_pwce_name(line):
    """Extract the pwce_name (a noun, a verb, an adjective, a phrase etc)
    from a header.

    >>> extract_pwce_name("*** Die Kurve\\n")
    'Die Kurve'
    >>> extract_pwce_name("*     Der Stuhl")
    'Der Stuhl'
    """
    regex = compile("(\\*+) ([\w\s]+)")
    m = regex.match(line)
    pwce_name = m.group(2).strip()
    return pwce_name


def insert_pwce_name_into_db(pwce_name, db_connection):
    """
    Inserts a pwce_name into table PWCENTRIES_TABLE_NAME (if it doesn't exist).
    :return:
    """
    try:
        db_connection.execute("INSERT INTO {0} (NAME) VALUES (?);".format(PWCENTRIES_TABLE_NAME),
                              (pwce_name,))
        db_connection.commit()
    except sqlite3.IntegrityError:
        pass
        # this just means this pwcentry already exists in the database which is fine
        # I don't want to use 'INSERT OR REPLACE' because that deltes the pwce_entry
        # and so the data in the FLASHCARDS_TABLE_NAME database is lost too


def insert_flashcard_into_db(flashcard: Flashcard, db_connection: sqlite3.Connection):
    """
    Inserts a single flashcard into the database.
    :param flashcard: Flashcard object instance
    :param db_connection: sqlite3.Connection object instance, a database
    :return: True if flashcard was successfully added to the database, False otherwise
    """
    insert_pwce_name_into_db(flashcard.PWCENTRY, db_connection)
    try:
        pwce_id = db_connection.execute("select ID from {0} where name = ?;".format(
                                        PWCENTRIES_TABLE_NAME),
                                        (flashcard.PWCENTRY,)).fetchone()
        pwce_id = pwce_id[0]
    except (sqlite3.OperationalError, IndexError):
        logging.warning("Error occurred while writing flashcard " + flashcard.ID
                        + " to the database.", exc_info=True)
        return False

    try:
        db_connection.execute("""
            insert or replace into {0} (
                 ID, SCHEDULED, FRONT, BACK,
                 DRILL_LAST_INTERVAL, DRILL_REPEATS_SINCE_FAIL,
                 DRILL_TOTAL_REPEATS, DRILL_FAILURE_COUNT,
                 DRILL_AVERAGE_QUALITY, DRILL_EASE,
                 DRILL_LAST_QUALITY, DRILL_LAST_REVIEWED,
                 PWCE_ID
            ) values (
                ?, date(?), ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,
                ?
            );
        """.format(FLASHCARDS_TABLE_NAME), flashcard._replace(
            SCHEDULED=flashcard.SCHEDULED[1:11], PWCENTRY=pwce_id))
        db_connection.commit()
    except sqlite3.IntegrityError:
        logging.warning("Error occured while writing flashcard " + flashcard.ID
                        + " to the database.", exc_info=True)
        return False
    except sqlite3.DatabaseError:
        logging.critical("Error occured while writing flashcard " + flashcard.ID
                         + " to the database. Quitting.", exc_info=True)
        sys.exit(1)
    return True


def read_and_save_flashcards(filewrp, db_connection):
    """Reads an org-mode file and parses Flashcard objects from org-drill style
    flashcards, and writes it to a database in parallel.
    :param filewrp: FileWrapper over file from which Flashcard instances are parsed
    :param db_connection: sqlite3.Connection instance to the database for storing flashcards
    :return: number of flashcards correctly parsed
    """
    pwce_name = None
    flashcards_counter = 0
    while True:
        try:
            line = filewrp.readline()  # Raises ORGEOFError when file is finished
            if is_drill_header(line):
                if pwce_name is None:
                    raise OrgLineFormatError(filewrp,
                                             "pwce_name is None but should"
                                             " have been set. Skipping flashcard")
                flashcard = extract_flashcard(filewrp, pwce_name)
                if insert_flashcard_into_db(flashcard, db_connection):
                    flashcards_counter += 1
            elif is_org_header(line):
                pwce_name = extract_pwce_name(line)
                # filewrp.readline()
            else:
                # Empty line, a comment, or an error happened in the middle of parsing
                # a flashcard.  So now go forward until the next org header.
                continue
        except OrgLineFormatError as exc:
            logging.warning("OrgLineFormatError at line" +
                            str(exc.linecounter) +
                            ": '" + exc.message + "'. line = '" +
                            exc.currentline)
        except OrgEOFError:
            break
    return flashcards_counter





def inspect_database(db_connection: sqlite3.Connection):
    """Creates tables 'flashcards' and 'pwce_entries' if they don't exist.
    Also serves as a reminder of the structure of those tables."""

    db_connection.execute("""
        create table if not exists {0} (
            ID integer primary key,
            NAME text unique not null
        );
    """.format(PWCENTRIES_TABLE_NAME))

    db_connection.execute("""
        create table if not exists {0} (
            ID text primary key,
            SCHEDULED text not null,
            FRONT text not null,
            BACK text not null,
            DRILL_LAST_INTERVAL real not null,
            DRILL_REPEATS_SINCE_FAIL integer not null,
            DRILL_TOTAL_REPEATS integer not null,
            DRILL_FAILURE_COUNT integer not null,
            DRILL_AVERAGE_QUALITY real not null,
            DRILL_EASE real not null,
            DRILL_LAST_QUALITY integer not null,
            DRILL_LAST_REVIEWED text not null,
            PWCE_ID integer,
            foreign key (PWCE_ID)
              references {1} (ID)
              on delete set null
              on update cascade
        );
    """.format(FLASHCARDS_TABLE_NAME, PWCENTRIES_TABLE_NAME))
    db_connection.commit()


def read_configuration():
    """Reads paths to the orgfile and database file from a configuration file.
    :return: a tuple (orfile_path, db_path)
    """
    config_parser = configparser.ConfigParser()
    if not config_parser.read('config'):
        logging.critical("Can't find configuration file. Quitting.")
        sys.exit(1)

    try:
        section_dict = config_parser['file_paths']
        db_path = section_dict['db_path']
        orgfile_path = section_dict['orgfile_worte_read_path']
    except KeyError as e:
        logging.critical("Missing a config property.  KeyError was raised on " + str(e.args))
        sys.exit(1)
    return orgfile_path, db_path


def __main__():
    """
    Reads an org-mode file containing org-drill flashcards, creates Flashcard
    object instances and writes them into database.
    :return:
    """

    with shared.logging_context():
        orgfile_path, db_path = read_configuration()
        try:
            filewrp = FileWrapper(open(orgfile_path, 'r', encoding="utf-8"))
        except IOError as e:
            logging.critical("An exception occured while opening file " + orgfile_path,
                             exc_info=True)
            sys.exit(1)
        try:
            db_connection = sqlite3.Connection(db_path)
            inspect_database(db_connection)
        except sqlite3.Error:
            logging.critical("An exception occured while starting connection to database"
                             " or creating one of the tables.",
                             exc_info=True)
            sys.exit(1)
        # all db_connection.__exit__() does is commit() or rollback().
        # I must close manually and exceptions are not suppressed (which is fine with me),
        # it gets reported by logging __exit__()
        with filewrp, db_connection:
            flashcards_counter = read_and_save_flashcards(filewrp, db_connection)
        db_connection.close()
        logging.info("Successfully parsed " + str(flashcards_counter) + " flashcards.")
        print("Successfully parsed", flashcards_counter, "flashcards. Press RETURN to finish.")
        input()


if __name__ == "__main__":
    __main__()

# TODO update docstrings if you did any changes
