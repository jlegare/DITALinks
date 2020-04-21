# DITALinks

Harvest the links from [DITA](https://www.oasis-open.org/committees/tc_home.php?wg_abbrev=dita) files, and build a table of incoming and outgoing links for each file, including the DITA class of the linking element (_i.e._, is the source of the link an `xref` or a `topicref`, ...).

## Table of Contents

* [Requirements](#requirements)
* [Installation](#installation)
* [Usage](#usage)
* [Discussion](#discussion)

## Requirements

* [Python 3.8 or newer](https://www.python.org/downloads/)
* [lxml 4.4.2 or newer](https://lxml.de)

## Installation

Clone this repository using:
```
git clone https://github.com/jlegare/DITALinks.git
```

## Usage

To harvest the links for a single file, provide the path to the file on the command-line:
```
python dita-links.py --catalog path-to-catalog some-topic.dita
```
Any outgoing links that are encountered will be recorded, and if the link targets are to local files (that is, not external) and those files are available, they will be recursively visited, until closure is obtained. If a link is to a local file but the file is not available, the link will recorded as broken. Knowing this, to harvest the links for an entire documentation set, we need only to provide the path to the top-most DITA map: for example, if the DITA 1.2 documentation set is located in `documentation/`, then the links for all the reachable files can be had using
```
python dita-links.py --catalog path-to-catalog documentation/dita-1.2-specification.ditamap
```

The `--catalog` command-line option is used to specify the path to an [OASIS catalog](https://www.oasis-open.org/committees/download.php/14810/xml-catalogs.pdf) for the version of DITA being used. (Standard DITA provides a catalog with the schema: for example, DITA 1.2 provides `dtd1.2/catalog.xml`. Most specializations will provide their own catalog that supplements the standard catalog.)

DITALinks attempts to determine the type of the file it is processing; it supports common XML file types, as well as files with extensions `.dita` and `.ditamap`. Additional mappings can be specified by modifying the file `etc/mimetypes.txt`, or by providing an entirely different file and using the `--mime-types` command-line option to point to this new configuration. The format of the MIME type configuration file is two, space-separated columns: the first column is the MIME type, the second column is the file name extension (without the leading period). 

DITALinks analyzes each element encountered to determine if it is the source of an outgoing link. The behaviour can be configured by adjusting the file `etc/dita-1.2.csv`, or by providing an entirely different file and using the `--link-origins` command-line option to point to this new configuration. The link origins file uses a simple CSV format, with three fields:

* link type,
* [XPath](https://www.w3.org/TR/1999/REC-xpath-19991116/) expression that evaluates to `true` for the link of interest, and
* XPath expression that extracts the link target from the element.

The XPath expressions are evaluated against each element as it is encountered in the input. (The _link type_ field is reserved for future development.)

The `--no-follow` command-line option can be used to limit output: when specified, links will only be followed for files specified on the command-line. For example, if a map is specified on the command-line, its `topicref` elements will generate entries in the output as always, but the files pointed-to by its `topicref` elements will not be visited any further.

Default output is a human-readable format. [JSON](https://www.json.org/json-en.html) output can be had by providing the `--json` command-line flag. [GraphViz](https://graphviz.gitlab.io) can be obtained by providing the `--graphviz` command-line flag. (Note: For any reasonable-sized documentation, don't expect the GraphViz output to be readable.)

## Discussion

The output of DITALinks is a sorted list of the files encountered as links were visited. For each file, a list of incoming and outgoing links is given, along with the DITA class of linking element. If a file has no incoming links, that section is omitted and only outgoing links will be shown; similarly if a file has no outgoing links. For example, in the DITA 1.2 documentation set, `documentation/introduction/formatting-conventions-xhtml-output.dita` references two images: so the following invocation
```
python dita-links.py -c dtd1.2/catalog-dita.xml \
                     documentation/introduction/formatting-conventions-xhtml-output.dita 
```
yields
```
introduction/formatting-conventions-xhtml-output.dita
    OUTGOING
        - topic/image                    resources/navigational-links.jpg
        - topic/image                    resources/preview-links.jpg
```
Note the absence of an incoming links section. The presence of those two outgoing links in this topic leads DITALinks to visit the two images in question, leading to further output
```
resources/navigational-links.jpg
    INCOMING
        - topic/image                    introduction/formatting-conventions-xhtml-output.dita

resources/preview-links.jpg
    INCOMING
        - topic/image                    introduction/formatting-conventions-xhtml-output.dita
```
Since images cannot link to anything, these two files have only an incoming section. 

When possible, DITALinks factors common path components out its output: in the examples above, `documentation/` was dropped because it was common to all visited files.

If a directory name is provided on the command-line, DITALinks will attempt to visit all files in the provided directory. This can be used to find _orphaned files_ in a documentation set (_i.e._, files that reference nothing, and are not referenced from anywhere). As an artificial example, the following invocation
```
python dita-links.py -c dtd1.2/catalog-dita.xml documentation/introduction/
```
will show that `introduction/c-terminology.dita` (among others) is orphaned. (This example is contrived: `documentation/introduction` is not a complete documentation set, and the file in question is in fact referenced from elsewhere when the full DITA 1.2 documentation set is taken in to consideration.)
