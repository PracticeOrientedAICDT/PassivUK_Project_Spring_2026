import requests
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

# ── CONFIG ────────────────────────────────────────────────────────────────────

API_KEY = "insert_api_key"
URL = "https://bristol.passivuk.com/optimisation"

inputs = {
    "start_datetime": "2024-06-01T00:00:00Z",
    "num_zones": 1,
    "zone_1_heating_daily_schedule": {
        "hours": [7, 9, 17, 22, 1, 3, 8, 10],
        "C": [21, "frost", 21, "frost",21, "frost",21, "frost"]
    },
    "hotwater_schedule": {
        "hours": [7, 9],
        "usage": ["high", "none"]
    },
    "tariff": {
        "hours": [0, 7, 23],
        "cost": [10, 35, 10]
    },
    "tank_temperature": 19,
    "zone_1_temperature": 19,
    "solar": False,
}

# ── CALL API ──────────────────────────────────────────────────────────────────

print("Calling API...")
r = requests.post(URL, headers={"X-API-Key": API_KEY}, json=inputs)
r.raise_for_status()
data = r.json()
print("Success!")

# ── PARSE RESULTS ─────────────────────────────────────────────────────────────

dts = [datetime.fromisoformat(t.replace("Z", "+00:00")) for t in data["real_dt"]]
n = len(dts)
S = data["State"]

def get(key):
    """Get a state variable, converting non-numbers to None and padding to length n."""
    vals = S.get(key, [])
    cleaned = [v if isinstance(v, (int, float)) else None for v in vals]
    
    while len(cleaned) < n:
        cleaned.insert(0, None)
    return cleaned[:n]

# ── PLOT ──────────────────────────────────────────────────────────────────────

fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
fig.suptitle("Passiv Optimisation Results", fontsize=14, fontweight="bold")

# --- Panel 1: Temperatures ---
ax = axes[0]
ax.plot(dts, get("room_temp.z1"), label="Room Temp Z1", color="steelblue",    linewidth=1.5)
ax.plot(dts, get("setpoint.z1"),  label="Setpoint Z1",  color="steelblue",    linewidth=1, linestyle="--")
if inputs.get("num_zones") == 2:
    ax.plot(dts, get("room_temp.z2"), label="Room Temp Z2", color="mediumpurple", linewidth=1.5)
    ax.plot(dts, get("setpoint.z2"),  label="Setpoint Z2",  color="mediumpurple", linewidth=1, linestyle="--")
ax.plot(dts, get("ext"), label="External Temp", color="gray", linewidth=1, linestyle=":")
ax.set_ylabel("Temperature (°C)")
ax.legend(loc="upper right", fontsize=8)
ax.grid(True, alpha=0.3)

# --- Panel 2: Heat pump power ---
ax = axes[1]
ax.plot(dts, get("E.hs1.heat.z1"), label="HP Input Power Z1",  color="mediumseagreen", linewidth=1.5)
ax.plot(dts, get("U.hs1.z1"),      label="HP Output Power Z1", color="mediumseagreen", linewidth=1, linestyle="--")
ax.plot(dts, get("E_HW.hs1.heat"), label="HP Input Power HW",  color="tomato",         linewidth=1.5)
ax.plot(dts, get("U_HW.hs1"),      label="HP Output Power HW", color="tomato",         linewidth=1, linestyle="--")
ax.set_ylabel("Power (kW)")
ax.legend(loc="upper right", fontsize=8)
ax.grid(True, alpha=0.3)

# --- Panel 3: Hot water tank + electricity cost ---
ax = axes[2]
ax.plot(dts, get("tank_temp"),   label="Tank Temp",   color="hotpink", linewidth=1.5)
ax.plot(dts, get("setpoint_hw"), label="HW Setpoint", color="hotpink", linewidth=1, linestyle="--")
ax.set_ylabel("Tank Temp (°C)")
ax.grid(True, alpha=0.3)

ax2 = ax.twinx()
ax2.plot(dts, get("elec_cost"), label="Elec Cost (p/kWh)", color="goldenrod", linewidth=1.5, linestyle="-.")
ax2.set_ylabel("Elec Cost (p/kWh)", color="goldenrod")
ax2.tick_params(axis="y", labelcolor="goldenrod")

lines1, labels1 = ax.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax.legend(lines1 + lines2, labels1 + labels2, loc="upper right", fontsize=8)

# X axis formatting
axes[2].xaxis.set_major_formatter(mdates.DateFormatter("%d %b %H:%M"))
axes[2].xaxis.set_major_locator(mdates.HourLocator(interval=6))
plt.xticks(rotation=30, ha="right")

plt.tight_layout()
plt.savefig("/Users/mm25873/Desktop/passiv/graphs_output/passiv_results.png", dpi=150, bbox_inches="tight")
plt.show()
print("Plot saved to passiv_results.png")

dts = [datetime.fromisoformat(t.replace("Z", "+00:00")) for t in data["real_dt"]]
duration_hours = (dts[-1] - dts[0]).total_seconds() / 3600
print(f"Data covers {duration_hours:.1f} hours ({len(dts)} timesteps)")