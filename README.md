# Trieste

This module defines the Trieste file format as well as the rules for manipulating Trieste files. Trieste files are
intended to contain *archival* data. Once written, they are not intended to be modified---only read.

Trieste files can store *N*-dimensional arrays, tables, and collections of arrays or tables. Every array, table, and
collection has a name and contains a metadata dictionary (a map data structure) that can be augmented by the
file's author to provide documentation regarding the content of each object stored in the file, as well as instructions
on using the data in the file. The goal is to provide the person reading the file with as much documentation and
forensic information as possible about the file's contents and the process by which the file was created.

The current prototype of Trieste is a Python-specific format consisting of a specially-formatted, compressed NumPy .npz
file in which every data object (NumPy array) has a corresponding metadata dictionary. Some of the metadata attributes
are automatically added. Others, such as documentation strings (comments / READMEs) and object names, are strongly
encouraged, but can be left empty. The automatically-added metadata are intended for software version compatibility
checks and record-keeping / traceability. For example, the following are automatically added to the metadata:

   * The versions of NumPy, Python, and the Trieste module that were used to generate the file.
   * The OS, platform, and CPU architecture with which the file was created.
   * The file's creation time / date.
   * The username under which the file was created.
   * The hostname of the system on which the file was created.
   * The path to the active directory on the host machine when the file was created.
   * If the file is generated within an IPython session or Jupyter notebook session, the command history of the
     session is also stored, as a string.

The Trieste module contains 2 primary stand-alone functions:

1. `load()`: for loading a Trieste file from the file system.

2. `save()`: for saving a Trieste file to the file system.

There are 4 classes:

1. `Array`: for storing N-dimensional arrays.

2. `Table`: for storing Arrays with labeled columns of potentially different data types (analogous with a spreadsheet,
    ASCII table, or database table).

3. `Collection`: for storing multiple `Array` or `Table` objects. Collections are only allowed to store a single type
    of object. For example, a collection can store multiple 2-D `Array`s (like layers of an image) or multiple `Table`s,
    but not a `Table` *and* an `Array`. Furthermore, the names of the objects in a `Collection` must be unique. Among
    other benefits, this allows `Collection` objects to be indexed using the name of the object, so the syntax
    `collection['red']` can be used to access the object in the collection whose name is `red`. `Collection`s are also
    ordered containers, which means that they can be indexed by position, with an integer subscript, as in
    `collection[3]`. `Collection`s are iterable, so that the syntax `for object in collection:` can be used to iterate
    through the contents.

4. `File`: for interfacing with a file, after the file has been loaded.

    There are two types of files, in general:

    * files containing one object
    * files containing multiple objects

    When loading a file containing only one object, the `load` function constructs the object itself (i.e., an instance
    of `Array`, `Table`, or `Collection`). When a file containing multiple objects is loaded, a `File` instance is
    created. Just like `Collection` objects, `File` objects are iterable and can be indexed by object name or position.
