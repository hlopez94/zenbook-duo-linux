#!/usr/bin/env python3
"""
Translate ASUS Zenbook Duo vendor ABS_MISC events into standard KEY_* events.

Some function keys on the detachable Bluetooth keyboard are exposed as
EV_ABS/ABS_MISC values, so desktop environments do not receive standard
media/function keycodes. This bridge listens for those values and injects
mapped KEY_* events via uinput.
"""

import argparse
import signal
import sys
import time
from typing import Dict, Optional

from evdev import InputDevice, UInput, ecodes, list_devices

# Default mapping inferred from field captures.
# You can override entries with --map VALUE=KEY_NAME (repeatable).
DEFAULT_MAP: Dict[int, str] = {
    16: "KEY_BRIGHTNESSDOWN",
    32: "KEY_BRIGHTNESSUP",
    78: "KEY_FN_ESC",
    106: "KEY_DISPLAYTOGGLE",
    124: "KEY_MICMUTE",
    126: "KEY_EMOJI_PICKER",
    156: "KEY_SWITCHVIDEOMODE",
    199: "KEY_KBDILLUMTOGGLE",
}


def parse_mapping(override_items) -> Dict[int, int]:
    mapping: Dict[int, str] = dict(DEFAULT_MAP)
    for item in override_items:
        if "=" not in item:
            raise ValueError(f"Invalid --map '{item}'. Expected VALUE=KEY_NAME")
        value_str, key_name = item.split("=", 1)
        value = int(value_str.strip())
        key_name = key_name.strip()
        mapping[value] = key_name

    resolved: Dict[int, int] = {}
    for value, key_name in mapping.items():
        if not hasattr(ecodes, key_name):
            raise ValueError(f"Unknown key name '{key_name}' for value {value}")
        resolved[value] = getattr(ecodes, key_name)
    return resolved


def find_asus_misc_device(explicit_path: Optional[str]) -> InputDevice:
    if explicit_path:
        dev = InputDevice(explicit_path)
        _validate_device(dev)
        return dev

    for path in list_devices():
        dev = InputDevice(path)
        if _is_candidate_device(dev):
            return dev

    raise RuntimeError("No ASUS Zenbook Duo ABS_MISC device found")


def _is_candidate_device(dev: InputDevice) -> bool:
    if dev.name != "ASUS Zenbook Duo Keyboard":
        return False
    # Bluetooth bus expected for detached keyboard interfaces.
    if int(dev.info.bustype) != int(ecodes.BUS_BLUETOOTH):
        return False
    caps = dev.capabilities()
    return _has_abs_misc(caps)


def _validate_device(dev: InputDevice) -> None:
    caps = dev.capabilities()
    if not _has_abs_misc(caps):
        raise RuntimeError(
            f"Device '{dev.path}' does not expose EV_ABS/ABS_MISC"
        )


def _has_abs_misc(caps: Dict[int, list]) -> bool:
    abs_entries = caps.get(ecodes.EV_ABS, [])
    for entry in abs_entries:
        # evdev can expose ABS entries either as int codes or as
        # (code, AbsInfo) tuples depending on version/options.
        if isinstance(entry, int):
            code = entry
        elif isinstance(entry, tuple) and entry:
            code = entry[0]
        else:
            continue
        if code == ecodes.ABS_MISC:
            return True
    return False


def emit_key(ui: UInput, key_code: int) -> None:
    ui.write(ecodes.EV_KEY, key_code, 1)
    ui.syn()
    ui.write(ecodes.EV_KEY, key_code, 0)
    ui.syn()


def main() -> int:
    parser = argparse.ArgumentParser(description="ASUS Zenbook Duo FN bridge")
    parser.add_argument(
        "--device",
        help="Input device path (default: auto-detect ASUS ABS_MISC interface)",
    )
    parser.add_argument(
        "--map",
        action="append",
        default=[],
        metavar="VALUE=KEY_NAME",
        help="Override one mapping entry, e.g. --map 106=KEY_PROG1",
    )
    parser.add_argument(
        "--print-only",
        action="store_true",
        help="Print ABS_MISC values without injecting keys",
    )
    args = parser.parse_args()

    mapping = parse_mapping(args.map)
    ui = None
    if not args.print_only:
        key_set = set(mapping.values())
        ui = UInput({ecodes.EV_KEY: key_set}, name="ASUS Zenbook Duo FN Bridge")

    stop = False

    def _stop_handler(signum, frame):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, _stop_handler)
    signal.signal(signal.SIGTERM, _stop_handler)

    while not stop:
        try:
            dev = find_asus_misc_device(args.device)
            print(f"Listening on {dev.path} ({dev.name})", flush=True)

            for ev in dev.read_loop():
                if stop:
                    break
                if ev.type != ecodes.EV_ABS or ev.code != ecodes.ABS_MISC:
                    continue

                value = int(ev.value)
                if value == 0:
                    continue

                key_code = mapping.get(value)
                if key_code is None:
                    print(f"ABS_MISC={value} (unmapped)", flush=True)
                    continue

                key_name = ecodes.KEY[key_code]
                print(f"ABS_MISC={value} -> {key_name}", flush=True)
                if ui is not None:
                    emit_key(ui, key_code)

        except OSError as exc:
            # Device can disappear/reappear while Bluetooth reconnects.
            print(f"Input device unavailable: {exc}. Retrying...", flush=True)
            time.sleep(1)
        except RuntimeError as exc:
            print(f"{exc}. Retrying...", flush=True)
            time.sleep(1)
        except KeyboardInterrupt:
            stop = True

    return 0


if __name__ == "__main__":
    sys.exit(main())
