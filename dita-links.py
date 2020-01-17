import os
import os.path
import sys

import argparse
import mimetypes # libmagic is not available on macOS without installing Brew.
import pprint

from lxml import etree

import dita
import files
import utilities


def classify (path_name):
    ( mime_type, _ ) = mimetypes.guess_type (path_name)

    if mime_type == "application/xml":
        parser = etree.XMLParser (attribute_defaults = True, dtd_validation = True)
        tree   = etree.parse (path_name, parser)
        root   = tree.getroot ()

        if dita.has_dita_class (root, "topic/topic"):
            return ( "TOPIC", path_name, tree )

        elif dita.has_dita_class (root, "map/map"):
            return ( "MAP  ", path_name, tree )

        else:
            return ( "OTHER", path_name, None )

    else:
        return ( "OTHER", path_name, None )


def configure ():
    mimetypes.init ()

    parser = argparse.ArgumentParser (description = "Collect incoming/outgoing links from DITA files.")

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


def harvest (path_name):
    def outgoing_links_of (element, path_name, accumulator):
        dita_classes = dita.dita_classes_of (element)

        if "topic/xref" in dita_classes and "href" in element.attrib:
            accumulator.append (dita.resolve (dita_classes, element.attrib["href"], element, path_name))

        elif "topic/link" in dita_classes and "href" in element.attrib:
            accumulator.append (dita.resolve (dita_classes, element.attrib["href"], element, path_name))

        elif "topic/image" in dita_classes and "href" in element.attrib:
            accumulator.append (dita.resolve (dita_classes, element.attrib["href"], element, path_name))

        elif "map/topicref" in dita_classes and "href" in element.attrib:
            accumulator.append (dita.resolve (dita_classes, element.attrib["href"], element, path_name))

        elif "map/navref" in dita_classes and "href" in element.attrib:
            accumulator.append (dita.resolve (dita_classes, element.attrib["href"], element, path_name))


    def harvest_outgoing (tree, path_name):
        accumulator = [ ]
        dita.visit_xml (tree.getroot (), lambda element : outgoing_links_of (element, path_name, accumulator))

        return utilities.uniquify (accumulator) # Make the links unique.


    classification = classify (path_name)

    if classification[0] == "OTHER":
        return ( path_name, { "classification": classification[0],
                              "links": { "incoming": [ ],
                                         "outgoing": [ ] } } )

    else:
        return ( path_name, { "classification": classification[0],
                              "links": { "incoming": [ ],
                                         "outgoing": harvest_outgoing (classification[2], classification[1]) } } )


if __name__ == "__main__":
    indices = { }

    for path_name in configure ():
        indices.update ({ path_name: { "classification": d["classification"],
                                       "links":          d["links"] }
                          for ( path_name, d ) in files.visit_path (path_name, harvest) })

    for ( path_name, index ) in indices.items ():
        for outgoing in index["links"]["outgoing"]:
            if not outgoing["is_external"] and outgoing["path"] in indices:
                indices[outgoing["path"]]["links"]["incoming"].append ({ "classes": outgoing["classes"], "path": path_name })

    pp = pprint.PrettyPrinter ()

    pp.pprint (indices)
