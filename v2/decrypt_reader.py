from PIL import Image
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import hashlib


SECRET = b"foo"


def derive_key():
    return hashlib.sha256(SECRET).digest()


def decrypt_pixels(encrypted_pixels: bytes) -> bytes:
    key = derive_key()

    iv = hashlib.sha256(b"robin-demo-iv").digest()[:16]

    cipher = Cipher(algorithms.AES(key),modes.CTR(iv))

    decryptor = cipher.decryptor()

    return decryptor.update(encrypted_pixels) + decryptor.finalize()


# MAIN

input_file = "notfoo.png"
encrypted_image = Image.open(input_file).convert("RGB")

width, height = encrypted_image.size

encrypted_pixels = encrypted_image.tobytes()

print("Encrypted image:")
print("  size:", width, "x", height)
print("  bytes:", len(encrypted_pixels))


# Decrypt
original_pixels = decrypt_pixels(encrypted_pixels)
print("Decrypted bytes:", len(original_pixels))
assert len(original_pixels) == width * height * 3


# Reconstruct
original_image = Image.frombytes(
    "RGB",
    (width, height),
    original_pixels,
)

original_image.save("recovered.png")
print("Recovered image: recovered.png")
original_image.show()