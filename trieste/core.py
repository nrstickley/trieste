import platform as _platform
import numpy as _np
import copy as _copy
import time as _time
import getpass as _getpass
import types as _types


__version__ = '0.1.0'


# detect whether or not we are running in IPython
try:
    _ipy = get_ipython()
except NameError:
    _ipy = None


# This is used to keep track of the number of untitled objects.
# Untitled objects are given names based upon the order in which they are created.
_n_untitled = 1


def numpy_version_tuple():
    """Determines the version of NumPy installed on the machine and returns the version tuple."""
    return tuple([int(v) for v in _np.version.full_version.split('.')])


def python_version_tuple():
    """Returns the Python language version tuple."""
    version = _platform.python_version_tuple()
    return tuple([int(v) for v in version])


def check_compatibility(input_file):
    """
    Checks that an input file is compatible with the current operating environment. Raises an exception upon identifying
    an incompatibility.
    :param input_file: a NumPy file object.
    """
    if not isinstance(input_file, _np.lib.npyio.NpzFile):
        raise TypeError("Expected a NumPy .npz file (numpy.lib.npyio.NpzFile)")

    name = input_file.fid.name

    invalid_file_format = f"The input file, {name}, is not a valid Trieste file."

    # Check that the basic format is approximately correct:

    if len(input_file.keys()) < 2 or 'metadata' not in input_file.keys():
        raise RuntimeError(invalid_file_format)

    metadata = input_file['metadata'][0]

    # Check that the metadata contains the required keywords

    required_keys = {
                    'numpy_version',
                    'python_version',
                    'n_objects',
                    'trieste_version',
                    'creation_time',
                    'creation_date',
                    'author',
                    'author_working_dir',
                    'hostname',
                    'OS',
                    'architecture',
                    'platform',
                    'python_implementation'
                    }

    actual_keys = set(metadata.keys())

    if not required_keys.issubset(actual_keys):
        missing_keys = required_keys - actual_keys
        raise RuntimeError(f"{invalid_file_format} The following keywords are missing from the metadata: {missing_keys}")

    file_trieste_version = metadata['trieste_version']

    my_trieste_version = tuple([int(v) for v in __version__.split('.')])

    if my_trieste_version < file_trieste_version:
        message = f"Your Trieste installation is too old. {name} was created using Trieste {file_trieste_version}."
        raise RuntimeError(message)

    file_python_version = metadata['python_version']

    my_python_version = python_version_tuple()

    if my_python_version < file_python_version:
        raise Warning(f"{name} was created with a newer version of Python.")

    file_numpy_version = metadata['numpy_version']

    my_numpy_version = numpy_version_tuple()

    if my_numpy_version < file_numpy_version:
        raise Warning(f"'{name}' was created using a newer version of NumPy.")


def save(filename, metadata, *objects):
    """
    Saves objects to a file, with specified metadata. Note that metadata is a required parameter.
    :param filename: (string) The name of the output file.
    :param metadata: (dict) User-defined metadata keywords and values.
    :param objects: one or more Trieste Array, Table, or Collection objects.
    """
    if isinstance(objects[0], tuple) or isinstance(objects[0], list):
        args = {}

        for ob in objects[0]:
            if type(ob) not in (Array, Table, Collection):
                raise TypeError(f"Encountered a non-Trieste object of type {type(ob)} in Trieste.save().")
            if ob.name not in args.keys():
                args[ob.name] = ob.raw
            else:
                raise Exception(f"Object names must be unique. The name '{ob.name}' has been used more than once.")
    else:
        for ob in objects:
            if type(ob) not in (Array, Table, Collection):
                raise TypeError(f"Encountered a non-Trieste object of type {type(ob)} in Trieste.save().")

        args = {ob.name: ob.raw for ob in objects}

        if len(objects) == 1:
            metadata = {**objects[0].raw[0], **metadata}  # merge the metadata

    metadata['numpy_version'] = numpy_version_tuple()
    metadata['python_version'] = python_version_tuple()
    metadata['n_objects'] = len(args)
    metadata['trieste_version'] = tuple([int(v) for v in __version__.split('.')])
    metadata['creation_time'] = _time.time()
    metadata['creation_date'] = _time.asctime()
    metadata['author'] = _getpass.getuser()
    metadata['author_working_dir'] = _platform.os.path.realpath('./')
    metadata['hostname'] = _platform.os.uname().nodename
    metadata['OS'] = _platform.system()
    metadata['architecture'] = _platform.uname().processor
    metadata['platform'] = _platform.platform()
    metadata['python_implementation'] = _platform.python_implementation()
    metadata['ipython_history'] = _get_ipython_history()

    if 'doc' not in metadata.keys():
        metadata['doc'] = ""

    args['metadata'] = _np.array([metadata], dtype=_np.object)

    _np.savez_compressed(filename, **args)


def load(filename):
    """
    Reads a .npz file from disk and returns a File object.
    """
    f = _np.load(filename)

    check_compatibility(f)

    is_single_object_file = (len(f.keys()) == 2)  # 1 for metadata and 1 for data

    if is_single_object_file:
        # Handle the case of a single-object file: just return the Array or Collection.
        # First, find the key that isn't 'metadata'
        keys = set(f.keys())
        keys.remove('metadata')
        data_name = keys.pop()

        if 'Collection' in f[data_name][0]['type']:
            return Collection(f[data_name][1], name=data_name, metadata=f['metadata'][0])
        elif 'Array' in f[data_name][0]['type']:
            return Array(f[data_name][1], name=data_name, metadata=f['metadata'][0])
        elif 'Table' in f[data_name][0]['type']:
            return Table(f[data_name][1], name=data_name, metadata=f['metadata'][0])

    else:
        # Handle the case of a multi-object file. Construct File object and return it:
        return File(f)


def _variable_name(variable):
    """
    Returns the name of the argument `variable` as a string, if the user is running IPython.
    :param variable: A variable whose variable name you would like to know.
    :return: The string representation of the variable's name. More precisely, this returns the first key in
    `globals()` that is mapped to the variable in question. If the variable is anonymous, `None` is returned.
    """
    if _ipy is not None:
        global_vars = _ipy.user_global_ns
    else:
        global_vars = globals()

    _varname = None
    for k, v in global_vars.items():
        if v is variable and k != '_':
            _varname = k
            break
    return _varname


def _get_ipython_history():
    """
    If the module is running in an IPython session, this returns the command history for the entire session.
    """
    if _ipy is not None:
        hist_manager = _ipy.history_manager
        return "\n".join((line[2] for line in hist_manager.get_range()))
    else:
        return ""


class Array:
    """
    Manages a single NumPy `ndarray` object as well as the metadata describing the contents of the `ndarray`.
    """
    def __init__(self, data, name=None, metadata=None):
        """
        :param data: The NumPy `ndarray` object that will be stored in the Trieste `Array`.
        :param metadata: Metadata describing the content of `data` (optional, but strongly encouraged).
        :param name: The name / label of this data object (optional). If the name is not provided and the code is
        being executed in IPython, then the name of the variable provided as the `data` parameter will be used as the
        name of the `Array`. Otherwise, the name will be set to `untitled_N`, where `N` is an integer.
        """
        if isinstance(data, _np.ndarray):
            self._data = data
        elif isinstance(data, list) or isinstance(data, tuple):
            self._data = _np.array(data)
        else:
            raise TypeError(f"data must be a NumPy ndarray, a Python list, or a Python tuple---not a {type(data)}.")

        if metadata is None:
            self._metadata = {}
        else:
            if isinstance(metadata, dict):
                self._metadata = _copy.copy(metadata)
            else:
                raise TypeError('Metadata must be a dict')

        self._ndim = _np.ndim(self._data)

        if name is None:
            varname = _variable_name(data)
            if 'name' in self._metadata.keys():
                self._name = self._metadata['name']
            elif varname is not None:
                self._name = varname
            else:
                global _n_untitled
                self._name = f"untitled_{_n_untitled}"
                _n_untitled += 1
        else:
            if isinstance(name, str):
                self._name = name
            else:
                raise TypeError("The name of an array must be a string.")

        self._metadata['numpy_version'] = numpy_version_tuple()
        self._metadata['python_version'] = python_version_tuple()
        self._metadata['type'] = f"{self._ndim}-D Array"
        self._metadata['ndim'] = self._ndim
        self._metadata['name'] = self._name
        if 'doc' not in self._metadata.keys():
            self._metadata['doc'] = ""

        self._ndarray = _np.array([self._metadata, self._data], dtype=_np.object)

        self.__doc__ = self._metadata['doc']

        # only add a new ipython history string if this is not being loaded from a file that already
        # contains a history string.
        if 'ipython_history' not in self._metadata.keys():
            self._metadata['ipython_history'] = _get_ipython_history()

    def set_readme(self, docstring):
        """
        Sets the object's documentation string.
        :param docstring: a string, describing the contents of the `Array` (if possible, also include information
        regarding how to use the data and how the data was created).
        """
        self._metadata['doc'] = docstring
        self.__doc__ = self._metadata['doc']

    def save_as(self, filename):
        save(filename, {}, self)

    @property
    def metadata(self):
        """
        The array's metadata.
        """
        return self._metadata
    
    @property
    def data(self):
        """
        The contents of the managed array (the NumPy `ndarray`).
        """
        return self._data

    @property
    def raw(self):
        """
        The nested array (data and metadata together in a larger container).
        """
        return self._ndarray

    @property 
    def name(self):
        """
        The name of the object.
        """
        return self._name

    @property
    def ndim(self):
        """
        The number of dimensions of the managed array.
        """
        return self._ndim

    @property
    def readme(self):
        """
        Returns a documentation string describing the contents of the array.
        """
        return self._metadata['doc']

    @property
    def history(self):
        """
        If the object was created from within an IPython session. The commands leading up to the creation of
        the object are listed here, as a string.
        """
        if 'ipython_history' in self._metadata.keys():
            return self._metadata['ipython_history']
        else:
            return ''

    def print_history(self):
        """
        Prints the string output by `self.history` See the documentation of `history` for more details.
        """
        print(self.history)

    def __repr__(self):
        name = self._name
        my_type = self._ndarray[0]['type']
        return f"<{name}: a Trieste {my_type}>"

    def __getitem__(self, item):
        return self._data[item]


class Table(Array):
    """
    Manages an Array containing records (named columns of potentially different datatypes).
    """
    def __init__(self, data, name=None, metadata=None):
        """
        Constructs a `Table` object, which is a special type of `Array` containing named columns with specified
        data types. Refer to the documentation for `Array` for more information.
        :param data: a NumPy array with specified column names and datatypes.
        :param name: The name of the table. If the name is not provided and the code is
        being executed in IPython, then the name of the variable provided as the `data` parameter will be used as the
        name of the `Table`. Otherwise, the name will be set to `untitled_N`, where `N` is an integer.
        :param metadata: metadata describing the contents of the `data`.
        """

        if _np.ndim(data) != 1:
            raise ValueError(f"Table() does not support {_np.ndim(data)}-dimensional arrays.")

        fields = data.dtype.fields

        if not isinstance(fields, _types.MappingProxyType):
            raise TypeError(f"Table objects require named columns.")

        super().__init__(data, name, metadata)

        self._metadata['type'] = "Table"

    @property
    def column_types(self):
        """
        Lists the column names and data types.
        :return: a dictionary containing the names and data types of the columns of the table
        """
        fields = self._data.dtype.fields
        return {name: fields[name][0] for name in fields.keys()}

    @property
    def column_names(self):
        """
        Lists the column names.
        :return: a tuple of the column names, in the order in which they are stored in the table.
        """
        return self._data.dtype.names

    def as_recarray(self):
        """
        Returns a NumPy RecArray containing the table's data (but not its metadata).
        :return: a numpy.recarray, which allows fields to be accessed as data attributes (i.e., object.column_name).
        """
        return self._data.view(_np.recarray)


class Collection:
    """
    Manages a collection of objects and the metadata describing the collection.
    """
    def __init__(self, data, name=None, metadata=None):
        """
        :param data: an iterable, indexable container of Trieste `Array` objects or `Table` objects. Note that
        `Collection`s are not intended to be nested; you cannot create a `Collection` of `Collection`s.
        :param metadata: a Python dict containing metadata describing the content of `data` (optional, but encouraged).
        :param name: the name of the group of data objects stored in this `Collection` (optional). If the name is not
        provided and the code is being executed in IPython, then the name of the variable provided as the `data`
        parameter will be used as the name of the `Collection`. Otherwise, the name will be set to `untitled_N`, where
        `N` is an integer.
        """

        self._data = data

        if len(self._data) < 2:
            raise ValueError("Do not use a Collection to store a single object.")

        self._container_type = data[0].metadata['type']

        if 'Collection' in self._container_type:
            raise ValueError("A Collection cannot contain another Collection (Collections must not be nested).")

        names = set()

        for ob in data:
            if ob.metadata['type'] != self._container_type:
                raise ValueError("All objects inside of a Collection must be of the same type.")
            data_name = ob.metadata['name']
            if data_name in names:
                raise ValueError("Each object in a Collection must have a unique name. Encountered '{name}' twice.")
            names.add(data_name)

        if metadata is None:
            self._metadata = {}
        else:
            if isinstance(metadata, dict):
                self._metadata = _copy.copy(metadata)
            else:
                raise TypeError('Metadata must be a dict')

        if name is None:
            varname = _variable_name(data)
            if 'name' in self._metadata.keys():
                self._name = self._metadata['name']
            elif varname is not None:
                self._name = varname
            else:
                global _n_untitled
                self._name = f"untitled_{_n_untitled}"
                _n_untitled += 1
        else:
            if isinstance(name, str):
                self._name = name
            else:
                raise TypeError("The name of an array must be a string.")

        self._metadata['numpy_version'] = numpy_version_tuple()
        self._metadata['python_version'] = python_version_tuple()
        self._metadata['type'] = f"{self._data[0].metadata['type']} Collection"
        self._metadata['name'] = self._name
        if 'doc' not in self._metadata.keys():
            self.metadata['doc'] = ""

        # only add a new IPython history string if this is not being loaded from a file that already
        # contains a history string.
        if 'ipython_history' not in self._metadata.keys():
            self._metadata['ipython_history'] = _get_ipython_history()

        self._data = _np.array(self._data, dtype=_np.object)

        self._contents = _np.array([self._metadata, self._data], dtype=_np.object)

        self._counter = 0

        self.__doc__ = self._metadata['doc']

        self._index_of = {a.name: idx for idx, a in enumerate(self._data)}

    def set_readme(self, docstring):
        """
        Sets the object's documentation string.
        :param docstring: a string, describing the contents of the `Collection` (if possible, also include information
        regarding how to use the data and how the data was created).
        """
        self._metadata['doc'] = docstring
        self.__doc__ = self._metadata['doc']

    def save_as(self, filename):
        save(filename, {}, self)

    @property
    def metadata(self):
        return self._metadata

    @property
    def data(self):
        """
        The contents of the managed array, which contains multiple Array objects.
        """
        return self._data

    @property
    def name(self):
        """
        The name of the object.
        """
        return self._name

    @property
    def raw(self):
        """
        The raw, NumPy version of this object (i.e., the underlying data structure).
        """
        return self._contents

    @property
    def toc(self):
        """
        A list containing the names of the objects in the collection.
        """
        return [ob.name for ob in self._data]

    @property
    def readme(self):
        """
        Returns a documentation string describing the contents of the array.
        """
        return self._metadata['doc']

    @property
    def history(self):
        """
        If the object was created from within an IPython session. The commands leading up to the creation of
        the object are listed here, as a string.
        """
        if 'ipython_history' in self._metadata.keys():
            return self._metadata['ipython_history']
        else:
            return ''

    def print_history(self):
        """
        Prints the string output by self.history.
        """
        print(self.history)

    def __getitem__(self, index):
        """
        Allows the Collection to be indexed.
        :param index: The index of the Array object within the Collection OR the name of one of the objects within the
        Collection.
        :return: The Array object at the position specified by the index parameter.
        """
        if isinstance(index, int):
            return self._data[index]
        elif isinstance(index, str):
            return self._data[self._index_of[index]]
        else:
            raise ValueError("index must be either an integer or string")

    def __repr__(self):
        return f"<{self._name}: a Collection of {len(self._data)} {self._container_type}s>"

    def __iter__(self):
        """Returns itself as an iterator object."""
        return self

    def __next__(self):
        """Returns the next item, when iterating."""
        if self._counter == len(self._data):
            self._counter = 0
            raise StopIteration
        else:
            self._counter += 1
            return self._data[self._counter - 1]


class File:
    """
    Represents the contents of a file stored on disk. This should only be used when reading data. It is not
    designed for modifying the contents of files.
    """
    def __init__(self, raw_numpy_file):
        self._file = raw_numpy_file

        self._toc = {k: self._file[k][0]['type'] for k in self._file.keys() if k != 'metadata'}

        self._keys = [k for k in self._file.keys() if k != 'metadata']

        self._name = raw_numpy_file.fid.name

        metadata = self._file['metadata'][0]

        self.__doc__ = metadata['doc']

        self._counter = 0

    @property
    def metadata(self):
        """
        The file's metadata dictionary.
        """
        return self._file['metadata'][0]

    @property
    def toc(self):
        """
        Table of contents: A dictionary summarizing the contents of the file.
        """
        return self._toc

    @property
    def name(self):
        """
        The name of the file (i.e., the actual file path / name).
        """
        return self._name

    @property
    def readme(self):
        """
        A documentation string (a ReadMe) document describing the contents of the file.
        """
        return self.__doc__

    @property
    def history(self):
        """
        If the file was created from within an IPython session. The commands leading up to the creation of
        the file are listed here, as a string.
        """
        if 'ipython_history' in self.metadata.keys():
            return self.metadata['ipython_history']
        else:
            return ''

    def print_history(self):
        """
        Prints the string output by `self.history` See the documentation of `history` for more details.
        """
        print(self.history)

    def print_toc(self):
        """
        Prints the table of contents.
        """
        print("")
        header = f" Index      Name               Type"
        print(header)
        print(' ' + '-' * (len(header) + 6))

        for i, (key, value) in enumerate(self.toc.items()):
            print(f"{i:6d} :    {key:15.15}    {value}")

        print(' ' + '-' * (len(header) + 6))

    def __repr__(self):
        return f"<{self._name}: a Trieste file>"

    def __getitem__(self, key):
        """Returns the `Array`, `Table`, or `Collection` object associated with the key."""

        if isinstance(key, int):
            key = self._keys[key]

        if not isinstance(key, str):
            raise TypeError(f"The key, must either be an integer or a string, not {type(key)}")

        target_file = self._file[key]

        target_metadata = target_file[0]
        target_data = target_file[1]

        if 'Collection' in target_metadata['type']:
            ObjectType = Collection
        elif 'Array' in target_metadata['type']:
            ObjectType = Array
        elif 'Table' in target_metadata['type']:
            ObjectType = Table
        else:
            raise TypeError(f"{target_metadata['type']} is not a supported type.")

        return ObjectType(data=target_data, name=key, metadata=target_metadata)

    def __iter__(self):
        """Returns itself as an iterator object."""
        return self

    def __next__(self):
        """Returns the next item, when iterating."""
        if self._counter == len(self._keys):
            self._counter = 0
            raise StopIteration
        else:
            self._counter += 1
            return self[self._keys[self._counter - 1]]
