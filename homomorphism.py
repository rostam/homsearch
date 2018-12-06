import networkx as nx
import homsearch
import csv
import itertools

# G = nx.petersen_graph()
# H = nx.complete_graph(3)
#
# homs = homsearch.find_homomorphisms(G, H)
# print(homs[0])

# all_homs = {}
# with open("v4.g6") as f1:
#     for line1 in f1:
#         G = nx.parse_graph6(line1.strip())
#         with open("v4.g6") as f2:
#             for line2 in f2:
#                 if line2 != line1:
#                     H = nx.parse_graph6(line2.strip())
#                     homs = homsearch.find_homomorphisms(G, H)
#                     if len(homs) > 0:
#                         all_homs[line1.strip()+","+line2.strip()] = homs[0]
#                     else:
#                         all_homs[line1.strip() + "," + line2.strip()] = []
all_homs = {}
with open("v4.g6") as f1:
    for line1 in f1:
        G = nx.parse_graph6(line1.strip())
        with open("v4.g6") as f2:
            for line2 in f2:
                if line2 != line1:
                    H = nx.parse_graph6(line2.strip())
                    homs = homsearch.find_homomorphisms(G, H, only_count=True)
                    all_homs[line1.strip() + "-" + line2.strip()] = str(homs)

for gh in all_homs:
    if all_homs[gh] == "0":
        GH = gh.split("-")
        G = nx.parse_graph6(GH[0])
        H = nx.parse_graph6(GH[1])
        edges = G.edges()
        found = False
        for e in edges:
            G = nx.parse_graph6(GH[0])
            G.remove_edge(e[0], e[1])
            homs = homsearch.find_homomorphisms(G, H, only_count=True)
            if homs != 0:
                found = True
                break
        if found:
            all_homs[gh] = all_homs[gh] + ",1"
        else:
            all_homs[gh] = all_homs[gh] + ",2"
    else:
        all_homs[gh] = all_homs[gh] + ",0"

for gh in all_homs:
    if all_homs[gh][-1] == "2":
        GH = gh.split("-")
        G = nx.parse_graph6(GH[0])
        H = nx.parse_graph6(GH[1])
        edges = G.edges()
        found = False
        two_edges = itertools.combinations(range(len(edges)), 2)
        for index_ee in two_edges:
            e1 = edges[index_ee[0]]
            e2 = edges[index_ee[1]]
            G = nx.parse_graph6(GH[0])
            G.remove_edge(e1[0], e1[1])
            G.remove_edge(e2[0], e2[1])
            homs = homsearch.find_homomorphisms(G, H, only_count=True)
            if homs != 0:
                found = True
                break
        if found:
            all_homs[gh] = all_homs[gh] + ",2"
        else:
            all_homs[gh] = all_homs[gh] + ",3"
    else:
        all_homs[gh] = all_homs[gh] + ",0"

with open('vis/data', 'w') as csvfile:
    fieldnames = ['graphs', 'HO', 'NH']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for graphs in all_homs:
        line_splitted = all_homs[graphs].split(",")
        writer.writerow({"graphs": graphs, "HO": line_splitted[0], "NH" : line_splitted[1]})