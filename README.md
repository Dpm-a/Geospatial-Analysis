
<a href="https://ibb.co/HzCRTvG"><img src="https://i.ibb.co/zRFCVcP/ww.png" alt="ww" border="0"></a>
# Geospatial Analytics
---

## Routing on road Networks Strategy

This repository contains the source code of the final project for the course "Geospatial Analytics" at the University of Pisa.

The aim of this work, shown in is to understand how different routing approaches affect vehicles and relative consumptions/emission.

<br>

Three methos will be investigated:

1.   `Shortest Path`
2.   `Fastest Path`
3.   `Duarouter Path`

The latter will eventually answer to the question: is that true that by simultaneously perturbing routing of a given amount of drivers thw total co2/NOX emissions, as well as fuel consumptions, will be reduced?

--- 

### Tools

The main mobility tools adopted in this project are:

*  [**SUMO**](https://pypi.org/project/sumolib/) which is traffic simulation package designed to handle large road networks and different modes of transport.

* [**Traci**](https://sumo.dlr.de/docs/TraCI.html): a Python controller that allows to control and manipulate at runtime any aspect of the traffic simulation, e.g., the internal data structures of SUMO; the cost to pay is an overhead.
With TraCi is possible to retrieve several simulations variables (e.g., vehicles' GPS positions, vehicles' emissions and so on). <br>

* **Duarouter**: a tool able to perturbe the fastest path using a randomisation parameter 𝑤 ∈ \[1, $+\infty$\), where 𝑤 = 1 means no randomisation (i.e., the fastest path), and the higher 𝑤, the more randomly perturbed the fastest.





