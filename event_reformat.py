import ast
import pandas as pd
from pathlib import Path

# load event files
data_path = Path("PSTData5")
event_files = data_path.glob("*_Events_*.csv")

houses = {}
for file in event_files:
    house_id = file.stem.split("_")[0]
    houses[house_id] = pd.read_csv(file)
    houses[house_id]["Timestamp"] = pd.to_datetime(houses[house_id]["Timestamp"])
    
# reformat schedule in payload column to be a dictionary with hours and temp for each day of the week
def reformat_schedule(payload):
    
    data = ast.literal_eval(payload) # convert payload string to dict
    if data.get("type")!= "heating": # only use heating schedules
        return data
    
    # loop through each layer in payload dictionary data to find schedule
    week_schedule = []
    for layer in data.get("layers", []):
        if "week" in layer and "events" in layer["week"]:
            week_schedule = layer["week"]["events"]
            break
        
    # find schedule for each day of the week
    schedule = {}
    for day in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]:
        day_schedule = []
        for event in week_schedule:
            if event.get("day") == day:
                day_schedule.append(event)
        if not day_schedule:
            continue
        
        # get hours and temp for each day in schedule
        hours = []
        C = []
        for event in day_schedule:
            hours.append(int(event["time"].split(":")[0])) # extract hour from time string
            C.append(event.get("C", event.get("preset")))
        
        # reformat schedule for each day as dictionary with hours and temp    
        schedule[day] = {"hours": hours, "C": C}
        
    return schedule

# reformat override in payload column to be a dictionary with hours and temp for each override event
def get_override(payload):
    
    if isinstance(payload, str): # if payload is string, convert to dict
        data = ast.literal_eval(payload)
    else: # if payload is already a dict, use as is
        data = payload
    if data.get("type") != "heating": # only use heating overrides
        return None
    
    # loop through each layer in payload dictionary data to find override
    for layer in data.get("layers", []):
        if "override" in layer and "events" in layer["override"]:
            override_events = layer["override"]["events"]
            
            # get hours and temp for override
            hours = []
            C = []
            for event in override_events:
                hours.append(event.get("datetime"))
                C.append(event.get("C"))
                
            return {"hours": hours, "C": C}
        
    return None

# loop through each house and reformat schedule and override, then save to new csv file
Path("PSTData5_reformat").mkdir(exist_ok = True) # create new directory for reformatted files

for house_id, df_house in houses.items():
    df = df_house.copy()
    
    mask = df["Type"] == "Schedule" # only change 'Schedule' rows
    schedule_payloads = df.loc[mask, "Payload"]
    
    df.loc[mask,"Override"] = schedule_payloads.apply(get_override) # create new override column for 'Schedule' rows
    df.loc[mask, "Payload"] = schedule_payloads.apply(reformat_schedule) # reformat week schedule for 'Schedule' rows

    df.to_csv(f"PSTData5_reformat/{house_id}_reformat_events.csv", index = False) # save to new csv file
    
    print(f"{house_id} complete")
    
print("All houses reformatted")