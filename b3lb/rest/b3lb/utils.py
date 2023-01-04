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

from jinja2 import Template

def xml_escape(string):
    if isinstance(string, str):
        escape_symbols = [("&", "&amp;"), ("<", "&lt;"), (">", "&gt;"), ("'", "&apos;"), ('"', "&quot;") ]
        for symbol, escape in escape_symbols:
            string = string.replace(symbol, escape)
        return string
    else:
        return ""

# ToDo: Use django-template instead of jinja2 -> Needs to update the templates, because of DjangoTemplateErrors
def load_template(file_name):
    with open(f"rest/templates/{file_name}") as template_file:
        return Template(template_file.read())
