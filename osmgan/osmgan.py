import os
import sys
import glob
import skimage
import math
import csv
import cv2
import re
import geojson
import time


import numpy as np
import shapely.geometry as geometry
import shapely.affinity as affinity
import matplotlib.pyplot as plt
import scipy.optimize
from skimage import draw
from skimage import io
from scipy.ndimage.measurements import label
from PIL import Image
import datetime
import rdp

# Loading custom libraries
libs_path = os.path.join("..", "libs")
sys.path.append(libs_path)
import QuadKey.quadkey as quadkey

sys.path.append("..")
from crawlers.utils import find_files


DEBUG = False
show_images = False


def plot_figures(figures, nrows=1, ncols=1, figsize=(25, 25)):
    """Plot a dictionary of figures.

    Parameters
    ----------
    figures : <title, figure> dictionary
    ncols : number of columns of subplots wanted in the display
    nrows : number of rows of subplots wanted in the figure
    """
    fig, axeslist = plt.subplots(ncols=ncols, nrows=nrows, figsize=figsize)
    if len(figures) == 1:
        axeslist.imshow(figures[0], cmap=plt.gray())
        axeslist.set_title(0, fontsize=40)
        axeslist.set_axis_off()
    else:
        for ind, title in enumerate(figures):
            axeslist.ravel()[ind].imshow(figures[title], cmap=plt.gray())
            axeslist.ravel()[ind].set_title(title, fontsize=40)
            axeslist.ravel()[ind].set_axis_off()
    plt.tight_layout()  # optional


def show_image(path):
    plt.axis("off")
    pred_img = cv2.imread(path, 0)
    plt.imshow(pred_img, cmap="gray")
    # plt.close()


def getContours(image_path, min_area=250):
    image = cv2.imread(image_path, 0)
    maxImageSize = image.shape[0] * 3
    image = cv2.resize(
        image, (maxImageSize, maxImageSize), interpolation=cv2.INTER_CUBIC
    )

    blur = cv2.medianBlur(image, 5)
    thresh = cv2.threshold(blur, 180, 255, cv2.THRESH_BINARY)[1]
    cnts = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = cnts[0] if len(cnts) == 2 else cnts[1]
    true_cnts = []
    for i, c in enumerate(cnts):
        area = cv2.contourArea(c)
        if area > min_area:
            true_cnts.append(c)
    return true_cnts, image


def draw_contours(image, contours):
    # image = cv2.imread(image_path, 0)
    maxImageSize = image.shape[0]
    image = cv2.resize(
        image, (maxImageSize, maxImageSize), interpolation=cv2.INTER_CUBIC
    )
    imageNoMasks = np.copy(image)
    cnts_fig = {}
    for i, c in enumerate(contours):
        mask = np.zeros(image.shape, image.dtype)
        xs, ys = map(list, zip(*c[:, 0, :].tolist()))
        r, c = draw.polygon(xs, ys, (maxImageSize, maxImageSize))
        mask[c, r] = 255
        cnts_fig[i] = mask
        image = np.copy(imageNoMasks)
    plot_figures(figures=cnts_fig, nrows=1, ncols=len(cnts_fig))


def get_features(vector_db, filter=True, featureName="building", zoom=19):
    features = {}
    if filter:
        csv_files = find_files(vector_db, "csv")
    else:
        csv_files = vector_db
    for csv_file in csv_files:
        # print(f"Processing {csv_file}")
        if os.path.exists(csv_file):
            with open(csv_file, "rt") as csvfile:
                reader = csv.reader(csvfile, delimiter="\t")
                try:
                    points_1 = []
                    for row in reader:
                        latlot = (float(row[0]), float(row[1]))
                        pixel = quadkey.TileSystem.geo_to_pixel(latlot, zoom)
                        points_1.append(pixel)

                    polygon = geometry.Polygon(points_1)

                    feature = {"geometry": polygon, "filename": csv_file}

                    if (featureName in features) == False:
                        features[featureName] = []

                    features[featureName].append(feature)
                except:
                    print(f"Polygon not found!...{csvfile.split('/')[-1]}")
                    pass
        else:
            pass
    return features


def read_meta(metaFilePath):
    quadKeyStr = ""
    osmBuildings = []
    with open(metaFilePath) as metafile:
        quadKeyStr = metafile.readline()
        for line in metafile:
            if line.strip().endswith(".csv"):
                osmBuildings.append(line.strip().split("\\")[-1])
    return quadKeyStr.strip(), osmBuildings


def GetPredictionMask(image, predicted_buildings, i, maxImageSize):
    # maxImageSize = image.shape[0]*3
    pred_building = predicted_buildings[i]
    pred_mask = np.zeros((maxImageSize, maxImageSize), image.dtype)
    _xs, _ys = map(list, zip(*pred_building[:, 0, :].tolist()))
    r, c = draw.polygon(_xs, _ys, (maxImageSize, maxImageSize))
    pred_mask[c, r] = 1
    return pred_mask


def GetOsmMask(image, features, i, maxImageSize, tilePixel):
    # maxImageSize = image.shape[0]*3
    feature = features[i]
    original_mask = np.zeros((maxImageSize, maxImageSize), image.dtype)
    xs, ys = feature["geometry"].exterior.coords.xy
    xs = [x - tilePixel[0] for x in xs]
    ys = [y - tilePixel[1] for y in ys]
    original_mask.fill(0)
    rr, cc = draw.polygon(xs, ys, (maxImageSize, maxImageSize))
    original_mask[cc, rr] = 1
    return original_mask


def DrawTable(osm_features, predicted_buildings, table_vals, title_text):
    col_labels = [re.findall(r"\d+", x["filename"])[0] for x in osm_features]
    row_labels = [f"    {i}    " for i in range(0, len(predicted_buildings))]
    col_labels.append("total")
    ncol = len(col_labels)
    nrow = len(row_labels)

    norm = plt.Normalize(
        min(min(x) for x in table_vals) - 1, max(max(x) for x in table_vals) + 1
    )
    colours = plt.cm.Reds(norm(table_vals))

    the_table = plt.table(
        cellText=table_vals,
        rowLabels=row_labels,
        colLabels=col_labels,
        colWidths=[0.1 for x in col_labels],
        cellColours=colours,
        loc="center",
    )

    the_table.auto_set_font_size(False)
    the_table.set_fontsize(8)
    the_table.scale(3, 3)
    plt.subplots_adjust(left=0.2, bottom=0.2)
    ax = plt.gca()
    ax.get_xaxis().set_visible(False)
    ax.get_yaxis().set_visible(False)
    plt.box(on=None)
    #     plt.suptitle(title_text)
    plt.draw()


def combine_images(image_list, dir, output="test.jpg", resize=False):
    images = [Image.open(x) for x in image_list]
    images = [x.resize((600,600)) for x in images]
    widths, heights = zip(*(i.size for i in images))

    total_width = sum(widths)
    max_height = max(heights)

    new_im = Image.new('RGB', (total_width, max_height))

    x_offset = 0
    for im in images:
        new_im.paste(im, (x_offset,0))
        x_offset += im.size[0]
    
    if not output.endswith(".png"):
        output += ".png"
        
    new_im.save(dir +"/"+ output)
    print(f"[{datetime.datetime.now().strftime('%a %b %d %H:%M:%S %Y')}] [info] Combined images saved to {output}")


# def combine_images(image_list, out_dir, out_name, resize=True):
#     images = [Image.open(x) for x in image_list]
#     if resize:
#         images = [x.resize((600, 600)) for x in images]
#     widths, heights = zip(*(i.size for i in images))

#     total_width = sum(widths)
#     max_height = max(heights)

#     new_im = Image.new('P', (total_width, max_height))
#     if not out_name.endswith(".png"):
#         out_name += ".png"

#     print(f"[DEBUG]\tSaving {out_name}")

#     x_offset = 0
#     for im in images:
#         new_im.paste(im, (x_offset, 0))
#         x_offset += im.size[0]
#     new_im.save(out_dir + "/" + out_name)

#     for im in images:
#         im.close()

def image2geojson(data_path, feature_index, building_coords, quadKeyStr, qkRoot, tilePixel):
    coords = np.array([i[0] for i in building_coords.tolist()])
    l = len(coords)
    coords = coords.reshape((l,1,2))

    geo_tagged_coords = []
    for pt in coords:
            geo = quadkey.TileSystem.pixel_to_geo( (pt[0,0]+tilePixel[0],pt[0,1]+tilePixel[1]),qkRoot.level)
            #https://wiki.openstreetmap.org/wiki/Node
            geo_tagged_coords.append((geo[1],geo[0]))

    # Create a Polygon feature from the coordinates
    polygon = geojson.Polygon([geo_tagged_coords])
    # Create a FeatureCollection from the Polygon feature
    feature_collection = geojson.FeatureCollection([geojson.Feature(geometry=polygon)])
    jsonFileName = os.path.join(data_path, f'{quadKeyStr}_{feature_index}.geojson')
    # Save the FeatureCollection to a file
    with open(jsonFileName, "w") as f:
            geojson.dump(feature_collection, f)
    print(f"> {len(geo_tagged_coords)} coordinates saved to {quadKeyStr}_{feature_index}.geojson")
    return l

def change_detection(
    result_dir, coco_db, config, vector_db, reg_changes_save_path, reg_save_path, rdp_save_path
):

    featureName = config["name"]
    name = config["prediction"]["model_name"]
    pred_ext = config["prediction"]["pred_ext"]
    zoom = config["zoom"]
    min_area = config["prediction"]["min_area"]

    vector_db = os.path.join(vector_db, "building")

    # coco_db = config['coco_dataset']

    # result_dir = os.path.join(pix2pix_home, "results", name, "test_latest", "images")

    content = list(filter(lambda file: file.endswith(pred_ext), os.listdir(result_dir)))
    maxImageSize = 256 * 3

    for prediction in content:
        possible_changes = set()
        predictionID = prediction.split("_")[0]
        real_path = os.path.join(result_dir, prediction)
        if DEBUG:
            show_image(real_path)
        contours, image = getContours(real_path, min_area)
        predicted_buildings = contours

        if DEBUG:
            draw_contours(image, contours)

        # Find meta data file
        metadata_file = os.path.join(coco_db, predictionID, f"{predictionID}.txt")
        if not os.path.exists(metadata_file):
            print(f"{metadata_file} not found...")
            exit(0)
        else:
            print(f">>>> Processing {metadata_file}...")
            quadKeyStr, osmBuildings = read_meta(metadata_file)

            osmBuildings = list(
                map(lambda file: os.path.join(vector_db, file), osmBuildings)
            )
            qkRoot = quadkey.from_str(quadKeyStr)
            tilePixel = quadkey.TileSystem.geo_to_pixel(qkRoot.to_geo(), qkRoot.level)
            osmFeatures = get_features(osmBuildings, filter=False, zoom=zoom)
            
            if len(osmFeatures)==0:
                osm_features = []
            else:
                osm_features = osmFeatures[featureName]

            print(f"{len(osm_features) } features detected on OSM database!")
            print(f"{len(predicted_buildings)} Features detected on prediction image!")

            A = []
            for i in range(0, len(predicted_buildings)):
                pred_mask = GetPredictionMask(
                    image, predicted_buildings, i, maxImageSize
                )
                overlap_sum = 0
                B = []
                for j in range(0, len(osm_features)):
                    original_mask = GetOsmMask(
                        image, osm_features, j, maxImageSize, tilePixel
                    )
                    U = np.logical_and(pred_mask, original_mask)
                    overlap = (
                        np.sum(U)
                        / (np.sum(pred_mask) + np.sum(original_mask) - np.sum(U))
                    ) * 100
                    osmID = re.findall(r"\d+", osm_features[j]["filename"])[0]
                    if DEBUG == True:
                        print(i, osmID, overlap)
                    overlap_sum += overlap
                    B.append(round(overlap, 2))
                    if show_images == True:
                        imgs = {
                            "prediction mask": pred_mask,
                            "osm mask": original_mask,
                            "Union": U,
                        }
                        plot_figures(imgs, 1, 3)
                if overlap_sum == 0:
                    print(f"New feature found @ predcted object ID = {i}")
                    possible_changes.add(i)

                if DEBUG == True:
                    print("===")
                B.append(round(overlap_sum, 2))
                A.append(B)
            changes = {}
            for i, ch in enumerate(possible_changes):
                pred_building = predicted_buildings[ch]
                pred_mask = np.zeros((maxImageSize, maxImageSize), image.dtype)
                coords = np.array([i[0] for i in pred_building.tolist()])
                coords = coords.reshape((len(coords),1,2))
                # apply RDP algorithm to reduce the number of points
                rdp_coords = rdp.rdp(coords, epsilon=0.9)
                rdp_coords = np.array(rdp_coords)
                
                # saving geojson
                image2geojson(rdp_save_path, i, rdp_coords, quadKeyStr, qkRoot, tilePixel)


                print(f"{len(coords)} -> {len(rdp_coords)}")

                _xs, _ys = map(list, zip(*rdp_coords[:, 0, :].tolist()))
                pred_mask.fill(0)
                r, c = draw.polygon(
                    _xs, _ys, (maxImageSize, maxImageSize)
                )  # , clip=True)
                pred_mask[c, r] = 255
                io.imsave(f"{reg_changes_save_path}/{quadKeyStr}_{i}.png", pred_mask, check_contrast=False)
                changes[ch] = pred_mask
            # save image
            images = [i for i in os.listdir(reg_changes_save_path) if i.endswith(".png")]
            for _image in images:
                # find area of the white blob
                # print(_image)
                image = f"{reg_changes_save_path}/{_image}"
                # print("======================HERE======================")
                # print(image)
                # Load the image in grayscale
                img = cv2.imread(image, 0)
                # Apply a binary threshold to the image
                ret, thresh = cv2.threshold(img, 127, 255, 0)
                # Find contours in the binary image
                contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
                # Find the contour with the largest area
                max_contour = max(contours, key=cv2.contourArea)
                # Calculate the area of the largest contour
                area = cv2.contourArea(max_contour)
                if area >= 200: #12.65
                    image_list = [image, image]
                    combine_images(image_list, reg_save_path, _image, resize=False)
                    os.remove(image)

                # predict regularised mask

                # simplify the REG mask

            if DEBUG:
                plot_figures(changes, 1, len(changes))
                # DrawTable(osm_features=osm_features, predicted_buildings=predicted_buildings, table_vals=A, title_text='overlap score matrix for OSM and predicted features')
                plt.show()


# if __name__ == "__main__":
#     print("success...")
#     change_detection()
