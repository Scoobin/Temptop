"""
Temp Top - Terminal User Interface & Application Controller
Implements btop-style Unicode borders, Braille graphs, real-time sensor toggling,
device management modal, interactive rename prompt, defaults reset, and alarm beeper.
"""

import os
import sys
import tty
import time
import signal
import termios
import select
import shutil
import re
import unicodedata
from typing import Optional, List, Dict, Tuple, Any

from config import Config, COLOR_NAMES, COLOR_PALETTE, resolve_color, RESET_COLOR
from sensors import SensorManager, SensorDevice
from plotter import BraillePlotter

# ANSI regex for visible width calculation
ANSI_REGEX = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")

def char_width(c: str) -> int:
    """Return the terminal cell column width of a single character."""
    if unicodedata.combining(c) or c == '\ufe0f':
        return 0
    if c == '\u26a0':  # Warning symbol ⚠️
        return 2
    if unicodedata.east_asian_width(c) in ('W', 'F'):
        return 2
    return 1

def visible_len(s: str) -> int:
    """Calculate the visible terminal column width of an ANSI-colored string."""
    plain = ANSI_REGEX.sub("", s)
    return sum(char_width(c) for c in plain)

def pad_visible(s: str, target_width: int, align: str = "left") -> str:
    """Pad string to exact visible width taking ANSI codes and wide characters into account."""
    vlen = visible_len(s)
    pad = max(0, target_width - vlen)
    if align == "right":
        return (" " * pad) + s
    elif align == "center":
        left_pad = pad // 2
        right_pad = pad - left_pad
        return (" " * left_pad) + s + (" " * right_pad)
    return s + (" " * pad)

def truncate_visible(s: str, max_width: int) -> str:
    """Truncate a plain or ANSI string to max_width visible terminal columns."""
    if visible_len(s) <= max_width:
        return s
    plain = ANSI_REGEX.sub("", s)
    cur_w = 0
    truncated = []
    ellipsis_w = char_width("…")
    limit = max(0, max_width - ellipsis_w)
    for c in plain:
        w = char_width(c)
        if cur_w + w > limit:
            break
        truncated.append(c)
        cur_w += w
    return "".join(truncated) + "…"


# UI Colors
C_BORDER = "\033[38;2;85;105;135m"      # Steel blue btop border
C_TITLE = "\033[1;38;2;0;229;255m"      # Bright cyan title
C_SECTION = "\033[1;38;2;170;190;220m"  # Section headers
C_TEXT = "\033[38;2;220;225;235m"       # Normal crisp text
C_DIM = "\033[38;2;120;130;145m"        # Dim grey
C_HIGHLIGHT = "\033[1;38;2;255;203;107m"# Amber highlight
C_KEY = "\033[1;38;2;130;170;255m"      # Key shortcut highlight
C_ALARM_WARN = "\033[1;38;2;255;83;112m"# Bright red/coral alarm
C_MODAL_BG = "\033[48;2;25;30;40m"      # Modal background
C_MODAL_SEL = "\033[48;2;50;65;90m"     # Modal selected row
C_MODAL_BORDER = "\033[38;2;130;170;255m"


class TerminalManager:
    """Handles raw terminal mode, cursor visibility, screen buffer, and input."""
    def __init__(self):
        self.old_settings = None
        self.is_raw = False

    def enter(self):
        if sys.stdin.isatty():
            self.old_settings = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())
            self.is_raw = True
        # Alternate screen buffer, hide cursor, clear
        sys.stdout.write("\033[?1049h\033[?25l\033[2J")
        sys.stdout.flush()

    def exit(self):
        # Show cursor, restore main screen buffer
        sys.stdout.write("\033[?25h\033[?1049l\033[0m")
        sys.stdout.flush()
        if self.is_raw and self.old_settings:
            try:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)
            except Exception:
                pass
            self.is_raw = False

    def get_key(self, timeout: float = 0.05) -> Optional[str]:
        """Read a single keypress or escape sequence non-blockingly."""
        if not sys.stdin.isatty():
            time.sleep(timeout)
            return None

        r, _, _ = select.select([sys.stdin], [], [], timeout)
        if not r:
            return None

        try:
            ch = sys.stdin.read(1)
        except Exception:
            return None

        if ch == "\033":
            # Check for escape sequence
            r2, _, _ = select.select([sys.stdin], [], [], 0.05)
            if r2:
                seq1 = sys.stdin.read(1)
                if seq1 == "[":
                    r3, _, _ = select.select([sys.stdin], [], [], 0.05)
                    if r3:
                        seq2 = sys.stdin.read(1)
                        if seq2 == "A": return "UP"
                        if seq2 == "B": return "DOWN"
                        if seq2 == "C": return "RIGHT"
                        if seq2 == "D": return "LEFT"
                        if seq2 == "H": return "HOME"
                        if seq2 == "F": return "END"
                        if seq2 in "12345678":
                            seq3 = sys.stdin.read(1)
                            return f"FN_{seq2}{seq3}"
                return "ESC"
            return "ESC"
        return ch


class TempTopApp:
    def __init__(self, config_path: Optional[str] = None):
        self.config = Config(config_path)
        self.sensor_mgr = SensorManager(self.config)
        self.plotter = BraillePlotter()
        self.term = TerminalManager()

        # Window state
        self.cols, self.lines = shutil.get_terminal_size((80, 24))
        self.running = False
        self.needs_full_redraw = True

        # UI Modes: "NORMAL", "DEVICE_MANAGER", "RENAME_PROMPT", "CONFIRM_RESET", "HELP"
        self.ui_mode = "NORMAL"

        # Device manager state
        self.selected_dev_index = 0
        self.rename_buffer = ""

        # Available time durations for quick switching: [30s, 1m, 2m, 3m, 5m, 10m, 15m, 30m, 60m]
        self.plot_durations = [30, 60, 120, 180, 300, 600, 900, 1800, 3600]

        # Setup SIGWINCH handler
        signal.signal(signal.SIGWINCH, self._handle_resize)

    def _handle_resize(self, signum=None, frame=None):
        """Handle terminal window resize."""
        self.cols, self.lines = shutil.get_terminal_size((80, 24))
        self.needs_full_redraw = True

    def run(self):
        """Main application lifecycle loop."""
        self.term.enter()
        self.running = True
        self.sensor_mgr.start_background_polling()

        last_render_time = 0.0

        try:
            while self.running:
                # 1. Process keyboard input non-blockingly
                user_interacted = self._process_input()

                # 2. Render frame: refresh rate is no higher than the set graph update rate
                now = time.time()
                update_interval_sec = self.config.get_update_frequency_ms() / 1000.0
                time_to_refresh = (now - last_render_time) >= update_interval_sec

                if user_interacted or self.needs_full_redraw or time_to_refresh:
                    self._render()
                    self.needs_full_redraw = False
                    last_render_time = now

                # Small sleep to prevent busy looping while polling keys
                time.sleep(0.01)
        except KeyboardInterrupt:
            pass
        finally:
            self.sensor_mgr.stop_background_polling()
            self.config.save()
            self.term.exit()

    def _process_input(self) -> bool:
        """Process non-blocking key presses. Returns True if a key was handled."""
        key = self.term.get_key(timeout=0.03)
        if not key:
            return False

        if self.ui_mode == "NORMAL":
            self._handle_normal_key(key)
        elif self.ui_mode == "DEVICE_MANAGER":
            self._handle_device_manager_key(key)
        elif self.ui_mode == "RENAME_PROMPT":
            self._handle_rename_key(key)
        elif self.ui_mode == "CONFIRM_RESET":
            self._handle_confirm_reset_key(key)
        elif self.ui_mode == "HELP":
            self._handle_help_key(key)
        return True

    def _handle_normal_key(self, key: str):
        dev_list = list(self.sensor_mgr.devices.values())

        if key in ("q", "Q"):
            self.running = False

        # Quick sensor toggles via keys 1-9
        elif key in "123456789":
            idx = int(key) - 1
            if 0 <= idx < len(dev_list):
                dev = dev_list[idx]
                self.sensor_mgr.toggle_sensor(dev.device_id)

        # Sampling frequency adjustment: + / - or ] / [
        elif key in ("+", "="):
            # Increase interval by 250ms
            curr = self.config.get_update_frequency_ms()
            self.config.set_update_frequency_ms(curr + 250)
            self.config.save()
        elif key in ("-", "_"):
            # Decrease interval by 250ms down to 100ms
            curr = self.config.get_update_frequency_ms()
            new_val = max(100, curr - 250)
            self.config.set_update_frequency_ms(new_val)
            self.config.save()

        # Plot time adjustment: > / < or } / { or w / W
        elif key in (">", ".", "w"):
            # Increase window duration
            curr = self.config.get_plot_time_seconds()
            for d in self.plot_durations:
                if d > curr:
                    self.config.set_plot_time_seconds(d)
                    self.config.save()
                    break
        elif key in ("<", ",", "W"):
            # Decrease window duration
            curr = self.config.get_plot_time_seconds()
            for d in reversed(self.plot_durations):
                if d < curr:
                    self.config.set_plot_time_seconds(d)
                    self.config.save()
                    break

        # Pause / Resume
        elif key in ("p", "P"):
            self.sensor_mgr.paused = not self.sensor_mgr.paused

        # Open Device Manager modal
        elif key in ("m", "M", "\n", "\r"):
            self.ui_mode = "DEVICE_MANAGER"

        # Help modal
        elif key in ("h", "H", "?"):
            self.ui_mode = "HELP"

        # Save settings now
        elif key in ("s", "S"):
            self.config.save()

        # Reset defaults: Ctrl+R (\x12) or 'D' (Shift+d)
        elif key in ("\x12", "D"):
            self.ui_mode = "CONFIRM_RESET"

    def _handle_device_manager_key(self, key: str):
        dev_list = list(self.sensor_mgr.devices.values())
        if not dev_list:
            if key in ("ESC", "q", "m", "\n", "\r"):
                self.ui_mode = "NORMAL"
            return

        self.selected_dev_index = max(0, min(len(dev_list) - 1, self.selected_dev_index))
        curr_dev = dev_list[self.selected_dev_index]

        if key in ("ESC", "q", "m"):
            self.ui_mode = "NORMAL"
        elif key in ("UP", "k"):
            self.selected_dev_index = (self.selected_dev_index - 1) % len(dev_list)
        elif key in ("DOWN", "j"):
            self.selected_dev_index = (self.selected_dev_index + 1) % len(dev_list)
        elif key == " ":
            # Toggle visibility
            self.sensor_mgr.toggle_sensor(curr_dev.device_id)
        elif key in ("r", "e"):
            # Rename prompt
            self.rename_buffer = curr_dev.display_name
            self.ui_mode = "RENAME_PROMPT"
        elif key in ("R", "\x7f", "\x08"):
            # Reset device name to default
            self.sensor_mgr.reset_sensor_name(curr_dev.device_id)
        elif key in ("a", "A"):
            # Toggle alarm on/off
            self.sensor_mgr.toggle_alarm(curr_dev.device_id)
        elif key in ("+", "=", "RIGHT", "]"):
            # Increase alarm threshold by 1°C
            self.sensor_mgr.set_alarm_threshold(curr_dev.device_id, curr_dev.alarm_threshold + 1.0)
        elif key in ("-", "_", "LEFT", "["):
            # Decrease alarm threshold by 1°C
            self.sensor_mgr.set_alarm_threshold(curr_dev.device_id, curr_dev.alarm_threshold - 1.0)
        elif key in ("c", "C"):
            # Cycle color
            try:
                curr_idx = COLOR_NAMES.index(curr_dev.color)
            except ValueError:
                curr_idx = 0
            new_color = COLOR_NAMES[(curr_idx + 1) % len(COLOR_NAMES)]
            self.sensor_mgr.set_sensor_color(curr_dev.device_id, new_color)
        elif key in ("\x12", "D"):
            # Reset all defaults
            self.ui_mode = "CONFIRM_RESET"

    def _handle_rename_key(self, key: str):
        dev_list = list(self.sensor_mgr.devices.values())
        if not dev_list:
            self.ui_mode = "NORMAL"
            return
        curr_dev = dev_list[self.selected_dev_index]

        if key in ("\n", "\r"):
            # Accept new name
            if self.rename_buffer.strip():
                self.sensor_mgr.rename_sensor(curr_dev.device_id, self.rename_buffer.strip())
            self.ui_mode = "DEVICE_MANAGER"
        elif key == "ESC":
            # Cancel
            self.ui_mode = "DEVICE_MANAGER"
        elif key in ("\x7f", "\x08"):
            # Backspace
            self.rename_buffer = self.rename_buffer[:-1]
        elif len(key) == 1 and 32 <= ord(key) <= 126:
            # Printable character
            if len(self.rename_buffer) < 40:
                self.rename_buffer += key

    def _handle_confirm_reset_key(self, key: str):
        if key in ("y", "Y"):
            self.sensor_mgr.reset_all_defaults()
            self.ui_mode = "NORMAL"
        elif key in ("n", "N", "ESC", "q"):
            self.ui_mode = "NORMAL"

    def _handle_help_key(self, key: str):
        if key in ("ESC", "q", "h", "?", "\n", "\r", " "):
            self.ui_mode = "NORMAL"

    def _render(self):
        """Render the complete screen buffer and flush."""
        cols = self.cols
        lines = self.lines

        if cols < 40 or lines < 12:
            msg = "Terminal window too small! Please enlarge."
            sys.stdout.write(f"\033[H\033[2J{msg}")
            sys.stdout.flush()
            return

        frame: List[str] = []

        # 1. Header Line
        frame.append(self._render_header(cols))

        # Determine layout heights:
        # Title bar: 1 line
        # Sensor Key Guide at bottom: lines depending on sensor count and terminal height
        dev_list = list(self.sensor_mgr.devices.values())
        # Deduplicate sensors by device_id
        seen_ids = set()
        unique_devs: List[SensorDevice] = []
        for dev in dev_list:
            if dev.device_id not in seen_ids:
                seen_ids.add(dev.device_id)
                unique_devs.append(dev)

        key_lines_needed = self._calculate_sensor_key_height(len(unique_devs), cols)
        overhead = 1 + 1 + key_lines_needed + 1
        graph_box_height = max(4, lines - overhead)
        plot_height = graph_box_height
        # Subtract 2 for borders (│...│), 6 for left axis, 6 for right axis = 14
        plot_width = max(10, cols - 14)

        # 2. Render Graph Plot Rows
        duration = self.config.get_plot_time_seconds()
        now = time.time()
        plot_rows, oldest_str, latest_str = self.plotter.render_graph(
            plot_width=plot_width,
            plot_height=plot_height,
            duration_seconds=duration,
            devices=unique_devs,
            current_time=now,
        )

        for row in plot_rows:
            frame.append(f"{C_BORDER}│{RESET_COLOR}{row}{C_BORDER}│{RESET_COLOR}")

        # 3. Divider Row with Bottom Time Labels
        frame.append(self._render_time_divider(cols, oldest_str, latest_str, duration))

        # 4. Sensor Key Guide Area
        sensor_key_rows = self._render_sensor_key(cols, key_lines_needed, unique_devs)
        for skr in sensor_key_rows:
            frame.append(f"{C_BORDER}│{RESET_COLOR}{skr}{C_BORDER}│{RESET_COLOR}")

        # 5. Footer Line
        frame.append(self._render_footer(cols))

        # Overlay Modals if active
        if self.ui_mode == "DEVICE_MANAGER":
            self._apply_modal(frame, self._create_device_manager_modal(cols, lines))
        elif self.ui_mode == "RENAME_PROMPT":
            self._apply_modal(frame, self._create_rename_modal(cols, lines))
        elif self.ui_mode == "CONFIRM_RESET":
            self._apply_modal(frame, self._create_confirm_reset_modal(cols, lines))
        elif self.ui_mode == "HELP":
            self._apply_modal(frame, self._create_help_modal(cols, lines))

        # Write whole screen buffer in one shot
        output = "\033[H" + "\n".join(frame[:lines])
        sys.stdout.write(output)
        sys.stdout.flush()

    def _render_header(self, cols: int) -> str:
        """Render top btop-style title bar with exact visible width == cols."""
        rate_ms = self.config.get_update_frequency_ms()
        window_sec = self.config.get_plot_time_seconds()
        window_fmt = self._format_duration(window_sec)

        # Check for alarm alert
        if self.sensor_mgr.is_alarm_active and self.sensor_mgr.alarming_devices:
            first_alarm = self.sensor_mgr.alarming_devices[0]
            alarm_str = f" ⚠️  ALARM: {first_alarm.display_name} @ {first_alarm.current_temp:.1f}°C (>{first_alarm.alarm_threshold:.1f}°C) "
            title_section = f"{C_ALARM_WARN}╭─ [TEMP TOP] ─{alarm_str}"
        else:
            status_text = "PAUSED" if self.sensor_mgr.paused else "LIVE"
            status_color = C_HIGHLIGHT if self.sensor_mgr.paused else C_TITLE
            title_section = f"{C_BORDER}╭─ {C_TITLE}Temp Top{C_BORDER} ─┤ {status_color}{status_text}{C_BORDER} ├"

        if cols >= 80:
            ctrl_section = f"┤ Rate: {C_TEXT}{rate_ms}ms{C_DIM} [+/-]{C_BORDER} ├─┤ Time: {C_TEXT}{window_fmt}{C_DIM} [</>]{C_BORDER} ├─╮{RESET_COLOR}"
        else:
            ctrl_section = f"┤ {C_TEXT}{rate_ms}ms{C_BORDER} ├─┤ {C_TEXT}{window_fmt}{C_BORDER} ├─╮{RESET_COLOR}"
        
        vis_title = visible_len(title_section)
        vis_ctrl = visible_len(ctrl_section)

        if vis_title + vis_ctrl < cols:
            middle_dashes = "─" * (cols - vis_title - vis_ctrl)
            return f"{title_section}{middle_dashes}{ctrl_section}"
        else:
            # Fallback if narrow
            left_part = f"{title_section}"
            dashes = max(1, cols - visible_len(left_part) - 1)
            return f"{left_part}{'─' * dashes}╮{RESET_COLOR}"

    def _render_time_divider(self, cols: int, oldest_str: str, latest_str: str, duration_sec: int) -> str:
        """
        Render bottom divider row of the graph containing:
        - Bottom-left: time when oldest visible data was updated
        - Bottom-right: time of latest visible data (current time)
        - Far-right end: length of time currently being measured
        Exact visible width == cols.
        """
        dur_str = f"[{self._format_duration(duration_sec)}]"
        left_str = f" {oldest_str} "
        right_str = f" {latest_str} {dur_str} "

        inner_w = cols - 2
        dashes_needed = inner_w - (visible_len(left_str) + visible_len(right_str))
        if dashes_needed < 0:
            left_str = f" {oldest_str} "
            right_str = f" {latest_str} "
            dashes_needed = max(0, inner_w - (visible_len(left_str) + visible_len(right_str)))

        middle_dashes = "─" * dashes_needed
        return f"{C_BORDER}├{RESET_COLOR}{C_TEXT}{left_str}{C_BORDER}{middle_dashes}{C_TEXT}{right_str}{C_BORDER}┤{RESET_COLOR}"

    def _calculate_sensor_key_height(self, dev_count: int, cols: int) -> int:
        """Calculate how many lines the sensor key table needs."""
        if dev_count == 0:
            return 1
        cols_per_row = self._get_key_columns_count(cols)
        data_rows = (dev_count + cols_per_row - 1) // cols_per_row
        return max(1, min(6, data_rows))

    def _get_key_columns_count(self, cols: int) -> int:
        """Determine number of sensor columns based on screen width."""
        if cols >= 150:
            return 4
        elif cols >= 110:
            return 3
        elif cols >= 70:
            return 2
        return 1

    def _render_sensor_key(self, cols: int, max_rows: int, dev_list: List[SensorDevice]) -> List[str]:
        """Render multi-column sensor key with current and max temp, colors, and alarms."""
        inner_w = cols - 2
        num_columns = self._get_key_columns_count(cols)
        col_width = inner_w // num_columns

        # Remove duplicates while preserving order
        seen_ids = set()
        unique_devs: List[SensorDevice] = []
        for dev in dev_list:
            if dev.device_id not in seen_ids:
                seen_ids.add(dev.device_id)
                unique_devs.append(dev)

        # Build badges for each sensor
        badges: List[str] = []
        for i, dev in enumerate(unique_devs):
            hotkey = f"{i+1}" if i < 9 else " "
            color_code = dev.get_color_code()

            # Status bullet & checkbox
            if dev.enabled:
                bullet = f"{color_code}●{RESET_COLOR}"
                chk = f"{C_KEY}✓{RESET_COLOR}"
            else:
                bullet = f"{C_DIM}○{RESET_COLOR}"
                chk = f"{C_DIM} {RESET_COLOR}"

            # Temperature values
            temp_str = f"{dev.current_temp:4.1f}°" if dev.current_temp is not None else " N/A "
            max_str = f"M:{dev.session_max_temp:2.0f}°" if dev.session_max_temp is not None else "M:--"

            # Alarm indicator: only show if enabled, otherwise show none to reduce clutter
            if dev.alarm_enabled:
                if dev.is_alarming():
                    alarm_badge = f" {C_ALARM_WARN}🚨{dev.alarm_threshold:.0f}°{RESET_COLOR}"
                else:
                    alarm_badge = f" {C_HIGHLIGHT}🔔{dev.alarm_threshold:.0f}°{RESET_COLOR}"
            else:
                alarm_badge = ""

            hk_badge = f"{C_KEY}[{hotkey}]{RESET_COLOR}" if hotkey != " " else "   "

            fixed_overhead = 22 + visible_len(alarm_badge)
            name_budget = max(4, col_width - fixed_overhead)
            disp_name = truncate_visible(dev.display_name, name_budget)
            disp_padded = pad_visible(disp_name, name_budget)

            badge = f" {hk_badge} {chk} {bullet} {C_TEXT}{disp_padded}{RESET_COLOR} {C_TITLE}{temp_str:>6}{RESET_COLOR} {C_DIM}{max_str:>5}{RESET_COLOR}{alarm_badge}"
            badge = pad_visible(badge, col_width)
            badges.append(badge)

        # Distribute into rows in natural row-major order:
        # Row 0: [1], [2], [3]
        # Row 1: [4], [5], [6]
        # Row 2: [7], [8], [9]
        rows: List[str] = []
        for r in range(max_rows):
            row_items: List[str] = []
            for c in range(num_columns):
                idx = r * num_columns + c
                if idx < len(badges):
                    row_items.append(badges[idx])
                else:
                    row_items.append(" " * col_width)
            row_str = "".join(row_items)
            rows.append(pad_visible(row_str, inner_w))

        return rows

    def _render_footer(self, cols: int) -> str:
        """Render bottom status line with keyboard shortcuts tailored to width. Exact visible width == cols."""
        if cols >= 115:
            shortcuts = (
                f" {C_KEY}[1-9]{C_TEXT} Toggle  "
                f"{C_KEY}[+/-]{C_TEXT} Rate  "
                f"{C_KEY}[</>]{C_TEXT} Time  "
                f"{C_KEY}[M/Enter]{C_TEXT} Sensors  "
                f"{C_KEY}[P]{C_TEXT} Pause  "
                f"{C_KEY}[D/Ctrl+R]{C_TEXT} Defaults  "
                f"{C_KEY}[H]{C_TEXT} Help  "
                f"{C_KEY}[Q]{C_TEXT} Quit {RESET_COLOR}"
            )
        elif cols >= 76:
            shortcuts = (
                f" {C_KEY}[1-9]{C_TEXT} Toggle  "
                f"{C_KEY}[+/-]{C_TEXT} Rate  "
                f"{C_KEY}[</>]{C_TEXT} Time  "
                f"{C_KEY}[M]{C_TEXT} Sensors  "
                f"{C_KEY}[D]{C_TEXT} Reset  "
                f"{C_KEY}[Q]{C_TEXT} Quit {RESET_COLOR}"
            )
        else:
            shortcuts = (
                f" {C_KEY}[1-9]{C_TEXT} Toggle  "
                f"{C_KEY}[M]{C_TEXT} Manage  "
                f"{C_KEY}[D]{C_TEXT} Reset  "
                f"{C_KEY}[Q]{C_TEXT} Quit {RESET_COLOR}"
            )

        vis_sc = visible_len(shortcuts)
        if vis_sc + 2 <= cols:
            left_dash = "─"
            right_dash = "─" * max(0, (cols - 2) - 1 - vis_sc)
            return f"{C_BORDER}╰{left_dash}{RESET_COLOR}{shortcuts}{C_BORDER}{right_dash}╯{RESET_COLOR}"
        else:
            truncated = truncate_visible(shortcuts, max(0, cols - 4))
            vis_tr = visible_len(truncated)
            right_dash = "─" * max(0, cols - 3 - vis_tr)
            return f"{C_BORDER}╰─{RESET_COLOR}{truncated}{C_BORDER}{right_dash}╯{RESET_COLOR}"

    def _format_duration(self, seconds: int) -> str:
        """Format duration cleanly (e.g. 5m 00s or 30s)."""
        if seconds < 60:
            return f"{seconds}s"
        m = seconds // 60
        s = seconds % 60
        if s == 0:
            return f"{m}m"
        return f"{m}m {s:02d}s"

    # =========================================================================
    # MODAL DIALOGS
    # =========================================================================
    def _create_device_manager_modal(self, cols: int, lines: int) -> List[str]:
        """Create interactive Device Manager modal dialog."""
        dev_list = list(self.sensor_mgr.devices.values())
        modal_w = min(74, cols - 6)
        modal_h = min(len(dev_list) + 8, lines - 4)

        modal_lines: List[str] = []
        # Header
        modal_lines.append(f"{C_MODAL_BORDER}╭─ {C_TITLE}Device Manager & Sensor Settings{C_MODAL_BORDER} ─" + "─" * (modal_w - 36) + f"╮{RESET_COLOR}")
        modal_lines.append(f"{C_MODAL_BORDER}│{RESET_COLOR}  {C_DIM}Navigate: [↑/↓]  Toggle: [Space]  Rename: [R]  Reset: [Bksp]  Alarm: [A]{RESET_COLOR}" + " " * max(0, modal_w - 74) + f"{C_MODAL_BORDER}│{RESET_COLOR}")
        modal_lines.append(f"{C_MODAL_BORDER}│{RESET_COLOR}  {C_DIM}Threshold: [+/-]  Cycle Color: [C]  Defaults: [Ctrl+R]  Exit: [Esc/M]{RESET_COLOR}" + " " * max(0, modal_w - 73) + f"{C_MODAL_BORDER}│{RESET_COLOR}")
        modal_lines.append(f"{C_MODAL_BORDER}├" + "─" * (modal_w - 2) + f"┤{RESET_COLOR}")

        # List rows
        list_height = modal_h - 6
        start_idx = max(0, min(self.selected_dev_index - list_height // 2, len(dev_list) - list_height))
        visible_devs = dev_list[start_idx : start_idx + list_height]

        for i, dev in enumerate(visible_devs):
            real_idx = start_idx + i
            is_sel = (real_idx == self.selected_dev_index)
            prefix = f"{C_HIGHLIGHT}►{RESET_COLOR} " if is_sel else "  "

            chk = "[✓]" if dev.enabled else "[ ]"
            color_code = dev.get_color_code()
            bullet = f"{color_code}■{RESET_COLOR}"

            # Name and default name
            is_renamed = (dev.display_name != dev.default_name)
            name_str = dev.display_name
            if is_renamed:
                name_str += f" {C_DIM}(def: {truncate_visible(dev.default_name, 14)}){RESET_COLOR}"

            alarm_info = f"Alarm:{'ON' if dev.alarm_enabled else 'OFF'} ({dev.alarm_threshold:.0f}°C)"
            row_content = f"{prefix}{chk} {bullet} {name_str} | {dev.color} | {alarm_info}"

            bg = C_MODAL_SEL if is_sel else ""
            line_str = f"{C_MODAL_BORDER}│{RESET_COLOR}{bg}{pad_visible(row_content, modal_w - 2)}{RESET_COLOR}{C_MODAL_BORDER}│{RESET_COLOR}"
            modal_lines.append(line_str)

        # Fill remaining rows if any
        while len(modal_lines) < modal_h - 1:
            modal_lines.append(f"{C_MODAL_BORDER}│{RESET_COLOR}" + " " * (modal_w - 2) + f"{C_MODAL_BORDER}│{RESET_COLOR}")

        modal_lines.append(f"{C_MODAL_BORDER}╰" + "─" * (modal_w - 2) + f"╯{RESET_COLOR}")
        return modal_lines

    def _create_rename_modal(self, cols: int, lines: int) -> List[str]:
        """Create prompt modal to rename a sensor."""
        modal_w = min(60, cols - 6)
        modal_lines: List[str] = [
            f"{C_MODAL_BORDER}╭─ {C_TITLE}Rename Sensor{C_MODAL_BORDER} " + "─" * (modal_w - 17) + f"╮{RESET_COLOR}",
            f"{C_MODAL_BORDER}│{RESET_COLOR}" + " " * (modal_w - 2) + f"{C_MODAL_BORDER}│{RESET_COLOR}",
            f"{C_MODAL_BORDER}│{RESET_COLOR}  Enter custom display name for device: " + " " * max(0, modal_w - 43) + f"{C_MODAL_BORDER}│{RESET_COLOR}",
            f"{C_MODAL_BORDER}│{RESET_COLOR}  {C_HIGHLIGHT}> {self.rename_buffer}█{RESET_COLOR}" + " " * max(0, modal_w - 6 - len(self.rename_buffer)) + f"{C_MODAL_BORDER}│{RESET_COLOR}",
            f"{C_MODAL_BORDER}│{RESET_COLOR}" + " " * (modal_w - 2) + f"{C_MODAL_BORDER}│{RESET_COLOR}",
            f"{C_MODAL_BORDER}│{RESET_COLOR}  {C_DIM}[Enter] Confirm   [Esc] Cancel{RESET_COLOR}" + " " * max(0, modal_w - 33) + f"{C_MODAL_BORDER}│{RESET_COLOR}",
            f"{C_MODAL_BORDER}╰" + "─" * (modal_w - 2) + f"╯{RESET_COLOR}",
        ]
        return modal_lines

    def _create_confirm_reset_modal(self, cols: int, lines: int) -> List[str]:
        """Create confirmation modal to reset all settings to defaults."""
        modal_w = min(58, cols - 6)
        modal_lines: List[str] = [
            f"{C_ALARM_WARN}╭─ Reset All Settings to Defaults ─" + "─" * (modal_w - 36) + f"╮{RESET_COLOR}",
            f"{C_ALARM_WARN}│{RESET_COLOR}" + " " * (modal_w - 2) + f"{C_ALARM_WARN}│{RESET_COLOR}",
            f"{C_ALARM_WARN}│{RESET_COLOR}  Are you sure you want to reset all settings?    " + " " * max(0, modal_w - 52) + f"{C_ALARM_WARN}│{RESET_COLOR}",
            f"{C_ALARM_WARN}│{RESET_COLOR}  This restores default names, colors, alarms,    " + " " * max(0, modal_w - 52) + f"{C_ALARM_WARN}│{RESET_COLOR}",
            f"{C_ALARM_WARN}│{RESET_COLOR}  and sampling rate (2000ms).                     " + " " * max(0, modal_w - 52) + f"{C_ALARM_WARN}│{RESET_COLOR}",
            f"{C_ALARM_WARN}│{RESET_COLOR}" + " " * (modal_w - 2) + f"{C_ALARM_WARN}│{RESET_COLOR}",
            f"{C_ALARM_WARN}│{RESET_COLOR}  {C_HIGHLIGHT}Press [Y] to confirm  |  [N] to cancel{RESET_COLOR}          " + " " * max(0, modal_w - 50) + f"{C_ALARM_WARN}│{RESET_COLOR}",
            f"{C_ALARM_WARN}│{RESET_COLOR}" + " " * (modal_w - 2) + f"{C_ALARM_WARN}│{RESET_COLOR}",
            f"{C_ALARM_WARN}╰" + "─" * (modal_w - 2) + f"╯{RESET_COLOR}",
        ]
        return modal_lines

    def _create_help_modal(self, cols: int, lines: int) -> List[str]:
        """Create Help modal displaying keys and features."""
        modal_w = min(68, cols - 6)
        modal_lines: List[str] = [
            f"{C_MODAL_BORDER}╭─ {C_TITLE}Temp Top Help & Keyboard Shortcuts{C_MODAL_BORDER} " + "─" * (modal_w - 38) + f"╮{RESET_COLOR}",
            f"{C_MODAL_BORDER}│{RESET_COLOR}" + " " * (modal_w - 2) + f"{C_MODAL_BORDER}│{RESET_COLOR}",
            f"{C_MODAL_BORDER}│{RESET_COLOR}  {C_KEY}1 - 9{RESET_COLOR}       : Toggle sensor visibility on graph in real time" + " " * max(0, modal_w - 65) + f"{C_MODAL_BORDER}│{RESET_COLOR}",
            f"{C_MODAL_BORDER}│{RESET_COLOR}  {C_KEY}+ / -{RESET_COLOR}       : Increase/decrease sample rate by 250ms (down to 100ms)" + " " * max(0, modal_w - 73) + f"{C_MODAL_BORDER}│{RESET_COLOR}",
            f"{C_MODAL_BORDER}│{RESET_COLOR}  {C_KEY}> / <{RESET_COLOR}       : Increase/decrease plot time window (30s..60m)" + " " * max(0, modal_w - 63) + f"{C_MODAL_BORDER}│{RESET_COLOR}",
            f"{C_MODAL_BORDER}│{RESET_COLOR}  {C_KEY}M / Enter{RESET_COLOR}   : Open Device Manager (rename, alarms, colors)" + " " * max(0, modal_w - 63) + f"{C_MODAL_BORDER}│{RESET_COLOR}",
            f"{C_MODAL_BORDER}│{RESET_COLOR}  {C_KEY}P{RESET_COLOR}           : Pause or resume live graph updates" + " " * max(0, modal_w - 53) + f"{C_MODAL_BORDER}│{RESET_COLOR}",
            f"{C_MODAL_BORDER}│{RESET_COLOR}  {C_KEY}S{RESET_COLOR}           : Save configuration file immediately" + " " * max(0, modal_w - 54) + f"{C_MODAL_BORDER}│{RESET_COLOR}",
            f"{C_MODAL_BORDER}│{RESET_COLOR}  {C_KEY}D / Ctrl+R{RESET_COLOR}  : Reset ALL settings and names to factory defaults" + " " * max(0, modal_w - 67) + f"{C_MODAL_BORDER}│{RESET_COLOR}",
            f"{C_MODAL_BORDER}│{RESET_COLOR}  {C_KEY}Q / Esc{RESET_COLOR}     : Quit application" + " " * max(0, modal_w - 35) + f"{C_MODAL_BORDER}│{RESET_COLOR}",
            f"{C_MODAL_BORDER}│{RESET_COLOR}" + " " * (modal_w - 2) + f"{C_MODAL_BORDER}│{RESET_COLOR}",
            f"{C_MODAL_BORDER}│{RESET_COLOR}  {C_DIM}Config file: ~/.config/temp-top/config.toml{RESET_COLOR}" + " " * max(0, modal_w - 48) + f"{C_MODAL_BORDER}│{RESET_COLOR}",
            f"{C_MODAL_BORDER}│{RESET_COLOR}  {C_DIM}Press any key to close this help window{RESET_COLOR}" + " " * max(0, modal_w - 44) + f"{C_MODAL_BORDER}│{RESET_COLOR}",
            f"{C_MODAL_BORDER}╰" + "─" * (modal_w - 2) + f"╯{RESET_COLOR}",
        ]
        return modal_lines

    def _apply_modal(self, frame: List[str], modal_lines: List[str]):
        """Superimpose modal dialog centered on top of the frame."""
        modal_h = len(modal_lines)
        if not modal_h:
            return

        modal_w = visible_len(modal_lines[0])
        start_y = max(1, (len(frame) - modal_h) // 2)
        start_x = max(1, (self.cols - modal_w) // 2)

        for i, m_line in enumerate(modal_lines):
            target_y = start_y + i
            if target_y >= len(frame):
                break
            orig = frame[target_y]
            # Replace character slice between start_x and start_x + modal_w
            # For simplicity with ANSI codes, we can construct the line:
            # left_slice + m_line + right_slice
            plain_orig = ANSI_REGEX.sub("", orig)
            left_part = plain_orig[:start_x]
            right_part = plain_orig[start_x + modal_w :]
            frame[target_y] = f"{left_part}{m_line}{right_part}"
