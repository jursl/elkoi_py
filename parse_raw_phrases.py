import sys
from re import compile, match
from collections import deque
from abc import ABC, abstractmethod
from datetime import datetime


class ReadFileWrapper:
    """A wrapper class around the file that is being read from.

    This wrapper is an iterable and an iterator over items within the file.
    The client of this class should use it only as an iterator over the items
    and not read lines directly.
    """

    def __init__(self, file):
        self.line_counter = 0
        self._file = file
        self._end_reached = False
        self._current_item_first_line = None

    def _readline(self):
        """Read from file and do necessary wrapper's maintenance.

        :return: latest read line
        """
        line = self._file.readline()
        if line == '':
            raise StopIteration
        self.line_counter += 1
        return line

    def __iter__(self):
        return self

    def _wnr_current_item(self, next_item_first_line):
        """'wnr' stands for 'wrap up and return' -- this method takes
        all the lines that belong to an item (within a deque) and wraps them up
        in a string and returns them.

        :return: string -- the clines that compose the current org-mode item in file
        """

        self._current_item.insert(0, self._current_item_first_line)
        self._current_item_first_line = next_item_first_line
        return "".join(self._current_item)

    def __next__(self):
        """Reads 1 or more lines and returns the next item as found in file.

        :return: A string -- the lines that compose the current org-mode item in file
        """

        if self._end_reached:
            raise StopIteration

        self._current_item = deque()

        try:
            while not self._end_reached:    # this may as well be "while True" but let's leave it like this
                                            # to show the purpose of the while loop
                line = self._readline()  # can raise StopIteration
                if line.startswith("- "):
                    if self._current_item_first_line is None:
                        self._current_item_first_line = line
                        continue
                    else:
                        return self._wnr_current_item(line)
                elif line.startswith("  "):
                    self._current_item.append(line)
                elif line.startswith("#"):
                    continue
                elif line.isspace():
                    continue
                else:
                    raise StopIteration
        except StopIteration:
            self._end_reached = True
            return self._wnr_current_item('')

        # while not self._end_reached:
        #     try:
        #         line = self._readline()
        #     except StopIteration:
        #         self._end_reached = True
        #         return self._wnr_current_item('')
        #
        #     if line.startswith("- "):
        #         if self._current_item_first_line is None:
        #             self._current_item_first_line = line
        #             continue
        #         else:
        #             return self._wnr_current_item(line)
        #     elif line.startswith("  "):
        #         self._current_item.append(line)
        #     elif line.startswith("#"):
        #         continue
        #     elif line.isspace():
        #         continue
        #     else:
        #         self._end_reached = True
        #         raise StopIteration
        #
        # if self._end_reached:
        #     raise StopIteration

        # self._current_item = deque()
        # try:
        #     while not self._end_reached:
        #         line = self._readline()
        #         if line.startswith("- "):
        #             if self._current_item_first_line is None:
        #                 self._current_item_first_line = line
        #                 continue
        #             else:
        #                 return self._wnr_current_item(line)
        #         elif line.startswith("  "):
        #             self._current_item.append(line)
        #         elif line.startswith("#"):
        #             continue
        #         elif line.isspace():
        #             continue
        #         else:
        #             raise StopIteration
        # except StopIteration:
        #     if self._end_reached:
        #         raise
        #     else:
        #         self._end_reached = True
        #         return self._wnr_current_item('')
        # if self._end_reached:
        #     raise StopIteration

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return self._file.__exit__(*args)


class ItemFormatError(Exception):
    """Exception thrown when the item that is being parsed is in an unrecognized
    format or errors were made.

    """

    def __init__(self, message):
        """

        :param message: Write only the basic context of the error, i.e. what format
        the currently executing method was trying to confirm.
        """
        self.message = message


class ParseResult(ABC):
    """A class that knows how to create flashcards from an org-mode item.
    This class is abstract, but it's subclasses know how to make flashcards
    for their particular sorts of item formats.

    The subclasses are assumed to have data attribute 'flashcard_lines'.
    """

    ROOT_DEPTH = 2
    FRONTSIDE_DEPTH = 3
    BACKSIDE_DEPTH = 4
    FILL_TO_TAG = 30

    # TODO add __init__() that calls _set_header instead of calling it from subclasses?
    # _set_header() initializes flashcard_lines which doesn't belong in this method,
    # or rather it should belong in __init__()

    def _set_header(self, header):
        """
        This should be called before first call of _add_card method from within
        concrete _create_flashcards() methods.
        :param header:
        :return:
        """
        self.flashcard_lines = deque()
        self.flashcard_lines.append(self.ROOT_DEPTH * "*" + " " + header + "\n")

    def _add_card(self, question, answer, qheader='q', aheader='a'):
        """"It creates the string of a single org-drill style card with
        question-and-answer pair.

        This should be called from within _create_flashcards within
        subclasses of ParseResult after text that goes into cards is parsed.
        """
        self.flashcard_lines.append((self.FRONTSIDE_DEPTH * "*" + " " + qheader)
                                    .ljust(self.FILL_TO_TAG) + ":drill:\n")
        self.flashcard_lines.append(question + "\n")
        self.flashcard_lines.append(self.BACKSIDE_DEPTH * "*" + " " + aheader + "\n")
        self.flashcard_lines.append(answer + "\n")

    @abstractmethod
    def _create_flashcards(*args):
        pass


class SimplePair(ParseResult):
    """A class that knows how to create flashcards from a simple pair
    "german phrase = translation".

    """

    def __init__(self, item):
        self._create_flashcards(item)

    def _apply_special_tags(self, front_tags, tagless_text, back_tags):
        """Find special tags in 'front_tags', edit the 'tagless_text'
        in accordance, and remove the special tags from 'front_tags'.
        Currently supported special tags are '<eng>', '<*>' and </>.

        :return: 'front_tags' but without special tags, concatenated to the
        new form of 'tagless_text' and then back_tags
        """
        star_index = front_tags.find("<*>")
        if star_index != -1:
            tagless_text = "*" + tagless_text + "*"
            front_tags = front_tags.replace("<*>", "")

        slash_index = front_tags.find("</>")
        if slash_index != -1:
            tagless_text = "/" + tagless_text + "/"
            front_tags = front_tags.replace("</>", "")

        eng_index = front_tags.find("<eng>")
        if eng_index != -1:
            tagless_text = "Translate to English: " + tagless_text
            front_tags = front_tags.replace("<eng>", "")

        return front_tags + tagless_text + back_tags

    def _apply_tags(self, text):
        """Finds tags (written in '<','>' brackets) within 'text', which are
        to be used when 'text' is used as a question, but omitted when used
        as an answer.  Returns tuple (question, answer) created from 'text'
        in accordance with tags.

        :param text: a string with no whitespace around it, that may contain
        tags enclosed in '<' and '>' on the front and back.
        :return: (question, answer)
        """
        tag_chars = "\\w*:\'\",;/() -"
        text_match = compile("(<[" + tag_chars + "]+>)*" +
                             "([\\w,;/()\'\" -]+)" +
                             "(<[" + tag_chars + "]+>)*").fullmatch(text)
        if text_match is None:
            raise ItemFormatError("Tag format is wrong")

        tagless_text = text_match.group(2)
        answer_text = tagless_text
        front_tags = text[0:(text_match.start(2))]
        back_tags = text[(text_match.end(2)):]
        # some tags like <eng> or <*> are 'special'
        # update 'text' in accordance
        question_text = self._apply_special_tags(front_tags, tagless_text, back_tags)

        tag_regex = compile("(<[" + tag_chars + "]+>)")

        # def helper_extract_tags(start_i, end_i):
        #     tag_contents = ""
        #     tag_match = tag_regex.search(text, start_i, end_i)
        #     while tag_match is not None:
        #         raw_tag_text = tag_match.group(0)
        #         tag_text = raw_tag_text[1:(len(raw_tag_text)-1)]
        #         tag_contents += tag_text
        #         start_i = tag_match.end()
        #         tag_match = tag_regex.search(text, start_i, end_i)
        #     return tag_contents

        tag_match = tag_regex.search(question_text)
        while tag_match is not None:
            raw_tag_text = tag_match.group(0)
            tag_text = raw_tag_text[1:(len(raw_tag_text) - 1)]
            question_text = question_text.replace(raw_tag_text, tag_text)
            tag_match = tag_regex.search(question_text)
        return question_text, answer_text

        # extract tags in front
        # front_tags = helper_extract_tags(0, text_match.start(2))
        # back_tags = helper_extract_tags(text_match.end(2), len(text))
        # return front_tags + tagless_text + back_tags, answer_text

    def _create_flashcards(self, item):
        self.flashcard_lines = deque()  # TODO ovo makni? (postavlja se u _set_header)
        item = " ".join(item.split())
        (german, _, translation) = item.partition("=")
        if translation == '':
            raise ItemFormatError("'=' not found in string")
        german = german[2:].strip() # remove the "- " prefix
        translation = translation.strip()

        (german_q, german_a) = self._apply_tags(german)
        (translation_q, translation_a) = self._apply_tags(translation)

        german_q = fill_paragraph(german_q)
        german_a = fill_paragraph(german_a)
        translation_q = fill_paragraph(translation_q)
        translation_a = fill_paragraph(translation_a)

        self._set_header(german_a)
        self._add_card(german_q, translation_a)
        self._add_card(translation_q, german_a)


class OldNoun(ParseResult):
    """A class that knows how to create flashcards (from an org-mode
    item) for old nouns (nouns that the user knows but is a
    bit shaky on the details).

    """

    def __init__(self, noun_dict):
        self._create_flashcards(noun_dict)

    def _create_flashcards(self, noun_dict):
        """Creates flashcards from the singular, translation and plural of a
        noun.
        
        :param: noun_dict is a dictionary with keys singular, plural (optional) and
        translation.  Output is a list of strings to be directly printed
        to an org file and used with org-drill as flashcards.
        """

        singular = noun_dict.get("singular")
        plural = noun_dict.get("plural")

        self._set_header(singular)

        (_, _, noun_wo_article) = singular.partition(" ")
        self._add_card("Rod od *" + noun_wo_article + "*", singular)

        if plural is None:
            return

        self._add_card("množina od *" + singular + "*", plural)
        self._add_card("jednina od *" + plural + "*", singular)


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

        self._set_header(singular)

        self._add_card(translation, singular)
        self._add_card("*" + singular + "*", translation)

        if plural is None:
            return

        self._add_card("množina od *" + singular + "*", plural)
        self._add_card("jednina od *" + plural + "*", singular)


def fill_paragraph(paragraph, max_width=79):
    """"Takes a string (paragraph) and returns a paragraph filled to be a
    maximum width of 'width' characters long (more or less).  No trailing
    newlines.

    """
    line = ''
    lines = []
    for word in paragraph.split():
        if len(line) != 0:
            if len(line) + 1 + len(word) > max_width:
                lines.append(line + "\n")
                line = word
            else:
                line += ' ' + word
        else:
            line = word
    if not lines:
        return line

    return "".join(lines).strip()


def parse_noun(item):
    """Tries to parse an item containing singular, translation and (maybe)
    plural of a noun.

    If it fails in parsing a noun, an ItemFormatException is raised.
    """

    item = " ".join(item.split())

    # regex for a noun for which plural is explicitly written
    r_match = compile("- ([Dd]er|[Dd]ie|[Dd]as) (\\w+), ([Dd]ie \\w+) ="
                      " ([\\w,;()\'\" -]+)").fullmatch(item)
    if r_match:
        singular = r_match.group(1) + " " + r_match.group(2)
        plural = r_match.group(3)
        translation = r_match.group(4)
        return {"singular": singular, "plural": plural, "translation": translation}

    # regex for when only the plural ending is written, and the full
    # plural is to be created from the singular and ending
    r_match = compile("- ([Dd]er|[Dd]ie|[Dd]as) (\\w+), (-?\\w*) = "
                      "([\\w,;()\'\" -]+)").fullmatch(item)
    if r_match:
        singular = r_match.group(1) + " " + r_match.group(2)
        if r_match.group(3) == '-':
            plural = "die " + singular[4:]
        else:
            if r_match.group(3).startswith('-'):
                suffix = r_match.group(3)[1:]
            else:
                suffix = r_match.group(3)
            plural = "die " + singular[4:] + suffix
        translation = r_match.group(4)
        return {"singular": singular, "plural": plural, "translation": translation}

    # regex for a noun with the plural form ommited completely
    r_match = compile("- ([Dd]er|[Dd]ie|[Dd]as) (\\w+) "
                      "= ([\\w,;()\'\" -]+)").fullmatch(item)
    if r_match:
        singular = r_match.group(1) + " " + r_match.group(2)
        translation = r_match.group(3)
        return {"singular": singular, "translation": translation}

    raise ItemFormatError("Not a noun")


def parse_item(item):
    """Tries to extract an item's translation and possibly additional
    data and create flashcards.

    :return: ParseResult object instance.
    """

    try:
        if item.startswith("- (o) "):
            return OldNoun(parse_noun("-" + item[5:]))
    except (ItemFormatError, IndexError):
        pass
    try:
        return NewNoun(parse_noun(item))
    except ItemFormatError:
        pass
    return SimplePair(item)
    # TODO other formats


def __main__():
    """Parses 'german phrase'-translation pairs from the passed file
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

    with ReadFileWrapper(open(f_read_name, 'r', encoding="utf-8")) as fwrap:
        flashcards = deque()
        for item in fwrap:
            try:
                flashcards.extend(parse_item(item).flashcard_lines)
            except ItemFormatError as ex:
                # TODO BETTER LOGGING
                sys.stderr.write("Bad item format around line "
                                 + str(fwrap.line_counter)
                                 + ", message = "
                                 + ex.message
                                 + "\n")

    with open(f_write_name, 'a', encoding="utf-8") as f_write:
        # first line is header for file
        flashcards.insert(0, "* flashcards " + str(datetime.now()) + "\n")
        for entry in flashcards:
            f_write.write(entry)


if __name__ == '__main__':
    __main__()
