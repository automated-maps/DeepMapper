import os
import shutil
from polymerge import createCollisionsGraph, PolyMerge

data_dir = "final_footprints"
save_dir = "merged_footprints"
os.makedirs(save_dir, exist_ok=True)
files = [os.path.join(data_dir, f) for f in os.listdir(data_dir)]

collision_groups = createCollisionsGraph(files, "groups", "1")

for i, group in enumerate(collision_groups):
    print(f"Group {i+1}:")
    # if length of group is one, copy the file into save destination
    if len(group) == 1:
        print(list(group)[0])
        print()
        shutil.copy(list(group)[0], os.path.join(save_dir, f"group_{i+1}.geojson"))
        continue
    else:
        for file in group:
            print(file)
        print()
        PolyMerge(list(group), save_dir, f"group_{i+1}.geojson")