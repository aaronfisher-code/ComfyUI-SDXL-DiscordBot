from datetime import datetime
from math import ceil, sqrt

from PIL import Image


def create_gif_collage(images):
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    collage_path = f"./out/images_{timestamp}.gif"
    images[0].save(collage_path, save_all=True, append_images=images[1:], duration=125, loop=0)

    return collage_path


def create_collage(images):
    if (len(images) == 0):
        print("Error: No images to make collage")
        return None

    if (images[0].format == 'GIF'):
        return create_gif_collage(images)

    num_images = len(images)
    num_cols = ceil(sqrt(num_images))
    num_rows = ceil(num_images / num_cols)
    collage_width = max(image.width for image in images) * num_cols
    collage_height = max(image.height for image in images) * num_rows
    collage = Image.new('RGB', (collage_width, collage_height))

    for idx, image in enumerate(images):
        row = idx // num_cols
        col = idx % num_cols
        x_offset = col * image.width
        y_offset = row * image.height
        collage.paste(image, (x_offset, y_offset))

    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    collage_path = f"./out/images_{timestamp}.png"
    collage.save(collage_path)

    return collage_path

