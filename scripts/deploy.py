# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import upip
import upip_utarfile as tarfile
from uzlib import DecompIO

print("Installing package from deploy")
with open('/deploy.tgz', 'rb') as f:
    decomp_stream = DecompIO(f, 16 + 15)
    tarchive = tarfile.TarFile(fileobj=decomp_stream)

    # This assumes upip.install_tar just installs everything
    # TODO Could use own code here
    upip.install_tar(tarchive, '/lib/')
