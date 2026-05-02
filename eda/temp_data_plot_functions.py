import matplotlib.pyplot as plt
from matplotlib.dates import DayLocator, DateFormatter, HourLocator


colours = ["#dc267f", "#ffb000", "#1589e8", "#631ff3", "#fe5100"]  # - IBM colourblind palette
LINEWIDTH = 2.5

def set_up_figure(df, house_id, plot_weeks, week_to_plot, dates, start_index, end_index, i):
    """Set up figure with subplots for plotting
    
    Args:
        df (Dataframe): dataframe of a house to plot
        house_id (str): id of house ot plot
        plot_weeks (Bool): whether or not we are plotting weeks, if True: weeks if False: days
        week_to_plot (index): either index of week to plot data for (must be <num_weeks) OR None indicating all weeks should be plotted
        dates (array): dates from data between start_index and end_index
        start_index (int): index at start of data to begin plot from
        end_index (int): index at end of data to end plot at
        i (int): week index being used

    Returns:
        temp_plot (matplotlib subplot): subplot to plot room temperature variables
        hot_water_plot (matplotlib subplot): subplot to plot hot water variables
        tariff_plot (matplotlib subplot): subplot to plot tariff
    
    """
    fig, (temp_plot, hot_water_plot, tariff_plot) = plt.subplots(3, 1, sharex=True, height_ratios=[5, 5, 2], figsize=(15,6), layout="tight")
    plt.xlim(df["Datetime"][start_index],df["Datetime"][end_index])
    if plot_weeks:
        fig.suptitle(f"House: {df}, \
                Week index: {i} \
                Week commencing: {dates[start_index].day}/{dates[start_index].month}/{dates[start_index].year}")
        plt.xlabel("Date")
        
        ax = fig.gca()
        ax.xaxis.set_major_locator(DayLocator(interval=1))
        ax.xaxis.set_major_formatter(DateFormatter('%d/%m/%y'))
    else:
        fig.suptitle(f"House: {house_id}, \
        Week index: {week_to_plot} \
        Date: {dates[start_index].day}/{dates[start_index].month}/{dates[start_index].year}")
        plt.xlabel("Time of day")
        ax = fig.gca()
        ax.xaxis.set_major_locator(HourLocator(interval=1))
        ax.xaxis.set_major_formatter(DateFormatter('%H:%M'))
    return temp_plot, hot_water_plot, tariff_plot


def plot_room_temp(subfig, dates, room_temp_z1, user_setpoint_z1, room_temp_z2, user_setpoint_z2, flow_temp, ext_temp):
    """Heating plot
    
    Args:
        sub_fig (matplotlib subplot): subplot to plot room temperature variables
        dates (array): dates from data between start_index and end_index
        room_temp (array): room temperature values to plot
        user_setpoint (array): user setpoint values to plot
        flow_temp (array): flow temperature values to plot
        ext_temp (array): external temperature values to plot (None if not present in data)
    """
    # If no zone 2 - make setpoint and room temp lines different colours, and use same linestyle
    setpoint_z1_colour = colours[1] if room_temp_z2 is None else colours[0]
    setpoint_z1_ls = '-' if room_temp_z2 is None else '--'

    subfig.plot(dates, room_temp_z1, label="Room Z1", c=colours[0], lw=LINEWIDTH)
    subfig.plot(dates, user_setpoint_z1, label="User setpoint Z1", c=setpoint_z1_colour, ls=setpoint_z1_ls, lw=LINEWIDTH)

    if room_temp_z2 is not None:  # Plot zone 2
        subfig.plot(dates, room_temp_z2, label="Room Z2", c=colours[1], lw=LINEWIDTH)
        subfig.plot(dates, user_setpoint_z2, label="User setpoint Z2", c=colours[1], ls=':', lw=LINEWIDTH)

    #subfig.plot(dates, flow_temp, label="Flow", c=colours[2], lw=LINEWIDTH)
    if ext_temp is not None:
        subfig.plot(dates, ext_temp, label="External", c=colours[3], lw=LINEWIDTH, ls='--')
    subfig.grid(visible=True, lw=1.5)  #, axis="x")
    subfig.set_ylabel("Temp. (°C)")
    subfig.legend(bbox_to_anchor=(1.0, 1.0))


def plot_hot_water(sub_fig, dates, hot_water_temp, hot_water_setpoint, flow_temp):
    """Hot water plot
    
    Args:
        sub_fig (matplotlib subplot): subplot to plot hot water variables
        dates (array): dates from data to plot
        hot_water_temp (array): hot water temperature values to plot
        hot_water_setpoint (array): hot water setpoint values to plot
        flow_temp (array): flow temperature values to plot
    """
    sub_fig.plot(dates, hot_water_temp, label="Hot water", c=colours[0], lw=LINEWIDTH)
    sub_fig.plot(dates, hot_water_setpoint, label = "Hot water setpoint", c=colours[1], lw=LINEWIDTH)
    sub_fig.plot(dates, flow_temp, label="Flow", c=colours[2], lw=LINEWIDTH)
    sub_fig.grid(visible=True, lw=1.5)  #, axis="x")
    sub_fig.set_ylabel("Temp. (°C)")
    sub_fig.legend(bbox_to_anchor=(1.0, 1.0))


def plot_power(sub_fig, dates, input_power, output_power=None):
    """Hot water plot
    
    Args:
        sub_fig (matplotlib subplot): subplot to plot hot water variables
        dates (array): dates from data to plot
        hot_water_temp (array): hot water temperature values to plot
        hot_water_setpoint (array): hot water setpoint values to plot
        flow_temp (array): flow temperature values to plot
    """
    sub_fig.plot(dates, input_power, label="Input Power",  color="#1589e8", lw=LINEWIDTH)
    if output_power is not None:
        sub_fig.plot(dates, output_power, label="Output Power", color="#1589e8", linestyle="--", lw=LINEWIDTH)
    sub_fig.set_ylabel("Power (kW)")
    sub_fig.grid(visible=True, lw=1.5)  #, axis="x")


def plot_tariff(df, sub_fig, dates, tariff):
    """Tariff plot
    
    Args:
        df (Dataframe): dataframe of a house to plot
        sub_fig (matplotlib subplot): subplot to plot tariff
        dates (array): dates from data to plot
        tariff (array): tariff values from data to plot
    """
    sub_fig.plot(dates, tariff, color=colours[4], lw=LINEWIDTH)
    sub_fig.grid(visible=True, lw=1.5)  #, axis="x")
    sub_fig.set_ylabel("Tariff (p/kWh)")
    sub_fig.set_ylim(df["Tariff rate (p/kWh)"].min()-0.5, df["Tariff rate (p/kWh)"].max()+0.5)
