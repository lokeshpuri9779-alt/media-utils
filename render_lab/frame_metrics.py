from PIL import Image, ImageChops, ImageStat

def difference(a, b):
    with Image.open(a) as src:
        first = src.convert('RGB').resize((256, 256))
    with Image.open(b) as src:
        second = src.convert('RGB').resize((256, 256))
    return round(sum(ImageStat.Stat(ImageChops.difference(first, second)).mean) / 3, 2)


def regional_differences(a, b):
    """Compare coarse regions; these are not character identity scores."""
    from PIL import Image
    with Image.open(a) as src:
        first = src.convert('RGB').resize((256, 256))
    with Image.open(b) as src:
        second = src.convert('RGB').resize((256, 256))
    regions = {'left': (0, 0, 128, 256), 'right': (128, 0, 256, 256),
               'center': (64, 32, 192, 224), 'upper': (0, 0, 256, 128)}
    from PIL import ImageChops, ImageStat
    results = {}
    for name, bounds in regions.items():
        delta = ImageChops.difference(first.crop(bounds), second.crop(bounds))
        results[name] = round(sum(ImageStat.Stat(delta).mean) / 3, 2)
    return results
