import struct
import hashlib
import io

from PIL import Image


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
TAMP_CHUNK = b"TAMP"


def read_chunks(data):
    """Parse PNG chunks."""

    if not data.startswith(PNG_SIGNATURE):
        raise ValueError("Not a PNG file")

    chunks = []

    offset = 8

    while offset < len(data):

        length = struct.unpack(
            ">I",
            data[offset:offset + 4]
        )[0]

        chunk_type = data[offset + 4:offset + 8]

        chunk_data = data[
            offset + 8:
            offset + 8 + length
        ]

        chunks.append(
            (chunk_type, chunk_data)
        )

        offset += 12 + length

        if chunk_type == b"IEND":
            break

    return chunks


def read_robin(filename):

    # ---------------------------------------------------------
    # Read entire PNG
    # ---------------------------------------------------------

    with open(filename, "rb") as f:
        png_data = f.read()

    chunks = read_chunks(png_data)

    # ---------------------------------------------------------
    # Extract authentication information
    # ---------------------------------------------------------

    ihdr = None
    idat_data = bytearray()
    stored_hash = None

    for chunk_type, chunk_data in chunks:

        if chunk_type == b"IHDR":

            ihdr = chunk_data

        elif chunk_type == b"IDAT":

            idat_data.extend(chunk_data)

        elif chunk_type == TAMP_CHUNK:

            if len(chunk_data) != 36:
                raise ValueError(
                    "Invalid TAMP chunk"
                )

            version = struct.unpack(
                ">I",
                chunk_data[:4]
            )[0]

            if version != 1:
                raise ValueError(
                    f"Unsupported TAMP version: {version}"
                )

            stored_hash = chunk_data[4:36]

    # ---------------------------------------------------------
    # Make sure everything exists
    # ---------------------------------------------------------

    if ihdr is None:
        raise ValueError("Missing IHDR")

    if not idat_data:
        raise ValueError("Missing IDAT")

    if stored_hash is None:
        raise ValueError(
            "This PNG does not contain a TAMP authentication chunk"
        )

    # ---------------------------------------------------------
    # Calculate current hash
    # ---------------------------------------------------------

    authenticated_data = (
        ihdr +
        bytes(idat_data)
    )

    calculated_hash = hashlib.sha256(
        authenticated_data
    ).digest()

    # ---------------------------------------------------------
    # Compare
    # ---------------------------------------------------------

    valid = (
        stored_hash == calculated_hash
    )

    print()
    print("========== ROBIN READER ==========")
    print()

    print("Stored hash:")
    print(stored_hash.hex())

    print()

    print("Calculated hash:")
    print(calculated_hash.hex())

    print()

    if valid:

        print("STATUS: ✓ AUTHENTIC")
        print("Image integrity verified.")

    else:

        print("STATUS: ✗ TAMPERED")
        print("Image integrity verification failed.")

    print()

    return valid, png_data


def display_image(filename, valid):

    # ---------------------------------------------------------
    # Load the actual PNG
    # ---------------------------------------------------------

    image = Image.open(filename)

    image.load()

    if valid:

        print("Displaying authentic image.")

        image.show()

    else:

        print("Displaying distorted image.")

        distort(image)


def distort(image):

    """
    Very simple demonstration distortion.

    We'll replace every second horizontal strip
    with noisy pixels.
    """

    import random

    image = image.convert("RGB")

    width, height = image.size

    pixels = image.load()

    # Distort roughly 20% of the image

    for y in range(0, height, 10):

        if random.random() < 0.2:

            for x in range(width):

                pixels[x, y] = (
                    random.randint(0, 255),
                    random.randint(0, 255),
                    random.randint(0, 255)
                )

    image.show()


if __name__ == "__main__":

    filename = "inj.png"

    valid, _ = read_robin(filename)

    display_image(filename, valid)