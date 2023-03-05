import sys
import os
import traci

import skmob
import random
import numpy as np
import pandas as pd
import geopandas as gpd

from datetime import datetime
import subprocess
from tqdm.notebook import tqdm
from numpy.random import choice



class Traci_simulation:

    def __init__(self, 
                 net,
                 n_veichles: int,
                 net_file: str, 
                 edge_list = list, 
                 random_seed: int = 42):
        
        self.n_veichles = n_veichles
        self.net = net
        self.net_file = net_file
        self.edge_list = edge_list
        self.fastest = None
        self.duarouter_w = None
        self.random_seed = random_seed
        self.departures = list()
        self.arrivals = list()
        self.xml_str = None
        self.perturbed_path_xml = 'traffic_demand_la_spezia_duarouter.rou.xml'


    def __repr__(self):

        var_dict = {}
        for var_name, var_value in vars(self).items():
            if not var_name.startswith("__"):  # ignore built-in attributes
                if type(var_value) == list: var_dict[var_name] = True
                else : var_dict[var_name] = var_value
                
        return f"Traci_simulation({var_dict})"


    def init_traci(self, 
                   config_file_path: str):

        if 'SUMO_HOME' in os.environ:
            tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
            sys.path.append(tools)
        else:
            sys.exit("please declare environment variable 'SUMO_HOME'")

        #Configuration
        sumo_binary = os.environ['SUMO_HOME'] + "/bin/sumo"

        sumo_cmd = [sumo_binary, "-c", config_file_path]

        traci.start(sumo_cmd)


    def create_traffic_demand(self,
                              geo_df, 
                              od_matrix: skmob.FlowDataFrame,
                              od_matrix_pd: pd.DataFrame):

        
        random.seed(self.random_seed)
        for _ in tqdm(range(self.n_veichles), desc = "Getting departures_arrivals"):
            path = None

            while not path:
                
                # Getting a random departure Edge
                departure = random.choice(self.edge_list)

                # Retrieving its Tile
                tile_departure = geo_df[geo_df["edge_id"] == departure.getID()]["tile_ID"].index[0]

                # List of probability regarding the selected Tile
                probability_list = np.array(od_matrix[od_matrix["origin"] == str(tile_departure)]["flow"])
                
                # Weighted (w.r.t. "flow" column) random choice among destination Tiles
                arrival_tile = int(random.choices(list(od_matrix[od_matrix_pd["origin"] == tile_departure]["destination"].values), weights = probability_list, k=1)[0])

                #getting an Edge 
                arrival = self.net.getEdge( random.sample( list(geo_df[geo_df["tile_ID"] == arrival_tile]["edge_id"].values) , 1)[0] )
                
                # Path Existance Check
                path, _ = self.net.getOptimalPath(departure, arrival)

            self.departures.append(departure)
            self.arrivals.append(arrival)


    def create_traffic_xml(self):

        random.seed(self.random_seed)

        # duarouter type if there's duarouter_w as input, fast if there is "fastest = True" as input else Short
        traffic_type = "dua" if self.duarouter_w else "fast" if self.fastest else "short"
        departure_time = sorted([int(random.uniform(0,601)) for i in range(len(self.arrivals))])

        #constructing the xml file
        with open(f"traffic_demand_la_spezia_{traffic_type}.rou.xml", "w") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?> \n\n')
            f.write('<routes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/routes_file.xsd">\n\n')
            f.write(f'    <vType id="type1" length="4.00" maxSpeed="70.00" accel="2.6" decel="4.5" sigma="0.5"/> \n\n')

            for i in tqdm(range(len(self.departures)), desc="Writing XML"):
                
                if self.duarouter_w:
                    shorth_path, _ = self.net.getOptimalPath(self.departures[i], self.arrivals[i], fastest = False)
                    f.write(f'    <flow id="flow_{i}" begin="{departure_time[i]}" end="1000" number="1" from="{self.departures[i].getID()}" to="{self.arrivals[i].getID()}" type="type1" color="green"></flow>\n')
                    continue

                if self.fastest == False:
                    shorth_path, _ = self.net.getOptimalPath(self.departures[i], self.arrivals[i], fastest = False)
                    path = " ".join([edge.getID() for edge in shorth_path])
                    f.write(f'    <flow id="flow_{i}" begin="{departure_time[i]}" end="1000" number="1" from="{self.departures[i].getID()}" to="{self.arrivals[i].getID()}" via="{path}" type="type1" color="green"></flow>\n')
                else:
                    fast_path , _ = self.net.getOptimalPath(self.departures[i], self.arrivals[i], fastest = True)
                    path = " ".join([edge.getID() for edge in fast_path])
                    f.write(f'    <flow id="flow_{i}" begin="{departure_time[i]}" end="1000" number="1" from="{self.departures[i].getID()}" to="{self.arrivals[i].getID()}" via="{path}" type="type1" color="green"></flow>\n')

            f.write("\n\n")
            f.write("</routes>")

        self.xml_str = f"traffic_demand_la_spezia_{traffic_type}.rou.xml"


    # Config file editing
    def create_sumocfg_file(self):

        today_date = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
        sumo_config = f"""<?xml version="1.0" encoding="UTF-8"?>

        <!-- generated on {today_date} by Eclipse SUMO sumo Version 1.15.0
        -->

        <configuration xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/sumoConfiguration.xsd">

            <input>
                <net-file value="{self.net_file}"/>
                <route-files value="{self.xml_str}"/>
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


    def run_duarouter(self):

        command_str = f"duarouter --route-files {self.xml_str}"+\
                        " --net-file la_spezia_net.xml"+\
                        f" --output-file {self.perturbed_path_xml} --weights.random-factor {self.duarouter_w}"

        process = subprocess.Popen( command_str, 
                                    shell=True, 
                                    stdout=subprocess.PIPE, 
                                    stderr=subprocess.STDOUT)
        retval = process.wait()



    def travel_consumption(self):
        
        """
        Calculates the following measures produced a Traci simulation:
        
        ● Total distance traveled;
        ● Travel time;
        ● CO2 emissions;
        ● NOx emissions;
        ● Fuel consumption.
        
        Returns a dataframe with all the above informations.
        """

        self.init_traci(config_file_path="./osm.sumocfg")
        
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


    def run_traci(self,
                 fastest: bool = False, 
                 duarouter_w: int = None) -> pd.DataFrame:
        
        self.fastest = fastest
        self.duarouter_w = duarouter_w

        # Creating traffic demand file
        self.create_traffic_xml()

        if not self.duarouter_w:
            # Modifing SUMO .sumocfg file with the above XML
            self.create_sumocfg_file()
        else:
            self.run_duarouter()
            self.create_sumocfg_file()

        try:
            travels_tot = self.travel_consumption()
        except:
            traci.close()
            travels_tot = self.travel_consumption()

        return travels_tot    
    
