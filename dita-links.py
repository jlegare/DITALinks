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


def classify (path):
    ( mime_type, _ ) = mimetypes.guess_type (path)

    if mime_type == "application/xml":
        parser = etree.XMLParser (attribute_defaults = True, dtd_validation = True)
        tree   = etree.parse (path, parser)
        root   = tree.getroot ()

        if dita.has_class (root, "topic/topic"):
            return { "type": "TOPIC", "path": path, "tree": tree }

        elif dita.has_class (root, "map/map"):
            return { "type": "MAP", "path": path, "tree": tree }

        else:
            return { "type": "OTHER", "path": path, "tree": None }

    else:
        return { "type": "OTHER", "path": path, "tree": None }


def configure ():
    mimetypes.init ()

    parser = argparse.ArgumentParser (description = "Collect incoming/outgoing links from DITA files.")

    parser.add_argument ("-c", "--catalog",    help = "path to OASIS catalog")
    parser.add_argument ("-m", "--mime-types", help = "path to file containing additional MIME type mappings")

    parser.add_argument ("path", nargs = "*", help = "paths to files")

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

    return arguments.path


def harvest (path):
    def harvest_outgoing (tree, path):
        # Call utilities.uniquify () on the result to make the links unique.
        #
        return utilities.uniquify (dita.visit (tree.getroot (), lambda element : dita.outgoing_links_of (element, path)))


    def harvest_title (tree):
        title = tree.find ("/title")

        if title is None:
            return None

        else:
            return title.text # This isn't quite correct: there might be child elements ... .


    classification = classify (path)

    if classification["type"] == "OTHER":
        return ( path, { "classification": classification["type"],
                         "description":    None,
                         "links": { "incoming": [ ],
                                    "outgoing": [ ] } } )

    else:
        return ( path, { "classification": classification["type"],
                         "description":    harvest_title (classification["tree"]),
                         "links": { "incoming": [ ],
                                    "outgoing": harvest_outgoing (classification["tree"], 
                                                                  classification["path"]) } } )


if __name__ == "__main__":
    def incoming_of (entry):
        # This function is here solely to help readability below.
        #
        return indices[entry["path"]]["links"]["incoming"]


    def is_harvested (entry):
        # This function is here solely to help readability below.
        #
        return entry["path"] in indices and not entry["is_external"]


    indices = { }

    for path in configure ():
        indices.update ({ path: harvested for ( path, harvested ) in files.visit (path, harvest) })

    for ( path, index ) in indices.items ():
        for outgoing in index["links"]["outgoing"]:
            if is_harvested (outgoing):
                incoming_of (outgoing).append ({ "class": outgoing["class"], "path": path })

    for entry in indices.values ():
        entry["links"]["incoming"] = utilities.uniquify (entry["links"]["incoming"])

    pp = pprint.PrettyPrinter ()

    pp.pprint (indices)
