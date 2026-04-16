import matplotlib.pyplot as plt
from matplotlib.dates import DayLocator, DateFormatter, HourLocator


colours = ["#dc267f", "#ffb000", "#1589e8", "#631ff3", "#fe5100"]  # - IBM colourblind palette

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


def plot_room_temp(subfig, dates, room_temp, user_setpoint, flow_temp, ext_temp):
    """Heating plot
    
    Args:
        sub_fig (matplotlib subplot): subplot to plot room temperature variables
        dates (array): dates from data between start_index and end_index
        room_temp (array): room temperature values to plot
        user_setpoint (array): user setpoint values to plot
        flow_temp (array): flow temperature values to plot
        ext_temp (array): external temperature values to plot (None if not present in data)
    """
    subfig.plot(dates, room_temp, label="Room temperature", c=colours[0])
    subfig.plot(dates, user_setpoint, label="User setpoint", c=colours[1])
    subfig.plot(dates, flow_temp, label="Flow temperature", c=colours[2])
    if ext_temp is not None:
        subfig.plot(dates, ext_temp, label="External temperature", c=colours[3])
    subfig.grid(visible=True, axis="x")
    subfig.set_ylabel("Temperature (°C)")
    subfig.legend(bbox_to_anchor=(1.0, 0.5))


def plot_hot_water(sub_fig, dates, hot_water_temp, hot_water_setpoint, flow_temp):
    """Hot water plot
    
    Args:
        sub_fig (matplotlib subplot): subplot to plot hot water variables
        dates (array): dates from data to plot
        hot_water_temp (array): hot water temperature values to plot
        hot_water_setpoint (array): hot water setpoint values to plot
        flow_temp (array): flow temperature values to plot
    """
    sub_fig.plot(dates, hot_water_temp, label="Hot water temperature",c=colours[0])
    sub_fig.plot(dates, hot_water_setpoint, label = "Hot water setpoint", c=colours[1])
    sub_fig.plot(dates, flow_temp, label="Flow temperature", c=colours[2])
    sub_fig.grid(visible=True, axis="x")
    sub_fig.set_ylabel("Temperature (°C)")
    sub_fig.legend(bbox_to_anchor=(1.0, 0.5))


def plot_tariff(df, sub_fig, dates, tariff):
    """Tariff plot
    
    Args:
        df (Dataframe): dataframe of a house to plot
        sub_fig (matplotlib subplot): subplot to plot tariff
        dates (array): dates from data to plot
        tariff (array): tariff values from data to plot
    """
    sub_fig.plot(dates, tariff, color=colours[4])
    sub_fig.grid(visible=True, axis="x")
    sub_fig.set_ylabel("Tariff rate (p/kWh)")
    sub_fig.set_ylim(df["Tariff rate (p/kWh)"].min()-0.5, df["Tariff rate (p/kWh)"].max()+0.5)
