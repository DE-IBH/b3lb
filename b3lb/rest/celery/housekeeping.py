from rest.models import Asset, AssetLogo, AssetSlide


def celery_cleanup_assets():
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
