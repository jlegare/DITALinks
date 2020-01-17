def uniquify (dictionaries):
    return list ({ ":".join ([ str (dictionary[key]) for key in sorted (dictionary.keys ()) ]) : dictionary
                   for dictionary in dictionaries }.values ())
