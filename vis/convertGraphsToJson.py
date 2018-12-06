import csv, json
import networkx as nx
from networkx.readwrite import json_graph

with open("data", "r") as f:
    reader = csv.DictReader(f)
    json_all_graphs = {}
    for row in reader:
        graphs = row['graphs'].split("-")
        G = nx.parse_graph6(graphs[0])
        d = json_graph.node_link_data(G)
        cy_json = []
        for n in d["nodes"]:
            cy_json.append({"group": "nodes", "data": {"id": n["id"]}})

        for e in d["links"]:
            cy_json.append({"group": "edges", "data": {"source": e["source"], "target": e["target"]}})

        json_all_graphs[graphs[0]] = cy_json

with open('force/graphs/all.json', 'w') as jsonfile:
    json.dump(json_all_graphs, jsonfile)
