import os.path


def dita_classes_of (element):
    if "class" in element.attrib:
        return list (filter (lambda s : s != "", element.attrib["class"].split (" ")))

    else:
        return [ ]


def has_dita_class (element, dita_class):
    return dita_class in dita_classes_of (element)



def resolve (href, element, path_name):
    if os.path.isabs (href):
        return href

    else:
        return os.path.normpath (os.path.join (os.path.split (path_name)[0], href))

