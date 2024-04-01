# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from binascii import a2b_base64, b2a_base64


def urlsafe_b64decode(s):
    if isinstance(s, str):
        s = s.encode()

    s = s.replace(b'-', b'+').replace(b'_', b'/')
    remainder = len(s) % 4
    if remainder:
        # Add padding
        s += b"=" * (4 - remainder) 
    return a2b_base64(s)
    

def urlsafe_b64encode(b):
    encoded_padded = b2a_base64(b).replace(b'/', b'_').replace(b'+', b'-')
    # Strip padding, somehow includes a newline from b2a_base64?
    return encoded_padded.strip(b'\n').strip(b'=')
