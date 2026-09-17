# First Iteration

- Read the .png file, collect:
    - bytes = (header bytes + data bytes)

- Hash the bytes and inject as a custom PNG chunk as an "Authentication Tag"

- If any changes made to pixel bytes - hash changes

- Reader checks and compares hash.
    - If no change is made then hash verification is successful.
    - Else, verification fails

```
|   IHDR                         |

|   TAMP(custom chunk)           |

|   IDAT(compressed pixel bytes) |

|   ...                          |

|   IEND                         |
```