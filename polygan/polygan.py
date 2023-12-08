# RDP applied
# Poly-GAN predictions are generated

import sys
import os
import cv2
import geojson
import rdp
import numpy as np
from skimage import draw
from skimage import io
from PIL import Image


sys.path.append(r"C:\Users\lasit\Desktop\DeepMapper\backend\libs")
import QuadKey.quadkey as quadkey

sys.path.append(r"C:\Users\lasit\Desktop\DeepMapper\backend\regularization")
from algorithms.perpendicular_distance import perpendicular_distance
from algorithms.utils import *

maxImageSize = 256 * 3

# save to .osm file
# save predicted change as geojson
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

def applyRDP(coords, rdp_save_path, feature_index, maxImageSize, quadKeyStr):
    l = len(coords)
    coords = coords.reshape((l,1,2))
    
    # rdp simplified coords 
    rdp_coords = rdp.rdp(coords, epsilon=0.9)
    rdp_coords = np.array(rdp_coords)
    print(f">> RDP simplified {l} coordinates to {len(rdp_coords)} coordinates")
    
    pred_mask = np.zeros((maxImageSize, maxImageSize), image.dtype)
    _xs, _ys = map(list, zip(*rdp_coords[:,0,:].tolist()))
    r,c = draw.polygon(_xs, _ys, (maxImageSize, maxImageSize))
    pred_mask[c,r] = 255
    io.imsave(os.path.join(rdp_save_path, f"{quadKeyStr}_{feature_index}.png"), pred_mask, check_contrast=False)
    return rdp_coords

def combine_images(image_list, dir, output="test.jpg"):
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
    new_im.save(dir +"/"+ output)
    print(f">>> Combined images saved to {output}")

def footprint2OSM(featureName, building_coords, tilePixel, qkRoot):
    # coords = np.array([i[0] for i in building_coords.tolist()])
    coords = np.array(building_coords)
    l = len(coords)
    coords = coords.reshape((l,1,2))
    
    version = 1.0
    generator = 'DeepMapper by TU Dublin GIS Research Group (c) 2021'
    osm_version = 0.6
    osm_xml = ""
    osm_xml+=f"<?xml version=\"{version}\" encoding=\"UTF-8\"?>\n"
    osm_xml+=f"<osm version=\"{osm_version}\" generator=\"{generator}\" >\n"
    idx = -1
    for pt in coords :
        geo = quadkey.TileSystem.pixel_to_geo( (pt[0,0]+tilePixel[0],pt[0,1]+tilePixel[1]),qkRoot.level)
        #https://wiki.openstreetmap.org/wiki/Node
        osm_xml+="\t<node id=\"{}\" lat=\"{}\" lon=\"{}\" />\n".format(idx,geo[0],geo[1])
        idx -= 1

    osm_xml+="\t<way id=\"{}\" visible=\"true\">\n".format(idx)
    idx = -1
    for pt in coords :
        osm_xml+="\t\t<nd ref=\"{}\" />\n".format(idx)
        idx -= 1
    osm_xml+="\t<nd ref=\"{}\" />\n".format(-1)
    osm_xml+="\t<tag k=\"{}\" v=\"{}\" />\n".format("building", "yes")
    osm_xml+="\t<tag k=\"{}\" v=\"{}\" />\n".format("building", featureName)
    # Add name here from Knowledge-base @lasithniro
    osm_xml+="\t</way>\n"
    osm_xml+="</osm>\n"
    return osm_xml


def getObject(image):
    # Read the image in grayscale
    img = cv2.imread(image, 0)
    # resize the image to maxImageSize
    img = cv2.resize(img, (maxImageSize, maxImageSize), interpolation=cv2.INTER_CUBIC)
    # Apply a binary threshold to the image
    ret, thresh = cv2.threshold(img, 127, 255, 0)
    # Find contours in the binary image
    contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    print(f"len(contours) => {len(contours)}")
    try:
        # Find the contour with the largest area
        max_contour = max(contours, key=cv2.contourArea)
        # Calculate the area of the largest contour
        area = cv2.contourArea(max_contour)
        if area >= 200: #12.65
            return max_contour
        else:
            return None
    except:
        return None

# apply perpendicular distance algorithm
path = r"C:\Users\lasit\Desktop\DeepMapper\frontend\DeepMapper-frontend\data\31f84dda-b941-4af8-9791-0902df614ca5\poly_gan\results\REG-GAN-01\test_latest\images"
def applyPerpendicularDistance(path, final_save_path):
    extension = "_fake_B.png"
    

    # filter out all the images that are ends with extension
    image_list = [file for file in os.listdir(path) if file.endswith(extension)]

    for image in image_list:
        imgID = image.split("_")[0]
        i = image.split("_")[1]
        qkRoot = quadkey.from_str(imgID)
        tilePixel = quadkey.TileSystem.geo_to_pixel(qkRoot.to_geo(), qkRoot.level)
        image_path = os.path.join(path, image)
        contour = getObject(image_path)
        if contour is not None:
            gan_polygon = cv2.approxPolyDP(contour, 0.01 * cv2.arcLength(contour, True), True)
            polygon = np.array([i[0] for i in gan_polygon.tolist()])
            mask,_ = perpendicular_distance(p=polygon, tolerance=5)
            simplified_polygon = polygon[mask]
            simplified_polygon = simplified_polygon.reshape((len(simplified_polygon),1,2))
            image2geojson(final_save_path, i, simplified_polygon, imgID, qkRoot, tilePixel)
