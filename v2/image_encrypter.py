from PIL import Image
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import hashlib
import struct
import zlib
import binascii


SECRET = b"foo"
CUSTOM_CHUNK = b"iTXt"


def derive_key():
    return hashlib.sha256(SECRET).digest()


def encrypt_pixels(pixel_data: bytes) -> bytes:
    key = derive_key()

    iv = hashlib.sha256(
        b"robin-demo-iv"
    ).digest()[:16]

    cipher = Cipher(algorithms.AES(key),modes.CTR(iv))
    encryptor = cipher.encryptor()
    return encryptor.update(pixel_data) + encryptor.finalize()


def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    crc = binascii.crc32(chunk_type + data) & 0xffffffff
    return (struct.pack(">I", len(data))+ chunk_type+ data+ struct.pack(">I", crc))


def create_png(
    encrypted_pixels: bytes,
    width: int,
    height: int,
    output_path: str,
):
    # RGB = 3 bytes/pixel
    row_size = width * 3

    assert len(encrypted_pixels) == row_size * height

    # Construct PNG scanlines.
    # [filter byte][RGB RGB RGB ...]
    raw = bytearray()

    for y in range(height):
        start = y * row_size
        end = start + row_size

        raw.append(0)  # PNG filter = None
        raw.extend(encrypted_pixels[start:end])

    compressed = zlib.compress(bytes(raw), 9)

    png = bytearray()

    # PNG signature
    png.extend(b"\x89PNG\r\n\x1a\n")

    # IHDR
    ihdr = struct.pack(">IIBBBBB",width,height,8,  2,  0,0,0,)

    png.extend(png_chunk(b"IHDR", ihdr))


    # ENC1 = encryption format version
    # AES1 = AES-CTR
    metadata = b"ENC1AES1"

    png.extend(
        png_chunk(CUSTOM_CHUNK, metadata)
    )

    # Encrypted image data
    png.extend(png_chunk(b"IDAT", compressed))

    # End
    png.extend(png_chunk(b"IEND", b""))

    with open(output_path, "wb") as f:
        f.write(png)


# MAIN

source = "foo.png"
destination = "notfoo.png"

image = Image.open(source).convert("RGB")

width, height = image.size

original_pixels = image.tobytes()

print("Original image:")
print("  size:", width, "x", height)
print("  bytes:", len(original_pixels))

encrypted_pixels = encrypt_pixels(original_pixels)

print("Encrypted:")
print("  bytes:", len(encrypted_pixels))

assert len(original_pixels) == len(encrypted_pixels)

create_png(
    encrypted_pixels,
    width,
    height,
    destination,
)

print("Created:", destination)