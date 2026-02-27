from pathlib import Path


def test_core_does_not_import_adapters() -> None:
    root = Path("custom_components/xiaomi_doorbell_m3u8_archiver/core")
    violations: list[str] = []

    for py_file in root.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("from") or stripped.startswith("import"):
                if "adapters" in stripped:
                    violations.append(f"{py_file}: {stripped}")

    assert not violations, "\n".join(violations)
