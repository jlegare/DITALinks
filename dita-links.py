import os
import os.path
import sys

import argparse
import csv
import json
import mimetypes # libmagic is not available on macOS without installing Brew.

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

        if dita.has_class (root, "topic/topic") or dita.has_class (root, "map/map"):
            return { "type":  "DITA",
                     "class": dita.class_of (root),
                     "path":  path,
                     "tree":  tree }

        else:
            return { "type":  None,
                     "class": None,
                     "path":  path,
                     "tree":  None }

    else:
        return { "type":  None,
                 "class": None,
                 "path":  path,
                 "tree":  None }


def configure ():
    mimetypes.init ()

    parser = argparse.ArgumentParser (description = "Collect incoming/outgoing links from DITA files.")

    parser.add_argument ("-c", "--catalog", help = "path to OASIS catalog")
    parser.add_argument ("-m", "--mime-types", help = "path to file containing additional MIME type mappings",
                         default = "etc/mimetypes.txt")
    parser.add_argument ("-l", "--link-origins", help = "DITA class attribute for elements that are link origins",
                         default = "etc/dita-1.2.csv")
    parser.add_argument ("-j", "--json", help = "generate JSON output",
                         action = "store_true")
    parser.add_argument ("path", help = "paths to files",
                         nargs = "+")

    arguments = parser.parse_args ()

    if arguments.catalog:
        catalog_path = os.path.abspath (arguments.catalog)

        if os.path.exists (catalog_path):
            catalogs = os.environ["XML_CATALOG_FILES"].split (" ") if "XML_CATALOG_FILES" in os.environ else [ ]
            catalogs.append (catalog_path)
            os.environ["XML_CATALOG_FILES"] = " ".join (catalogs)

        else:
            print ("ERROR: \"" + arguments.catalog + "\" not found. It will be ignored.")

    origins = [ ]

    if os.path.exists (arguments.link_origins):
        with open (arguments.link_origins) as csv_file:
            reader = csv.DictReader (csv_file)
            for row in reader:
                origins.append (row)

    else:
        print ("ERROR: \"" + arguments.link_origins + "\" not found. It will be ignored.")

    if os.path.exists (arguments.mime_types):
        mime_types = mimetypes.read_mime_types (arguments.mime_types)
        if mime_types is not None:
            for ( extension, mime_type ) in mime_types.items ():
                mimetypes.add_type (mime_type, extension)

    else:
        print ("ERROR: \"" + arguments.mime_types + "\" not found. It will be ignored.")

    return { "origins": origins,
             "paths":   arguments.path,
             "json":    arguments.json }


def harvest (path, origins):
    def harvest_outgoing (tree, path):
        def outgoing_links_of (element):
            return dita.outgoing_links_of (element, path, origins)


        # Flatten the lists and call utilities.uniquify () on the result to make the links unique.
        #
        links = [ target for targets in dita.visit (tree.getroot (), outgoing_links_of) for target in targets ]
        return utilities.uniquify (links)


    def harvest_title (tree):
        title = tree.find ("/title")

        if title is None:
            return None

        else:
            return "".join (dita.text_of (title))


    classification = classify (path)

    if classification["type"] is None:
        return ( path, { "classification": classification["type"],
                         "description":    None,
                         "links": { "incoming": [ ],
                                    "outgoing": [ ] } } )

    else:
        return ( path, { "classification": classification["type"],
                         "class":          classification["class"],
                         "description":    harvest_title (classification["tree"]),
                         "links": { "incoming": [ ],
                                    "outgoing": harvest_outgoing (classification["tree"],
                                                                  classification["path"]) } } )


if __name__ == "__main__":
    def incoming_of (entry, entries):
        # This function is here solely to help readability below.
        #
        return entries[entry["path"]]["links"]["incoming"]


    def is_harvested (entry, entries):
        # This function is here solely to help readability below.
        #
        return entry["path"] in entries and not entry["is_external"]


    def incomings (path, entries, stream):
        if len (entries[path]["links"]["incoming"]) > 0:
            stream.write ("INCOMING\n")

            with utilities.Indenter (stream = stream) as indenter:
                for incoming in sorted (entries[path]["links"]["incoming"], key = lambda incoming : incoming["path"]):
                    indenter.write ("{:<32}".format (" ".join (incoming["class"])) + " " + incoming["path"] + "\n")


    def outgoings (path, entries, stream):
        if len (entries[path]["links"]["outgoing"]) > 0:
            if len (entries[path]["links"]["incoming"]) > 0:
                stream.write ("\n")

            stream.write ("OUTGOING\n")

            with utilities.Indenter (stream = stream) as indenter:
                for outgoing in sorted (entries[path]["links"]["outgoing"], key = lambda outgoing : outgoing["path"]):
                    indenter.write ("{:<32}".format (" ".join (outgoing["class"])) + " " + outgoing["path"]
                                    + ("#" if outgoing["fragment"] != "" else "") + outgoing["fragment"] + "\n")


    def unvisited_of (file_names, entries):
        return { }.fromkeys ([ file_name for file_name in file_names if file_name not in entries ])


    entries = { }

    configuration = configure ()

    origins = configuration["origins"]
    paths   = configuration["paths"]

    unvisited = { }.fromkeys ([ file_name for path in paths
                                          for file_name in files.visit (path, lambda file_name : file_name) ])

    while unvisited:
        ( path, _ )      = utilities.popfront (unvisited)
        ( _, harvested ) = harvest (path, origins)

        entries.update ({ path : harvested })
        unvisited.update (unvisited_of ([ h["path"]
                                          for h in harvested["links"]["outgoing"]
                                          if h["path"] != path and not h["is_external"] ], entries))

    for ( path, entry ) in entries.items ():
        for outgoing in entry["links"]["outgoing"]:
            if is_harvested (outgoing, entries):
                incoming_of (outgoing, entries).append ({ "class": outgoing["class"], "path": path })

    for entry in entries.values ():
        entry["links"]["incoming"] = utilities.uniquify (entry["links"]["incoming"])

    common_path = os.path.commonpath (entries.keys ())

    # If a single file name is specified on the command-line and that file has no incoming or outgoing links, then
    # common_path will be set to that file name. This makes for funky output. Adjust it to be the directory portion
    # only.
    #
    if os.path.isfile (common_path):
        common_path = os.path.dirname (common_path)

    normalized_entries = { }

    for ( path, entry ) in entries.items ():
        for incoming in entry["links"]["incoming"]:
            incoming["path"] = os.path.relpath (incoming["path"], common_path)

        for outgoing in entry["links"]["outgoing"]:
            if not outgoing["is_external"]:
                outgoing["path"] = os.path.relpath (outgoing["path"], common_path)

        normalized_entries[os.path.relpath (path, common_path)] = entry

    if configuration["json"]:
        json.dump (normalized_entries, sys.stdout)

    else:
        stream = sys.stdout

        for path in sorted (list (normalized_entries)):
            stream.write (path + "\n")
            incomings (path, normalized_entries, utilities.Indenter (stream = stream))
            outgoings (path, normalized_entries, utilities.Indenter (stream = stream))
            stream.write ("\n")
