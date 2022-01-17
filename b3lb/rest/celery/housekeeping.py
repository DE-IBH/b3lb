# B3LB - BigBlueButton Load Balancer
# Copyright (C) 2020-2021 IBH IT-Service GmbH
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

from rest.models import Asset, AssetLogo, AssetSlide


def celery_cleanup_assets():
    """
    Housekeeping routine for assets.
    """
    slides = list(AssetSlide.objects.all())
    logos = list(AssetLogo.objects.all())
    assets = Asset.objects.all()

    for asset in assets:
        for slide_index in range(len(slides)-1, -1, -1):
            if asset.slide.name == slides[slide_index].filename:
                del slides[slide_index]
        for logo_index in range(len(logos)-1, -1, -1):
            if asset.logo.name == logos[logo_index].filename:
                del logos[logo_index]

    del assets

    slides_deleted = 0
    for slide in slides:
        slide.delete()
        slides_deleted += 1
    logos_deleted = 0
    for logo in logos:
        logo.delete()
        logos_deleted += 1

    return "Delete {} slides and {} logos.".format(slides_deleted, logos_deleted)
