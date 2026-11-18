"""Tests for the soc_caps extractor against a synthetic ESP-IDF tree."""

from pathlib import Path

import pytest

from verino.chipdata.extract_soc_caps import (
    ExtractError,
    chip_config,
    extract,
    main,
    update_chip_file,
)
from verino.model.yamlio import dump_text, load_text

FAKE_IDF = Path(__file__).parent / "data" / "fake-idf"
CONFIG = chip_config("testchip")


def test_extract_reads_all_headers() -> None:
    block = extract(FAKE_IDF, CONFIG)
    assert block["provenance"] == {
        "kind": "soc_caps",
        "source": "esp-idf@v9.8.7",
        "idf_version": "v9.8.7",
        "files": sorted(block["provenance"]["files"]),
        "generated_by": "verino.chipdata.extract_soc_caps",
    }
    assert "components/soc/testchip/include/soc/soc_caps.h" in block["provenance"]["files"]
    assert "components/esp_hal_rmt/testchip/include/hal/rmt_ll.h" in block["provenance"]["files"]
    assert block["gpio"] == {
        "count": 10,
        "valid": ["GPIO0", "GPIO1", "GPIO2", "GPIO5", "GPIO6", "GPIO7", "GPIO8", "GPIO9"],
        "output": ["GPIO0", "GPIO1", "GPIO2", "GPIO5", "GPIO6", "GPIO7", "GPIO8"],
    }
    assert block["adc"] == {"adc1": {"GPIO1": 0, "GPIO2": 1}, "adc2": {"GPIO5": 0}}
    assert block["rtc_io"] == {"GPIO0": 0, "GPIO1": 2, "GPIO2": 1}
    assert block["fixed_pins"] == {
        "usb_dm": "GPIO7",
        "usb_dp": "GPIO8",
        "uart0_tx": "GPIO5",
        "uart0_rx": "GPIO6",
    }
    assert block["macros"]["SOC_I2C_NUM"] == 2
    assert block["macros"]["PCNT_LL_UNITS_PER_INST"] == 4
    assert block["macros"]["RMT_LL_CHANS_PER_INST"] == 8
    assert list(block["macros"]) == list(CONFIG.macros)


def test_missing_macro_is_an_error(tmp_path: Path) -> None:
    broken = tmp_path / "idf"
    for src in FAKE_IDF.rglob("*.h"):
        dst = broken / src.relative_to(FAKE_IDF)
        dst.parent.mkdir(parents=True, exist_ok=True)
        text = src.read_text(encoding="utf-8")
        dst.write_text(text.replace("#define SOC_I2C_NUM", "#define SOC_I2C_NUMBER"), "utf-8")
    with pytest.raises(ExtractError, match="SOC_I2C_NUM"):
        extract(broken, CONFIG)


def test_missing_header_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(ExtractError, match="not found"):
        extract(tmp_path, CONFIG)


def test_update_keeps_manual_block_and_comments(tmp_path: Path) -> None:
    out = tmp_path / "testchip.yaml"
    original = (
        "# Hand-written header comment\n"
        "schema: verino-chip/1\n"
        "chip: testchip\n"
        "manual:\n"
        "  # keep me\n"
        "  usb_pins:\n"
        "    pins: {GPIO7: USB_D-, GPIO8: USB_D+}\n"
        "    provenance: {kind: datasheet, source: test@1, ref: 'Table 1 (p. 1)'}\n"
    )
    out.write_text(original, encoding="utf-8")
    block = extract(FAKE_IDF, CONFIG)
    update_chip_file(out, "testchip", block)
    first = out.read_text(encoding="utf-8")
    assert "# Hand-written header comment" in first
    assert "  # keep me\n" in first
    doc = load_text(first)
    assert list(doc) == ["schema", "chip", "soc_caps", "manual"]
    assert doc["soc_caps"]["gpio"]["count"] == 10
    # Regenerating is a no-op.
    update_chip_file(out, "testchip", block)
    assert out.read_text(encoding="utf-8") == first


def test_update_creates_missing_file(tmp_path: Path) -> None:
    out = tmp_path / "new.yaml"
    update_chip_file(out, "testchip", extract(FAKE_IDF, CONFIG))
    doc = load_text(out.read_text(encoding="utf-8"))
    assert list(doc) == ["schema", "chip", "soc_caps"]


def test_update_refuses_other_chip(tmp_path: Path) -> None:
    out = tmp_path / "other.yaml"
    out.write_text("schema: verino-chip/1\nchip: otherchip\n", encoding="utf-8")
    with pytest.raises(ExtractError, match="otherchip"):
        update_chip_file(out, "testchip", extract(FAKE_IDF, CONFIG))


def test_output_is_deterministic() -> None:
    first = dump_text(extract(FAKE_IDF, CONFIG))
    assert dump_text(extract(FAKE_IDF, CONFIG)) == first


def test_main_cli(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "testchip.yaml"
    code = main(["--idf", str(FAKE_IDF), "--chip", "testchip", "--out", str(out)])
    assert code == 0
    assert "testchip" in capsys.readouterr().out
    assert load_text(out.read_text(encoding="utf-8"))["chip"] == "testchip"


def test_main_reports_errors(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["--idf", str(tmp_path), "--chip", "testchip", "--out", str(tmp_path / "x.yaml")])
    assert code == 1
    assert "not found" in capsys.readouterr().err
