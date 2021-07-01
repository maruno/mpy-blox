# Logging submodule
logging is Pycopy's implementation of a subset of CPythons logging module. This module defines functions and classes which implement a flexible event logging system for applications and libraries.

Major differences to CPython logging:

    Simplified event propagation, multilevel logger organization is not handled, currently there're just 2 levels: root logger and specific named loggers.
    Filters are not supported.

# Changes from pycopy-lib
* Removed requirement on pycopy to run instead on standard micropython
