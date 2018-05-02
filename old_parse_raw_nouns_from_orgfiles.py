import sys
from re import compile, match
from collections import deque
from abc import ABC, abstractmethod
from datetime import datetime


class LineFormatError(Exception):
    """Exception encountered when a line to be parsed is not in the format
    needed to be extracted by the parser

    """

    def __init__(self, message):
        self.message = message


class ParseResult(ABC):
    """A class that knows how to create flashcards from a result of parsing
    a line of a file. This abstract class does nothing, but it's subclasses
    know how to make flashcards for their particular sorts of line formats.

    """

    @abstractmethod
    def _create_flashcards(*args):
        pass


# # TODO I stopped here
# class SimplePhrase(ParseResult):
#     """A class that knows how to create flashcards from a sim

#     """

#     def _create_flashcards(self):
#         pass


class OldNoun(ParseResult):
    """A class that knows how to create flashcards (from a result of
    parsing a line) for old nouns (nouns that the user knows but is a
    bit shaky on the details).

    """

    def __init__(self, noun_dict):
        self._create_flashcards(noun_dict)

    def _create_flashcards(self, noun_dict):
        """Creates flashcards from the singular, translation and plural of a
        noun.
        
        Arg is a dictionary with keys singular, plural (optional) and
        translation.  Output is a list of strings to be directly printed
        to an org file and used with org-drill as flashcards.  Hence a
        header is added to each flashcard and the *** signs used in
        org-mode trees hierarchy.

        """

        singular = noun_dict.get("singular")
        plural = noun_dict.get("plural")
        self.flashcard_lines = deque()

        ROOT_DEPTH = 2
        FRONTSIDE_DEPTH = 3
        BACKSIDE_DEPTH = 4
        FILL_TO_TAG = 30

        self.flashcard_lines.append(ROOT_DEPTH * "*" + " " + singular +
                                    "\n")

        (_, _, noun_wo_article) = singular.partition(" ")
        self.flashcard_lines.append((FRONTSIDE_DEPTH * "*" + " i1")
                                    .ljust(FILL_TO_TAG) + ":drill:\n")
        self.flashcard_lines.append("Rod od *" + noun_wo_article + "*\n")
        self.flashcard_lines.append(BACKSIDE_DEPTH * "*" + " o\n")
        self.flashcard_lines.append(singular + "\n")

        if plural is None:
            return

        self.flashcard_lines.append((FRONTSIDE_DEPTH * "*" + " i3")
                                    .ljust(FILL_TO_TAG) + ":drill:\n")
        self.flashcard_lines.append("mnoÅ¾ina od *" + singular +
                                    "*\n")
        self.flashcard_lines.append(BACKSIDE_DEPTH * "*" + " o\n")
        self.flashcard_lines.append(plural + "\n")

        self.flashcard_lines.append((FRONTSIDE_DEPTH * "*" + " i4")
                                    .ljust(FILL_TO_TAG) + ":drill:\n")
        self.flashcard_lines.append("jednina od *" + plural +
                                    "*\n")
        self.flashcard_lines.append(BACKSIDE_DEPTH * "*" + " o\n")
        self.flashcard_lines.append(singular + "\n")


class NewNoun(ParseResult):
    """A class that knows how to create flashcards (from a result of
    parsing a line) for new nouns (nouns that the user doesn't know
    yet).

    """

    def __init__(self, noun_dict):
        self._create_flashcards(noun_dict)

    def _create_flashcards(self, noun_dict):
        """Creates flashcards from the singular, translation and plural of a
        noun.
        
        Arg is a dictionary with keys singular, plural (optional) and
        translation.  Output is a list of strings to be directly printed
        to an org file and used with org-drill as flashcards.  Hence a
        header is added to each flashcard and the *** signs used in
        org-mode trees hierarchy.

        """

        singular = noun_dict.get("singular")
        plural = noun_dict.get("plural")
        translation = noun_dict.get("translation")
        self.flashcard_lines = deque()

        ROOT_DEPTH = 2
        FRONTSIDE_DEPTH = 3
        BACKSIDE_DEPTH = 4
        FILL_TO_TAG = 30

        self.flashcard_lines.append(ROOT_DEPTH * "*" + " " + singular +
                                    "\n")

        self.flashcard_lines.append((FRONTSIDE_DEPTH * "*" + " i1")
                                    .ljust(FILL_TO_TAG) + ":drill:\n")
        self.flashcard_lines.append(translation + "\n")
        self.flashcard_lines.append(BACKSIDE_DEPTH * "*" + " o\n")
        self.flashcard_lines.append(singular + "\n")

        self.flashcard_lines.append((FRONTSIDE_DEPTH * "*" + " i2")
                                    .ljust(FILL_TO_TAG) + ":drill:\n")
        self.flashcard_lines.append('*' + singular + "*\n")
        self.flashcard_lines.append(BACKSIDE_DEPTH * "*" + " o\n")
        self.flashcard_lines.append(translation + "\n")

        if plural is None:
            return

        self.flashcard_lines.append((FRONTSIDE_DEPTH * "*" + " i3")
                                    .ljust(FILL_TO_TAG) + ":drill:\n")
        self.flashcard_lines.append("množina od *" + singular +
                                    "*\n")
        self.flashcard_lines.append(BACKSIDE_DEPTH * "*" + " o\n")
        self.flashcard_lines.append(plural + "\n")

        self.flashcard_lines.append((FRONTSIDE_DEPTH * "*" + " i4")
                                    .ljust(FILL_TO_TAG) + ":drill:\n")
        self.flashcard_lines.append("jednina od *" + plural +
                                    "*\n")
        self.flashcard_lines.append(BACKSIDE_DEPTH * "*" + " o\n")
        self.flashcard_lines.append(singular + "\n")


def parse_noun(line):
    """Tries to parse a line containing singular, translation and (maybe)
    plural of a noun.

    If it fails in parsing a noun, a LineFormatError is raised.
    """
    # regex for a noun for which plural is explicitly written
    match = compile("- ([Dd]er|[Dd]ie|[Dd]as) (\\w+), ([Dd]ie \\w+) ="
                    " ([\\w,;() ]+)\n").fullmatch(line)
    if match:
        singular = match.group(1) + " " + match.group(2)
        plural = match.group(3)
        translation = match.group(4)
        return {"singular": singular, "plural": plural, "translation": translation}

    # regex for when only the plural ending is written, and the full
    # plural is to be created from the singular and ending
    match = compile("- ([Dd]er|[Dd]ie|[Dd]as) (\\w+), (-?\\w*) = "
                    "([\\w,;() ]+)\n").fullmatch(line)
    if match:
        singular = match.group(1) + " " + match.group(2)
        if match.group(3) == '-':
            plural = "die " + singular[4:]
        else:
            if match.group(3).startswith('-'):
                suffix = match.group(3)[1:]
            else:
                suffix = match.group(3)
            plural = "die " + singular[4:] + suffix
        translation = match.group(4)
        return {"singular": singular, "plural": plural, "translation": translation}

    # regex for a noun with the plural form ommited completely
    match = compile("- ([Dd]er|[Dd]ie|[Dd]as) (\\w+) = ([\\w,;() ]+)"
                    "\n").fullmatch(line)
    if match:
        singular = match.group(1) + " " + match.group(2)
        translation = match.group(3)
        return {"singular": singular, "translation": translation}

    raise LineFormatError("Not a noun")


def parse_line(line):
    """Takes a line of org-mode text file (a string) and tries to extract
    a foreign word or phrase, it's translation and possibly additional
    data. TODO currently only nouns are supported

    The return value is a ParseResult object instance.
    """

    if line.startswith("- (o)"):
        try:
            return OldNoun(parse_noun("- " + line[6:]))  # (o) gets omitted
        except LineFormatError:
            pass # it's probably just a verb or something
        except IndexError: # could be raised because of line[6:], but shouldn't
            raise LineFormatError("Something's wrong here, IndexError was raised")
    try:
        return NewNoun(parse_noun(line))
    except LineFormatError:
        raise
    # try:
    #     return SimplePhrase(parse_simple_phrase(line)) TODO


def read_lines(src_file):
    """Reads all lines in the file src_file, parses them, extracts and
    saves german nouns in the form suitable for flashcard learning --
    returning it as a list of lines (strings) ready to be written to a file.

    """

    flashcards = deque()
    flashcards.append("* flashcards\n" + str(datetime.now()))  # first line is header for file
    line_counter = 0
    for line in src_file:
        line_counter += 1
        try:
            if line.startswith('*'):  # TODO change this maybe?  The
                                      # point of this was to allow one
                                      # file to be used to collect
                                      # new, unprocessed words and
                                      # also to collect words to be
                                      # made into cards
                break
            parse_result = parse_line(line)
            flashcards.extend(parse_result.flashcard_lines)
        except LineFormatError as e:
            sys.stderr.write("Bad format at line" + str(line_counter)
                             + " -- " + e.message + "\n")
    return flashcards


def write_lines(file, flashcards):
    """Writes the flashcards (in ready-to-print format) to the file.

    Arg flashcards is a deque of strings to be directly printed to
    file.

    """

    for entry in flashcards:
        file.write(entry)


def __main__():
    """Parses 'german noun'-translation pairs from the passed file
    (argument1), creates from them flashcards usable with org-drill in
    emacs org-mode and writes them into the other passed file
    (argument2).

    """
    # these are default names, but they can be overridden by user input
    f_read_name = "C:/Users/juras/orgtd/newwords.org"
    f_write_name = "C:/Users/juras/orgtd/newflashcards.org"

    if len(sys.argv) == 2 or len(sys.argv) > 3:
        sys.exit("This script expects names of 2 files -- one for reading"
                 " unprocessed words and one for writing processed flashcards."
                 " Expected format: 'script-name read-file-name write-file-name'."
                 " To use default files, pass 0 arguments.  To use default value"
                 " for only one file, write '-' on place of that file's name.")
    if len(sys.argv) == 3:
        if sys.argv[1] != '-':
            f_read_name = sys.argv[1]
        if sys.argv[2] != '-':
            f_write_name = sys.argv[2]

    with open(f_read_name, 'r', encoding="utf-8") as f_read:
        flashcards = read_lines(f_read)

    with open(f_write_name, 'a', encoding="utf-8") as f_write:
        write_lines(f_write, flashcards)


if __name__ == '__main__':
    __main__()
