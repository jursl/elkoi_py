import sys
import sqlite3
import doctest
from collections import namedtuple
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

    def readline(self):
        """While reading a new line, it updates _linecounter and _currentline,
        and also checks if EOF has been reached, in which case OrgEOFError
        is raised.

        """
        self._currentline = self.file.readline()
        if self._currentline == '':
            raise OrgEOFError
        self._linecounter += 1
        return self._currentline

    def getlinecounter(self):
        return self._linecounter

    def getcurrentline(self):
        """Gets _currentline, but also checks if EOF has been reached,
        and if so, OrgEOFError is raised.

        """
        if self._currentline == '':
            raise OrgEOFError
        return self._currentline

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
        self.currentline = filewrp.getcurrentline()
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
Properties = namedtuple('Properties',('SCHEDULED', 'ID', 'DRILL_LAST_INTERVAL',
                                       'DRILL_REPEATS_SINCE_FAIL',
                                       'DRILL_TOTAL_REPEATS',
                                       'DRILL_FAILURE_COUNT',
                                       'DRILL_AVERAGE_QUALITY',
                                       'DRILL_EASE',
                                       'DRILL_LAST_QUALITY', 'DRILL_LAST_REVIEWED'))

Flashcard = namedtuple("Flashcard", ('FRONT', 'BACK') + Properties._fields)

# # TODO WHAT ABOUT PWCE_ID?
# Flashcard = namedtuple("Flashcard", ['SCHEDULED', 'ID', 'FRONT',
#                                      'BACK', 'DRILL_LAST_INTERVAL',
#                                      'DRILL_REPEATS_SINCE_FAIL',
#                                      'DRILL_TOTAL_REPEATS',
#                                      'DRILL_FAILURE_COUNT',
#                                      'DRILL_AVERAGE_QUALITY',
#                                      'DRILL_EASE',
#                                      'DRILL_LAST_QUALITY', 'DRILL_LAST_REVIEWED'])


def extract_properties(filewrp):
    """Returns a Properties object from properties of a drill item,
    as read from the file.

    """
    # TAG_CHARS = "\\w\\.\\[\\]:-"
    # lineformat_re = compile(":(\\w+):\\s+([" +TAG_CHARS+ "]+)")
    lineformat_re = compile(":(\\w+):([\\w\\s.\\[\\]:-]+)")
    while True:
        line = filewrp.readline().strip()
        if line == ":PROPERTIES:":
            continue
        elif line == ":END:":
            return Properties(scheduled, id, dli, drsf, dtr, dfc, daq,
                              de, dlq, dlr)
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
        # TODO add checking if match is None? raises OrgLineFormatError
        name = m.group(1)
        value = m.group(2).strip()

        if name == "ID":
            id = value
        elif name == "DRILL_LAST_INTERVAL":
            dli = value
        elif name == "DRILL_REPEATS_SINCE_FAIL":
            drsf = value
        elif name == "DRILL_TOTAL_REPEATS":
            dtr = value
        elif name == "DRILL_FAILURE_COUNT":
            dfc = value
        elif name == "DRILL_AVERAGE_QUALITY":
            daq = value
        elif name == "DRILL_EASE":
            de = value
        elif name == "DRILL_LAST_QUALITY":
            dlq = value
        elif name == "DRILL_LAST_REVIEWED":
            dlr = value
        else:
            # TODO ADD FOR PROPERTY :PWCE_ID: ?
            raise OrgLineFormatError(filewrp, "Unexpected property " + name)


def extract_flashcard(filewrp):
    """'filewrp' is a FileWrapper object around a file in read mode.
    Returns a Flashcard object instance.

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
        except OrgEOFError: # EOF is expected in this function
            break
    flashcard = Flashcard(SCHEDULED=properties.SCHEDULED,
                          ID=properties.ID,
                          FRONT="".join(front).strip(),
                          BACK="".join(back).strip(),
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


def print_flashcards(fc_dict, w_file):
    """fc_dict is a dictionary of (pwce,list of flashcard) pairs; this
    function prints it to w_file.

    """
    for pwce, flashcards in fc_dict.items():
        w_file.write(pwce.ljust(20)+"\n")
        for flashcard in flashcards:
            for field in flashcard._fields:
                w_file.write(20*" " + field.ljust(20) + "=" +
                             str(getattr(flashcard, field)) + "\n")


def read_flashcards_from_file(filewrp):
    """Reads all flashcards in the FileWrapper filewrp and creates fitting
    Flashcard objects for them.

    """
    filewrp.readline()
    fc_dict = {}
    pwce_name = None
    while True:
        try:
            line = filewrp.getcurrentline()
            if is_drill_header(line):
                flashcard = extract_flashcard(filewrp)
                if pwce_name is None:
                    raise OrgLineFormatError(filewrp,
                                             "pwce_name is None but should"
                                             " have been set. Skipping flashcard "
                                             + str(flashcard))
                try:
                    fc_dict[pwce_name].append(flashcard)
                except (KeyError, AttributeError):
                    fc_dict[pwce_name] = [flashcard]
            elif is_org_header(line):
                pwce_name = extract_pwce_name(line)
                filewrp.readline()
            # TODO Sto ako je line nesto drugo ? ovo je beskonacna petlja ako je empty line prvi
            # takodjer, ako se dogodio ORGLineFormatError, onda ce se ovdje ucitavati usred
            # nepravilne kartice, i treba se doci do iduce
            # suggestion:
            # elif line == '' or line.startswith('#'):
            #     filewrp.readline()
            #     continue
            # else:
            #     # ovdje dodaj jos citanje ? (ali kad?)
            #     raise OrgLineFormatError(filewrp, "Unrecognized line format")
        except OrgLineFormatError as exc:
            # TODO DO BETTER LOGGING
            sys.stderr.write("OrgLineFormatError at line",
                             str(exc.linecounter),
                             ": '", exc.message, "'. line = '",
                             exc.currentline, "'\n")
            # TODO dodaj readline ovdje
        except OrgEOFError:
            break
    return fc_dict


def __main__():
    readfile_name = "C:/Users/juras/PycharmProjects/elkoi_py/worte_excerpt.org"
    writefile_name = "C:/Users/juras/PycharmProjects/elkoi_py/parsed-worte_excerpt.org"

    if len(sys.argv) == 2 or len(sys.argv) > 3:
        sys.exit("This script expects names of 2 files -- one for reading"
                 " org-drill flashcards and one for writing processed flashcards." # TODO writing file will have different purpse
                 " Expected format: 'script-name read-file-name write-file-name'."
                 " To use default files, pass 0 arguments.  To use default value"
                 " for only one file, write '-' on place of that file's name.")
    if len(sys.argv) == 3:
        if sys.argv[1] != '-':
            readfile_name = sys.argv[1]
        if sys.argv[2] != '-':
            writefile_name = sys.argv[2]
    with FileWrapper(open(readfile_name, 'r', encoding="utf-8")) as filewrp:
        fc_dict = read_flashcards_from_file(filewrp)
        # TODO also write the flashcards to database (sys.argv[2], in parallel)

    with open(writefile_name, 'w', encoding="utf-8") as file_w:
        print_flashcards(fc_dict, file_w)


if __name__ == "__main__":
    __main__()
