import os
import os.path
import sys

import argparse
import mimetypes # libmagic is not available on macOS without installing Brew.
import pprint

from lxml import etree


def classify (path_name):
    ( mime_type, _ ) = mimetypes.guess_type (path_name)

    if mime_type == "application/xml":
        parser = etree.XMLParser (attribute_defaults = True, dtd_validation = True)
        tree   = etree.parse (path_name, parser)
        root   = tree.getroot ()

        if has_dita_class (root, "topic/topic"):
            return ( "TOPIC", path_name )

        elif has_dita_class (root, "map/map"):
            return ( "MAP  ", path_name )

        else:
            return ( "OTHER", path_name )

    else:
        return ( "OTHER", path_name )


def configure ():
    mimetypes.init ()

    parser = argparse.ArgumentParser (description = "Classify DITA files into maps, topics, and others.")

    parser.add_argument ("-c", "--catalog",    help = "path to OASIS catalog")
    parser.add_argument ("-m", "--mime-types", help = "path to file containing additional MIME type mappings")

    parser.add_argument ("path_name", nargs = "*", help = "paths to files")

    arguments = parser.parse_args ()

    if arguments.catalog:
        catalog_path = os.path.abspath (arguments.catalog)

        if os.path.exists (catalog_path):
            catalogs = os.environ["XML_CATALOG_FILES"].split (" ") if "XML_CATALOG_FILES" in os.environ else [ ]
            catalogs.append (catalog_path)
            os.environ["XML_CATALOG_FILES"] = " ".join (catalogs)

        else:
            print ("ERROR: \"" + arguments.catalog + "\" not found. It will be ignored.")

    if arguments.mime_types:
        if os.path.exists (arguments.mime_types):
            mime_types = mimetypes.read_mime_types (arguments.mime_types)
            if mime_types is not None:
                for ( extension, mime_type ) in mime_types.items ():
                    mimetypes.add_type (mime_type, extension)

        else:
            print ("ERROR: \"" + arguments.mime_types + "\" not found. It will be ignored.")

    return arguments.path_name


def dita_classes_of (element):
    if "class" in element.attrib:
        return list (filter (lambda s : s != "", element.attrib["class"].split (" ")))

    else:
        return [ ]


def has_dita_class (element, dita_class):
    return dita_class in dita_classes_of (element)


def harvest (path_name):
    def harvest_outgoing (path_name):
        def walk (element):
            dita_classes = dita_classes_of (element)

            if "topic/xref" in dita_classes and "href" in element.attrib:
                accumulator.append (element.attrib["href"])

            elif "topic/link" in dita_classes and "href" in element.attrib:
                accumulator.append (element.attrib["href"])

            elif "topic/image" in dita_classes and "href" in element.attrib:
                accumulator.append (element.attrib["href"])

            for child in element:
                walk (child)


        parser = etree.XMLParser (attribute_defaults = True, dtd_validation = True)
        tree   = etree.parse (path_name, parser)

        accumulator = [ ]
        walk (tree.getroot ())

        return accumulator


    classification = classify (path_name)

    if classification[0] == "OTHER":
        return ( path_name, { "classification": classification[0],
                              "links": { "incoming": [ ],
                                         "outgoing": [ ] } } )

    else:
        return ( path_name, { "classification": classification[0],
                              "links": { "incoming": [ ],
                                         "outgoing": harvest_outgoing (path_name) } } )


def visit (path_name, visitor):
    if os.path.isfile (path_name):
        yield (visitor (path_name))

    else:
        for ( root, _, file_names ) in os.walk (path_name):
            for file_name in file_names:
                yield (visitor (os.path.join (root, file_name)))


if __name__ == "__main__":
    for path_name in configure ():
        print ({ path_name: { "classification": d["classification"],
                              "links":          d["links"] }
                 for ( path_name, d ) in visit (path_name, harvest) })
