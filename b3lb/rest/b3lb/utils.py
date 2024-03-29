# B3LB - BigBlueButton Load Balancer
# Copyright (C) 2020-2022 IBH IT-Service GmbH
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License
# for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# This utils file contains functions without import of b3lb files to prevent circular imports
from _hashlib import HASH
from xml.sax.saxutils import escape


def get_checksum(sha: HASH, url_string: str) -> str:
    sha.update(url_string.encode())
    return sha.hexdigest()

def xml_escape(string: str) -> str:
    if isinstance(string, str):
        return escape(string)
    else:
        return ""
