# Function Extractor

Function Extractor is a plugin created for the Clang compiler frontend.
Its goal is to extract C function definitions from C files, and outline them
to a C file of their own, where they can be trated as standalone kernels. It
can also perform this task for an entire source file in itself. In this mode,
it collects all the function definitions in a file, and outputs them to
a file that aggregates them, which can also be treated as a single program
for compilation.

IMPORTANT: Keep in mind that the plugin's goal is to deal with not-compilable
standalone C files. This means that even if the file is missing definitions,
header files, etc, the plugin will still run. As long as it can find a node
in the program's Abstract Syntax Tree for a function definition, it will
extract its source code.

The requirements for compiling the plugin are a working build of the LLVM
project, with Clang also compiled within it. The commands below show how
to build it.

```
  cd <path-to-llvm-build-folder>
  LLVM_BUILD_DIR=`pwd`

  cd <path-to-repository>
  cd src/extractor/
  mkdir build
  cd build
  cmake ../ -DLLVM_DIR=${LLVM_BUILD_DIR}/lib/cmake/llvm -DClang_DIR=${LLVM_BUILD_DIR}/lib/cmake/clang
```

Then, when you run CMake to create the Makefiles for your LLVM build then
compile it, Function Extractor should be compiled as well. You can find its
shared library file in the /lib/ directory of your LLVM build folder.

You can then run the plugin with Clang by doing the following:

```
PLUGIN_LIB=<path_to_repo>/build/libFunctionExtractor.so

clang -cc1 -load $PLUGIN_LIB -plugin -extract-funcs <input_file> -fsyntax-only
```

Then, for each function definition found in the input file, Function Extractor
will outline its implementation to a file with the format
"extr_\<filename\>_\<functionname\>", where \<filename\> refers to the original file
that contained the function, and \<functionname\> is the function's original name.

Keep in mind that for static functions the plugin will add a ((used)) attribute
before the function's definition. This is to force compilers to generate object
code for it regardless of it being used in its translation unit or not.

To run the extractor in whole-file processing mode, which collects functions
from the entire file instead, one can add the whole file flag, like so:

```
clang -cc1 -load $PLUGIN_LIB -plugin extract-funcs -plugin-arg-extract-funcs \
	-whole-file <input_file> -fsyntax-only
```

# Extracting and Reconstruction engine

We have also built an infrastructure that combines the Function Extractor
plugin and the Psyche-C type reconstruction engine to create a collection
of benchmarks from a corpus of C projects.

These are implemented in Python 3, thus having a working implementation
of Python 3 is a requirement. They are implemented in two Python programs:
extractor.py and reconstructor.py.

The extractor.py program takes as input a corpus of C repositories, and
breaks them down into would-be programs, each of which is composed of
a single C function. Its main input should be a parent directory,
where each subdirectory contains a folder for a repository that contains
C source code.

The example below shows a typical use case, where REPOS\_DIR is a folder
containing several C repositories cloned from GitHub.

```
PLUGIN_LIB=<path_to_repo>/build/libFunctionExtractor.so
CLANG_BIN=<path_to_llvm_build_dir>/bin/clang
REPOS_DIR=/path/to/root/folder/of/C/codebase/
DEST_DIR=/path/to/where/extracted/functions/will/be/stored/

python3 extractor.py $REPOS_DIR $CLANG_BIN $PLUGIN_LIB $DEST_DIR
```

An additional logging level flag can be sent to the program after the
other input arguments, which controls how much logging is done during
the extraction process. A log level of 0 logs nothing. Log level 1
logs general execution, which is shown after the process is done.
Log level 2 additionally creates csv files containing statistics
on the extraction process.

The reconstruction program then can leverage Psyche-C to create
a suite of compilable programs, from a collection extracted using
the extractor. The commands below show a typical use case, where
EXTR\_DIR refers to a directory containing a collection of programs
extracted using the extractor program.

```
PSYCHEC_DIR=<path_to_repo>/src/psychec
COMPILER=/path/to/C/compiler
EXTR_DIR=</path/to/folder/of/extracted/repos/
DEST_DIR=/path/to/where/compilable/programs/will/be/stored/

python3 reconstructor.py $EXTR_DIR $COMPILER $PSYCHEC_DIR $DEST_DIR
```

The additional logging flag can also be used for the reconstructor,
as described in the documentation for the extractor. Afer the
reconstructor is done running, the destination folder will contain
a directory for each original repository. In each directory, the
programs which could be successfully compiled by the compiler
provided will be stored in a subdirectory equivalent to their
location in the original repository.
