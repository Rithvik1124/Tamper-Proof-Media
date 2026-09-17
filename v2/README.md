# Second Iteration

## Image Encryption
- Decompress the pixel bytes in the original png
    - Encrypt them with a secret key
    - Convert image to png

## Image Decryption
- Reader shares the secret
    - Decrypt using AES, convert image back to its original form


```
|   IHDR                         |

|   TAMP(custom chunk)           |

|   IDAT(compressed pixel bytes) |

|   ...                          |

|   IEND                         |
```