import io
import sys


def popfront (dictionary):
    if dictionary:
        ( key, value ) = next (iter (dictionary.items ()))

        dictionary.pop (key)

        return ( key, value )

    else:
        return None


def uniquify (dictionaries):
    return list ({ ":".join ([ str (dictionary[key]) for key in sorted (dictionary.keys ()) ]) : dictionary
                   for dictionary in dictionaries }.values ())


class Indenter (io.TextIOBase):
    def __init__ (self, indent = 4, prefix = " ", stream = None):
        self.indentation = prefix * indent

        if stream is None:
            self.stream = sys.stdout

        else:
            self.stream = stream


    def write (self, data):
        self.stream.write ("".join ([ self.indentation + line for line in data.splitlines (True) ]))
