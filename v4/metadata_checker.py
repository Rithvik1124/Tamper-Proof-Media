import sys
import json
import subprocess

'''Metadata Checker based on: https://fast.io/resources/ai-generated-image-metadata-detection-tools/'''

AI_SOFTWARE = {
    "dall-e",
    "dall·e",
    "chatgpt",
    "openai",
    "adobe firefly",
    "firefly",
    "midjourney",
    "stable diffusion",
    "automatic1111",
    "comfyui",
    "invokeai",
    "imagen",
    "gemini",
}


AI_DIGITAL_SOURCE_TYPES = {
    "trainedalgorithmicmedia",
    "compositewithtrainedalgorithmicmedia",
}


PROMPT_INDICATORS = {
    "prompt:",
    "negative prompt:",
    "steps:",
    "sampler:",
    "cfg scale:",
    "seed:",
    "model:",
    "stable diffusion",
    "midjourney",
    "dall-e",
    "firefly",
}


def _normalise(value):
    if value is None:
        return ""

    if isinstance(value, list):
        value = " ".join(map(str, value))

    return str(value).strip().lower()

''' Get Metadata from image using exiftool'''
def get_metadata(path: str) -> dict:
    result = subprocess.run(
        [
            "exiftool",
            "-json",
            "-a",          # Include duplicate tags
            "-G1",         # Include metadata group
            "-s",          # Simplified tag names
            path,
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return {}

    try:
        data = json.loads(result.stdout)
        return data[0] if data else {}
    except (json.JSONDecodeError, IndexError):
        return {}


def analyze_image(path: str) -> dict:
    metadata = get_metadata(path)

    if not metadata:
        return {
            "ai_generated": False,
            "signals": [],
        }

    signals = []

    for key, value in metadata.items():

        key_lower = key.lower()
        value_lower = _normalise(value)

        if "software" in key_lower:

            for software in AI_SOFTWARE:
                if software in value_lower:
                    signals.append(
                        f"{key}: {value}"
                    )
    for key, value in metadata.items():

        if key.lower() in {
            "digitalsourcetype",
            "iptc:digitalsourcetype",
            "xmp:digitalsourcetype",
        }:

            value_lower = _normalise(value)

            for source_type in AI_DIGITAL_SOURCE_TYPES:

                if source_type in value_lower:
                    signals.append(
                        f"{key}: {value}"
                    )
    '''Find prompt in metadata (for image generators like midjourney)'''
    for key, value in metadata.items():

        value_lower = _normalise(value)

        if not value_lower:
            continue

        for indicator in PROMPT_INDICATORS:

            if indicator in value_lower:

                signals.append(
                    f"{key}: {value}"
                )

                break

    '''C2PA Metadata'''
    for key, value in metadata.items():

        key_lower = key.lower()
        value_lower = _normalise(value)

        if "c2pa" in key_lower:

            signals.append(
                f"{key}: {value}"
            )

        elif "c2pa" in value_lower:

            signals.append(
                f"{key}: {value}"
            )

    '''Remove duplicate signals'''
    signals = list(dict.fromkeys(signals))

    return {
        "ai_generated": bool(signals),
        "signals": signals,
    }


def contains_ai_metadata(path: str) -> bool:
    return analyze_image(path)["ai_generated"]

if __name__=="__main__":
    path = sys.argv[1]
    print(f"Contains AI metdata: {contains_ai_metadata(path)}")