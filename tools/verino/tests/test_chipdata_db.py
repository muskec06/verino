"""Tests for the typed chipdata loader."""

from conftest import REPO_ROOT

from verino.chipdata.db import ChipDB, default_root

DB = ChipDB(REPO_ROOT / "chipdata")


def test_default_root_finds_repository_chipdata() -> None:
    assert (default_root() / "sources.yaml").is_file()


def test_s3_pin_view_merges_generated_and_manual_facts() -> None:
    chip = DB.chip("esp32s3")
    assert chip is not None
    assert chip.idf_source == "esp-idf@v6.1.1"
    assert len(chip.pins) == chip.macros["SOC_GPIO_PIN_COUNT"] - 4  # GPIO22-25 do not exist
    assert chip.pin("GPIO22") is None
    gpio45 = chip.pin("GPIO45")
    assert gpio45 is not None and gpio45.strap is not None
    assert (gpio45.strap.boot_safe, gpio45.strap.severity) == ("low", "error")
    assert gpio45.boot is not None and gpio45.boot.state == "pulled_low"
    gpio11 = chip.pin("GPIO11")
    assert gpio11 is not None and gpio11.adc == ("adc2", 0)
    gpio19 = chip.pin("GPIO19")
    assert gpio19 is not None and gpio19.groups == {"usb_pins": "USB_D-"}
    assert chip.spi_hosts == ("SPI2", "SPI3")
    assert chip.adc2_wifi == "shared"


def test_module_view() -> None:
    module = DB.module("esp32-s3-wroom-1-n16r8")
    assert module is not None
    assert module.chip == "esp32s3"
    assert "GPIO33" not in module.exposed
    assert module.internal == {
        "GPIO35": "octal_psram",
        "GPIO36": "octal_psram",
        "GPIO37": "octal_psram",
    }
    assert DB.module("no-such-module") is None
    assert "esp32-s3-wroom-1-n8r8" in DB.modules()


def test_part_view() -> None:
    relay = DB.part("grove-relay")
    assert relay is not None
    assert relay.actuator and relay.safe_boot_level == "low"
    assert relay.reset_imposes == {"pin": "pulled_low"}
    sonar = DB.part("hc-sr04")
    assert sonar is not None
    assert sonar.supply == (5.0, 5.0) and sonar.supply_kind == "community"
    assert sonar.pins["echo"].level == "supply"
    assert DB.part("no-such-part") is None
    chip = DB.chip("esp32s3")
    assert chip is not None and chip.io_input_max_volts == 3.6


def test_partition_and_version_view() -> None:
    data = DB.partitions()
    assert (data.table_offset, data.table_size, data.app_align) == (0x8000, 0x1000, 0x10000)
    assert data.ota_app_subtypes == ("ota_0", "ota_1")
    assert [p.name for p in data.presets["two_ota_large"]][-2:] == ["ota_0", "ota_1"]
    assert DB.version() == "2026.11"
    module = DB.module("esp32-s3-wroom-1-n8r8")
    assert module is not None
    assert (module.flash_size, module.flash_max_freq_mhz) == ("8MB", 80)
    assert (module.psram_size, module.psram_interface) == ("8MB", "octal")
