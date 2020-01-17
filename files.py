import os
import os.path


def visit_path (path_name, visitor):
    if os.path.isfile (path_name):
        yield (visitor (path_name))

    else:
        for ( root, _, file_names ) in os.walk (path_name):
            for file_name in file_names:
                yield (visitor (os.path.join (root, file_name)))
