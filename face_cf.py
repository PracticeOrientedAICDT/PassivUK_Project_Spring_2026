import requests
import heapq

import numpy as np
import pandas as pd

from datetime import datetime, timedelta
from typing import Optional

def parse_dt(dt_str: str) -> datetime:
    """
    Parses an ISO datetime string, handling both 'Z' and '+00:00' suffixes.
    
    """
    if dt_str.endswith("Z"):
        dt_str = dt_str[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(dt_str)
    except ValueError:
        # Strip microseconds if present and retry
        dt_str = dt_str[:19] + dt_str[19:].replace(".", "")
        return datetime.fromisoformat(dt_str)
    
API_KEY = "your-key"

class APICallNode:
       def __init__(
        self,
        call_id: str,
        house_id: int,
        zone: int,
        call_datetime: datetime,
        outside_temp: float,
        start_hour: int,
        schedule_hours: list,
        schedule_temps: list,
        tariff_hours: list,
        tariff_costs: list,
        zone_start_temp: float,
        setpoint: list,
        room_temp: list,
        power_in: list,
        power_out: list,
        real_dt: list,
        override_happened: bool = False,
        override_time: Optional[datetime] = None,
        override_temp: Optional[float] = None
    ):
        self.call_id         = call_id
        self.house_id        = house_id
        self.zone            = zone
        self.call_datetime   = call_datetime
        self.outside_temp    = outside_temp
        self.start_hour      = start_hour
        self.schedule_hours  = schedule_hours
        self.schedule_temps  = schedule_temps
        self.tariff_hours    = tariff_hours
        self.tariff_costs    = tariff_costs
        self.zone_start_temp = zone_start_temp
        self.setpoint        = setpoint
        self.room_temp       = room_temp
        self.power_in        = power_in
        self.power_out       = power_out
        self.real_dt         = real_dt
        self.override_happened = override_happened
        self.override_time   = override_time
        self.override_temp   = override_temp

# Inputs that CANNOT change (not controllable via the API)
IMMUTABLE_INPUTS = [
    "outside_temp",   # weather — not controllable
    "tariff_hours",   # set by energy provider
    "tariff_costs",   # set by energy provider
]

# Inputs that CAN change (direct API inputs)
MUTABLE_INPUTS = [
    "schedule_hours",   
    "schedule_temps",   
    "start_hour",       
]

# Safety bounds — no CF can suggest values outside these
FEASIBILITY_BOUNDS = {
    "schedule_temps_min":  8.0,   # frost protection floor (°C)
    "schedule_temps_max":  25.0,  # safe upper limit (°C)
    "start_hour_shift_max": 2,    # max hours earlier/later to start
    "setpoint_step_max":   5.0,   # max °C change per CF step
}


# Minimum density — how many similar historical days must exist
# before FACE will suggest that transition
# (prevents suggesting something that has never happened before)
MIN_DENSITY_THRESHOLD = 3


def compute_node_distance(node_a: APICallNode, node_b: APICallNode) -> float:
    hour_diff = abs(node_a.start_hour - node_b.start_hour) / 24.0

    temps_a = [t for t in node_a.schedule_temps if isinstance(t, (int, float))]
    temps_b = [t for t in node_b.schedule_temps if isinstance(t, (int, float))]

    # Handle empty temperature lists (e.g. frost-only schedules)
    if not temps_a or not temps_b:
        return float('inf')  # can't compare, treat as maximally distant

    temp_a = np.mean(temps_a)
    temp_b = np.mean(temps_b)
    temp_diff = abs(temp_a - temp_b) / 25.0

    return hour_diff + temp_diff

def is_feasible_transition(
    node_a: APICallNode,
    node_b: APICallNode
) -> bool:
    """
    FACE's "conditions function" — checks if the transition
    from node_a to node_b is physically realistic.

    Returns True only if ALL of these hold:
        1. Temperature change is within safe bounds
        2. Start hour shift is within realistic range
        3. Immutable inputs are the same (can't change weather)
        4. No "frost" setpoints are being changed to real temps
           in an unsafe way
    """

    # Check 1: temperature bounds
    for temp in node_b.schedule_temps:
        if isinstance(temp, (int, float)):
            if temp < FEASIBILITY_BOUNDS["schedule_temps_min"]:
                return False   # below frost protection — unsafe
            if temp > FEASIBILITY_BOUNDS["schedule_temps_max"]:
                return False   # above safe upper limit

    # Check 2: start hour shift is realistic
    hour_shift = abs(node_a.start_hour - node_b.start_hour)
    if hour_shift > FEASIBILITY_BOUNDS["start_hour_shift_max"]:
        return False   # too large a shift — not realistic day-to-day

    # Check 3: setpoint step size
    temps_a = [t for t in node_a.schedule_temps if isinstance(t, (int, float))]
    temps_b = [t for t in node_b.schedule_temps if isinstance(t, (int, float))]
    if temps_a and temps_b:
        max_step = max(abs(a - b) for a, b in zip(temps_a, temps_b))
        if max_step > FEASIBILITY_BOUNDS["setpoint_step_max"]:
            return False   # too large a temperature jump

    return True

def compute_density(
    node: APICallNode,
    all_nodes: list,
    radius: float = 0.15
) -> int:
    """
    Counts how many historical nodes are "close" to this node.

    In FACE, high density = this region has been visited before
    = the suggestion is grounded in real historical behaviour.

    radius: how similar nodes need to be to count as "nearby"
            0.15 means roughly: within 1-2 hours start time
            AND within ~3°C setpoint difference
    """
    count = 0
    for other in all_nodes:
        if other.call_id != node.call_id:
            if compute_node_distance(node, other) <= radius:
                count += 1
    return count

def build_graph(
    nodes: list,
    similarity_threshold: float = 0.3
) -> dict:
    """
    Builds the density-weighted graph from all historical API calls.

    Each node = one logged API call
    Each edge = a feasible, realistic transition between two calls
    Edge weight = 1 / density (lower weight = more common transition = preferred by Dijkstra)

    INPUT:
        nodes : list of APICallNode objects
        (all your historical API calls)
        similarity_threshold: max distance for two nodes to be connected by an edge

    OUTPUT:
        graph: dict of {node_id: [(neighbour_id, weight)]}
    """

    graph = {node.call_id: [] for node in nodes}

    print(f"Building FACE graph from {len(nodes)} historical API calls...")

    for i, node_a in enumerate(nodes):
        for j, node_b in enumerate(nodes):
            if i == j:
                continue

            # Only connect nodes that are similar enough
            distance = compute_node_distance(node_a, node_b)
            if distance > similarity_threshold:
                continue

            # Only connect nodes where the transition is feasible
            if not is_feasible_transition(node_a, node_b):
                continue

            # Edge weight = 1 / density of node_b
            # High density node_b → low edge weight → preferred path
            # This is FACE's core insight: route through common states
            density_b = compute_density(node_b, nodes)
            if density_b < MIN_DENSITY_THRESHOLD:
                continue   # reject sparse regions — unrealistic CF

            edge_weight = 1.0 / (density_b + 1)   # +1 avoids division by zero

            graph[node_a.call_id].append((node_b.call_id, edge_weight))

    total_edges = sum(len(v) for v in graph.values())
    print(f"Graph built: {len(nodes)} nodes, {total_edges} edges")
    return graph

def dijkstra(
    graph: dict,
    source_id: str,
    target_ids: set
) -> tuple:
    """
    Dijkstra's Shortest Path First algorithm on the FACE graph.

    Finds the lowest-cost path from source_id (what happened —
    caused the override) to any node in target_ids (states where
    no override would have been needed).

    INPUT:
        graph      : dict from build_graph()
        source_id  : call_id of the node that caused the override
        target_ids : set of call_ids where Room_temp >= comfort_temp

    OUTPUT:
        distances  : dict of {node_id: shortest_distance_from_source}
        previous   : dict of {node_id: previous_node_id_on_path} used to reconstruct the path
    """

    # Initialise all distances to infinity
    distances = {node_id: float("inf") for node_id in graph}
    distances[source_id] = 0

    # Track which node came before each node on the shortest path
    previous = {node_id: None for node_id in graph}

    # Priority queue: (cost, node_id)
    # Always process the lowest-cost node next (greedy)
    priority_queue = [(0, source_id)]

    visited = set()

    while priority_queue:
        # Pop the node with the lowest current cost
        current_cost, current_id = heapq.heappop(priority_queue)

        if current_id in visited:
            continue
        visited.add(current_id)

        # Stop early if we've reached a target node
        if current_id in target_ids:
            break

        # Explore all neighbours of the current node
        for neighbour_id, edge_weight in graph.get(current_id, []):
            if neighbour_id in visited:
                continue

            # Cumulative cost to reach this neighbour via current node
            new_cost = current_cost + edge_weight

            # If this is cheaper than the known path, update it
            if new_cost < distances[neighbour_id]:
                distances[neighbour_id] = new_cost
                previous[neighbour_id] = current_id
                heapq.heappush(priority_queue, (new_cost, neighbour_id))

    return distances, previous

def reconstruct_path(
    previous: dict,
    source_id: str,
    target_id: str
) -> list:
    """
    Traces back through the 'previous' dict to reconstruct
    the full path from source to target.

    OUTPUT: list of node_ids from source → target
    """
    path = []
    current = target_id

    while current is not None:
        path.append(current)
        current = previous[current]

    path.reverse()

    if path[0] != source_id:
        return []   # no path found

    return path

def build_api_inputs_from_node(
    node: APICallNode,
    api_start_datetime: datetime
) -> dict:
    """
    Reconstructs the optim_inputs dict from an APICallNode
    so we can re-run the API with that node's parameters.

    """
    zone_key = f"zone_{node.zone}_heating_daily_schedule"

    optim_inputs = {
        "start_datetime": api_start_datetime.isoformat(),
        "num_zones": node.zone,
        zone_key: {
            "hours": node.schedule_hours,
            "C": node.schedule_temps
        },
        "tariff": {
            "hours": node.tariff_hours,
            "cost": node.tariff_costs
        },
        f"zone_{node.zone}_temperature": node.zone_start_temp,
    }

    return optim_inputs

def run_api_call(
    api_url: str,
    optim_inputs: dict
) -> dict:
    """
    Makes a single POST request to the optimisation model API.
    """
    response = requests.post(
        api_url,
        json=optim_inputs,
        headers={"X-API-Key": API_KEY}
    )
    response.raise_for_status()
    return response.json()

def get_real_room_temp_at_time(
    room_temp_df: pd.DataFrame,
    target_time: datetime,
    zone: int
) -> float:
    """
    Looks up the actual sensor reading closest to target_time.
    No model involved — pure sensor data.
    """
    col = f"Room temperature (Zone {zone}) (°C)"
    
    df = room_temp_df.dropna(subset=["Time (UTC)", col]).copy()
    df["Time (UTC)"] = pd.to_datetime(df["Time (UTC)"], utc=True)
    
    target = pd.Timestamp(target_time, tz="UTC")
    
    # Find the closest timestamp
    idx = (df["Time (UTC)"] - target).abs().idxmin()
    
    return float(df.loc[idx, col])


def get_energy_cost_from_node(node: APICallNode, up_to_hour: int) -> float:
    """
    Estimates the energy cost from the node's stored power data
    up to a given hour of day.
    """
    if not node.power_in or not node.real_dt:
        return 0.0

    total_cost = 0.0
    for i, dt_str in enumerate(node.real_dt):
        dt = parse_dt(dt_str).replace(tzinfo=None)
        if dt.hour > up_to_hour:
            break
        if i > 0:
            prev_dt = parse_dt(node.real_dt[i-1]).replace(tzinfo=None)
            timestep_h = (dt - prev_dt).total_seconds() / 3600
        else:
            timestep_h = 0.25

        # Use flat tariff if tariff data not available per-timestep
        tariff_rate = node.tariff_costs[0] if node.tariff_costs else 34
        cost = node.power_in[i] * timestep_h * tariff_rate / 100
        total_cost += cost

    return round(total_cost, 4)


def validate_cf_path_real_data(
    room_temp_df: pd.DataFrame,
    path_nodes: list,
    override_node: APICallNode,
    override_time: datetime,
    override_temp: float,
    zone: int,
    comfort_tolerance: float = 0.5
) -> list:
    """
    Validates each step in the FACE path using REAL sensor data

    For each node on the path:
        - That node represents a historical day
        - We look up what the room temp ACTUALLY was at the
          equivalent time of day on that historical day
        - If the real temp >= override_temp, the override
          would not have been needed on that day
    """
    results = []
    
    # What time of day did the override happen?
    override_hour = override_time.hour
    override_minute = override_time.minute

    # Skip the first node — it's the override day itself, which failed by definition
    nodes_to_validate = path_nodes[1:]

    if not nodes_to_validate:
        print("  No counterfactual nodes to validate (path only contains source)")
        return results

    for step_idx, node in enumerate(nodes_to_validate):
        print(f"\nValidating CF step {step_idx + 1}/{len(nodes_to_validate)}: "
              f"node {node.call_id}")

        # Construct the equivalent time on this historical day
        historical_date = node.call_datetime.date()
        equivalent_time = datetime(
            historical_date.year,
            historical_date.month,
            historical_date.day,
            override_hour,
            override_minute
        )

        # Look up REAL room temp from sensor data at that time
        try:
            real_temp = get_real_room_temp_at_time(
                room_temp_df, equivalent_time, zone
            )
        except Exception as e:
            print(f"  No sensor data for {equivalent_time}: {e}")
            continue

        # Look up real energy cost for that day
       
        period_cost = get_energy_cost_from_node(node, override_hour)
        
        if step_idx == 0:
            baseline_cost = period_cost

        extra_cost = period_cost - baseline_cost

        comfort_gap = override_temp - real_temp
        override_prevented = comfort_gap <= comfort_tolerance

        result = {
            "step":               step_idx + 1,
            "node_id":            node.call_id,
            "schedule_hours":     node.schedule_hours,
            "schedule_temps":     node.schedule_temps,
            "start_hour":         node.start_hour,
            "room_temp_achieved": round(real_temp, 2),
            "comfort_gap":        round(comfort_gap, 2),
            "override_prevented": override_prevented,
            "extra_cost_gbp":     round(extra_cost, 4),
            "cumulative_cost_gbp": round(period_cost - baseline_cost, 4),
            "data_source":        "real_sensor"
        }

        results.append(result)
        print(f"REAL room temp at {override_hour:02d}:{override_minute:02d} "
              f"on {historical_date}: {real_temp:.1f}°C "
              f"(wanted {override_temp}°C, gap={comfort_gap:.1f}°C)")
        print(f"Override prevented: {override_prevented}")

        if override_prevented:
            print(f" CF found at step {step_idx + 1} — stopping here")
            break

    return results

def generate_explanation(
    original_node: APICallNode,
    override_temp: float,
    override_time: datetime,
    cf_steps: list,
    zone: int
) -> str:
    if not cf_steps:
        return "No feasible counterfactual found in historical data."

    successful_step = next(
        (s for s in cf_steps if s["override_prevented"]), None
    )
    if not successful_step:
        successful_step = cf_steps[-1]

    original_setpoint = np.mean([
        t for t in original_node.schedule_temps
        if isinstance(t, (int, float))
    ])

    lines = []
    lines.append(
        f"WHY DID THE MODEL SET ZONE {zone} TO "
        f"{original_setpoint:.0f}°C AT {original_node.start_hour:02d}:00?"
    )
    lines.append(
        f"The model set {original_setpoint:.0f}°C because based on "
        f"previous similar days (outside temp ~{original_node.outside_temp:.0f}°C) "
        f"that was enough to reach your comfort level by "
        f"{override_time.strftime('%H:%M')}. "
        f"Your room was at {original_node.zone_start_temp:.1f}°C "
        f"when you overrode to {override_temp:.1f}°C."
    )

    lines.append("")
    lines.append("WHAT IS THE MINIMUM REALISTIC CHANGE?")

    for step in cf_steps:
        new_temps = [
            t for t in step["schedule_temps"]
            if isinstance(t, (int, float))
        ]
        new_temp_mean = np.mean(new_temps) if new_temps else original_setpoint

        change_desc = []

        # Start hour change
        if step["start_hour"] != original_node.start_hour:
            delta_h = original_node.start_hour - step["start_hour"]
            change_desc.append(
                f"start {abs(delta_h)} hour{'s' if abs(delta_h) > 1 else ''} "
                f"{'earlier' if delta_h > 0 else 'later'}"
            )

        # Temperature change — only mention if actually different
        if abs(new_temp_mean - original_setpoint) > 0.3:
            if new_temp_mean > original_setpoint:
                change_desc.append(
                    f"raise target from {original_setpoint:.0f}°C "
                    f"to {new_temp_mean:.0f}°C"
                )
            else:
                change_desc.append(
                    f"lower target from {original_setpoint:.0f}°C "
                    f"to {new_temp_mean:.0f}°C"
                )

        # Schedule structure change
        if step["schedule_hours"] != original_node.schedule_hours:
            if not change_desc:
                change_desc.append("use a different schedule structure")

        if not change_desc:
            change_desc = ["use similar settings (different day's conditions)"]

        cost_str = ""
        if abs(step["extra_cost_gbp"]) > 0.001:
            if step["extra_cost_gbp"] < 0:
                cost_str = f",saving £{abs(step['extra_cost_gbp']):.2f}"
            else:
                cost_str = f",costing an extra £{step['extra_cost_gbp']:.2f}"

        lines.append(
            f" Step {step['step']}: {' and '.join(change_desc)} "
            f"room was {step['room_temp_achieved']:.1f}°C on that day"
            f"{cost_str}"
        )
        if step["override_prevented"]:
            lines.append(
                f" This schedule would have prevented your override."
            )
            break

    if not any(s["override_prevented"] for s in cf_steps):
        lines.append("")
        lines.append(
            f"No historical schedule achieved {override_temp}°C "
            f"at this time of day. A larger schedule change may be needed "
            f"that goes beyond what has been tried before."
        )

    if successful_step and abs(successful_step["extra_cost_gbp"]) > 0.001:
        lines.append("")
        lines.append(
            f"Estimated cost difference: "
            f"£{abs(successful_step['cumulative_cost_gbp']):.2f} "
            f"{'extra' if successful_step['cumulative_cost_gbp'] > 0 else 'saved'} "
            f"per day when conditions are similar."
        )

    lines.append("")
    lines.append(
        "This suggestion is based on real sensor data from your home "
        "on a day with a similar schedule."
    )

    return "\n".join(lines)

def run_face(
    api_url: str,
    all_nodes: list,
    override_node_id: str,
    override_time: datetime,
    override_temp: float,
    zone: int,
    room_temp_df: pd.DataFrame,
    comfort_tolerance: float = 0.5
) -> dict:
    print("FACE COUNTERFACTUAL EXPLANATION")
    print(f"Override detected: zone {zone}, "
          f"time {override_time}, "
          f"user wanted {override_temp}°C")

    # Step 1: Find target nodes
    target_ids = set()
    for node in all_nodes:
        if node.call_id == override_node_id:
            continue
        if node.override_happened:
            continue
        max_room_temp = max(node.room_temp) if node.room_temp else 0
        if max_room_temp >= (override_temp - comfort_tolerance):
            target_ids.add(node.call_id)

    print(f"Found {len(target_ids)} target nodes "
          f"(days where {override_temp}°C was reached without override)")

    if not target_ids:
        return {
            "explanation": (
                f"No historical days found where the model reached "
                f"{override_temp}°C without user intervention. "
                "The schedule may need a significant structural change."
            ),
            "cf_steps": [],
            "path": [],
            "success": False
        }

    # Step 2: Build graph
    graph = build_graph(all_nodes)

    # Step 3: Run Dijkstra
    distances, previous = dijkstra(graph, override_node_id, target_ids)

    # Step 4: Try multiple targets, ranked by cost
    reachable_targets = {
        tid: distances[tid]
        for tid in target_ids
        if distances.get(tid, float("inf")) < float("inf")
    }

    if not reachable_targets:
        return {
            "explanation": (
                "No feasible path found through historical data. "
                "The override may be due to unusual conditions with no "
                "comparable historical precedent."
            ),
            "cf_steps": [],
            "path": [],
            "success": False
        }

    # Sort targets by distance (cheapest first)
    sorted_targets = sorted(reachable_targets.keys(),
                            key=lambda t: reachable_targets[t])

    node_lookup = {n.call_id: n for n in all_nodes}
    original_node = node_lookup[override_node_id]

    # Try up to 5 targets until we find one that works
    best_result = None

    for target_id in sorted_targets[:5]:
        path = reconstruct_path(previous, override_node_id, target_id)

        print(f"\nTrying path to {target_id} ({len(path)} steps)")
        print(f"Path: {''.join(path)}")

        path_nodes = [node_lookup[pid] for pid in path if pid in node_lookup]

        cf_steps = validate_cf_path_real_data(
            room_temp_df      = room_temp_df,
            path_nodes        = path_nodes,
            override_node     = original_node,
            override_time     = override_time,
            override_temp     = override_temp,
            zone              = zone,
            comfort_tolerance = comfort_tolerance
        )

        success = any(s["override_prevented"] for s in cf_steps)

        if success:
            explanation = generate_explanation(
                original_node, override_temp,
                override_time, cf_steps, zone
            )
            print("EXPLANATION FOR USER:")
            print(explanation)
            return {
                "explanation": explanation,
                "cf_steps": cf_steps,
                "path": path,
                "success": True
            }

        # Keep track of the best failed attempt
        if best_result is None or (cf_steps and
            cf_steps[-1]["comfort_gap"] < best_result["cf_steps"][-1]["comfort_gap"]):
            best_result = {
                "cf_steps": cf_steps,
                "path": path,
                "success": False
            }

    # No target worked — return the best attempt
    if best_result and best_result["cf_steps"]:
        explanation = generate_explanation(
            original_node, override_temp,
            override_time, best_result["cf_steps"], zone
        )
    else:
        explanation = (
            f"No historical schedule achieved {override_temp}°C "
            f"at this time of day under similar conditions."
        )
    print("EXPLANATION FOR USER:")
    print(explanation)

    return {
        "explanation": explanation,
        "cf_steps": best_result["cf_steps"] if best_result else [],
        "path": best_result["path"] if best_result else [],
        "success": False
    }

def get_room_temp_at_time(
    api_response: dict,
    target_time: datetime,
    zone: int
) -> float:
    """
    Extracts the room temperature at a specific time
    from the model
    """
    real_dt = [
        parse_dt(dt).replace(tzinfo=None)
        for dt in api_response["real_dt"]
    ]
    room_temps = api_response["State"][f"room_temp.z{zone}"]
 
    t = target_time.replace(tzinfo=None) if target_time.tzinfo else target_time
 
    closest_idx = min(
        range(len(real_dt)),
        key=lambda i: abs((real_dt[i] - t).total_seconds())
    )
 
    return room_temps[closest_idx]

def get_energy_cost_for_period(
    api_response: dict,
    start_time: datetime,
    end_time: datetime,
    zone: int
) -> float:
    """
    Calculates total energy cost (£) for a specific time window
    using the model's power and tariff outputs.
    """
    real_dt = [
        parse_dt(dt).replace(tzinfo=None)
        for dt in api_response["real_dt"]
    ]
    power_in = api_response["State"][f"E.hs1.heat.z{zone}"]
    tariff   = api_response["State"]["elec_cost"]
 
    s = start_time.replace(tzinfo=None) if start_time.tzinfo else start_time
    e = end_time.replace(tzinfo=None)   if end_time.tzinfo   else end_time
 
    total_cost = 0.0
    for i, dt in enumerate(real_dt):
        if s <= dt <= e:
            if i > 0:
                timestep_h = (dt - real_dt[i-1]).total_seconds() / 3600
            else:
                timestep_h = 0.25
 
            cost = power_in[i] * timestep_h * tariff[i] / 100
            total_cost += cost
 
    return round(total_cost, 4)

def real_time_override_check_with_face(
    api_url: str,
    zone: int,
    current_room_temp: float,
    outside_temp: float,
    current_schedule: dict,
    current_tariff: dict,
    override_temp: float,
    target_time: datetime,
    current_time: datetime,
    all_nodes: list = None,
    room_temp_df: pd.DataFrame = None,
    house_heat_loss_kw_per_c: float = 0.3,
    heat_pump_cop: float = 3.0
) -> dict:
    """
    Real-time override check enriched with FACE historical learning.
    this calculates the override cost directly from basic heat pump physics:

        energy_needed = heat_loss_rate * temp_gap * duration
        electrical_energy = energy_needed / COP
        cost = electrical_energy * tariff

    INPUT:
        api_url                : your model API URL
        zone                   : which zone (1 or 2)
        current_room_temp      : sensor reading right now (°C)
        outside_temp           : outside temp right now (°C)
        current_schedule       : currently active schedule
        current_tariff         : current tariff
        override_temp          : what the user wants to set (°C)
        target_time            : when the schedule was supposed to reach target
        current_time           : right now
        all_nodes              : historical APICallNodes (for FACE)
        room_temp_df           : sensor data DataFrame (for FACE)
        house_heat_loss_kw_per_c : heat loss coefficient (kW per °C difference
                                   between inside and outside). Typical UK house
                                   is 0.2-0.5. Default 0.3.
        heat_pump_cop          : coefficient of performance. Default 3.0.
    """

    print("REAL-TIME OVERRIDE CHECK")
    print(f"Room: {current_room_temp}°C | Outside: {outside_temp}°C")
    print(f"User wants: {override_temp}°C | Schedule target time: {target_time}")

    # PHYSICS-BASED COST ESTIMATE

    temp_gap = override_temp - current_room_temp
    hours_until_target = max(
        (target_time - current_time).total_seconds() / 3600, 0.25
    )
    tariff_rate = current_tariff["cost"][0]

    if temp_gap > 0:
        # Energy to raise the room temperature
        # Plus energy to maintain against heat loss during that period
        heat_loss_rate = house_heat_loss_kw_per_c * (override_temp - outside_temp)
        energy_to_raise_kwh = (house_heat_loss_kw_per_c * temp_gap * 2.0)
        energy_to_maintain_kwh = heat_loss_rate * hours_until_target
        total_thermal_kwh = energy_to_raise_kwh + energy_to_maintain_kwh
        electrical_kwh = total_thermal_kwh / heat_pump_cop
        override_cost = electrical_kwh * tariff_rate / 100

        # Baseline cost: just maintaining current temp
        baseline_heat_loss = house_heat_loss_kw_per_c * (current_room_temp - outside_temp)
        baseline_kwh = max(baseline_heat_loss * hours_until_target / heat_pump_cop, 0)
        baseline_cost = baseline_kwh * tariff_rate / 100

        extra_cost = override_cost - baseline_cost
    else:
        override_cost = 0.0
        baseline_cost = 0.0
        extra_cost = 0.0

    # Estimate what the room temp would be if they wait
    # Simple model: room drifts toward the schedule setpoint
    current_setpoint = None
    for i, h in enumerate(current_schedule["hours"]):
        if h <= current_time.hour:
            current_setpoint = current_schedule["C"][i]
    if current_setpoint is None:
        current_setpoint = current_schedule["C"][-1]

    # Room moves toward setpoint over time (simple exponential approach)
    time_constant = 2.0  # hours — how fast the room responds
    fraction = 1 - np.exp(-hours_until_target / time_constant)
    if isinstance(current_setpoint, (int, float)):
        predicted_temp = current_room_temp + fraction * (current_setpoint - current_room_temp)
    else:
        predicted_temp = current_room_temp

    print(f"Temperature gap: {temp_gap:.1f}°C")
    print(f"Hours until target: {hours_until_target:.1f}")
    print(f"Estimated override cost: £{override_cost:.2f}")
    print(f"Estimated baseline cost: £{baseline_cost:.2f}")
    print(f"Extra cost: £{extra_cost:.2f}")
    print(f"Predicted temp if wait: {predicted_temp:.1f}°C")

    # FACE HISTORICAL CONTEXT

    face_message = ""
    face_result = None
    similar_count = 0

    if all_nodes and room_temp_df is not None:
        similar_past_overrides = []
        for node in all_nodes:
            if not node.override_happened:
                continue
            if abs(node.start_hour - current_time.hour) > 2:
                continue
            if abs(node.override_temp - override_temp) > 2.0:
                continue
            similar_past_overrides.append(node)

        similar_count = len(similar_past_overrides)

        if similar_past_overrides:
            source_node = similar_past_overrides[-1]
            try:
                face_result = run_face(
                    api_url=api_url,
                    all_nodes=all_nodes,
                    override_node_id=source_node.call_id,
                    override_time=source_node.override_time,
                    override_temp=override_temp,
                    zone=zone,
                    room_temp_df=room_temp_df
                )
            except Exception as e:
                print(f"FACE analysis failed: {e}")
                face_result = None

            if face_result and face_result["success"]:
                best_step = next(
                    (s for s in face_result["cf_steps"]
                     if s["override_prevented"]), None
                )
                if best_step:
                    cf_temps = [t for t in best_step["schedule_temps"]
                                if isinstance(t, (int, float))]
                    cf_mean = np.mean(cf_temps) if cf_temps else 0
                    orig_temps = [t for t in source_node.schedule_temps
                                  if isinstance(t, (int, float))]
                    orig_mean = np.mean(orig_temps) if orig_temps else 0

                    change_parts = []
                    if abs(cf_mean - orig_mean) > 0.3:
                        direction = "raising" if cf_mean > orig_mean else "lowering"
                        change_parts.append(
                            f"{direction} the target from "
                            f"{orig_mean:.0f}°C to {cf_mean:.0f}°C"
                        )
                    if best_step["schedule_hours"] != source_node.schedule_hours:
                        change_parts.append("adjusting the schedule timing")

                    change_text = "and".join(change_parts) if change_parts else "a small schedule adjustment"

                    face_message = (
                        f"You've overridden like this {similar_count} time"
                        f"{'s' if similar_count != 1 else ''} before — "
                        f"{change_text} would prevent this in future."
                    )
            elif similar_count > 0:
                face_message = (
                    f"You've overridden to a similar temperature "
                    f"{similar_count} time{'s' if similar_count != 1 else ''} "
                    f"before at this time of day. Your schedule may need "
                    f"updating."
                )

    # BUILD THE USER-FACING MESSAGE

    if predicted_temp >= override_temp - 0.5:
        main_message = (
            f"Your room is currently {current_room_temp:.1f}°C and on track "
            f"to reach {predicted_temp:.1f}°C by "
            f"{target_time.strftime('%H:%M')}. "
            f"Overriding to {override_temp:.1f}°C now will cost an extra "
            f"£{extra_cost:.2f} compared to waiting."
        )
        recommendation = "wait"
    else:
        main_message = (
            f"Your room is currently {current_room_temp:.1f}°C. "
            f"The current schedule won't reach {override_temp:.1f}°C by "
            f"{target_time.strftime('%H:%M')} "
            f"(predicted: {predicted_temp:.1f}°C). "
            f"Boosting now will cost £{override_cost:.2f} "
            f"(£{extra_cost:.2f} extra)."
        )
        recommendation = "override_justified"

    full_message = main_message + face_message

    print(f"\n{'='*60}")
    print("MESSAGE FOR USER:")
    print(full_message)

    return {
        "message": full_message,
        "recommendation": recommendation,
        "current_room_temp": current_room_temp,
        "predicted_temp_if_wait": round(predicted_temp, 1),
        "override_temp": override_temp,
        "baseline_cost_gbp": round(baseline_cost, 2),
        "override_cost_gbp": round(override_cost, 2),
        "extra_cost_gbp": round(extra_cost, 2),
        "tariff_rate": tariff_rate,
        "similar_past_overrides": similar_count,
        "face_found_solution": face_result["success"] if face_result else False,
        "face_suggestion": face_result["cf_steps"] if face_result else [],
        "success": True
    }