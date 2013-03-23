# M13

M13 is an LLDB script which gives you a REST API to interact with LLDB.

## Dependencies

M13 has only one external dependency: Bottle.

* bottle v0.11+ (may work with earlier versions)

## Installation

It's recommended to load M13 when LLDB starts. To do this, throw the following code snippit into your `~/.lldbinit` file.

    command script import /path/to/m13/m13.py

