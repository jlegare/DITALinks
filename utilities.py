import collections
import os.path
import urllib.parse

def dita_classes_of (element):
    if "class" in element.attrib:
        return list (filter (lambda s : s != "", element.attrib["class"].split (" ")))

    else:
        return [ ]


def has_dita_class (element, dita_class):
    return dita_class in dita_classes_of (element)


def resolve (href, element, path_name):
    Resolved = collections.namedtuple ("Resolved", [ "is_external", "path", "fragment" ])

    parsed = urllib.parse.urlparse (href)

    if parsed.scheme != "":
        return Resolved (True, urllib.parse.urlunparse (( parsed.scheme, parsed.netloc, parsed.path, "", "", "" )), parsed.fragment)

    elif os.path.isabs (parsed.path):
        return Resolved (False, parsed.path, parsed.fragment)

    elif parsed.path == "":
        return Resolved (False, os.path.normpath (path_name), parsed.fragment)

    else:
        return Resolved (False, os.path.normpath (os.path.join (os.path.split (path_name)[0], parsed.path)), parsed.fragment)


def visit_path (path_name, visitor):
    if os.path.isfile (path_name):
        yield (visitor (path_name))

    else:
        for ( root, _, file_names ) in os.walk (path_name):
            for file_name in file_names:
                yield (visitor (os.path.join (root, file_name)))


def visit_xml (element, visitor):
    visitor (element)

    for child in element:
        visit_xml (child, visitor)


