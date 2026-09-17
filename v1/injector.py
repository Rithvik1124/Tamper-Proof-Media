# injector.py
import struct
import zlib
import hashlib
import sys


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
TAMP_CHUNK = b"TAMP"


def read_chunks(data):
    """
    Parse a PNG into:
        (chunk_type, chunk_data)
    """

    if not data.startswith(PNG_SIGNATURE):
        raise ValueError("Not a PNG file")

    chunks = []
    offset = len(PNG_SIGNATURE)

    while offset < len(data):
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        chunk_type = data[offset + 4:offset + 8]
        chunk_data = data[offset + 8:offset + 8 + length]

        chunks.append((chunk_type, chunk_data))

        offset += 12 + length

        if chunk_type == b"IEND":
            break

    return chunks


def make_chunk(chunk_type, data):
    """
    Construct a PNG chunk:

        length
        type
        data
        CRC
    """

    length = struct.pack(">I", len(data))

    crc = zlib.crc32(chunk_type)
    crc = zlib.crc32(data, crc)
    crc = struct.pack(">I", crc & 0xffffffff)

    return length + chunk_type + data + crc


def inject(input_file, output_file):
    with open(input_file, "rb") as f:
        png = f.read()

    chunks = read_chunks(png)

    ihdr = None
    idat_data = bytearray()

    for chunk_type, chunk_data in chunks:

        if chunk_type == b"IHDR":
            ihdr = chunk_data

        elif chunk_type == b"IDAT":
            idat_data.extend(chunk_data)

    if ihdr is None:
        raise ValueError("PNG does not contain IHDR")

    if not idat_data:
        raise ValueError("PNG does not contain IDAT")

    # ---------------------------------------------------------
    # AUTHENTICATED DATA
    #
    # We deliberately DON'T hash the tamp chunk itself.
    # Otherwise the authentication value would depend on itself.
    # ---------------------------------------------------------

    authenticated_data = ihdr + bytes(idat_data)

    image_hash = hashlib.sha256(authenticated_data).digest()

    print("SHA-256:")
    print(image_hash.hex())

    # tamp payload:
    #
    # 4 bytes  -> version
    # 32 bytes -> SHA-256
    #
    tamp_payload = struct.pack(">I", 1) + image_hash

    tamp_chunk = make_chunk(TAMP_CHUNK, tamp_payload)

    # ---------------------------------------------------------
    # Rebuild PNG
    # ---------------------------------------------------------

    output = bytearray()
    output.extend(PNG_SIGNATURE)

    inserted = False

    for chunk_type, chunk_data in chunks:

        # Put tamp immediately after IHDR
        output.extend(make_chunk(chunk_type, chunk_data))

        if chunk_type == b"IHDR" and not inserted:
            output.extend(tamp_chunk)
            inserted = True

    with open(output_file, "wb") as f:
        f.write(output)

    print(f"Protected PNG written to: {output_file}")


if __name__ == "__main__":

    if len(sys.argv) != 3:
        print("Usage:")
        print("  python injector.py input.png protected.png")
        sys.exit(1)

    inject(sys.argv[1], sys.argv[2])