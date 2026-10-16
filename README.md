# Temp Top 🌡️

> A Linux terminal hardware temperature monitor and Braille grapher inspired by **Psensor** and **btop**.

```
╭─ Temp Top ─┤ LIVE ├──────────────────────┤ Rate: 2000ms [+/-] ├─┤ Time: 5m [</>] ├─╮
│100°C┤┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄│
│ 90°C┤┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄│
│ 80°C┤┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄│
│ 70°C┤┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄│
│ 60°C┤┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄⣀⣀⣀⣀⠤⠤⠤⠔⠒⠒⠒⠉⠉⠉┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄│
│ 50°C┤┄┄┄┄⢀⣀⣀⣀⠤⠤⠤⠔⠒⠒⠊⠉⠉⠉┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄│
│ 40°C┤⠒⠊⠉⠉⠁┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄│
│ 30°C┤┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄│
│ 20°C┤┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄│
├─ 09:35:16 ────────────────────────────────────────────────────────── 09:40:16 [5m] ─┤
│ [1] [✓] ● CPU (Tctl)       60.0°C Max: 64° [🔕]  [6] [✓] ● NVMe 0 (Sensor 1)  39.9°C Max: 41° [🔕]│
│ [2] [✓] ● GPU (edge)       51.0°C Max: 53° [🔕]  [7] [✓] ● NVMe 0 (Sensor 2)  32.9°C Max: 35° [🔕]│
│ [3] [✓] ● NVMe 1 (Overall) 30.9°C Max: 33° [🔕]  [8] [✓] ● WiFi (temp1)       30.0°C Max: 32° [🔕]│
│ [4] [✓] ● NVMe 1 (Sensor 1)30.9°C Max: 33° [🔕]  [9] [✓] ● Motherboard (temp1)64.0°C Max: 66° [🔕]│
│ [5] [✓] ● NVMe 0 (Overall) 39.9°C Max: 41° [🔕]                                                   │
╰─ [1-9] Toggle  [+/-] Rate  [</>] Time  [M] Sensors  [D] Reset  [Q] Quit ──────────────────╯
```

---

## Features

- **Braille Multi-Curve Plotting**: Renders smooth, continuous curves using Unicode Braille characters (`U+2800` through `U+28FF`) with sub-pixel Bresenham line interpolation.
- **lm-sensors & sysfs Integration**: Auto-detects all hardware devices containing temperature monitoring data (`sensors -j`), with direct `/sys/class/hwmon` acceleration for sub-millisecond, low-CPU sampling.
- **Dynamic Layout & Window Resizing**: Automatically handles `SIGWINCH` resize events to maximize screen space; the graph occupies almost the entire terminal window with btop-style rounded box borders.
- **Temperature Axis & Guides**:
  - Y-axis labeled from **20°C to 100°C** in 10°C intervals.
  - Consistent **dark grey guide lines** (`┄`) spaced at 10°C intervals across the graph.
- **Accurate Time Range Tracking**:
  - Bottom-left shows the time when the oldest visible data point was sampled.
  - Bottom-right shows the current time (latest visible data).
  - Far-right end displays the length of time currently being graphed (e.g. `[5m 00s]`).
- **Interactive Sensor Key & Controls**:
  - Toggle individual sensors on/off in real-time by pressing `1` through `9` or using the spacebar in the manager.
  - Shows current temperature and session maximum recorded temperature (`Max: XX°C`).
  - Distinct colors for every device line.
- **Configurable Sample Frequency & Graph Window**:
  - Sample frequency defaults to **2000 ms**, adjustable in **250 ms increments** (down to **100 ms**).
  - Total graphed plot time defaults to **5 minutes**, adjustable up and down (**30s to 60m**).
- **Alarm System**:
  - Beeps once per **10 seconds** via terminal bell (`\a`) and system audio when a device reaches its configured threshold.
  - Automatically ceases beeping when temperatures drop below the threshold.
  - Alarms are disabled by default and can be enabled and configured per device.
- **Plain-Language Config File**:
  - Stored at `~/.config/temp-top/config.toml`.
  - Clearly commented TOML format.
  - Preserves original hardware names (`default_name`) right beside custom names (`display_name`).
  - Allows returning to default names anytime.
  - Persists settings across runs.
  - Key combo `D` or `Ctrl+R` returns all settings to factory defaults.

---

## Installation

### Nix Flake

Run directly without installing:

```bash
nix run github:Scoobin/temptop
```

Install into your profile:

```bash
nix profile install github:Scoobin/temptop
```

Or add to a NixOS/home-manager configuration:

```nix
# flake.nix inputs
inputs.temptop.url = "github:Scoobin/temptop";

# Then in your packages list
inputs.temptop.packages.${system}.default
```

For local development with all dependencies available:

```bash
nix develop
```

---

### CLI Options

```
temp-top [options]

Options:
  -c, --config PATH     Path to custom configuration file
  -r, --rate MS         Initial sensor sample frequency in ms (default: 2000)
  -t, --time SECONDS    Initial total graphed plot time in seconds (default: 300)
  -l, --list-sensors    List detected temperature sensors and exit
  -v, --version         Show application version
  -h, --help            Show help message
```

---

## Keyboard Controls

| Key | Action |
|-----|--------|
| `1` – `9` | **Toggle Sensor**: Immediately show/hide sensors 1 through 9 |
| `+` / `-` | **Sample Frequency**: Increase / decrease sample interval by 250ms (down to 100ms) |
| `>` / `<` (or `w` / `W`) | **Plot Duration**: Increase / decrease total graphed plot time (30s, 1m, 2m, 3m, 5m, 10m, 15m, 30m, 60m) |
| `M` or `Enter` | **Device Manager**: Open interactive menu to rename sensors, toggle alarms, edit thresholds, and change colors |
| `P` | **Pause / Resume**: Freeze live graph plotting for inspection |
| `S` | **Save Settings**: Force save current settings to configuration file |
| `D` or `Ctrl+R` | **Reset Defaults**: Prompt to reset all settings, names, colors, and alarms to factory defaults |
| `H` or `?` | **Help**: View keyboard shortcut overlay |
| `Q` or `Esc` | **Quit**: Exit application cleanly (current settings are auto-saved) |

---

## Device Manager Modal (`M` or `Enter`)

When inside the Device Manager:

- `Up` / `Down` (`k` / `j`): Select sensor
- `Space`: Toggle visibility on graph
- `R`: Rename sensor (opens interactive text entry prompt)
- `Backspace`: Revert sensor name back to default hardware name
- `A`: Toggle threshold alarm on/off
- `+` / `-` (`Right` / `Left`): Adjust alarm threshold temperature (±1°C)
- `C`: Cycle line color through the 16-color palette
- `Esc` / `M`: Close manager and return to graph

---

## Configuration File (`~/.config/temp-top/config.toml`)

Temp Top creates a plain-language TOML configuration file on first launch:

```toml
# ==============================================================================
#                           TEMP TOP CONFIGURATION FILE
#                   Inspired by Psensor & btop hardware monitors
# ==============================================================================

[general]
# Sensor sampling update frequency in milliseconds (default: 2000 ms, min: 100 ms)
update_frequency_ms = 2000

# Total graphed plot time in seconds (default: 300 seconds = 5 minutes)
plot_time_seconds = 300

# Terminal sound / bell alarm enabled
sound_alarm_enabled = true

# Beep cooldown interval in seconds (default: 10 seconds between alarm beeps)
alarm_beep_interval_seconds = 10

# Graph temperature Y-axis bounds in degrees Celsius
temp_axis_min = 20.0
temp_axis_max = 100.0

# ==============================================================================
# HARDWARE TEMPERATURE DEVICES
# ------------------------------------------------------------------------------
# All devices containing temperature sensors are listed below.
#
# Fields for each device:
#   default_name    : Original hardware name detected by lm-sensors (reference)
#   display_name    : Custom user-chosen name (editable; return to default anytime)
#   enabled         : true to plot on graph, false to hide
#   color           : Color of the graph curve and sensor key badge
#   alarm_enabled   : true to sound alarm when threshold is reached (default: false)
#   alarm_threshold : Threshold temperature in °C for alarm (default: 85.0)
# ==============================================================================

[devices."k10temp-pci-00c3.Tctl"]
default_name = "k10temp-pci-00c3 Tctl (PCI adapter)"
display_name = "CPU (Tctl)"
enabled = true
color = "cyan"
alarm_enabled = false
alarm_threshold = 85.0

[devices."amdgpu-pci-0600.edge"]
default_name = "amdgpu-pci-0600 edge (PCI adapter)"
display_name = "GPU (edge)"
enabled = true
color = "purple"
alarm_enabled = false
alarm_threshold = 85.0
```
