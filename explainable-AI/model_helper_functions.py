import matplotlib.dates as mdates
import matplotlib.pyplot as plt


def get(S, n, key):
    """Get a state variable, converting non-numbers to None and padding to length n.
    
    Args:
        S (dict): "State" data from API return
        n (int): Length of data required (controls padding needed)
        key (str): State variable to extract 
    
    Return:
        cleaned (list): return extracted and cleaned data for specified variable
    """
    vals = S.get(key, [])
    cleaned = [v if isinstance(v, (int, float)) else None for v in vals]
    
    while len(cleaned) < n:
        cleaned.insert(0, None)  # Some of the data (power) are one item shorter, fix this
    return cleaned[:n]


def plot_temp_power(df, num_zones, axis_int=6, share_x=True, plot_tariff=True, z1_setpoints=None, z2_setpoints=None, setpoint_dts=None):
    """Plot temperature, power, and cost from the model calculations
    
    Args:
        df (DataFrame): model output data
        num_zones (int): number of zones used for model
        axis_int (int): interval for the x axis (defaults to 6 hours)
        share_x (bool): whether or not to have subfigures share x axis
        plot_tariff (bool): whether or not to plot tariff information
    """

    # --- Set up ---
    dts = df["Datetimes"]
    if plot_tariff:
        fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=share_x)
    else:
        fig, axes = plt.subplots(2, 1, figsize=(12, 6.5), sharex=share_x)
    # fig.suptitle("Passiv Optimisation Results", fontsize=14, fontweight="bold")

    # --- Panel 1: Temperatures ---
    ax = axes[0]
    ax.plot(dts, df["Room Temp Z1"], label="Room Temp Z1", color="#dc267f",    linewidth=1.5)
    if setpoint_dts is None:
        ax.plot(dts, df["Setpoint Z1"],  label="Setpoint Z1",  color="#dc267f",    linewidth=1, linestyle="-.")
    else:
        ax.plot(setpoint_dts, z1_setpoints,  label="Setpoint Z1",  color="#dc267f",    linewidth=1, linestyle="-.")
    
    if num_zones == 2:
        ax.plot(dts, df["Room Temp Z2"], label="Room Temp Z2", color="#ffb000", linewidth=1.5)
        if setpoint_dts is None:
            ax.plot(dts, df["Setpoint Z2"],  label="Setpoint Z2",  color="#ffb000",    linewidth=1, linestyle="--")
        else:
            ax.plot(setpoint_dts, z2_setpoints,  label="Setpoint Z2",  color="#ffb000", linewidth=1, linestyle="--")
    ax.plot(dts, df["External Temp"], label="External Temp", color="#631ff3", linewidth=1, linestyle="--")
    ax.set_ylabel("Temperature (°C)")
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=axis_int))

    # --- Panel 2: Heat pump power ---
    ax = axes[1]
    ax.plot(dts, df["Input Power"], label="HP Input Power",  color="#1589e8", linewidth=1.5)
    try:
        ax.plot(dts, df["Output Power"], label="HP Output Power", color="#1589e8", linewidth=1, linestyle="--")
    except KeyError:
        print("No output power")
    # ax.plot(dts, get("E_HW.hs1.heat"), label="HP Input Power HW",  color="tomato", linewidth=1.5)
    # ax.plot(dts, get("U_HW.hs1"), label="HP Output Power HW", color="tomato", linewidth=1, linestyle="--")
    ax.set_ylabel("Power (kW)")
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)


    ax.xaxis.set_major_locator(mdates.HourLocator(interval=axis_int))
    if not plot_tariff:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b %H:%M"))
        plt.xticks(rotation=30, ha="right")
    else:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))

    # --- Panel 3: Hot water tank + electricity cost ---
    if plot_tariff:
        ax = axes[2]
        # ax.plot(dts, df["Tank Temp"],   label="Tank Temp",   color="hotpink", linewidth=1.5)
        # ax.plot(dts, df["HW Setpoint"], label="HW Setpoint", color="hotpink", linewidth=1, linestyle="--")
        # ax.set_ylabel("Tank Temp (°C)")
        ax.grid(True, alpha=0.3)

        # ax2 = ax.twinx()
        ax.plot(dts, df["Elec Cost (p/kWh)"], label="Elec Cost (p/kWh)", color="#fe5100", linewidth=1.5, linestyle="-.")
        ax.set_ylabel("Elec Cost (p/kWh)", color="#fe5100")
        ax.tick_params(axis="y", labelcolor="#fe5100")

        # lines1, labels1 = ax.get_legend_handles_labels()
        # lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(fontsize=10)

        # X axis formatting
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b %H:%M"))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=axis_int))
        plt.xticks(rotation=30, ha="right")

    plt.tight_layout()
    # plt.savefig("/Users/mm25873/Desktop/passiv/graphs_output/passiv_results.png", dpi=150, bbox_inches="tight")
    plt.show()
    # print("Plot saved to passiv_results.png")

    duration_hours = (list(dts)[-1] - list(dts)[0]).total_seconds() / 3600
    print(f"Data covers {duration_hours:.1f} hours ({len(dts)} timesteps)")
