import os.path
import urllib.parse


def class_of (element):
    if "class" in element.attrib:
        return list (filter (lambda s : s != "", element.attrib["class"].split (" ")))

    else:
        return [ ]


def has_class (element, dita_class):
    return dita_class in class_of (element)


def outgoing_links_of (element, path_name):
    dita_class = class_of (element)

    if "topic/xref" in dita_class and "href" in element.attrib:
        return resolve (dita_class, element.attrib["href"], element, path_name)

    elif "topic/link" in dita_class and "href" in element.attrib:
        return resolve (dita_class, element.attrib["href"], element, path_name)

    elif "topic/image" in dita_class and "href" in element.attrib:
        return resolve (dita_class, element.attrib["href"], element, path_name)

    elif "map/topicref" in dita_class and "href" in element.attrib:
        return resolve (dita_class, element.attrib["href"], element, path_name)

    elif "map/navref" in dita_class and "href" in element.attrib:
        return resolve (dita_class, element.attrib["href"], element, path_name)


def resolve (dita_class, href, element, path_name):
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
        return resolved (False, os.path.normpath (path_name), parsed.fragment)

    else:
        return resolved (False, os.path.normpath (os.path.join (os.path.split (path_name)[0], parsed.path)), parsed.fragment)


def visit (element, visitor):
    visited = visitor (element)

    if visited is not None:
        yield visited

    for child in element:
        yield from visit (child, visitor)


