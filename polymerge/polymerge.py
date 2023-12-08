import os
import geojson
import json
import shapely
import numpy as np
import geopandas as gpd
from shapely.geometry import shape, MultiPolygon
from shapely.ops import unary_union
import networkx as nx
from networkx.readwrite import json_graph



def PolyCollide(gj_1, gj_2):
    """
    This function takes two GeoJSON objects and returns True if they
    overlap.
    """
    x_shape = shape(gj_1['features'][0]['geometry'])
    y_shape = shape(gj_2['features'][0]['geometry'])
    return x_shape.intersects(y_shape)

"""
This code creates a graph, adds nodes for each file, and adds edges between 
nodes for files that have colliding objects. Then, it uses the 
connected_components function from networkx to find all the connected 
components in the graph, which represent groups of files with colliding 
objects. Finally, it prints out the groups.

Note that this approach can be slow for large numbers of files, 
since it checks every pair of files for collisions. 
If you have many files, you may want to consider a more efficient approach
that takes advantage of spatial indexing or other techniques to reduce 
the number of collision checks.


```
from rtree.index import Index

# create an R-tree index
idx = Index()

# add geometries to the index
for i, geom in enumerate(geometries):
    bbox = geom.bounds # get the bounding box of the geometry
    idx.insert(i, bbox) # insert the geometry ID and its bounding box into the index

# query the index for intersecting geometries
for i, geom in enumerate(geometries):
    bbox = geom.bounds
    results = idx.intersection(bbox, objects=True) # find the IDs of all intersecting geometries
    intersecting_geoms = [geometries[r.object] for r in results] # get the actual intersecting geometries
    # do something with the intersecting geometries...
```

"""

def createCollisionsGraph(files, save_path, session):
    # create a graph
    G = nx.Graph()

    # add nodes to the graph
    for file in files:
        G.add_node(file)

    # add edges to the graph
    for i in range(len(files)):
        for j in range(i+1, len(files)):
            file1, file2 = files[i], files[j]
            with open(file1) as f1, open(file2) as f2:
                data1, data2 = geojson.load(f1), geojson.load(f2)
                if PolyCollide(data1, data2):
                    G.add_edge(file1, file2)

    # find connected components
    groups = list(nx.connected_components(G))
    
    # Convert the graph to a JSON-compatible dictionary
    graph_dict = json_graph.node_link_data(G)

    # Save the dictionary to a JSON file
    with open(os.path.join(save_path, f'{session}.json'), 'w') as f:
        json.dump(graph_dict, f)
        f.close()
    return groups
    # print(groups)
    # print the groups
    # for i, group in enumerate(groups):
    #     print(f"Group {i+1}:")
    #     for file in group:
    #         print(file)
    #     print()

def PolyMerge(geo_files, save_path, save_name, save=True):
    shapes = []
    for geo_file in geo_files:
        with open(geo_file) as f:
            gj = geojson.load(f)
            f.close()
        shape = shapely.geometry.shape(gj['features'][0]['geometry'])
        shapes.append(shape)
    merged_shape = shapely.ops.unary_union(shapes)
    
    merged_geojson = {
        'type': 'FeatureCollection',
        'features': [
            {
                'type': 'Feature',
                'geometry': merged_shape.__geo_interface__,
                'properties': {}
            }
        ]
    }
    if save:
        with open(os.path.join(save_path, save_name), 'w') as f:
            geojson.dump(merged_geojson, f)
            f.close()
    return 1 if merged_shape.is_valid else 0
    
