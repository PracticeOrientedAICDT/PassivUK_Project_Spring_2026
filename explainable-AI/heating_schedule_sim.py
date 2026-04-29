import sys
import json
import time
import requests
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


#  Config

API_KEY = "insert_api_key"
API_URL = "https://bristol.passivuk.com/optimisation"

# Simulation window 
START_DATE = "2026-01-03"   # First day to simulate (YYYY-MM-DD)
NUM_DAYS   = 4              # How many days to run (chained)

# Override definition
# Time-of-day that the user hits boost each day  (HH:MM)
OVERRIDE_TIME = "06:30"
# Hour at which the override window closes and the normal (or proposed) schedule resumes
OVERRIDE_END_HOUR = 10
# Which zones to boost — [1], [2], or [1, 2]
OVERRIDE_ZONES    = [1]
OVERRIDE_SETPOINT = 21

NUM_ZONES = 1   # Set to 1 for single-zone, 2 for two-zone

# Schedules 
# Current ("base") schedule
BASE_SCHEDULE_Z1 = {
    "hours": [7,    10,       17,    22      ],
    "C":     [19,   "frost",  19,    "frost" ],
}
BASE_SCHEDULE_Z2 = {
    "hours": [7,    10,       17,    22      ],
    "C":     [19,   "frost",  19,    "frost" ],
}

# Proposed schedule — edit these to test a different programme
# Example below: earlier start + slightly higher morning setpoint
PROPOSED_SCHEDULE_Z1 = {
    "hours": [7,    10,       17,    22      ],
    "C":     [21,   "frost",  19,    "frost" ],
}
PROPOSED_SCHEDULE_Z2 = {
    "hours": [7,    10,       17,    22      ],
    "C":     [21,   "frost",  19,    "frost" ],
}

# Hot water, tariff, start temps 
HOT_WATER_SCHEDULE = {"hours": [0], "usage": ["none"]}
TARIFF_P_PER_KWH   = 24.5

START_ZONE_1_TEMP = 19.0
START_ZONE_2_TEMP = 19.0
START_TANK_TEMP   = 45.0

API_DELAY_SECONDS = 2



#  API

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


#  Schedule helpers

def _base_payload(start_dt, schedule_z1, schedule_z2, conditions):
    """Build a full-day payload using the given schedules and starting conditions."""
    p = {
        "start_datetime":                start_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "num_zones":                     NUM_ZONES,
        "zone_1_heating_daily_schedule": schedule_z1,
        "hotwater_schedule":             HOT_WATER_SCHEDULE,
        "tariff":                        {"hours": [0], "cost": [TARIFF_P_PER_KWH]},
        "tank_temperature":              conditions["tank"],
        "zone_1_temperature":            conditions["z1"],
        "solar":                         False,
    }
    if NUM_ZONES == 2:
        p["zone_2_heating_daily_schedule"] = schedule_z2
        p["zone_2_temperature"]            = conditions["z2"]
    return p


def stage1_payload(midnight_dt, conditions, schedule_z1=None, schedule_z2=None):
    """midnight → override_time using the given (or base) schedule."""
    return _base_payload(
        midnight_dt,
        schedule_z1 or BASE_SCHEDULE_Z1,
        schedule_z2 or BASE_SCHEDULE_Z2,
        conditions,
    )


def stage2_baseline_payload(override_dt, conditions, schedule_z1, schedule_z2):
    """override_time → override_end: no boost, just continue the given schedule."""
    override_hour = override_dt.hour + override_dt.minute / 60

    def trim(sched):
        hours = [h for h in sched["hours"] if h >= override_hour]
        temps = [c for h, c in zip(sched["hours"], sched["C"]) if h >= override_hour]
        return {"hours": hours, "C": temps}

    p = {
        "start_datetime":                override_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "num_zones":                     NUM_ZONES,
        "zone_1_heating_daily_schedule": trim(schedule_z1),
        "hotwater_schedule":             HOT_WATER_SCHEDULE,
        "tariff":                        {"hours": [0], "cost": [TARIFF_P_PER_KWH]},
        "tank_temperature":              conditions["tank"],
        "zone_1_temperature":            conditions["z1"],
        "solar":                         False,
    }
    if NUM_ZONES == 2:
        p["zone_2_heating_daily_schedule"] = trim(schedule_z2)
        p["zone_2_temperature"]            = conditions["z2"]
    return p


def stage2_override_payload(override_dt, conditions):
    """
    override_time → override_end: boosted zones see only the new setpoint,
    non-boosted zones carry forward within the window only.
    """
    override_hour = override_dt.hour + override_dt.minute / 60

    def make(sched, apply_override):
        hours, temps = [], []
        if apply_override:
            hours.append(override_hour)
            temps.append(OVERRIDE_SETPOINT)
        else:
            for h, c in zip(sched["hours"], sched["C"]):
                if override_hour <= h < OVERRIDE_END_HOUR:
                    hours.append(h)
                    temps.append(c)
            if not hours:
                prior = [(h, c) for h, c in zip(sched["hours"], sched["C"])
                         if h < override_hour]
                last_c = prior[-1][1] if prior else sched["C"][0]
                hours.append(override_hour)
                temps.append(last_c)
        return {"hours": hours, "C": temps}

    p = {
        "start_datetime":                override_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "num_zones":                     NUM_ZONES,
        "zone_1_heating_daily_schedule": make(BASE_SCHEDULE_Z1, 1 in OVERRIDE_ZONES),
        "hotwater_schedule":             HOT_WATER_SCHEDULE,
        "tariff":                        {"hours": [0], "cost": [TARIFF_P_PER_KWH]},
        "tank_temperature":              conditions["tank"],
        "zone_1_temperature":            conditions["z1"],
        "solar":                         False,
    }
    if NUM_ZONES == 2:
        p["zone_2_heating_daily_schedule"] = make(BASE_SCHEDULE_Z2, 2 in OVERRIDE_ZONES)
        p["zone_2_temperature"]            = conditions["z2"]
    return p


def stage3_payload(override_end_dt, conditions, schedule_z1, schedule_z2):
    """override_end → midnight: resume the given schedule."""
    return _base_payload(override_end_dt, schedule_z1, schedule_z2, conditions)


# In simulate_day, add a clean single-call proposed run
def full_day_proposed_payload(midnight_dt, conditions):
    """Single uninterrupted call for the proposed schedule — no stage splitting."""
    p = {
        "start_datetime":                midnight_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "num_zones":                     NUM_ZONES,
        "zone_1_heating_daily_schedule": PROPOSED_SCHEDULE_Z1,
        "hotwater_schedule":             HOT_WATER_SCHEDULE,
        "tariff":                        {"hours": [0], "cost": [TARIFF_P_PER_KWH]},
        "tank_temperature":              conditions["tank"],
        "zone_1_temperature":            conditions["z1"],
        "solar":                         False,
    }
    if NUM_ZONES == 2:
        p["zone_2_heating_daily_schedule"] = PROPOSED_SCHEDULE_Z2
        p["zone_2_temperature"]            = conditions["z2"]
    return p

#  Data extraction


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
    z2   = get_state(data, "room_temp.z2", n) if NUM_ZONES == 2 else [0.0] * n
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


def peak_room_temp(data, after, zone):
    dts  = get_dts(data)
    n    = len(dts)
    room = get_state(data, f"room_temp.z{zone}", n)
    vals = [t for dt, t in zip(dts, room) if dt >= after and t > 0]
    return max(vals) if vals else None


def setpoint_reached_at(data, after, zone):
    dts  = get_dts(data)
    n    = len(dts)
    room = get_state(data, f"room_temp.z{zone}", n)
    for dt, t in zip(dts, room):
        if dt >= after and t >= OVERRIDE_SETPOINT:
            return dt
    return None



#  Single-day simulation
#  Returns (base_kwh, over_kwh, prop_kwh,
#           base_cost, over_cost, prop_cost,
#           s1, s2b, s2o, s2p, s3b, s3o, s3p,
#           override_dt, override_end_dt,
#           handoff_b_eod, handoff_o_eod, handoff_p_eod)


def simulate_day(day_idx, midnight_dt, start_conds_base, start_conds_over, start_conds_prop):
    midnight_next   = midnight_dt + timedelta(days=1)
    override_h, override_m = [int(x) for x in OVERRIDE_TIME.split(":")]
    override_dt     = midnight_dt + timedelta(hours=override_h, minutes=override_m)
    override_end_dt = midnight_dt + timedelta(hours=OVERRIDE_END_HOUR)

    day_label = midnight_dt.strftime("%Y-%m-%d")
    zones_str = "+".join(f"Z{z}" for z in OVERRIDE_ZONES)

    print(f"\n  {'─'*56}")
    print(f"  Day {day_idx + 1}: {day_label}")
    print(f"  {'─'*56}")

    # Stage 1: midnight → override_time (shared across all three scenarios)
    print(f"  Stage 1: midnight → {OVERRIDE_TIME}")
    # All three scenarios follow the base schedule until the override fires.
    # The proposed schedule diverges only when it has an earlier start than the
    # override time; if its first entry is after override_time, stage 1 is identical.
    s1_base = call_api(stage1_payload(midnight_dt, start_conds_base,
                                      BASE_SCHEDULE_Z1, BASE_SCHEDULE_Z2), f"s1_base_d{day_idx}")
    time.sleep(API_DELAY_SECONDS)
    s1_prop = call_api(stage1_payload(midnight_dt, start_conds_prop,
                                      PROPOSED_SCHEDULE_Z1, PROPOSED_SCHEDULE_Z2), f"s1_prop_d{day_idx}")
    time.sleep(API_DELAY_SECONDS)
    s1_over = call_api(stage1_payload(midnight_dt, start_conds_over,
                                      BASE_SCHEDULE_Z1, BASE_SCHEDULE_Z2), f"s1_over_d{day_idx}")
    time.sleep(API_DELAY_SECONDS)

    handoff_base = conditions_at(s1_base, override_dt)
    handoff_over = conditions_at(s1_over, override_dt)
    handoff_prop = conditions_at(s1_prop, override_dt)

    s1b_kwh_sp, s1b_kwh_hw = kwh_in_window(s1_base, midnight_dt, override_dt)
    s1p_kwh_sp, s1p_kwh_hw = kwh_in_window(s1_prop, midnight_dt, override_dt)
    s1o_kwh_sp, s1o_kwh_hw = kwh_in_window(s1_over, midnight_dt, override_dt)
    s1o_kwh = s1o_kwh_sp + s1o_kwh_hw
    s1b_kwh = s1b_kwh_sp + s1b_kwh_hw
    s1p_kwh = s1p_kwh_sp + s1p_kwh_hw
    print(f"  Base stage 1 kWh: {s1b_kwh:.3f}   Proposed stage 1 kWh: {s1p_kwh:.3f}")

    # Stage 2: override_time → override_end
    print(f"  Stage 2: {OVERRIDE_TIME} → {OVERRIDE_END_HOUR:02d}:00")

    # Baseline (no boost, base schedule)
    s2_base = call_api(stage2_baseline_payload(override_dt, handoff_base,
                                               BASE_SCHEDULE_Z1, BASE_SCHEDULE_Z2), f"s2_base_d{day_idx}")
    time.sleep(API_DELAY_SECONDS)

    # Override (user boost, base schedule context)
    s2_over = call_api(stage2_override_payload(override_dt, handoff_over), f"s2_over_d{day_idx}")
    time.sleep(API_DELAY_SECONDS)

    # Proposed (no boost needed — proposed schedule already covers the need)
    s2_prop = call_api(stage2_baseline_payload(override_dt, handoff_prop,
                                               PROPOSED_SCHEDULE_Z1, PROPOSED_SCHEDULE_Z2), f"s2_prop_d{day_idx}")
    time.sleep(API_DELAY_SECONDS)

    handoff_b_s2end = conditions_at(s2_base, override_end_dt)
    handoff_o_s2end = conditions_at(s2_over, override_end_dt)
    handoff_p_s2end = conditions_at(s2_prop, override_end_dt)

    s2b_sp, s2b_hw = kwh_in_window(s2_base, override_dt, override_end_dt)
    s2o_sp, s2o_hw = kwh_in_window(s2_over, override_dt, override_end_dt)
    s2p_sp, s2p_hw = kwh_in_window(s2_prop, override_dt, override_end_dt)
    s2b_kwh = s2b_sp + s2b_hw
    s2o_kwh = s2o_sp + s2o_hw
    s2p_kwh = s2p_sp + s2p_hw

    for z in OVERRIDE_ZONES:
        pk  = peak_room_temp(s2_over, override_dt, z)
        hit = setpoint_reached_at(s2_over, override_dt, z)
        print(f"  [Override] Zone {z} peak: {pk:.1f}°C" if pk else f"  [Override] Zone {z} peak: n/a")
        if hit:
            mins = (hit - override_dt).total_seconds() / 60
            print(f"  [Override] Zone {z}: {OVERRIDE_SETPOINT}°C reached at {hit.strftime('%H:%M')} (+{mins:.0f} min)")
        else:
            print(f"  [Override] Zone {z}: {OVERRIDE_SETPOINT}°C not reached in window")

    # Stage 3: override_end → midnight 
    print(f"  Stage 3: {OVERRIDE_END_HOUR:02d}:00 → midnight")
    s3_base = call_api(stage3_payload(override_end_dt, handoff_b_s2end,
                                      BASE_SCHEDULE_Z1, BASE_SCHEDULE_Z2), f"s3_base_d{day_idx}")
    time.sleep(API_DELAY_SECONDS)
    s3_over = call_api(stage3_payload(override_end_dt, handoff_o_s2end,
                                      BASE_SCHEDULE_Z1, BASE_SCHEDULE_Z2), f"s3_over_d{day_idx}")
    time.sleep(API_DELAY_SECONDS)
    s3_prop = call_api(stage3_payload(override_end_dt, handoff_p_s2end,
                                      PROPOSED_SCHEDULE_Z1, PROPOSED_SCHEDULE_Z2), f"s3_prop_d{day_idx}")
    time.sleep(API_DELAY_SECONDS)

    s3b_sp, s3b_hw = kwh_in_window(s3_base, override_end_dt, midnight_next)
    s3o_sp, s3o_hw = kwh_in_window(s3_over, override_end_dt, midnight_next)
    s3p_sp, s3p_hw = kwh_in_window(s3_prop, override_end_dt, midnight_next)
    s3b_kwh = s3b_sp + s3b_hw
    s3o_kwh = s3o_sp + s3o_hw
    s3p_kwh = s3p_sp + s3p_hw

    # Day totals 
    base_kwh  = s1b_kwh + s2b_kwh + s3b_kwh
    over_kwh  = s1o_kwh + s2o_kwh + s3o_kwh   # stage 1 is shared with base
    prop_kwh  = s1p_kwh + s2p_kwh + s3p_kwh

    base_cost = base_kwh * TARIFF_P_PER_KWH / 100
    over_cost = over_kwh * TARIFF_P_PER_KWH / 100
    prop_cost = prop_kwh * TARIFF_P_PER_KWH / 100

    print(f"  Day totals  — Base: {base_kwh:.3f} kWh (£{base_cost:.4f})"
          f"  Override: {over_kwh:.3f} kWh (£{over_cost:.4f})"
          f"  Proposed: {prop_kwh:.3f} kWh (£{prop_cost:.4f})")

    # End-of-day handoff temperatures for chaining
    handoff_b_eod = conditions_at(s3_base, midnight_next - timedelta(minutes=1))
    handoff_o_eod = conditions_at(s3_over, midnight_next - timedelta(minutes=1))
    handoff_p_eod = conditions_at(s3_prop, midnight_next - timedelta(minutes=1))

    return (
        base_kwh, over_kwh, prop_kwh,
        base_cost, over_cost, prop_cost,
        s1_base, s1_over, s1_prop,
        s2_base, s2_over, s2_prop,
        s3_base, s3_over, s3_prop,
        override_dt, override_end_dt,
        handoff_b_eod, handoff_o_eod, handoff_p_eod,
    )



#  Plotting (multi-day)

def plot_days(day_results):
    for day_idx, dr in enumerate(day_results):
        (_, _, _,
         _, _, _,
         s1_base, s1_over, s1_prop,
         s2_base, s2_over, s2_prop,
         s3_base, s3_over, s3_prop,
         override_dt, override_end_dt,
         _, _, _) = dr

        over_line     = override_dt
        end_line      = override_end_dt
        midnight_dt   = override_dt.replace(hour=0, minute=0, second=0)
        midnight_next = midnight_dt + timedelta(days=1)

        n_zone_rows   = len(OVERRIDE_ZONES)
        height_ratios = [2] * n_zone_rows + [1]
        fig, axes = plt.subplots(
            n_zone_rows + 1, 1,
            figsize=(13, 4 + 3 * n_zone_rows),
            sharex=True,
            gridspec_kw={"height_ratios": height_ratios, "hspace": 0.05},
        )
        if n_zone_rows == 1:
            zone_axes = [axes[0]]
            ax_power  = axes[1]
        else:
            zone_axes = list(axes[:n_zone_rows])
            ax_power  = axes[-1]

        zones_str = "+".join(f"Z{z}" for z in OVERRIDE_ZONES)

        scenarios = [
            ("Baseline", s1_base, s2_base, s3_base, "#555555", "--", 1.4),
            ("Override", s1_over, s2_over, s3_over, "#e63946", "-",  1.8),
            ("Proposed", s1_prop, s2_prop, s3_prop, "#2a9d8f", "-.", 1.6),
        ]

        def clip(dts, vals, start, end):
            pairs = [(dt, v) for dt, v in zip(dts, vals) if start <= dt < end]
            if not pairs:
                return [], []
            return [x[0] for x in pairs], [x[1] for x in pairs]

        for ax_idx, z in enumerate(OVERRIDE_ZONES):
            ax = zone_axes[ax_idx]
            room_key = f"room_temp.z{z}"
            setp_key = f"setpoint.z{z}"

            for label, s1, s2, s3, col, ls, lw in scenarios:
                def get_series(data, key):
                    dts = get_dts(data)
                    return dts, get_state_float(data, key, len(dts))

                s1_dts, s1_room = get_series(s1, room_key)
                s2_dts, s2_room = get_series(s2, room_key)
                s3_dts, s3_room = get_series(s3, room_key)

                t1, v1 = clip(s1_dts, s1_room, midnight_dt, over_line)
                t2, v2 = clip(s2_dts, s2_room, over_line,   end_line)
                t3, v3 = clip(s3_dts, s3_room, end_line,    midnight_next)

                ax.plot(t1 + t2 + t3, v1 + v2 + v3,
                        color=col, linewidth=lw, linestyle=ls,
                        label=f"{label}")

                if label == "Override":
                    s1_dts_s, s1_setp = get_series(s1, setp_key)
                    s2_dts_s, s2_setp = get_series(s2, setp_key)
                    s3_dts_s, s3_setp = get_series(s3, setp_key)

                    t1s, v1s = clip(s1_dts_s, s1_setp, midnight_dt, over_line)
                    t2s, v2s = clip(s2_dts_s, s2_setp, over_line,   end_line)
                    t3s, v3s = clip(s3_dts_s, s3_setp, end_line,    midnight_next)

                    ax.step(t1s + t2s + t3s, v1s + v2s + v3s,
                            where="post", color=col, linewidth=0.8,
                            linestyle=":", alpha=0.5, label="Override setpoint")

            ax.axvline(over_line, color="grey", linestyle="--", linewidth=0.9, alpha=0.6)
            ax.axvline(end_line,  color="grey", linestyle=":",  linewidth=0.9, alpha=0.6)
            ax.axhline(OVERRIDE_SETPOINT, color="#e63946", linewidth=0.7,
                       linestyle="-.", alpha=0.3)
            ax.grid(axis="y", linestyle="--", alpha=0.3)
            ax.set_ylabel(f"Zone {z} Temp (°C)")
            ax.legend(fontsize=8, framealpha=0.85)
            ax.set_xlim(midnight_dt, midnight_next)

        zone_axes[0].set_title(
            f"Day {day_idx + 1}: {override_dt.strftime('%Y-%m-%d')}  |  "
            f"{zones_str} override to {OVERRIDE_SETPOINT}°C at {OVERRIDE_TIME}  "
            f"(window closes {OVERRIDE_END_HOUR:02d}:00)\n"
            f"Baseline vs Override vs Proposed schedule",
            fontsize=10,
        )

        # Power subplot
        for label, s1, s2, s3, col, ls, lw in scenarios:
            s1_dts_p = get_dts(s1)
            s2_dts_p = get_dts(s2)
            s3_dts_p = get_dts(s3)
            s1_pow = get_state_float(s1, "E.hs1.heat.z1", len(s1_dts_p))
            s2_pow = get_state_float(s2, "E.hs1.heat.z1", len(s2_dts_p))
            s3_pow = get_state_float(s3, "E.hs1.heat.z1", len(s3_dts_p))

            t1p, v1p = clip(s1_dts_p, s1_pow, midnight_dt, over_line)
            t2p, v2p = clip(s2_dts_p, s2_pow, over_line,   end_line)
            t3p, v3p = clip(s3_dts_p, s3_pow, end_line,    midnight_next)

            ax_power.plot(t1p + t2p + t3p, v1p + v2p + v3p,
                          color=col, linewidth=lw, linestyle=ls, label=label)

        ax_power.axvline(over_line, color="grey", linestyle="--", linewidth=0.9, alpha=0.6)
        ax_power.axvline(end_line,  color="grey", linestyle=":",  linewidth=0.9, alpha=0.6)
        ax_power.grid(axis="y", linestyle="--", alpha=0.3)
        ax_power.set_ylabel("Input Power (kW)")
        ax_power.legend(fontsize=8, framealpha=0.85)
        ax_power.set_xlim(midnight_dt, midnight_next)
        ax_power.xaxis.set_major_locator(mdates.HourLocator(byhour=range(0, 24, 2)))
        ax_power.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        ax_power.xaxis.set_minor_locator(mdates.HourLocator())
        plt.setp(ax_power.xaxis.get_majorticklabels(), rotation=30, ha="right", fontsize=8)
        fig.tight_layout()

    plt.show()


#  Multi-day summary table

def print_summary(day_results):
    print()
    print("=" * 72)
    print("  Multi-Day Summary")
    print("=" * 72)

    hdr = f"  {'Day':<12}  {'Base kWh':>9}  {'Over kWh':>9}  {'Prop kWh':>9}  " \
          f"{'Base £':>7}  {'Over £':>7}  {'Prop £':>7}"
    print(hdr)
    print(f"  {'─'*12}  {'─'*9}  {'─'*9}  {'─'*9}  {'─'*7}  {'─'*7}  {'─'*7}")

    totals = [0.0] * 6   # base_kwh, over_kwh, prop_kwh, base_£, over_£, prop_£
    midnight_dt = pd.Timestamp(START_DATE)

    for day_idx, dr in enumerate(day_results):
        bk, ok, pk, bc, oc, pc = dr[0], dr[1], dr[2], dr[3], dr[4], dr[5]
        date_str = (midnight_dt + timedelta(days=day_idx)).strftime("%Y-%m-%d")
        print(f"  {date_str:<12}  {bk:>9.3f}  {ok:>9.3f}  {pk:>9.3f}  "
              f"{bc:>7.4f}  {oc:>7.4f}  {pc:>7.4f}")
        for i, v in enumerate([bk, ok, pk, bc, oc, pc]):
            totals[i] += v

    print(f"  {'─'*12}  {'─'*9}  {'─'*9}  {'─'*9}  {'─'*7}  {'─'*7}  {'─'*7}")
    print(f"  {'TOTAL':<12}  {totals[0]:>9.3f}  {totals[1]:>9.3f}  {totals[2]:>9.3f}  "
          f"{totals[3]:>7.4f}  {totals[4]:>7.4f}  {totals[5]:>7.4f}")

    print()
    print("  Δ vs Baseline (total across all days):")
    print(f"    Override  : {totals[1] - totals[0]:>+.3f} kWh  £{totals[4] - totals[3]:>+.4f}")
    print(f"    Proposed  : {totals[2] - totals[0]:>+.3f} kWh  £{totals[5] - totals[3]:>+.4f}")

    
    prop_vs_base_cost = totals[5] - totals[3]
    over_vs_base_cost = totals[4] - totals[3]
    print()
    if prop_vs_base_cost < over_vs_base_cost - 0.001:
        saving = over_vs_base_cost - prop_vs_base_cost
        print(f"  ✔  Adopting the proposed schedule would save £{saving:.4f} over {len(day_results)} day(s)")
        print(f"     compared with continuing to override manually.")
    elif abs(prop_vs_base_cost - over_vs_base_cost) <= 0.001:
        print("  ≈  Proposed schedule and manual override have similar cost over this period.")
    else:
        extra = prop_vs_base_cost - over_vs_base_cost
        print(f"  ✘  Proposed schedule costs £{extra:.4f} more than manual override over {len(day_results)} day(s).")
        print(f"     Consider tuning PROPOSED_SCHEDULE to better match actual usage.")

    print("=" * 72)
    print()


#  Main

def main():
    start_dt   = pd.Timestamp(START_DATE)
    # start_dt = datetime.strptime(START_DATE + " 16:00", "%Y-%m-%d %H:%M")
    zones_str  = "+".join(f"Z{z}" for z in OVERRIDE_ZONES)

    print()
    print("=" * 72)
    print("  Multi-Day Heating Simulation")
    print("=" * 72)
    print(f"  Start date    : {START_DATE}")
    print(f"  Days          : {NUM_DAYS}")
    print(f"  Override      : {zones_str} → {OVERRIDE_SETPOINT}°C at {OVERRIDE_TIME}, "
          f"window closes {OVERRIDE_END_HOUR:02d}:00")
    print(f"  Tariff        : {TARIFF_P_PER_KWH}p/kWh")
    print(f"  Start temps   : Z1={START_ZONE_1_TEMP}°C  "
          + (f"Z2={START_ZONE_2_TEMP}°C  " if NUM_ZONES == 2 else "")
          + f"Tank={START_TANK_TEMP}°C")
    print(f"  Zones         : {NUM_ZONES}")

    # Chained starting conditions
    conds_base = {"z1": START_ZONE_1_TEMP, "z2": START_ZONE_2_TEMP, "tank": START_TANK_TEMP}
    conds_over = {"z1": START_ZONE_1_TEMP, "z2": START_ZONE_2_TEMP, "tank": START_TANK_TEMP}
    conds_prop = {"z1": START_ZONE_1_TEMP, "z2": START_ZONE_2_TEMP, "tank": START_TANK_TEMP}

    day_results = []

    for day_idx in range(NUM_DAYS):
        midnight_dt = start_dt + timedelta(days=day_idx)

        
        result = simulate_day(day_idx, midnight_dt, conds_base, conds_over, conds_prop)

        (bk, ok, pk, bc, oc, pc,
         s1_base, s1_over, s1_prop,
         s2_base, s2_over, s2_prop,
         s3_base, s3_over, s3_prop,
         override_dt, override_end_dt,
         handoff_b_eod, handoff_o_eod, handoff_p_eod) = result

        # (bk, ok, pk, bc, oc, pc,
        #  s_base,
        #  s1_over, s2_over, s3_over,
        #  s_prop,
        #  override_dt, override_end_dt,
        #  handoff_b_eod, handoff_o_eod, handoff_p_eod) = result
        day_results.append(result)

        # Chain end-of-day temperatures into the next day
        # Each scenario independently evolves its own thermal state
        conds_base = handoff_b_eod
        conds_over = handoff_o_eod
        conds_prop = handoff_p_eod

    print_summary(day_results)
    plot_days(day_results)


if __name__ == "__main__":
    main()
