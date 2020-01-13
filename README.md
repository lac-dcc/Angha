# Project Angha #

Project Angha provides an infrastructure for creating synthetic compilable
C benchmarks out of publicly available code repositories. Using a combination
of web-crawling, compiler frontend extension and type reconstruction, this
framework allows one to create a virtually unbounded number of compilable
programs.

This framework has three main components, whose requirements need to be met for
it to be usable. Refer to the documentation within each of these subprojects
to use them. They are:

* Web-crawler - contained within src/crawler, this Java application collects
publicly available C code using GitHub's public API.
* Psyche-C - this external project, included as a submodule in src/psychec,
is a type reconstruction engine for C. It receives as input an incomplete
program, and builds a compilable version of it through type inference.
* Function Extractor - contained within src/extractor, this tool uses a
combination of Clang frontend extensions, the aforementioned Psyche-C engine,
and Python to build a collection of compilable programs, from a corpus of raw C
repositories.

To use the project, clone the repository with the --recursive flag, then follow
the instructions to build and use each subproject.