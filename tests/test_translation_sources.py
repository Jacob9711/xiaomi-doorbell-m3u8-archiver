import json
from pathlib import Path


INTEGRATION_ROOT = Path("custom_components/xiaomi_doorbell_m3u8_archiver")


def test_english_translation_matches_canonical_strings() -> None:
    strings = json.loads((INTEGRATION_ROOT / "strings.json").read_text())
    english = json.loads((INTEGRATION_ROOT / "translations/en.json").read_text())

    assert english == strings
