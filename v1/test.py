import struct

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

with open("inj.png", "rb") as f:
    data = f.read()

offset = 8

while offset < len(data):

    length = struct.unpack(">I", data[offset:offset + 4])[0]
    chunk_type = data[offset + 4:offset + 8]
    chunk_data = data[offset + 8:offset + 8 + length]

    print(
        chunk_type.decode("ascii", errors="replace"),
        "length =", length
    )

    # Look for our authentication chunk
    if chunk_type == b"TAMP":

        print("  *** TAMPER AUTHENTICATION CHUNK ***")

        version = struct.unpack(">I", chunk_data[:4])[0]
        auth_hash = chunk_data[4:36]

        print("  Version :", version)
        print("  SHA-256 :", auth_hash.hex())

    offset += 12 + length