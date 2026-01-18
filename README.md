# CoolX4 GPS Fusion Interview 

## Overview

This simulation mimics a PX4-like flight system where the candidate must diagnose why the drone is stuck in "dead reckoning" mode and fix it by adjusting system parameters.

## Running the Simulation

```bash
python3 -m src.cli
```

### Available Commands

| Command | Description |
|---------|-------------|
| `help` | Show available commands |
| `docs` | Open parameter documentation in browser |
| `param get <NAME>` | Get a parameter value |
| `param set <NAME> <VALUE>` | Set a parameter value |
| `ros topic list` | List available topics |
| `ros topic echo <TOPIC>` | Stream topic messages |
| `ros topic hz <TOPIC>` | Show topic publish rate |
| `ros topic plot <TOPIC> <FIELD>` | Real-time plot of a field |
| `exit` | Exit the simulation |

### Key Topics

- `vehicle_global_position` - Filtered position estimate (lat, lon, alt, dead_reckoning)
- `gps_position` - Raw GPS data (lat, lon, alt, satellites, uncertainty)
- `imu_1`, `imu_2` - IMU sensor data (accel_x/y/z, gyro_x/y/z)

---

## Interview 

**Prompt:**
> "The drone's position estimate is in dead reckoning, which is defined as the drone's position estimate being only informed by IMU. IMU is accurate locally, but drifts and diverges from the true state quickly. Your task is to investigate why and fix it. Use the CLI tools and documentation to diagnose the problem. You should not modify any code, and only consider code under the src/filter, src/gps, and src/imu submodules."

---

## Solution

### Problem 1: GPS Not Being Fused

**Diagnosis:**
```bash
> ros topic echo vehicle_global_position
```
Candidate observes `dead_reckoning: True`.

```bash
> docs
```
Opens documentation. Candidate reads about `FILTER_FUSE_SRC`:
- Default value: `6` (binary `110`)
- Bit 0 = GPS fusion (currently OFF)
- Bit 1 = IMU2 fusion (ON)
- Bit 2 = IMU1 fusion (ON)

**Solution:**
```bash
> param set FILTER_FUSE_SRC 7
```
This sets all three bits: `111` = IMU1 + IMU2 + GPS.

---

### Problem 2: GPS Update Rate Too Low

**Diagnosis:**
After enabling GPS, candidate observes `dead_reckoning` flickering between True and False.

```bash
> ros topic hz gps_position
```
Shows `average rate: 1.000` (1 Hz).

The filter requires GPS data to be < 500ms old. At 1 Hz, data is stale 50% of the time.

**Solution:**
```bash
> param set GPS_PUB_FREQ 5
```
Sets GPS to 5 Hz. Now `dead_reckoning` stays False.

---

### Problem 3: Satellite Dropout Causes Position Jumps

**Prompt:**

> "We're now informed of a new issue - the global position estimate ocassionally jumps significantly before converging back. During these episodes. Why is this happening, and how can we stabilize it?"

**Diagnosis:**
```bash
> ros topic plot vehicle_global_position lat
```
Shows periodic spikes in the position.

```bash
> ros topic plot gps_position satellites
```
Shows satellite count dropping from ~18 to ~6 periodically.

The GPS driver simulates intermittent satellite loss, simulating jamming.

**Solution:**
```bash
> param set MIN_GPS_SAT_VAL 12
```
This tells the filter to reject GPS data when satellites < 12. During dropouts, the system uses dead reckoning instead of the occasionally unstable GPS.

---

### Step 4: Bit Packing A Parameter

**Prompt:**
> "We've received a request to implement a new feature: reading IMU calibration data that is packed into a 32-bit integer to save bandwidth. Please implement the unpacking logic in `src/parameters/pack_param.py`."

**The Task:**
1.  Open `src/parameters/pack_param.py`.
2.  Implement `pack_imu_calibration(x, y, z)` using **only bitwise operators**.
3.  The format is dynamic:
    - Header (Bits 20-31) determines the bit-width for X, Y, Z.
    - The payload (X, Y, Z) is packed sequentially.
    - All values are signed (Two's Complement).
4.  Run `python3 -m src.parameters.test_pack_param` to verify the solution against test cases.
