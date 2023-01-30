import traci
import sys
import os
import subprocess
from utils import init_traci
from datetime import datetime
from skmob.tessellation.tilers import H3TessellationTiler



# function to initialize traci
def init_traci(config_file_path):

    if 'SUMO_HOME' in os.environ:
        tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
        sys.path.append(tools)
    else:
        sys.exit("please declare environment variable 'SUMO_HOME'")

    #Configuration
    sumo_binary = os.environ['SUMO_HOME'] + "/bin/sumo"

    sumo_cmd = [sumo_binary, "-c", config_file_path]

    traci.start(sumo_cmd)
    
    
    
def create_traffic_xml(departures: list,
                       arrivals: list,
                       fastest: bool = False,
                       duarouter_w: int = None) -> str:

    random.seed(0)
    traffic_type = "dua" if duarouter_w else "fast" if fastest else "short"
    departure_time = sorted([int(random.uniform(0,601)) for i in range(len(arrivals))])

    #constructing the xml file
    with open(f"traffic_demand_la_spezia_{traffic_type}.rou.xml", "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?> \n\n')
        f.write('<routes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/routes_file.xsd">\n\n')
        f.write(f'    <vType id="type1" length="4.00" maxSpeed="70.00" accel="2.6" decel="4.5" sigma="0.5"/> \n\n')

        for i in tqdm(range(len(departures)), desc="Writing XML"):
             
            if duarouter_w:
                shorth_path, _ = net.getOptimalPath(departures[i], arrivals[i], fastest = False)
                f.write(f'    <flow id="flow_{i}" begin="{departure_time[i]}" end="1000" number="1" from="{departures[i].getID()}" to="{arrivals[i].getID()}" type="type1" color="green"></flow>\n')
                continue

            if fastest == False:
                shorth_path, _ = net.getOptimalPath(departures[i], arrivals[i], fastest = False)
                path = " ".join([edge.getID() for edge in shorth_path])
                f.write(f'    <flow id="flow_{i}" begin="{departure_time[i]}" end="1000" number="1" from="{departures[i].getID()}" to="{arrivals[i].getID()}" via="{path}" type="type1" color="green"></flow>\n')
            else:
                fast_path , _ = net.getOptimalPath(departures[i], arrivals[i], fastest = True)
                path = " ".join([edge.getID() for edge in fast_path])
                f.write(f'    <flow id="flow_{i}" begin="{departure_time[i]}" end="1000" number="1" from="{departures[i].getID()}" to="{arrivals[i].getID()}" via="{path}" type="type1" color="green"></flow>\n')

        f.write("\n\n")
        f.write("</routes>")
            
    return f"traffic_demand_la_spezia_{traffic_type}.rou.xml"



# Config file editing
def create_sumocfg_file(net_file: str, route_file: str):

    today_date = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
    sumo_config = f"""<?xml version="1.0" encoding="UTF-8"?>

    <!-- generated on {today_date} by Eclipse SUMO sumo Version 1.15.0
    -->

    <configuration xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/sumoConfiguration.xsd">

        <input>
            <net-file value="{net_file}"/>
            <route-files value="{route_file}"/>
        </input>

        <time>
            <begin value="0"/>
            <end value="1000"/>
        </time>

    </configuration>"""

    #saving the configuration
    config_path = 'osm.sumocfg'
    with open(config_path, 'w') as f:
        f.write(sumo_config)
    
    #saving the view file as set in the config file
    with open('osm.view.xml', 'w') as f:
        f.write("""<viewsettings>
    <scheme name="real world"/>
    <delay value="20"/>
</viewsettings>
    """)
        
    return None



def duaroute_command_string(w: int, route_file: str) -> str:
    res = f"duarouter --route-files {route_file}"+\
        " --net-file la_spezia_net.xml"+\
        f" --output-file {perturbed_path_xml} --weights.random-factor {w}"
    return res



def run_duarouter(w: int, route_file: str):
    command_str = duaroute_command_string(w, route_file)
    process = subprocess.Popen( command_str, 
                                shell=True, 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.STDOUT)
    retval = process.wait()

    

def travel_consumption() -> pd.DataFrame:
    
    """
    Calculates the following measures produced a Traci simulation:
    
    ● Total distance traveled;
    ● Travel time;
    ● CO2 emissions;
    ● NOx emissions;
    ● Fuel consumption.
    
    Returns a dataframe with all the above informations.
    """

    init_traci("./osm.sumocfg")
    
    vehicles = dict()
    tot_co2, tot_distance, tot_nox, tot_fuel = 0, 0, 0, 0
    
    # simulate each step
    for step in tqdm(range(2500), desc="Running simulation"): # assuming to be above the finishing time

        traci.simulationStep()
        vehicle_list = traci.vehicle.getIDList()

        # values retrieval
        if vehicle_list:
            for v_id in vehicle_list:
                if v_id not in vehicles:
            
                    #initializing dictionary's record
                    vehicles[v_id] = {"co2_emissions" : 0, "distance": 0,
                                      "nox_emissions" : 0, "fuel_consumption" : 0, 
                                      "time": 0} 

                # Adding up each metric's amount to it's v_id reference in the dictionary
                
                # CO2 emissions [mg/s] 
                vehicles[v_id]["co2_emissions"] += traci.vehicle.getCO2Emission(v_id)
                
                # distance [meters]
                vehicles[v_id]["distance"] = traci.vehicle.getDistance(v_id)
                
                # NOX emissions [mg/s]
                vehicles[v_id]["nox_emissions"] += traci.vehicle.getNOxEmission(v_id)

                # Fuel consumption [ml/s]
                vehicles[v_id]["fuel_consumption"] += traci.vehicle.getFuelConsumption(v_id)
                vehicles[v_id]["time"] += 1

    # total time
    time = sum([vehicle["time"] for vehicle in vehicles.values()])

    for vehicle in vehicles.values():
        vehicle["tot_time"] = time
        tot_co2 += vehicle["co2_emissions"]
        tot_distance += vehicle["distance"]
        tot_nox += vehicle["nox_emissions"]
        tot_fuel += vehicle["fuel_consumption"]

    traci.close()

    return pd.DataFrame.from_dict(vehicles).T.reset_index(drop=True)


# To run traci
def run_traci(net_file: str, 
              departures: list,
              arrivals: list,
              fastest: bool = False,
              duarouter_w: int = None) -> pd.DataFrame:

    # Creating traffic demand file
    route_file_xml = create_traffic_xml(departures = departures, 
                                        arrivals = arrivals,
                                        fastest = fastest,
                                        duarouter_w = duarouter_w)

    if not duarouter_w:
        # Modifing SUMO .sumocfg file with the above XML
        create_sumocfg_file(net_file, route_file_xml)
    else:
        run_duarouter(duarouter_w, route_file_xml)
        create_sumocfg_file(net_file, perturbed_path_xml)

    try:
        travels_tot = travel_consumption()
    except:
        traci.close()
        travels_tot = travel_consumption()

    return travels_tot



def h3_resolution(resolution: int = 9) -> tuple:
    """
    Given the desired Resolution value, returns the min and max meters treshold w.r.t. that resolution
    """
    max_res = 763_194
    res = [i for i in range(1, max_res) if H3TessellationTiler()._meters_to_resolution(meters=i) == resolution]
    return min(res), max(res)