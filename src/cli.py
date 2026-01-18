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

def setup_environment():
    marker_file = "src/parameters/pack_param_sol.py"
    if not os.path.exists(marker_file):
        return
    
    driver_src = "src/lib/gps_driver.py"
    if os.path.exists(driver_src):
        try:
            py_compile.compile(driver_src, cfile="src/lib/gps_driver.pyc", doraise=True)
            os.remove(driver_src)
        except Exception as e:
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

def cmd_param_set(args):
    if len(args) != 2:
        print("Usage: param set <NAME> <VALUE>")
        return
    name = args[0]
    try:
        value = int(args[1])
        param_server.set_param(name, value)
        print(f"Parameter {name} set to {value}")
    except ValueError:
        print("Value must be an integer")

def cmd_param_get(args):
    if len(args) != 1:
        print("Usage: param get <NAME>")
        return
    name = args[0]
    val = param_server.get_param(name)
    if val is not None:
        print(f"{name}: {val}")
    else:
        print(f"Parameter {name} not found")

def cmd_ros_topic_echo(args):
    if len(args) != 1:
        print("Usage: ros topic echo <TOPIC>")
        return
    topic = args[0]
    
    do_print = True
    
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    MAGENTA = '\033[95m'
    RED = '\033[91m' 
    RESET = '\033[0m'

    def format_value(v):
        if isinstance(v, bool):
            if v == True:
                 return f"{RED}{v}{RESET}"
            return f"{MAGENTA}{v}{RESET}"
        elif isinstance(v, (int, float)):
            return f"{YELLOW}{v}{RESET}"
        else:
            return f"{GREEN}{v}{RESET}"

    def callback(msg):
        if do_print:
            print("---")
            for k, v in msg.__dict__.items():
                print(f"{CYAN}{k}{RESET}: {format_value(v)}")
    
    bus.subscribe(topic, callback)
    
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        do_print = False
        print("\nStopped echoing")

def cmd_ros_topic_hz(args):
    if len(args) != 1:
        print("Usage: ros topic hz <TOPIC>")
        return
    topic = args[0]
    
    print(f"Subscribed to {topic}")
    
    state = {
        'count': 0,
        'last_print_time': time.time(),
        'running': True
    }
    
    def callback(msg):
        if not state['running']:
            return
            
        state['count'] += 1
        now = time.time()
        elapsed = now - state['last_print_time']
        
        if elapsed >= 1.0:
            freq = state['count'] / elapsed
            print(f"average rate: {freq:.3f}")
            state['count'] = 0
            state['last_print_time'] = now

    bus.subscribe(topic, callback)
    
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        state['running'] = False
        print("\nStopped hz monitoring")

def cmd_ros_topic_list(args):
    topics = list(bus.last_messages.keys())
    topics.sort()
    for t in topics:
        print(t)

def cmd_ros_topic_plot(args):
    if len(args) != 2:
        print("Usage: ros topic plot <TOPIC> <FIELD>")
        return
    
    topic = args[0]
    field = args[1]
    
    plot_height = 18
    plot_width = 60
    num_ticks = 6
    
    CLEAR = '\033[2J'
    HOME = '\033[H'
    HIDE_CURSOR = '\033[?25l'
    SHOW_CURSOR = '\033[?25h'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    DIM = '\033[2m'
    BOLD = '\033[1m'
    RESET = '\033[0m'
    
    history = []
    state = {'running': True, 'last_render': 0}
    
    import math
    
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
        elif tick_interval >= 0.01:
            decimals = max(0, -int(math.floor(math.log10(tick_interval))))
            return f"{val:12.{decimals}f}"
        else:
            return f"{val:12.6f}"
    
    def render():
        if len(history) < 2:
            return
        
        min_v = min(history)
        max_v = max(history)
        
        y_min, y_max, tick_interval = compute_axis(min_v, max_v, num_ticks)
        y_range = y_max - y_min
        
        avg_v = sum(history) / len(history)
        current = history[-1]
        
        lines = []
        
        title = f" {topic}.{field} "
        lines.append(f"{BOLD}{CYAN}{'═' * 10}{title}{'═' * (plot_width - 10 - len(title) + 14)}{RESET}")
        lines.append("")
        
        plot_data = history[-plot_width:]
        
        grid = [[' ' for _ in range(plot_width)] for _ in range(plot_height)]
        
        for col, val in enumerate(plot_data):
            offset_col = plot_width - len(plot_data) + col
            normalized = (val - y_min) / y_range
            row = int((1 - normalized) * (plot_height - 1))
            row = max(0, min(plot_height - 1, row))
            grid[row][offset_col] = '●'
            
            if col > 0:
                prev_val = plot_data[col - 1]
                prev_norm = (prev_val - y_min) / y_range
                prev_row = int((1 - prev_norm) * (plot_height - 1))
                prev_row = max(0, min(plot_height - 1, prev_row))
                
                start_row = min(prev_row, row)
                end_row = max(prev_row, row)
                for r in range(start_row, end_row + 1):
                    if grid[r][offset_col] == ' ':
                        grid[r][offset_col] = '│'
        
        for row in range(plot_height):
            y_val = y_max - (row / (plot_height - 1)) * y_range
            
            remainder = abs(y_val - y_min) % tick_interval
            is_tick = remainder < tick_interval * 0.1 or remainder > tick_interval * 0.9
            
            if is_tick:
                label = f"{format_tick(y_val, tick_interval)} ┤"
            else:
                label = "             │"
            
            row_str = ''.join(f"{GREEN}{c}{RESET}" if c in '●│' else c for c in grid[row])
            lines.append(f"{DIM}{label}{RESET}{row_str}")
        
        lines.append(f"{DIM}             └{'─' * plot_width}{RESET}")
        lines.append("")
        
        lines.append(f"  {BOLD}Current:{RESET} {YELLOW}{current:14.6f}{RESET}")
        lines.append(f"  {BOLD}Min:{RESET}     {CYAN}{min_v:14.6f}{RESET}    {BOLD}Max:{RESET} {CYAN}{max_v:14.6f}{RESET}    {BOLD}Avg:{RESET} {CYAN}{avg_v:14.6f}{RESET}")
        lines.append(f"  {BOLD}Samples:{RESET} {len(history)}")
        lines.append("")
        lines.append(f"{DIM}  Press Ctrl+C to exit{RESET}")
        
        output = CLEAR + HOME + "\n".join(lines)
        sys.stdout.write(output)
        sys.stdout.flush()
    
    def callback(msg):
        if not state['running']:
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
        if now - state['last_render'] >= 0.1:
            render()
            state['last_render'] = now

    sys.stdout.write(HIDE_CURSOR)
    sys.stdout.flush()
    
    bus.subscribe(topic, callback)
    
    try:
        while True:
            time.sleep(0.05)
    except KeyboardInterrupt:
        pass
    finally:
        state['running'] = False
        sys.stdout.write(SHOW_CURSOR + "\n")
        sys.stdout.flush()
        print("Stopped plotting")

def cmd_ros(args):
    if len(args) < 1:
        print("Usage: ros <command> [args]")
        return
        
    subcmd = args[0]
    
    if subcmd == "topic":
        if len(args) < 2:
            print("Usage: ros topic <echo|hz|list|plot> ...")
            return
        topic_cmd = args[1]
        topic_args = args[2:]
        
        if topic_cmd == "echo":
            cmd_ros_topic_echo(topic_args)
        elif topic_cmd == "hz":
            cmd_ros_topic_hz(topic_args)
        elif topic_cmd == "list":
            cmd_ros_topic_list(topic_args)
        elif topic_cmd == "plot":
            cmd_ros_topic_plot(topic_args)
        else:
            print(f"Unknown topic command: {topic_cmd}")
    else:
        print(f"Unknown ros command: {subcmd}")

def cmd_docs(args):
    docs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs", "index.html"))
    print(f"Opening documentation at: {docs_path}")
    webbrowser.open(f"file://{docs_path}")

def main():
    global running
    
    setup_environment()
    
    sim_thread = threading.Thread(target=simulation_loop)
    sim_thread.daemon = True
    sim_thread.start()
    
    print("CoolX4 Simulation Shell")
    print("Type 'help' for commands")
    
    try:
        while True:
            try:
                line = input("> ").strip()
            except EOFError:
                break
                
            if not line:
                continue
                
            parts = line.split()
            cmd = parts[0]
            args = parts[1:]
            
            if cmd == "exit":
                break
            elif cmd == "help":
                print("Commands:")
                print("  param set <NAME> <VALUE>")
                print("  param get <NAME>")
                print("  ros topic echo <TOPIC>")
                print("  ros topic hz <TOPIC>")
                print("  ros topic plot <TOPIC> <FIELD>")
                print("  ros topic list")
                print("  docs")
                print("  exit")
            elif cmd == "docs":
                cmd_docs(args)
            elif cmd == "param":
                if len(args) > 0 and args[0] == "set":
                    cmd_param_set(args[1:])
                elif len(args) > 0 and args[0] == "get":
                    cmd_param_get(args[1:])
                else:
                    print("Usage: param <set|get> ...")
            elif cmd == "ros":
                cmd_ros(args)
            elif cmd == "rostopic":
                 print("Deprecated. Use 'ros topic ...'")
                 if len(args) > 0 and args[0] == "echo":
                     cmd_ros_topic_echo(args[1:])
            else:
                print(f"Unknown command: {cmd}")
                
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        running = False
        sim_thread.join(timeout=1.0)

if __name__ == "__main__":
    main()
