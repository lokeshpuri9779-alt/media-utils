from PIL import Image, ImageChops, ImageStat

def difference(a, b):
    with Image.open(a) as src:
        first = src.convert('RGB').resize((256, 256))
    with Image.open(b) as src:
        second = src.convert('RGB').resize((256, 256))
    return round(sum(ImageStat.Stat(ImageChops.difference(first, second)).mean) / 3, 2)
