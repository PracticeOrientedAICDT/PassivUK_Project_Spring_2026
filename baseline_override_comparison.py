import sys
import json
import time
import requests
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


# Config

API_KEY = "insert_api_key"
API_URL = "https://bristol.passivuk.com/optimisation"

# When the user hits override
OVERRIDE_DATETIME = "2026-01-03T07:15:00Z"

# When the override window closes and normal schedule resumes
OVERRIDE_END_HOUR = 10

NUM_ZONES = 2

# Normal heating schedule
BASE_SCHEDULE_Z1 = {
    "hours": [7,    10,       17,    22      ],
    "C":     [19,   "frost",  19,    "frost" ],
}
BASE_SCHEDULE_Z2 = {
    "hours": [7,    10,       17,    22      ],
    "C":     [19,   "frost",  19,    "frost" ],
}

# What the user is overriding to
OVERRIDE_SETPOINT = 25
OVERRIDE_ZONE     = 1

HOT_WATER_SCHEDULE = {"hours": [0], "usage": ["none"]}
TARIFF_P_PER_KWH   = 24.5

# Starting conditions at midnight
START_ZONE_1_TEMP = 18.0
START_ZONE_2_TEMP = 18.0
START_TANK_TEMP   = 45.0

API_DELAY_SECONDS = 2

# API

def call_api(payload, label):
    try:
        r = requests.post(API_URL, headers={"X-API-Key": API_KEY},
                          json=payload, timeout=60)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.HTTPError:
        print(f"\nPayload sent:\n{json.dumps(payload, indent=2)}")
        sys.exit(f"API error ({label}): {r.status_code} {r.text}")
    except requests.exceptions.ConnectionError:
        sys.exit(f"Connection error ({label}): could not reach {API_URL}")
    except requests.exceptions.Timeout:
        sys.exit(f"Timeout ({label})")


# Schedule helpers
def stage1_payload(midnight_dt):
    p = {
        "start_datetime":                midnight_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "num_zones":                     NUM_ZONES,
        "zone_1_heating_daily_schedule": BASE_SCHEDULE_Z1,
        "hotwater_schedule":             HOT_WATER_SCHEDULE,
        "tariff":                        {"hours": [0], "cost": [TARIFF_P_PER_KWH]},
        "tank_temperature":              START_TANK_TEMP,
        "zone_1_temperature":            START_ZONE_1_TEMP,
        "solar":                         False,
    }
    if NUM_ZONES == 2:
        p["zone_2_heating_daily_schedule"] = BASE_SCHEDULE_Z2
        p["zone_2_temperature"]            = START_ZONE_2_TEMP
    return p


def stage2_baseline_payload(override_dt, conditions):
    # Base schedule continues from override time, no override at all
    override_hour = override_dt.hour + override_dt.minute / 60

    def trim(sched):
        hours = [h for h in sched["hours"] if h >= override_hour]
        temps = [c for h, c in zip(sched["hours"], sched["C"]) if h >= override_hour]
        return {"hours": hours, "C": temps}

    p = {
        "start_datetime":                override_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "num_zones":                     NUM_ZONES,
        "zone_1_heating_daily_schedule": trim(BASE_SCHEDULE_Z1),
        "hotwater_schedule":             HOT_WATER_SCHEDULE,
        "tariff":                        {"hours": [0], "cost": [TARIFF_P_PER_KWH]},
        "tank_temperature":              conditions["tank"],
        "zone_1_temperature":            conditions["z1"],
        "solar":                         False,
    }
    if NUM_ZONES == 2:
        p["zone_2_heating_daily_schedule"] = trim(BASE_SCHEDULE_Z2)
        p["zone_2_temperature"]            = conditions["z2"]
    return p


def stage2_override_payload(override_dt, conditions):
    # Override setpoint lands immediately, drops back to base at OVERRIDE_END_HOUR
    override_hour = override_dt.hour + override_dt.minute / 60

    def make(sched, apply_override):
        hours, temps = [], []
        if apply_override:
            hours.append(override_hour)
            temps.append(OVERRIDE_SETPOINT)
            for h, c in zip(sched["hours"], sched["C"]):
                if h >= OVERRIDE_END_HOUR:
                    hours.append(h)
                    temps.append(c)
        else:
            for h, c in zip(sched["hours"], sched["C"]):
                if h >= override_hour:
                    hours.append(h)
                    temps.append(c)
        return {"hours": hours, "C": temps}

    p = {
        "start_datetime":                override_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "num_zones":                     NUM_ZONES,
        "zone_1_heating_daily_schedule": make(BASE_SCHEDULE_Z1, OVERRIDE_ZONE == 1),
        "hotwater_schedule":             HOT_WATER_SCHEDULE,
        "tariff":                        {"hours": [0], "cost": [TARIFF_P_PER_KWH]},
        "tank_temperature":              conditions["tank"],
        "zone_1_temperature":            conditions["z1"],
        "solar":                         False,
    }
    if NUM_ZONES == 2:
        p["zone_2_heating_daily_schedule"] = make(BASE_SCHEDULE_Z2, OVERRIDE_ZONE == 2)
        p["zone_2_temperature"]            = conditions["z2"]
    return p


def stage3_payload(override_end_dt, conditions):
    # Full base schedule from override end — model uses it for next-day lookahead too
    p = {
        "start_datetime":                override_end_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "num_zones":                     NUM_ZONES,
        "zone_1_heating_daily_schedule": BASE_SCHEDULE_Z1,
        "hotwater_schedule":             HOT_WATER_SCHEDULE,
        "tariff":                        {"hours": [0], "cost": [TARIFF_P_PER_KWH]},
        "tank_temperature":              conditions["tank"],
        "zone_1_temperature":            conditions["z1"],
        "solar":                         False,
    }
    if NUM_ZONES == 2:
        p["zone_2_heating_daily_schedule"] = BASE_SCHEDULE_Z2
        p["zone_2_temperature"]            = conditions["z2"]
    return p



# Data extraction
def get_dts(data):
    return [datetime.fromisoformat(t.replace("Z", "+00:00")).replace(tzinfo=None)
            for t in data["real_dt"]]


def get_state(data, key, n):
    vals = data["State"].get(key, [])
    cleaned = [v if isinstance(v, (int, float)) else 0.0 for v in vals]
    while len(cleaned) < n:
        cleaned.insert(0, 0.0)
    return cleaned[:n]


def get_state_float(data, key, n):
    vals = data["State"].get(key, [])
    cleaned = [v if isinstance(v, (int, float)) else float("nan") for v in vals]
    while len(cleaned) < n:
        cleaned.append(float("nan"))
    return cleaned[:n]


def conditions_at(data, target_dt):
    dts = get_dts(data)
    n   = len(dts)
    z1   = get_state(data, "room_temp.z1", n)
    z2   = get_state(data, "room_temp.z2", n)
    tank = get_state(data, "tank_temp",    n)
    idx  = max((i for i, dt in enumerate(dts) if dt <= target_dt), default=0)
    return {
        "z1":   z1[idx]   if z1[idx]   else START_ZONE_1_TEMP,
        "z2":   z2[idx]   if z2[idx]   else START_ZONE_2_TEMP,
        "tank": tank[idx] if tank[idx] else START_TANK_TEMP,
    }


def kwh_in_window(data, start, end):
    dts  = get_dts(data)
    n    = len(dts)
    z1   = get_state(data, "E.hs1.heat.z1",  n)
    z2   = get_state(data, "E.hs1.heat.z2",  n) if NUM_ZONES == 2 else [0.0] * n
    hw   = get_state(data, "E_HW.hs1.heat",  n)
    kwh_space = kwh_hw = 0.0
    for i in range(n - 1):
        if dts[i] < start or dts[i] >= end:
            continue
        dt_h       = (dts[i + 1] - dts[i]).total_seconds() / 3600
        kwh_space += (z1[i] + z2[i]) * dt_h
        kwh_hw    += hw[i] * dt_h
    return kwh_space, kwh_hw


def peak_room_temp(data, after):
    dts  = get_dts(data)
    n    = len(dts)
    room = get_state(data, f"room_temp.z{OVERRIDE_ZONE}", n)
    vals = [t for dt, t in zip(dts, room) if dt >= after and t > 0]
    return max(vals) if vals else None


def setpoint_reached_at(data, after):
    dts  = get_dts(data)
    n    = len(dts)
    room = get_state(data, f"room_temp.z{OVERRIDE_ZONE}", n)
    for dt, t in zip(dts, room):
        if dt >= after and t >= OVERRIDE_SETPOINT:
            return dt
    return None

# Plotting

def plot(s1, s2_base, s2_over, s3_base, s3_over,
         override_dt, override_end_dt):

    def series(data, key):
        dts = get_dts(data)
        return dts, get_state_float(data, key, len(dts))

    tz_drop = lambda dt: dt  # already naive

    over_line = override_dt.to_pydatetime()
    end_line  = override_end_dt.to_pydatetime()

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 7), sharex=True,
                                    gridspec_kw={"height_ratios": [2, 1],
                                                 "hspace": 0.05})

    room_key  = f"room_temp.z{OVERRIDE_ZONE}"
    setp_key  = f"setpoint.z{OVERRIDE_ZONE}"
    power_key = "E.hs1.heat.z1"

    for label, s2, s3, col in [
        ("Baseline",  s2_base, s3_base, "#888888"),
        ("Override",  s2_over, s3_over, "#e63946"),
    ]:
        # Stitch: stage 1 up to override | stage 2 up to end | stage 3
        s1_dts, s1_room  = series(s1, room_key)
        s2_dts, s2_room  = series(s2, room_key)
        s3_dts, s3_room  = series(s3, room_key)

        t1 = [dt for dt in s1_dts if dt <= over_line]
        v1 = s1_room[:len(t1)]
        t2 = [dt for dt in s2_dts if dt <= end_line]
        v2 = s2_room[:len(t2)]

        ls = "--" if label == "Baseline" else "-"
        lw = 1.4  if label == "Baseline" else 1.8

        ax1.plot(t1 + t2 + s3_dts, v1 + v2 + s3_room,
                 color=col, linewidth=lw, linestyle=ls, label=f"{label} — room temp")

        # Setpoint (override scenario only)
        if label == "Override":
            s1_dts_s, s1_setp = series(s1, setp_key)
            s2_dts_s, s2_setp = series(s2, setp_key)
            s3_dts_s, s3_setp = series(s3, setp_key)
            t1s = [dt for dt in s1_dts_s if dt <= over_line]
            v1s = s1_setp[:len(t1s)]
            t2s = [dt for dt in s2_dts_s if dt <= end_line]
            v2s = s2_setp[:len(t2s)]
            ax1.step(t1s + t2s + s3_dts_s, v1s + v2s + s3_setp,
                     where="post", color=col, linewidth=0.9,
                     linestyle=":", alpha=0.6, label="Override setpoint")

        # Power
        s1_dts_p, s1_pow = series(s1, power_key)
        s2_dts_p, s2_pow = series(s2, power_key)
        s3_dts_p, s3_pow = series(s3, power_key)
        t1p = [dt for dt in s1_dts_p if dt <= over_line]
        v1p = s1_pow[:len(t1p)]
        t2p = [dt for dt in s2_dts_p if dt <= end_line]
        v2p = s2_pow[:len(t2p)]
        ax2.plot(t1p + t2p + s3_dts_p, v1p + v2p + s3_pow,
                 color=col, linewidth=lw, linestyle=ls, label=f"{label} — power")

    # Markers
    for ax in (ax1, ax2):
        ax.axvline(over_line, color="grey", linestyle="--", linewidth=0.9, alpha=0.6)
        ax.axvline(end_line,  color="grey", linestyle=":",  linewidth=0.9, alpha=0.6)
        ax.grid(axis="y", linestyle="--", alpha=0.3)
        ax.grid(axis="x", which="minor", linestyle=":", alpha=0.2)

    ax1.axhline(OVERRIDE_SETPOINT, color="#e63946", linewidth=0.7,
                linestyle="-.", alpha=0.35)
    ax1.set_ylabel("Room Temperature (°C)")
    ax1.set_title(
        f"Baseline vs Override  |  Zone {OVERRIDE_ZONE} boosted to {OVERRIDE_SETPOINT}°C  "
        f"from {OVERRIDE_DATETIME[11:16]} to {int(OVERRIDE_END_HOUR):02d}:00\n"
        f"Dashed vertical = override start, dotted = override end",
        fontsize=10
    )
    ax1.legend(fontsize=8, framealpha=0.85)

    ax2.set_ylabel("Input Power (kW)")
    ax2.legend(fontsize=8, framealpha=0.85)
    ax2.xaxis.set_major_locator(mdates.HourLocator(byhour=range(0, 24, 2)))
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax2.xaxis.set_minor_locator(mdates.HourLocator())
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=30, ha="right", fontsize=8)

    fig.tight_layout()
    plt.show()


# Main
def main():
    override_dt   = pd.Timestamp(OVERRIDE_DATETIME.replace("Z", "")).tz_localize(None)
    midnight_dt   = override_dt.normalize()
    midnight_next = midnight_dt + timedelta(days=1)
    override_end_dt = midnight_dt + timedelta(hours=OVERRIDE_END_HOUR)
    override_hour   = override_dt.hour + override_dt.minute / 60

    print()
    print("  Baseline vs Override Comparison")
    print(f"  Date:         {midnight_dt.date()}")
    print(f"  Override:     Zone {OVERRIDE_ZONE} → {OVERRIDE_SETPOINT}°C "
          f"at {OVERRIDE_DATETIME[11:16]}, ends {int(OVERRIDE_END_HOUR):02d}:00")
    print(f"  Tariff:       {TARIFF_P_PER_KWH}p/kWh")
    print(f"  Start temps:  Z1={START_ZONE_1_TEMP}°C  "
          f"Z2={START_ZONE_2_TEMP}°C  Tank={START_TANK_TEMP}°C")

    # Stage 1 — shared
    print(f"\n  Stage 1: midnight → {OVERRIDE_DATETIME[11:16]}")
    s1 = call_api(stage1_payload(midnight_dt), "stage1")
    s1_kwh_space, s1_kwh_hw = kwh_in_window(s1, midnight_dt.to_pydatetime(),
                                              override_dt.to_pydatetime())
    s1_kwh  = s1_kwh_space + s1_kwh_hw
    s1_cost = s1_kwh * TARIFF_P_PER_KWH / 100
    handoff = conditions_at(s1, override_dt.to_pydatetime())
    print(f"  kWh: {s1_kwh:.3f}  Cost: £{s1_cost:.4f}")
    print(f"  Room at {OVERRIDE_DATETIME[11:16]}: "
          f"Z1={handoff['z1']:.1f}°C  Z2={handoff['z2']:.1f}°C  Tank={handoff['tank']:.1f}°C")
    time.sleep(API_DELAY_SECONDS)

    # Stage 2 — baseline
    print(f"\n  Stage 2 (baseline): {OVERRIDE_DATETIME[11:16]} → {int(OVERRIDE_END_HOUR):02d}:00")
    s2_base = call_api(stage2_baseline_payload(override_dt, handoff), "stage2_baseline")
    s2b_space, s2b_hw = kwh_in_window(s2_base, override_dt.to_pydatetime(),
                                       override_end_dt.to_pydatetime())
    s2b_kwh  = s2b_space + s2b_hw
    s2b_cost = s2b_kwh * TARIFF_P_PER_KWH / 100
    handoff_b = conditions_at(s2_base, override_end_dt.to_pydatetime())
    print(f"  kWh: {s2b_kwh:.3f}  Cost: £{s2b_cost:.4f}")
    time.sleep(API_DELAY_SECONDS)

    # Stage 2 — override
    print(f"\n  Stage 2 (override): {OVERRIDE_DATETIME[11:16]} → {int(OVERRIDE_END_HOUR):02d}:00")
    s2_over = call_api(stage2_override_payload(override_dt, handoff), "stage2_override")
    s2o_space, s2o_hw = kwh_in_window(s2_over, override_dt.to_pydatetime(),
                                       override_end_dt.to_pydatetime())
    s2o_kwh  = s2o_space + s2o_hw
    s2o_cost = s2o_kwh * TARIFF_P_PER_KWH / 100
    handoff_o = conditions_at(s2_over, override_end_dt.to_pydatetime())
    pk   = peak_room_temp(s2_over, override_dt.to_pydatetime())
    hit  = setpoint_reached_at(s2_over, override_dt.to_pydatetime())
    print(f"  kWh: {s2o_kwh:.3f}  Cost: £{s2o_cost:.4f}")
    print(f"  Peak room temp: {pk:.1f}°C" if pk else "  Peak room temp: n/a")
    if hit:
        mins = (hit - override_dt.to_pydatetime()).total_seconds() / 60
        print(f"  {OVERRIDE_SETPOINT}°C reached at {hit.strftime('%H:%M')} (+{mins:.0f} min)")
    else:
        print(f"  {OVERRIDE_SETPOINT}°C not reached in override window")
    time.sleep(API_DELAY_SECONDS)

    # Stage 3 — baseline
    print(f"\n  Stage 3 (baseline): {int(OVERRIDE_END_HOUR):02d}:00 → midnight")
    s3_base = call_api(stage3_payload(override_end_dt, handoff_b), "stage3_baseline")
    s3b_space, s3b_hw = kwh_in_window(s3_base, override_end_dt.to_pydatetime(),
                                       midnight_next.to_pydatetime())
    s3b_kwh  = s3b_space + s3b_hw
    s3b_cost = s3b_kwh * TARIFF_P_PER_KWH / 100
    print(f"  kWh: {s3b_kwh:.3f}  Cost: £{s3b_cost:.4f}")
    time.sleep(API_DELAY_SECONDS)

    # Stage 3 — override
    print(f"\n  Stage 3 (override): {int(OVERRIDE_END_HOUR):02d}:00 → midnight")
    s3_over = call_api(stage3_payload(override_end_dt, handoff_o), "stage3_override")
    s3o_space, s3o_hw = kwh_in_window(s3_over, override_end_dt.to_pydatetime(),
                                       midnight_next.to_pydatetime())
    s3o_kwh  = s3o_space + s3o_hw
    s3o_cost = s3o_kwh * TARIFF_P_PER_KWH / 100
    print(f"  kWh: {s3o_kwh:.3f}  Cost: £{s3o_cost:.4f}")

    # Totals
    total_base_kwh  = s1_kwh  + s2b_kwh + s3b_kwh
    total_over_kwh  = s1_kwh  + s2o_kwh + s3o_kwh
    total_base_cost = s1_cost + s2b_cost + s3b_cost
    total_over_cost = s1_cost + s2o_cost + s3o_cost
    extra_kwh  = total_over_kwh  - total_base_kwh
    extra_cost = total_over_cost - total_base_cost

    print()
    print("  Results")
    print(f"  {'':25s}  {'Baseline':>10}  {'Override':>10}  {'Diff':>8}")
    print(f"  {'─'*25}  {'─'*10}  {'─'*10}  {'─'*8}")
    print(f"  {'Energy (kWh)':25s}  {total_base_kwh:>10.3f}  {total_over_kwh:>10.3f}  {extra_kwh:>+8.3f}")
    print(f"  {'Cost (£)':25s}  {total_base_cost:>10.4f}  {total_over_cost:>10.4f}  {extra_cost:>+8.4f}")
    print(f"\n  The override cost an extra £{extra_cost:.4f} "
          f"({extra_kwh:.3f} kWh) vs leaving the schedule alone.")

    print()

    plot(s1, s2_base, s2_over, s3_base, s3_over, override_dt, override_end_dt)


if __name__ == "__main__":
    main()
