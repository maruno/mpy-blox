# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from logging import DEBUG, INFO, WARNING, ERROR

from mpy_blox.time import isotime

# Control
ESC = b'\x1b['
END = b'm'

# Style
RESET = b'0'
UNDERLINE = b'4'

# Colors
FG_RED = b'31'
FG_YELLOW = b'33'
FG_BLUE = b'34'
FG_CYAN = b'36'
FG_GREY = b'37'


def get_sgr_escape(codes):
    if isinstance(codes, bytes):
        codes = (codes,)
    return ESC + b';'.join(codes) + END


class VTSGRColorFormatter:
    def format(self, record):
        # Start with date
        formatted_msg = get_sgr_escape(FG_CYAN)
        formatted_msg += isotime().encode()
        formatted_msg += get_sgr_escape(RESET)
        formatted_msg += b' '

        # Log level tag
        level = record.levelno
        if level == DEBUG:
            formatted_msg += get_sgr_escape(FG_GREY)
            formatted_msg += b'[debug]'
        elif level == INFO:
            formatted_msg += get_sgr_escape(FG_BLUE)
            formatted_msg += b'[info]'
        elif level == WARNING:
            formatted_msg += get_sgr_escape(FG_YELLOW)
            formatted_msg += b'[warning]'
        elif level == ERROR:
            formatted_msg += get_sgr_escape(FG_RED)
            formatted_msg += b'[error]'
        else:
            formatted_msg += get_sgr_escape((UNDERLINE, FG_RED))
            formatted_msg += b'[critical]'
        formatted_msg += get_sgr_escape(RESET)
        formatted_msg += b' '
        
        return formatted_msg + (record.msg % record.args).encode()
