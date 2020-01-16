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


def resolve (dita_classes, href, element, path_name):
    def resolved (is_external, path, fragment):
        return { "classes":     dita_classes,
                 "is_external": is_external,
                 "path":        path,
                 "fragment":    fragment }

    parsed = urllib.parse.urlparse (href)

    if parsed.scheme != "":
        return resolved (True, urllib.parse.urlunparse (( parsed.scheme, parsed.netloc, parsed.path, "", "", "" )), parsed.fragment)

    elif os.path.isabs (parsed.path):
        return resolved (False, parsed.path, parsed.fragment)

    elif parsed.path == "":
        return resolved (False, os.path.normpath (path_name), parsed.fragment)

    else:
        return resolved (False, os.path.normpath (os.path.join (os.path.split (path_name)[0], parsed.path)), parsed.fragment)


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


