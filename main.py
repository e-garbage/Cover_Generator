import os
import random
import typing
import numpy as np
from PIL import Image, ImageDraw
import datetime
from pathlib import Path

##############################
# This code is a remix of    #
# Github user qroph's        #
# ordered-dithering project  #
# and Github user kosachevds'#
# Invader-generator project. #
##############################

BACKGROUND_COLOR = (32,22,22)
BACKGROUND_DETAIL= (50,50,50)


class Dither:
    # 8×8 Bayer matrix, normalized to [-0.5, 0.5)
    DITHERING_MATRIX = tuple(
        x / 64.0 - 0.5
        for x in (
            0, 32,  8, 40,  2, 34, 10, 42,
            48, 16, 56, 24, 50, 18, 58, 26,
            12, 44,  4, 36, 14, 46,  6, 38,
            60, 28, 52, 20, 62, 30, 54, 22,
            3, 35, 11, 43,  1, 33,  9, 41,
            51, 19, 59, 27, 49, 17, 57, 25,
            15, 47,  7, 39, 13, 45,  5, 37,
            63, 31, 55, 23, 61, 29, 53, 21,
        )
    )

    @staticmethod
    def dithering_threshold(pos):
        """Return the dithering threshold for a pixel position."""
        x, y = (int(p) % 8 for p in pos)
        return Dither.DITHERING_MATRIX[x + y * 8]

    @staticmethod
    def lut_color(lut, color):
        """Return a LUT-mapped color for an RGB input."""
        size = lut.height
        rgb = np.floor((np.asarray(color) / 256.0) * size).astype(int)

        x = rgb[0] + rgb[2] * size + 0.5 / lut.width
        y = rgb[1] + 0.5 / lut.height

        return lut.getpixel((x, y))

    @classmethod
    def dither_image(cls, image, lut):
        """Dither an image using a lookup table."""
        output = Image.new("RGB", image.size)

        for pos in np.ndindex(image.width, image.height):
            color = np.asarray(image.getpixel(pos))

            spread = cls.lut_color(lut, color)[3]
            threshold = cls.dithering_threshold(pos)

            dithered = np.clip(color + spread * threshold, 0, 255)
            output.putpixel(pos, cls.lut_color(lut, dithered))

        return output


class Square(typing.NamedTuple):
    top_left_x: float
    top_left_y: float
    size: float


def get_random_color_set(count: int, count_non_black: int) -> list:
    lower = 50
    upper = 215
    colors = np.random.randint(lower, upper, (count_non_black, 3))
    colors = [tuple(item) for item in colors]
    colors += (count - count_non_black) * [(0, 0, 0)]
    return colors

def get_color_set(count: int, count_non_black: int) -> list:
    colors = [
        (255, 0, 0),
        (0, 255, 0),
        (0, 0, 255),
        (255, 255, 0),
        (255, 0, 255),
        (0, 255, 255),
        (128, 0, 128),
        (255, 165, 0),
        (0, 128, 0),
    ]
    selected_colors = colors[:count_non_black]
    selected_colors += (count - count_non_black) * [BACKGROUND_COLOR]
    return selected_colors


def draw_cell(square: Square, draw: ImageDraw, color: tuple):
    border = (
        square.top_left_x,
        square.top_left_y,
        square.top_left_x + square.size,
        square.top_left_y + square.size)
    # Don't draw background cells so underlying background remains visible
    if color == BACKGROUND_COLOR or color == (0, 0, 0):
        return
    draw.rectangle(border, color)


def generate_sprite_cells(square, invader_width):
    cell_width = square.size / invader_width
    colors = get_random_color_set(6, 3)
    color_stack = []
    middle = int(invader_width / 2)
    cells = {}
    for y in range(invader_width):
        for i, x in enumerate(range(invader_width)):
            cell = Square(
                x * cell_width + square.top_left_x,
                y * cell_width + square.top_left_y,
                cell_width
            )
            color_from_stack = (i > middle or
                                i == middle and invader_width % 2 == 0)
            if color_from_stack:
                color = color_stack.pop()
            else:
                color = random.choice(colors)
                if not (i == middle):
                    color_stack.append(color)
            cells[cell] = color
    black_cell_count = sum(1 for color in cells.values() if color == BACKGROUND_COLOR)
    if black_cell_count < len(cells) / 2:
        return cells
    return generate_sprite_cells(square, invader_width)


def draw_sprite(square, draw, invader_width):
    cells = generate_sprite_cells(square, invader_width)
    for (cell, color) in cells.items():
        draw_cell(cell, draw, color)

def generate_background(draw, picture_width):
    # draw a gray circle in the center (20% of image width radius)
    cx = picture_width / 2
    cy = picture_width / 2
    r = picture_width * 0.47
    for i in range(5):
        r = r-i*10
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(BACKGROUND_DETAIL), fill=None, width=i*5)

def scale_up(image, factor):
    image = image.resize((image.width*factor, image.height*factor), Image.NEAREST)
    return image

def save_image(image, directory, prefix):
    """
    Save an image to a directory with a timestamped filename.
    Returns the full path of the saved image.
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    t=datetime.datetime.now()
    filename = f"{prefix}-{t}.jpg"
    filepath = directory / filename
    image.save(filepath, format="JPEG")
    return filepath


def generate_grid(invader_width, invader_count, picture_width):
    result_image = Image.new("RGB", (picture_width, picture_width))
    draw = ImageDraw.Draw(result_image)
    draw = generate_background(draw, picture_width)
    sprite_layer = Image.new("RGBA", (picture_width, picture_width), (0, 0, 0, 0))
    sprite_draw = ImageDraw.Draw(sprite_layer)
    invader_size = picture_width / invader_count
    padding = invader_size / invader_width
    for x in range(0, invader_count):
        for y in range(0, invader_count):
            square = Square(
                x * invader_size + padding / 2,
                y * invader_size + padding / 2,
                invader_size - padding
            )
            draw_sprite(square, sprite_draw, invader_width)
    result_image.paste(sprite_layer, (0, 0), sprite_layer)
    dithered_image = Dither.dither_image(
        result_image,
        Image.open("citrink_lut.png"))
    result_image = dithered_image
    resize_factor = 7
    result_image = scale_up(result_image, resize_factor)
    if not os.path.exists("./Examples"):
        os.mkdir("./Examples")
    result_image.save("Examples/Example-{0}x{0}-{1}-{2}.jpg".format(
        invader_width, invader_count, picture_width))

def generate_one(invader_width, picture_width, resize_factor):
    # base with background drawn
    result_image = Image.new("RGB", (picture_width, picture_width), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(result_image)
    generate_background(draw, picture_width)
    # transparent sprite layer
    sprite_layer = Image.new("RGBA", (picture_width, picture_width), (0, 0, 0, 0))
    sprite_draw = ImageDraw.Draw(sprite_layer)
    invader_size = picture_width/2
    padding = (picture_width-invader_size)/2
    square = Square(
        padding ,
        padding,
        invader_size
    )
    draw_sprite(square, sprite_draw, invader_width)
    # composite sprites onto background then dither
    result_image.paste(sprite_layer, (0, 0), sprite_layer)

    dithered_image = Dither.dither_image(
        result_image,
        Image.open("citrink_lut.png"))
    result_image = dithered_image
    resize_factor=7
    result_image = scale_up(result_image, resize_factor)
    save_image(result_image, "Outputs", "Single")


if __name__ == "__main__":
    resize_factor=7
    generate_one(7, 256, resize_factor)