import os.path
import urllib.parse


def class_of (element):
    if "class" in element.attrib:
        return list (filter (lambda s : s != "", element.attrib["class"].split (" ")))

    else:
        return [ ]


def has_class (element, dita_class):
    return dita_class in class_of (element)


def outgoing_links_of (element, path, root_path):
    dita_class = class_of (element)

    # These can all be handled the same way, so they've been refactored.
    #
    linker_classes = [ "topic/xref", "topic/link", "topic/image", "map/topicref", "map/navref" ]

    if any (linker_class in dita_class for linker_class in linker_classes) and "href" in element.attrib:
        return resolve (dita_class, element.attrib["href"], element, path, root_path)


def resolve (dita_class, href, element, path, root_path):
    def resolved (is_external, path, fragment):
        return { "class":       dita_class,
                 "is_external": is_external,
                 "path":        path,
                 "fragment":    fragment }

    parsed = urllib.parse.urlparse (href)

    if parsed.scheme != "":
        return resolved (True, urllib.parse.urlunparse (( parsed.scheme, parsed.netloc, parsed.path, "", "", "" )), parsed.fragment)

    elif os.path.isabs (parsed.path):
        return resolved (False, parsed.path, parsed.fragment)

    elif parsed.path == "":
        return resolved (False, os.path.normpath (path), parsed.fragment)

    else:
        resolved_path = os.path.relpath (os.path.normpath (os.path.join (os.path.split (path)[0], parsed.path)), root_path)

        return resolved (False, resolved_path, parsed.fragment)


def text_of (element):
    if element.text is not None:
        yield element.text

    for child in element:
        yield from text_of (child)

        if child.tail is not None:
            yield child.tail


def visit (element, visitor):
    visited = visitor (element)

    if visited is not None:
        yield visited

    for child in element:
        yield from visit (child, visitor)


