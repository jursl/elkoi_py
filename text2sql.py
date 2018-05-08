import sys
import doctest
from collections import namedtuple
from sqlite3 import Connection
from re import compile, match


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
        # This is to be used in functions that read ahead of what they are supposed
        # to, in order to find the terminator of the text they are to work with.
        # In order for other functions to work normally, those read-ahead functions must
        # notify FileWrapper to "go back" one line.

    def readline(self):
        """While reading a new line, it updates _linecounter and _currentline,
        and also checks if EOF has been reached, in which case OrgEOFError
        is raised.

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
        return self


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


# like Flashcard but without FRONT, BACK
Properties = namedtuple('Properties', ('SCHEDULED', 'ID', 'DRILL_LAST_INTERVAL',
                                       'DRILL_REPEATS_SINCE_FAIL',
                                       'DRILL_TOTAL_REPEATS',
                                       'DRILL_FAILURE_COUNT',
                                       'DRILL_AVERAGE_QUALITY',
                                       'DRILL_EASE',
                                       'DRILL_LAST_QUALITY', 'DRILL_LAST_REVIEWED'))

Flashcard = namedtuple("Flashcard", ('FRONT', 'BACK', 'PWCENTRY') + Properties._fields)


def extract_properties(filewrp):
    """
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
                raise OrgLineFormatError("A property that should have been defined wasn't defined.")
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
            raise OrgLineFormatError("Line doesn't contain org-mode property.")

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


def insert_flashcard_into_db(flashcard: Flashcard, db_connection: Connection):
    """
    Inserts a single flashcard into the database.
    :param flashcard: Flashcard object instance
    :param db_connection: sqlite3.Connection object instance, a database
    """
    sql = """INSERT INTO flashcards VALUES (
             :ID, :PWCENTRY, :FRONT, :BACK, :SCHEDULED, :DRILL_LAST_INTERVAL,
             :DRILL_REPEATS_SINCE_FAIL, :DRILL_TOTAL_REPEATS,
             :DRILL_FAILURE_COUNT, :DRILL_AVERAGE_QUALITY,
             :DRILL_EASE, :DRILL_LAST_QUALITY, :DRILL_LAST_REVIEWED
          );"""

    db_connection.execute(sql, flashcard._asdict())


def read_and_save_flashcards(filewrp, db_connection):
    """Reads an org-mode file and parses Flashcard objects from org-drill style
    flashcards, and writes it to a database in parallel.
    :param filewrp: FileWrapper over file from which Flashcard instances are parsed
    :param db_connection: sqlite3.Connection instance to the database for storing flashcards
    """
    pwce_name = None
    while True:
        try:
            line = filewrp.readline()  # Raises ORGEOFError when file is finished
            if is_drill_header(line):
                if pwce_name is None:
                    raise OrgLineFormatError(filewrp,
                                             "pwce_name is None but should"
                                             " have been set. Skipping flashcard")
                flashcard = extract_flashcard(filewrp, pwce_name)
                insert_flashcard_into_db(flashcard, db_connection)
            elif is_org_header(line):
                pwce_name = extract_pwce_name(line)
                # filewrp.readline()
            else:
                # Empty line, a comment, or an error happened in the middle of parsing
                # a flashcard.  So now go forward until the next org header is all.
                continue
        except OrgLineFormatError as exc:
            # TODO DO BETTER LOGGING
            sys.stderr.write("OrgLineFormatError at line",
                             str(exc.linecounter),
                             ": '", exc.message, "'. line = '",
                             exc.currentline, "'\n")
        except OrgEOFError:
            break
    db_connection.commit()


def __main__():
    """
    Reads an org-mode file containing org-drill flashcards, creates Flashcard
    object instances and prints them to screen.
    :return:
    """

    readfile_name = "C:/Users/juras/PycharmProjects/elkoi_py/worte_excerpt.org"
    # writefile_name = "C:/Users/juras/PycharmProjects/elkoi_py/parsed-worte_excerpt.org"
    database_name = "C:/Users/juras/elkoi/db/test.db"

    if len(sys.argv) == 2 or len(sys.argv) > 3:
        sys.exit("This script expects names of 2 files -- one for reading"
                 " org-drill flashcards and one for the flashcards database." 
                 # TODO writing file will have different purpse
                 " Expected format: 'script-name read-file-name database-name'."
                 " To use default files, pass 0 arguments.  To use default value"
                 " for only one file, write '-' on place of that file's name.")
    if len(sys.argv) == 3:
        if sys.argv[1] != '-':
            readfile_name = sys.argv[1]
        if sys.argv[2] != '-':
            database_name = sys.argv[2]
    # with FileWrapper(open(readfile_name, 'r', encoding="utf-8")) as filewrp:
    #     db_connection = Connection(database_name)
    #     read_and_save_flashcards(filewrp, db_connection)

    filewrp = FileWrapper(open(readfile_name, 'r', encoding="utf-8"))
    db_connection = Connection(database_name)
    read_and_save_flashcards(filewrp, db_connection)


if __name__ == "__main__":
    __main__()

# TODO update docstrings if you did any changes
