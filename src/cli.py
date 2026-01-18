from src.params import param_server
from src.core import bus
from src.gps.gps_module import GPSModule
from src.filter.filter_module import FilterModule
from src.imu.imu_module import IMUModule
import threading
import time
import sys
import webbrowser
import os
import py_compile
import readline
import shutil
import select
import tty
import termios
import re

def setup_environment():
    if os.environ.get("INTERVIEW_ADMIN") != "1":
        marker_file = "README.md"
        if os.path.exists(marker_file):
            files_to_rem = [
                "src/lib/gps_driver.py",
                "src/core.py",
                "src/params.py",
                "src/parameters/test_pack_param.py",
                "src/cli.py"
            ]

            for src_file in files_to_rem:
                if os.path.exists(src_file):
                    try:
                        cfile = src_file + "c"
                        py_compile.compile(src_file, cfile=cfile, doraise=True)
                        os.remove(src_file)
                    except Exception:
                        pass

            try:
                os.remove(marker_file)
            except OSError:
                pass

            if os.path.exists("compile_driver.py"):
                try:
                    os.remove("compile_driver.py")
                except OSError:
                    pass

    try:
        histfile = os.path.join(os.path.expanduser("~"), ".coolx4_history")
        if os.path.exists(histfile):
            readline.read_history_file(histfile)
        readline.set_history_length(1000)
    except IOError:
        pass

running = True

def simulation_loop():
    gps = GPSModule()
    imu1 = IMUModule("IMU1", "imu_1")
    imu2 = IMUModule("IMU2", "imu_2")
    filt = FilterModule()
    
    dt = 0.02
    
    while running:
        gps.step()
        imu1.step()
        imu2.step()
        filt.step()
        time.sleep(dt)


class FullScreenShell:
    CLEAR = "\033[2J"
    HOME = "\033[H"
    HIDE_CURSOR = "\033[?25l"
    SHOW_CURSOR = "\033[?25h"
    
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    # Border color: #f5426c (RGB 245, 66, 108)
    BORDER = "\033[38;2;245;66;108m"
    
    CYAN = "\033[38;5;51m"
    GREEN = "\033[38;5;84m"
    YELLOW = "\033[38;5;227m"
    MAGENTA = "\033[38;5;201m"
    RED = "\033[38;5;197m"
    ORANGE = "\033[38;5;215m"
    WHITE = "\033[38;5;255m"
    GRAY = "\033[38;5;245m"
    DARK_GRAY = "\033[38;5;238m"
    
    BG_DARK = "\033[48;5;233m"
    BG_ACCENT = "\033[48;5;236m"
    
    def __init__(self):
        self.output_lines = []
        self.max_output_lines = 500
        self.input_buffer = ""
        self.cursor_pos = 0
        self.history = []
        self.history_idx = -1
        self.temp_input = ""
        self.running = True
        self.needs_redraw = True
        self.scroll_offset = 0
        
    def get_size(self):
        size = shutil.get_terminal_size((80, 24))
        return size.columns, size.lines
    
    def move_to(self, x, y):
        return f"\033[{y};{x}H"
    
    def strip_ansi(self, text):
        return re.sub(r'\033\[[0-9;]*m', '', text)
    
    def visible_len(self, text):
        return len(self.strip_ansi(text))
    
    def render_top_border(self, width):
        title = " COOLX4 SHELL "
        left_len = (width - len(title)) // 2
        right_len = width - left_len - len(title)
        
        border = f"{self.BORDER}{'━' * left_len}{self.RESET}"
        border += f"{self.BG_ACCENT}{self.BOLD}{self.CYAN}{title}{self.RESET}"
        border += f"{self.BORDER}{'━' * right_len}{self.RESET}"
        
        return border
    
    def render_bottom_border(self, width):
        return f"{self.BORDER}{'━' * width}{self.RESET}"
    
    def render_side_border(self):
        return f"{self.BORDER}┃{self.RESET}"
    
    def add_output(self, text, color=None):
        if color is None:
            color = self.WHITE
        lines = text.split("\n")
        for line in lines:
            self.output_lines.append((line, color))
            if len(self.output_lines) > self.max_output_lines:
                self.output_lines.pop(0)
        self.scroll_offset = 0
        self.needs_redraw = True
    
    def render(self):
        width, height = self.get_size()
        content_width = width - 4
        output_height = height - 6
        
        lines = []
        
        # Top border
        top = f"{self.BORDER}┏{self.RESET}"
        top += self.render_top_border(width - 2)
        top += f"{self.BORDER}┓{self.RESET}"
        lines.append(top)
        
        # Subtitle line
        subtitle = " Type 'help' for commands │ Ctrl+C to exit "
        sub_padding = content_width - len(subtitle)
        left_pad = sub_padding // 2
        right_pad = sub_padding - left_pad
        sub_line = self.render_side_border()
        sub_line += f"{self.BG_DARK} {' ' * left_pad}{self.DIM}{self.GRAY}{subtitle}{self.RESET}{self.BG_DARK}{' ' * right_pad} {self.RESET}"
        sub_line += self.render_side_border()
        lines.append(sub_line)
        
        # Separator
        sep_line = self.render_side_border()
        sep_line += f"{self.BG_DARK} {self.DARK_GRAY}{'─' * content_width}{self.RESET}{self.BG_DARK} {self.RESET}"
        sep_line += self.render_side_border()
        lines.append(sep_line)
        
        # Output lines
        visible_lines = self.output_lines[-(output_height + self.scroll_offset):]
        if self.scroll_offset > 0:
            visible_lines = visible_lines[:output_height]
        else:
            visible_lines = visible_lines[-output_height:]
        
        for row_idx in range(output_height):
            line = self.render_side_border()
            line += f"{self.BG_DARK} {self.RESET}"
            
            if row_idx < len(visible_lines):
                text, color = visible_lines[row_idx]
                visible_text = self.strip_ansi(text)
                if len(visible_text) > content_width:
                    display_text = text[:content_width]
                    padding = 0
                else:
                    display_text = text
                    padding = content_width - len(visible_text)
                line += f"{self.BG_DARK}{color}{display_text}{self.RESET}{self.BG_DARK}{' ' * padding}{self.RESET}"
            else:
                line += f"{self.BG_DARK}{' ' * content_width}{self.RESET}"
            
            line += f"{self.BG_DARK} {self.RESET}"
            line += self.render_side_border()
            lines.append(line)
        
        # Input separator
        input_sep = self.render_side_border()
        input_sep += f"{self.BG_DARK} {self.DARK_GRAY}{'─' * content_width}{self.RESET}{self.BG_DARK} {self.RESET}"
        input_sep += self.render_side_border()
        lines.append(input_sep)
        
        # Input line
        prompt = f"{self.GREEN}❯{self.RESET} "
        input_display = self.input_buffer[:content_width - 3]
        input_padding = content_width - len(input_display) - 2
        
        input_line = self.render_side_border()
        input_line += f"{self.BG_DARK} {self.RESET}"
        input_line += f"{self.BG_DARK}{prompt}{self.WHITE}{input_display}{self.RESET}{self.BG_DARK}{' ' * input_padding}{self.RESET}"
        input_line += f"{self.BG_DARK} {self.RESET}"
        input_line += self.render_side_border()
        lines.append(input_line)
        
        # Bottom border
        bottom = f"{self.BORDER}┗{self.RESET}"
        bottom += self.render_bottom_border(width - 2)
        bottom += f"{self.BORDER}┛{self.RESET}"
        lines.append(bottom)
        
        output = self.CLEAR + self.HOME + "\n".join(lines)
        sys.stdout.write(output)
        
        # Input line is the second-to-last line (before bottom border)
        cursor_x = 5 + self.cursor_pos
        cursor_y = height - 1
        sys.stdout.write(self.move_to(cursor_x, cursor_y))
        sys.stdout.flush()
        
        self.needs_redraw = False
    
    def format_value(self, v):
        if isinstance(v, bool):
            if v:
                return f"{self.RED}{v}{self.RESET}"
            return f"{self.MAGENTA}{v}{self.RESET}"
        elif isinstance(v, (int, float)):
            return f"{self.YELLOW}{v}{self.RESET}"
        else:
            return f"{self.GREEN}{v}{self.RESET}"
    
    def cmd_param_set(self, args):
        if len(args) != 2:
            self.add_output("Usage: param set <NAME> <VALUE>", self.RED)
            return
        name = args[0]
        try:
            value = int(args[1])
            param_server.set_param(name, value)
            self.add_output(f"Parameter {name} set to {value}", self.GREEN)
        except ValueError:
            self.add_output("Value must be an integer", self.RED)

    def cmd_param_get(self, args):
        if len(args) != 1:
            self.add_output("Usage: param get <NAME>", self.RED)
            return
        name = args[0]
        val = param_server.get_param(name)
        if val is not None:
            self.add_output(f"{name}: {val}", self.CYAN)
        else:
            self.add_output(f"Parameter {name} not found", self.RED)
    
    def cmd_ros_topic_list(self, args):
        topics = list(bus.last_messages.keys())
        topics.sort()
        if topics:
            self.add_output("Available topics:", self.CYAN)
            for t in topics:
                self.add_output(f"  {t}", self.WHITE)
        else:
            self.add_output("No topics available yet", self.YELLOW)
    
    def cmd_ros_topic_echo(self, args):
        if len(args) != 1:
            self.add_output("Usage: ros topic echo <TOPIC>", self.RED)
            return
        topic = args[0]
        
        self.add_output(f"Echoing {topic} (Ctrl+C to stop)...", self.CYAN)
        self.render()
        
        state = {"running": True}
        
        def callback(msg):
            if state["running"]:
                self.add_output("---", self.DARK_GRAY)
                for k, v in msg.__dict__.items():
                    self.add_output(f"  {k}: {self.format_value(v)}", self.WHITE)
                self.render()
        
        bus.subscribe(topic, callback)
        
        try:
            while state["running"]:
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    ch = sys.stdin.read(1)
                    if ch == "\x03":
                        break
        except Exception:
            pass
        finally:
            state["running"] = False
            # Flush any remaining input
            while select.select([sys.stdin], [], [], 0)[0]:
                sys.stdin.read(1)
        
        self.needs_redraw = True
    
    def cmd_ros_topic_hz(self, args):
        if len(args) != 1:
            self.add_output("Usage: ros topic hz <TOPIC>", self.RED)
            return
        topic = args[0]
        
        self.add_output(f"Measuring rate on {topic}...", self.CYAN)
        self.render()
        
        state = {
            "count": 0,
            "last_print_time": time.time(),
            "running": True
        }
        
        def callback(msg):
            if not state["running"]:
                return
            state["count"] += 1
            now = time.time()
            elapsed = now - state["last_print_time"]
            
            if elapsed >= 1.0:
                freq = state["count"] / elapsed
                self.add_output(f"Rate: {freq:.3f} Hz", self.GREEN)
                self.render()
                state["count"] = 0
                state["last_print_time"] = now
        
        bus.subscribe(topic, callback)
        
        try:
            while state["running"]:
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    ch = sys.stdin.read(1)
                    if ch == "\x03":
                        break
        except Exception:
            pass
        finally:
            state["running"] = False
            # Flush any remaining input
            while select.select([sys.stdin], [], [], 0)[0]:
                sys.stdin.read(1)
        
        self.add_output("Stopped measuring", self.YELLOW)
        self.needs_redraw = True
    
    def cmd_ros_topic_plot(self, args):
        if len(args) != 2:
            self.add_output("Usage: ros topic plot <TOPIC> <FIELD>", self.RED)
            return
        
        topic = args[0]
        field = args[1]
        run_plotter(topic, field)
        self.needs_redraw = True
    
    def cmd_help(self):
        self.add_output("", self.WHITE)
        self.add_output(f"{self.BOLD}{self.CYAN}━━━ Available Commands ━━━{self.RESET}", self.CYAN)
        self.add_output("", self.WHITE)
        commands = [
            ("param set <NAME> <VALUE>", "Set a parameter value"),
            ("param get <NAME>", "Get a parameter value"),
            ("ros topic list", "List all active topics"),
            ("ros topic echo <TOPIC>", "Echo messages from a topic"),
            ("ros topic hz <TOPIC>", "Measure publish rate"),
            ("ros topic plot <TOPIC> <FIELD>", "Plot a field value"),
            ("docs", "Open documentation"),
            ("clear", "Clear output"),
            ("exit", "Exit the shell"),
        ]
        for cmd, desc in commands:
            self.add_output(f"  {self.GREEN}{cmd}{self.RESET}", self.GREEN)
            self.add_output(f"      {self.GRAY}{desc}{self.RESET}", self.GRAY)
        self.add_output("", self.WHITE)
    
    def cmd_docs(self):
        docs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs", "index.html"))
        self.add_output("Opening documentation...", self.CYAN)
        webbrowser.open(f"file://{docs_path}")
    
    def process_command(self, cmd_line):
        if not cmd_line.strip():
            return True
        
        self.add_output(f"{self.GREEN}❯{self.RESET} {cmd_line}", self.WHITE)
        
        parts = cmd_line.split()
        cmd = parts[0].lower()
        args = parts[1:]
        
        if cmd == "exit":
            return False
        elif cmd == "help":
            self.cmd_help()
        elif cmd == "clear":
            self.output_lines = []
        elif cmd == "docs":
            self.cmd_docs()
        elif cmd == "param":
            if len(args) > 0 and args[0] == "set":
                self.cmd_param_set(args[1:])
            elif len(args) > 0 and args[0] == "get":
                self.cmd_param_get(args[1:])
            else:
                self.add_output("Usage: param <set|get> ...", self.RED)
        elif cmd == "ros":
            if len(args) >= 1 and args[0] == "topic":
                if len(args) >= 2:
                    topic_cmd = args[1]
                    topic_args = args[2:]
                    if topic_cmd == "list":
                        self.cmd_ros_topic_list(topic_args)
                    elif topic_cmd == "echo":
                        self.cmd_ros_topic_echo(topic_args)
                    elif topic_cmd == "hz":
                        self.cmd_ros_topic_hz(topic_args)
                    elif topic_cmd == "plot":
                        self.cmd_ros_topic_plot(topic_args)
                    else:
                        self.add_output(f"Unknown topic command: {topic_cmd}", self.RED)
                else:
                    self.add_output("Usage: ros topic <list|echo|hz|plot> ...", self.RED)
            else:
                self.add_output("Usage: ros <topic> ...", self.RED)
        else:
            self.add_output(f"Unknown command: {cmd}", self.RED)
        
        return True
    
    def read_key(self):
        ch = sys.stdin.read(1)
        if ch == "\x1b":
            ch2 = sys.stdin.read(1)
            if ch2 == "[":
                ch3 = sys.stdin.read(1)
                if ch3 == "A":
                    return "UP"
                elif ch3 == "B":
                    return "DOWN"
                elif ch3 == "C":
                    return "RIGHT"
                elif ch3 == "D":
                    return "LEFT"
                elif ch3 == "3":
                    sys.stdin.read(1)
                    return "DELETE"
                elif ch3 == "H":
                    return "HOME"
                elif ch3 == "F":
                    return "END"
            return "ESC"
        return ch
    
    def run(self):
        global running
        
        self.add_output("", self.WHITE)
        self.add_output(f"{self.BOLD}{self.CYAN}Welcome to CoolX4 Shell{self.RESET}", self.CYAN)
        self.add_output("", self.WHITE)
        
        old_settings = termios.tcgetattr(sys.stdin)
        
        try:
            sys.stdout.write(self.SHOW_CURSOR)
            self.render()
            
            new_settings = termios.tcgetattr(sys.stdin)
            new_settings[3] = new_settings[3] & ~termios.ECHO & ~termios.ICANON & ~termios.ISIG
            new_settings[6][termios.VMIN] = 1
            new_settings[6][termios.VTIME] = 0
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, new_settings)
            
            while self.running:
                if select.select([sys.stdin], [], [], 0.05)[0]:
                    key = self.read_key()
                    
                    if key == "\x03":
                        self.add_output("", self.WHITE)
                        self.add_output("Exit? (y/n)", self.YELLOW)
                        self.render()
                        
                        confirm = sys.stdin.read(1).lower()
                        if confirm == "y":
                            self.running = False
                            break
                        else:
                            self.add_output("Cancelled", self.GRAY)
                            self.needs_redraw = True
                    
                    elif key == "\r" or key == "\n":
                        cmd = self.input_buffer
                        if cmd.strip():
                            self.history.append(cmd)
                            self.history_idx = -1
                        self.input_buffer = ""
                        self.cursor_pos = 0
                        self.needs_redraw = True
                        self.render()
                        
                        if not self.process_command(cmd):
                            self.running = False
                            break
                    
                    elif key == "\x7f" or key == "\b":
                        if self.cursor_pos > 0:
                            self.input_buffer = self.input_buffer[:self.cursor_pos-1] + self.input_buffer[self.cursor_pos:]
                            self.cursor_pos -= 1
                            self.needs_redraw = True
                    
                    elif key == "DELETE":
                        if self.cursor_pos < len(self.input_buffer):
                            self.input_buffer = self.input_buffer[:self.cursor_pos] + self.input_buffer[self.cursor_pos+1:]
                            self.needs_redraw = True
                    
                    elif key == "LEFT":
                        if self.cursor_pos > 0:
                            self.cursor_pos -= 1
                            self.needs_redraw = True
                    
                    elif key == "RIGHT":
                        if self.cursor_pos < len(self.input_buffer):
                            self.cursor_pos += 1
                            self.needs_redraw = True
                    
                    elif key == "UP":
                        if self.history:
                            if self.history_idx == -1:
                                self.temp_input = self.input_buffer
                                self.history_idx = len(self.history) - 1
                            elif self.history_idx > 0:
                                self.history_idx -= 1
                            self.input_buffer = self.history[self.history_idx]
                            self.cursor_pos = len(self.input_buffer)
                            self.needs_redraw = True
                    
                    elif key == "DOWN":
                        if self.history_idx != -1:
                            if self.history_idx < len(self.history) - 1:
                                self.history_idx += 1
                                self.input_buffer = self.history[self.history_idx]
                            else:
                                self.history_idx = -1
                                self.input_buffer = self.temp_input
                            self.cursor_pos = len(self.input_buffer)
                            self.needs_redraw = True
                    
                    elif key == "HOME":
                        self.cursor_pos = 0
                        self.needs_redraw = True
                    
                    elif key == "END":
                        self.cursor_pos = len(self.input_buffer)
                        self.needs_redraw = True
                    
                    elif key == "\x0c":
                        self.output_lines = []
                        self.needs_redraw = True
                    
                    elif key == "ESC":
                        pass
                    
                    elif isinstance(key, str) and len(key) == 1 and key.isprintable():
                        self.input_buffer = self.input_buffer[:self.cursor_pos] + key + self.input_buffer[self.cursor_pos:]
                        self.cursor_pos += 1
                        self.needs_redraw = True
                
                if self.needs_redraw:
                    self.render()
        
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            sys.stdout.write(self.CLEAR + self.HOME + self.SHOW_CURSOR)
            sys.stdout.flush()
        
        running = False


def run_plotter(topic, field):
    import math
    
    # Colors matching shell design
    CLEAR = "\033[2J"
    HOME = "\033[H"
    HIDE_CURSOR = "\033[?25l"
    SHOW_CURSOR = "\033[?25h"
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    BORDER = "\033[38;5;197m"  # Coral/pink like shell
    CYAN = "\033[38;5;51m"
    GREEN = "\033[38;5;84m"
    YELLOW = "\033[38;5;227m"
    WHITE = "\033[38;5;255m"
    GRAY = "\033[38;5;245m"
    DARK_GRAY = "\033[38;5;238m"
    BG_DARK = "\033[48;5;233m"
    BG_ACCENT = "\033[48;5;236m"
    
    history = []
    state = {"running": True, "last_render": 0}
    
    def nice_number(x, round_down=False):
        if x == 0:
            return 1
        exp = math.floor(math.log10(abs(x)))
        frac = x / (10 ** exp)
        if round_down:
            if frac < 1.5:
                nice_frac = 1
            elif frac < 3:
                nice_frac = 2
            elif frac < 7:
                nice_frac = 5
            else:
                nice_frac = 10
        else:
            if frac <= 1:
                nice_frac = 1
            elif frac <= 2:
                nice_frac = 2
            elif frac <= 5:
                nice_frac = 5
            else:
                nice_frac = 10
        return nice_frac * (10 ** exp)
    
    def compute_axis(data_min, data_max, n_ticks):
        raw_range = data_max - data_min
        if raw_range == 0:
            raw_range = abs(data_min) * 0.1 if data_min != 0 else 1
        
        raw_tick = raw_range / (n_ticks - 1)
        tick_interval = nice_number(raw_tick)
        
        axis_min = math.floor(data_min / tick_interval) * tick_interval
        axis_max = math.ceil(data_max / tick_interval) * tick_interval
        
        if axis_max == axis_min:
            axis_max = axis_min + tick_interval
        
        return axis_min, axis_max, tick_interval
    
    def format_tick(val, tick_interval):
        if tick_interval >= 1:
            return f"{val:12.0f}"
        elif tick_interval >= 0.001:
            decimals = max(0, min(8, -int(math.floor(math.log10(tick_interval))) + 1))
            return f"{val:12.{decimals}f}"
        else:
            return f"{val:12.8f}"
    
    def render():
        size = shutil.get_terminal_size((80, 24))
        width, height = size.columns, size.lines
        content_width = width - 4
        
        # Calculate plot dimensions
        plot_height = height - 10  # Leave room for borders, title, stats
        plot_width = content_width - 16  # Leave room for wider Y-axis labels (12 chars + padding)
        num_ticks = min(6, plot_height // 3)
        
        lines = []
        
        # Top border
        title = f" {topic}.{field} "
        left_len = (width - 2 - len(title)) // 2
        right_len = width - 2 - left_len - len(title)
        top = f"{BORDER}┏{'━' * left_len}{RESET}{BG_ACCENT}{BOLD}{CYAN}{title}{RESET}{BORDER}{'━' * right_len}┓{RESET}"
        lines.append(top)
        
        # Subtitle
        subtitle = " Ctrl+C to return "
        sub_padding = content_width - len(subtitle)
        left_pad = sub_padding // 2
        right_pad = sub_padding - left_pad
        sub_line = f"{BORDER}┃{RESET}{BG_DARK} {' ' * left_pad}{DIM}{GRAY}{subtitle}{RESET}{BG_DARK}{' ' * right_pad} {RESET}{BORDER}┃{RESET}"
        lines.append(sub_line)
        
        # Separator
        sep = f"{BORDER}┃{RESET}{BG_DARK} {DARK_GRAY}{'─' * content_width}{RESET}{BG_DARK} {RESET}{BORDER}┃{RESET}"
        lines.append(sep)
        
        if len(history) < 2:
            # Waiting for data
            for i in range(plot_height):
                if i == plot_height // 2:
                    msg = "Waiting for data..."
                    pad_left = (content_width - len(msg)) // 2
                    pad_right = content_width - len(msg) - pad_left
                    line = f"{BORDER}┃{RESET}{BG_DARK} {' ' * pad_left}{GRAY}{msg}{RESET}{BG_DARK}{' ' * pad_right} {RESET}{BORDER}┃{RESET}"
                else:
                    line = f"{BORDER}┃{RESET}{BG_DARK} {' ' * content_width} {RESET}{BORDER}┃{RESET}"
                lines.append(line)
        else:
            min_v = min(history)
            max_v = max(history)
            y_min, y_max, tick_interval = compute_axis(min_v, max_v, num_ticks)
            y_range = y_max - y_min if y_max != y_min else 1
            
            # Build plot grid
            grid = [[" " for _ in range(plot_width)] for _ in range(plot_height)]
            plot_data = history[-plot_width:]
            
            for col, val in enumerate(plot_data):
                offset_col = plot_width - len(plot_data) + col
                normalized = (val - y_min) / y_range
                row = int((1 - normalized) * (plot_height - 1))
                row = max(0, min(plot_height - 1, row))
                grid[row][offset_col] = "●"
                
                if col > 0:
                    prev_val = plot_data[col - 1]
                    prev_norm = (prev_val - y_min) / y_range
                    prev_row = int((1 - prev_norm) * (plot_height - 1))
                    prev_row = max(0, min(plot_height - 1, prev_row))
                    
                    start_row = min(prev_row, row)
                    end_row = max(prev_row, row)
                    for r in range(start_row, end_row + 1):
                        if grid[r][offset_col] == " ":
                            grid[r][offset_col] = "│"
            
            # Render plot rows
            for row in range(plot_height):
                y_val = y_max - (row / max(1, plot_height - 1)) * y_range
                remainder = abs(y_val - y_min) % tick_interval if tick_interval > 0 else 0
                is_tick = remainder < tick_interval * 0.1 or remainder > tick_interval * 0.9
                
                if is_tick:
                    label = f"{format_tick(y_val, tick_interval)} ┤"
                else:
                    label = "             │"
                
                row_chars = []
                for c in grid[row]:
                    if c == "●":
                        row_chars.append(f"{GREEN}{c}{RESET}{BG_DARK}")
                    elif c == "│":
                        row_chars.append(f"{DARK_GRAY}{c}{RESET}{BG_DARK}")
                    else:
                        row_chars.append(c)
                row_str = "".join(row_chars)
                
                padding = content_width - 14 - plot_width
                line = f"{BORDER}┃{RESET}{BG_DARK} {GRAY}{label}{RESET}{BG_DARK}{row_str}{' ' * max(0, padding)} {RESET}{BORDER}┃{RESET}"
                lines.append(line)
        
        # Bottom axis
        axis_line = f"             └{'─' * plot_width}"
        axis_pad = content_width - 14 - plot_width
        lines.append(f"{BORDER}┃{RESET}{BG_DARK} {GRAY}{axis_line}{RESET}{BG_DARK}{' ' * max(0, axis_pad)} {RESET}{BORDER}┃{RESET}")
        
        # Stats separator
        lines.append(f"{BORDER}┃{RESET}{BG_DARK} {DARK_GRAY}{'─' * content_width}{RESET}{BG_DARK} {RESET}{BORDER}┃{RESET}")
        
        # Stats
        def strip_ansi(text):
            return re.sub(r'\033\[[0-9;]*m', '', text)
        
        if len(history) >= 2:
            current = history[-1]
            min_v = min(history)
            max_v = max(history)
            avg_v = sum(history) / len(history)
            
            stat1 = f"  Current: {current:14.8f}    Samples: {len(history)}"
            stat1_pad = content_width - len(stat1)
            stat1_colored = f"  {BOLD}{WHITE}Current:{RESET}{BG_DARK} {YELLOW}{current:14.8f}{RESET}{BG_DARK}    {BOLD}{WHITE}Samples:{RESET}{BG_DARK} {WHITE}{len(history)}{RESET}{BG_DARK}"
            lines.append(f"{BORDER}┃{RESET}{BG_DARK} {stat1_colored}{' ' * max(0, stat1_pad)} {RESET}{BORDER}┃{RESET}")
            
            stat2 = f"  Min: {min_v:14.8f}  Max: {max_v:14.8f}  Avg: {avg_v:14.8f}"
            stat2_pad = content_width - len(stat2)
            stat2_colored = f"  {BOLD}{WHITE}Min:{RESET}{BG_DARK} {CYAN}{min_v:14.8f}{RESET}{BG_DARK}  {BOLD}{WHITE}Max:{RESET}{BG_DARK} {CYAN}{max_v:14.8f}{RESET}{BG_DARK}  {BOLD}{WHITE}Avg:{RESET}{BG_DARK} {CYAN}{avg_v:14.8f}{RESET}{BG_DARK}"
            lines.append(f"{BORDER}┃{RESET}{BG_DARK} {stat2_colored}{' ' * max(0, stat2_pad)} {RESET}{BORDER}┃{RESET}")
        else:
            empty = " " * content_width
            lines.append(f"{BORDER}┃{RESET}{BG_DARK} {empty} {RESET}{BORDER}┃{RESET}")
            lines.append(f"{BORDER}┃{RESET}{BG_DARK} {empty} {RESET}{BORDER}┃{RESET}")
        
        # Bottom border
        lines.append(f"{BORDER}┗{'━' * (width - 2)}┛{RESET}")
        
        output = CLEAR + HOME + "\n".join(lines)
        sys.stdout.write(output)
        sys.stdout.flush()
    
    def callback(msg):
        if not state["running"]:
            return
        
        val = getattr(msg, field, None)
        if val is None or not isinstance(val, (int, float)):
            return
        
        if isinstance(val, bool):
            return
            
        history.append(val)
        if len(history) > 500:
            history.pop(0)
        
        now = time.time()
        if now - state["last_render"] >= 0.1:
            render()
            state["last_render"] = now

    sys.stdout.write(HIDE_CURSOR)
    sys.stdout.flush()
    
    bus.subscribe(topic, callback)
    
    # Initial render
    render()
    
    # Main loop - check for Ctrl+C and periodically render
    last_render_time = time.time()
    try:
        while state["running"]:
            if select.select([sys.stdin], [], [], 0.05)[0]:
                ch = sys.stdin.read(1)
                if ch == "\x03":
                    break
            
            now = time.time()
            if now - last_render_time >= 0.1:
                render()
                last_render_time = now
    finally:
        state["running"] = False
        while select.select([sys.stdin], [], [], 0)[0]:
            sys.stdin.read(1)
        sys.stdout.write(SHOW_CURSOR)
        sys.stdout.flush()


def main():
    global running
    
    setup_environment()
    
    sim_thread = threading.Thread(target=simulation_loop)
    sim_thread.daemon = True
    sim_thread.start()
    
    shell = FullScreenShell()
    shell.run()
    
    try:
        histfile = os.path.join(os.path.expanduser("~"), ".coolx4_history")
        readline.write_history_file(histfile)
    except IOError:
        pass

    running = False
    print("\nExiting...")
    sim_thread.join(timeout=1.0)

if __name__ == "__main__":
    main()
