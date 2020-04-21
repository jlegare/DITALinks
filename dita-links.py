import itertools
import os
import os.path
import sys

import argparse
import csv
import html
import json
import mimetypes # libmagic is not available on macOS without installing Brew.
import textwrap

from lxml import etree

import dita
import files
import utilities


def classify (path):
    ( mime_type, _ ) = mimetypes.guess_type (path)

    if os.path.isfile (path):
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

    else:
        return None


def configure ():
    mimetypes.init ()

    parser = argparse.ArgumentParser (description = "Collect incoming/outgoing links from DITA files.")

    parser.add_argument ("-c", "--catalog", help = "path to OASIS catalog")
    parser.add_argument ("-m", "--mime-types", help = "path to file containing additional MIME type mappings",
                         default = "etc/mimetypes.txt")
    parser.add_argument ("-l", "--link-origins", help = "DITA class attribute for elements that are link origins",
                         default = "etc/dita-1.2.csv")
    parser.add_argument ("-g", "--graphviz", help = "generate GraphViz output",
                         action = "store_true")
    parser.add_argument ("-j", "--json", help = "generate JSON output",
                         action = "store_true")
    parser.add_argument ("-f", "--no-follow", help = "do not follow referenced files",
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

    return { "origins":  origins,
             "paths":    arguments.path,
             "graphviz": arguments.graphviz,
             "json":     arguments.json,
             "follow":   not arguments.no_follow }


def graphviz (entries, stream):
    def edges (path, entries, stream):
        for outgoing in entries[path]["links"]["outgoing"]:
            if outgoing["path"] in entries:
                stream.write (name_of (path) + " -> " + name_of (outgoing["path"]) + ";\n")


    def node (path, entries, stream):
        stream.write (name_of (path) + " [label=<\n")
        stream.write ("<TABLE BORDER=\"0\" CELLBORDER=\"1\" CELLSPACING=\"0\">\n")

        if entries[path]["description"]:
            description = "<B>" + "<BR/>\n".join (textwrap.wrap (html.escape (entries[path]["description"]), width = 20)) + "</B>"

        else:
            description = "<I>" + path + "</I>"

        stream.write ("<TR><TD BGCOLOR=\"gray\"><B>" + description + "</B></TD></TR>\n")
        stream.write ("</TABLE>\n")
        stream.write (">];\n")


    def name_of (path):
        return path.replace ("/", "_").replace (".", "_").replace ("-", "_")


    stream.write ("digraph links {\n")
    stream.write ("    node[shape = none]\n\n")

    for path in sorted (list (entries)):
        node (path, entries, stream)

    for path in sorted (list (entries)):
        edges (path, entries, stream)

    stream.write ("}\n")


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

    if classification is None:
        return ( path, { "classification": None,
                         "description":    None,
                         "is_located":     False,
                         "links": { "incoming": [ ],
                                    "outgoing": [ ] } } )

    elif classification["type"] is None:
        return ( path, { "classification": classification["type"],
                         "description":    None,
                         "is_located":     True,
                         "links": { "incoming": [ ],
                                    "outgoing": [ ] } } )

    else:
        return ( path, { "classification": classification["type"],
                         "class":          classification["class"],
                         "description":    harvest_title (classification["tree"]),
                         "is_located":     True,
                         "links": { "incoming": [ ],
                                    "outgoing": harvest_outgoing (classification["tree"],
                                                                  classification["path"]) } } )


def human_readable (entries, stream):
    def brokens (path, entries, stream):
        if len (entries[path]["links"]["broken"]) > 0:
            if len (entries[path]["links"]["outgoing"]) > 0:
                stream.write ("\n")

            stream.write ("BROKEN\n")

            with utilities.Indenter (stream = stream) as indenter:
                for broken in sorted (entries[path]["links"]["broken"], key = lambda broken : broken["path"]):
                    indenter.write ("{:<32}".format (" ".join (broken["class"])) + " " + broken["path"]
                                    + ("#" if broken["fragment"] != "" else "") + broken["fragment"] + "\n")


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


    for path in sorted (list (entries)):
        stream.write (path)

        if not entries[path]["is_located"]:
            stream.write ("   *** MISSING ***")

        stream.write ("\n")

        incomings (path, entries, utilities.Indenter (stream = stream))
        outgoings (path, entries, utilities.Indenter (stream = stream))
        brokens (path, entries, utilities.Indenter (stream = stream))
        stream.write ("\n")


if __name__ == "__main__":
    def incoming_of (entry, entries):
        # This function is here solely to help readability below.
        #
        return entries[entry["path"]]["links"]["incoming"]


    def is_followable (entry):
        # This function is here solely to help readability below.
        #
        return entry["is_located"] or entry["is_external"]


    def is_harvested (entry, entries):
        # This function is here solely to help readability below.
        #
        return entry["path"] in entries and not entry["is_external"]


    def should_consider (harvested, path):
        # This function is here solely to help readability below.
        #
        return harvested["path"] != path and not harvested["is_external"]


    def should_visit (path, visitables):
        # This function is here solely to help readability below.
        #
        return path in visitables


    def unvisited_of (file_names, entries):
        return { }.fromkeys ([ file_name for file_name in file_names if file_name not in entries ])


    entries = { }

    configuration = configure ()

    origins = configuration["origins"]
    paths   = configuration["paths"]

    unvisited = { }.fromkeys ([ file_name for path in paths
                                          for file_name in files.visit (path, lambda file_name : file_name) ])
    visitables = paths[:]

    while unvisited:
        ( path, _ ) = utilities.popfront (unvisited)

        if configuration["follow"] or should_visit (path, visitables):
            ( _, harvested ) = harvest (path, origins)

            entries.update ({ path : harvested })

            # I tried various ways of implementing the "no follow" behaviour, and all appeared to yield about the same
            # performance. This one is succinct.
            #
            if path in paths:
                visitables = list (set (visitables + [ p["path"] for p in harvested["links"]["outgoing"] ]))

            if harvested["is_located"]:
                unvisited.update (unvisited_of ([ h["path"]
                                                  for h in harvested["links"]["outgoing"]
                                                  if should_consider (h, path) ], entries))

    for ( path, entry ) in entries.items ():
        for outgoing in entry["links"]["outgoing"]:
            if is_harvested (outgoing, entries):
                incoming_of (outgoing, entries).append ({ "class": outgoing["class"], "path": path })

        entry["links"]["broken"]   = list (itertools.filterfalse (is_followable, entry["links"]["outgoing"]))
        entry["links"]["outgoing"] = list (filter (is_followable, entry["links"]["outgoing"]))

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

    if configuration["graphviz"]:
        graphviz (normalized_entries, sys.stdout)

    elif configuration["json"]:
        json.dump (normalized_entries, sys.stdout)

    else:
        human_readable (normalized_entries, sys.stdout)
