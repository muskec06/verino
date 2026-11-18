"""Typed model tests: field conversion, shorthand pins and source locations."""

from conftest import EXAMPLES

from verino.model import HardwareSpec, PinAssignment, load_hardware, parse_hardware

GREENHOUSE = EXAMPLES / "s3-greenhouse.yaml"


def _greenhouse() -> HardwareSpec:
    result = load_hardware(GREENHOUSE)
    assert result.spec is not None
    return result.spec


def _line_of(fragment: str) -> int:
    lines = GREENHOUSE.read_text(encoding="utf-8").splitlines()
    return next(i for i, line in enumerate(lines, start=1) if fragment in line)


def test_top_level_fields() -> None:
    spec = _greenhouse()
    assert spec.schema == "verino-hw/1"
    assert spec.source == "native"
    assert spec.board == "esp32-s3-devkitc-1"
    assert spec.board_rev == "v1.1"
    assert spec.module == "esp32-s3-wroom-1-n16r8"
    assert spec.chip_rev is None
    assert spec.hw_rev == "A"
    assert spec.uses == ("wifi",)
    assert spec.uses_wifi


def test_source_defaults_to_native() -> None:
    spec = parse_hardware("schema: verino-hw/1\nmodule: m\n", "hw.yaml").spec
    assert spec is not None
    assert spec.source == "native"
    assert spec.uses is None
    assert spec.uses_wifi  # missing means Wi-Fi (change note 0003)
    assert spec.buses == {}
    assert spec.devices == {}


def test_memory() -> None:
    memory = _greenhouse().memory
    assert memory is not None
    assert memory.flash is not None
    assert (memory.flash.size, memory.flash.mode, memory.flash.origin) == ("16MB", "qio", "module")
    assert memory.psram is not None
    assert memory.psram.mode == "octal"
    assert memory.cpu_freq_mhz == 240
    assert memory.partitions is not None
    assert memory.partitions.preset is None
    assert [p.name for p in memory.partitions.custom] == [
        "nvs",
        "otadata",
        "app0",
        "app1",
        "storage",
    ]
    assert memory.partitions.custom[-1].size == "rest"


def test_bus_pins_keep_origin_lock_and_location() -> None:
    spec = _greenhouse()
    i2c = spec.buses["i2c0"]
    assert i2c.kind == "i2c"
    assert i2c.freq_hz == 400000
    assert i2c.pullups == "external_4k7"
    sda = i2c.pins["sda"]
    assert (sda.pin, sda.origin, sda.locked, sda.shorthand) == (
        "GPIO8",
        "board_default",
        False,
        False,
    )
    assert sda.loc.line == _line_of("sda: {pin: GPIO8")
    uart = spec.buses["uart1"]
    assert list(uart.pins) == ["tx", "rx"]
    assert uart.pins["tx"].locked is True
    assert uart.baud == 9600


def test_device_shorthand_pin_is_a_user_assignment() -> None:
    soil = _greenhouse().devices["soil_temp"]
    assert soil.kind == "onewire"
    pin = soil.pins["pin"]
    assert pin == PinAssignment(
        pin="GPIO4", origin="user", locked=False, shorthand=True, loc=pin.loc
    )
    assert pin.loc.line == _line_of("soil_temp:")


def test_device_full_assignment_and_roles() -> None:
    spec = _greenhouse()
    pump = spec.devices["pump"].pins["pin"]
    assert (pump.pin, pump.origin, pump.shorthand) == ("GPIO5", "user", False)
    tank = spec.devices["tank"]
    assert list(tank.pins) == ["trig", "echo"]
    assert spec.devices["status"].pins["pin"].pin == "LED_RGB"


def test_device_bus_and_hex_address() -> None:
    env = _greenhouse().devices["env"]
    assert env.part == "bme280"
    assert env.bus == "i2c0"
    assert env.addr == 0x76
    assert type(env.addr) is int
    assert env.pins == {}


def test_ack_and_tool_blocks() -> None:
    text = (
        "schema: verino-hw/1\n"
        "module: m\n"
        "ack:\n"
        "  - {rule: W-TEST-001, pin: GPIO1, reason: test}\n"
        "reserved:\n"
        "  - {pins: GPIO2-GPIO4, why: test}\n"
        "  - {pins: [GPIO7, GPIO9], why: test}\n"
        "validation:\n"
        "  tool: verino 0.1.0\n"
        "  chipdata: test\n"
        "  status: warnings\n"
        "  warnings: [W-TEST-001]\n"
        f"  checksum: sha256:{'0' * 64}\n"
    )
    result = parse_hardware(text, "hw.yaml")
    assert [str(d) for d in result.diagnostics] == []
    spec = result.spec
    assert spec is not None
    assert [(a.rule, a.pin, a.reason) for a in spec.ack] == [("W-TEST-001", "GPIO1", "test")]
    assert [r.pins for r in spec.reserved] == [("GPIO2", "GPIO3", "GPIO4"), ("GPIO7", "GPIO9")]
    assert spec.validation is not None
    assert spec.validation.status == "warnings"
    assert spec.validation.warnings == ("W-TEST-001",)


def test_ack_device_must_exist() -> None:
    text = (
        "schema: verino-hw/1\nmodule: m\n"
        "ack:\n  - {rule: W-TEST-001, device: ghost, reason: test}\n"
    )
    diags = parse_hardware(text, "hw.yaml").diagnostics
    assert len(diags) == 1
    assert "device 'ghost', which is not defined" in str(diags[0])


def test_reversed_reserved_range_is_rejected() -> None:
    text = "schema: verino-hw/1\nmodule: m\nreserved:\n  - {pins: GPIO9-GPIO2, why: test}\n"
    diags = parse_hardware(text, "hw.yaml").diagnostics
    assert len(diags) == 1
    assert diags[0].loc.line == 4


def test_uses_without_wifi() -> None:
    spec = parse_hardware("schema: verino-hw/1\nmodule: m\nuses: [ble, deep_sleep]\n").spec
    assert spec is not None
    assert spec.uses == ("ble", "deep_sleep")
    assert not spec.uses_wifi


def test_uses_rejects_unknown_values() -> None:
    diags = parse_hardware("schema: verino-hw/1\nmodule: m\nuses: [lora]\n").diagnostics
    assert [d.rule_id for d in diags] == ["E-SCHEMA-001"]
    assert "'lora' is not allowed" in str(diags[0])
