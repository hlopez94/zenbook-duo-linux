# Linux for the ASUS Zenbook Duo

A script to manage features on the Zenbook Duo.

## Functionality Status

| Feature | Working | Not Working |
|---------|:-------:|:-----------:|
| Toggle bottom screen on when keyboard removed | ✅ | |
| Toggle bottom screen off when keyboard placed on | ✅ | |
| Toggle bluetooth on when keyboard removed | ✅ | |
| Toggle bluetooth off when keyboard placed on (if bluetooth was off when removed) | ✅ | |
| Screen brightness sync | ✅ | |
| Reset Airplane mode when keyboard removed/placed (handles issue where Ubuntu toggles it on/off) | ✅ | |
| Keyboard backlight set on boot and/or keyboard placed | ✅ | |
| Checks for correct state on boot/resume (from suspend and hibernate)| ✅ | |
| Auto rotation | ✅ | |
| FN key bridge for BT keyboard (ABS_MISC -> KEY_*) | ✅ | |
| Keyboard backlight when keyboard off | | ❌ |
| Keyboard function keys (some work in BT mode) | | ❌ |
| Pen and Touch Input on second screen (before input on second screen mapped to main screen only) | ✅ | |

## Tested on

The following models and operating systems have been validated by users

- **Models**
    - 2025 Zenbook Duo (UX8406CA)

- **Distros**
    - Ubunutu 25.10

While I typicaly recommend Debian installs, and many items worked out of the box with `debian-backports`, Ubuntu 25.10 has so far proven to be the best option for compatibility of newer hardware, such as the Bluetooth module. Once Backports incorporates kernel 6.14, I may personally redo testing in Debian Bookworm.

## Install

Run the setup script below, choose a default keyboard backlight level of 0 (off) to 3 (high), and a default resolution scale.

```bash
$ ./setup.sh 
What would you like to use for the default keyboard backlight brightness [0-3]? 1
What would you like to use for monitor scale (1 = 100%, 1.5 = 150%, 2=200%) [1-2]? 1
...
<watch it install>
```

This will set up the required systemd scripts to handle all the above functionality. A log file will be created in `/tmp/duo/` when the services are running.

### FN key bridge (Bluetooth keyboard)

On some Zenbook Duo units, several FN keys are exposed as `EV_ABS/ABS_MISC` values instead of normal `KEY_*` events. GNOME cannot map those directly.

`setup.sh` now installs `duo_fn_bridge.sh` (entrypoint) and `duo_fn_bridge.py` (backend), then enables `zenbook-duo-fn-bridge.service` to translate known `ABS_MISC` values into standard keycodes via `uinput`.

Mappings are read from:

```bash
/etc/default/zenbook-duo-fn-bridge.conf
```

The installer seeds that file once from `duo_fn_bridge.conf` in this repository, and preserves user edits on subsequent runs.

Mapping format:

```bash
# ABS_MISC_VALUE=KEY_NAME
16=KEY_BRIGHTNESSDOWN
32=KEY_BRIGHTNESSUP
199=KEY_KBDILLUMTOGGLE
```

Useful commands:

```bash
# Service logs
sudo journalctl -u zenbook-duo-fn-bridge.service -f

# Edit mappings
sudo nano /etc/default/zenbook-duo-fn-bridge.conf

# Apply mapping changes
sudo systemctl restart zenbook-duo-fn-bridge.service

# Probe mode (no key injection, only prints values)
sudo /usr/local/bin/duo_fn_bridge.sh --print-only

# Override one mapping at runtime (example)
sudo /usr/local/bin/duo_fn_bridge.sh --map 106=KEY_PROG1
```

## Additional info

### Steam audio

When running systems with PipeWire, games run through Proton in Steam will often lose audio. To fix this, after boot run:
```bash
pw-metadata -n settings 0 clock.force-quantum 512
```