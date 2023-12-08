import os
import sys
import csv
import cv2
import numpy as np
import shapely.geometry as geometry
from skimage import draw
from skimage import io
from glob import glob
from PIL import Image

libs_path = os.path.join("..", "..", "backend", "libs")
sys.path.append(libs_path)
import QuadKey.quadkey as quadkey


def osm_gan_data_builder(coco_dataset, gan_dataset):
    dirs = glob(os.path.join(coco_dataset, "*"))
    for coco_dir in dirs:
        process_coco_images(coco_dir, gan_dataset)


def process_coco_images(coco_dir, gan_dataset):
    imageID = coco_dir.split("\\")[-1]
    content = os.listdir(coco_dir)
    pngs = list(filter(lambda png: png.endswith("png"), content))
    print(f"{len(pngs)} pngs in {coco_dir}")
    count = 1
    img1 = cv2.imread(coco_dir + "/" + pngs[0])
    for img in range(1, len(pngs)):
        img2 = cv2.imread(coco_dir + "/" + pngs[img])
        # img1 = cv2.bitwise_or(img2, img1, mask=None)
        img1 = img1 + img2
        count += 1
    io.imsave(f"{gan_dataset}/tmp.jpg", img1, quality=100)
    map_img = f"{gan_dataset}/tmp.jpg"
    sat_img = f"{coco_dir}/{imageID}.jpg"
    sat_and_map = [sat_img, map_img]
    combine_images(sat_and_map, gan_dataset, imageID)
    os.remove(map_img)


def combine_images(image_list, dir, output, resize=True):
    images = [Image.open(x) for x in image_list]
    if resize:
        images = [x.resize((600, 600)) for x in images]
    widths, heights = zip(*(i.size for i in images))

    total_width = sum(widths)
    max_height = max(heights)

    new_im = Image.new("RGB", (total_width, max_height))
    output += ".jpg"

    x_offset = 0
    for im in images:
        new_im.paste(im, (x_offset, 0))
        x_offset += im.size[0]
    new_im.save(dir + "/" + output)


def coco_builder(database, image_database, dataset, zoom):
    features = {}
    for featureDir in os.listdir(database):
        featureDirPath = os.path.join(database, featureDir)
        for fileName in os.listdir(featureDirPath):
            print(f">>> Processing {fileName}...")
            fullPath = os.path.join(database, featureDir, fileName)
            if fullPath.endswith(".csv"):
                with open(fullPath, "rt") as csvfile:
                    reader = csv.reader(csvfile, delimiter="\t")
                    try:
                        points_1 = []
                        for row in reader:
                            latlot = (float(row[0]), float(row[1]))
                            pixel = quadkey.TileSystem.geo_to_pixel(latlot, zoom)
                            points_1.append(pixel)

                        polygon = geometry.Polygon(points_1)

                        # if ( classDir != "baseball" or areaMeters > 2500) :
                        feature = {"geometry": polygon, "filename": fullPath}

                        if (featureDir in features) == False:
                            features[featureDir] = []

                        features[featureDir].append(feature)
                    except:
                        pass

    processedImageCount = 0
    for root, dirs, files in os.walk(image_database):
        for file in files:
            str_quadkey = os.path.splitext(file)[0]

            baseQuadKey = quadkey.from_str(str_quadkey)
            baseTilePixel = quadkey.TileSystem.geo_to_pixel(
                baseQuadKey.to_geo(), baseQuadKey.level
            )

            baseTileDir = os.path.split(root)[0]

            # stick the adjacent tiles together to make larger images up to max
            # image size.
            maxImageSize = 256 * 3
            maxTileCount = maxImageSize // 256
            count = 0
            image = np.zeros([maxImageSize, maxImageSize, 3], dtype=np.uint8)
            for x in range(maxTileCount):
                for y in range(maxTileCount):
                    pixel = (baseTilePixel[0] + 256 * x, baseTilePixel[1] + 256 * y)
                    geo = quadkey.TileSystem.pixel_to_geo(pixel, baseQuadKey.level)
                    qkey = quadkey.from_geo(geo, baseQuadKey.level)
                    qkStr = str(qkey)

                    tileCache = os.path.join(baseTileDir, qkStr[-3:])

                    tileName = "%s/%s.jpg" % (tileCache, qkStr)

                    if os.path.exists(tileName):
                        try:
                            image[
                                y * 256 : (y + 1) * 256, x * 256 : (x + 1) * 256, 0:3
                            ] = io.imread(tileName)
                            count += 1
                        except:
                            # try to get the tile again next time.
                            os.remove(tileName)

            points_1 = []
            points_1.append((baseTilePixel[0] + 0, baseTilePixel[1] + 0))
            points_1.append((baseTilePixel[0] + 0, baseTilePixel[1] + maxImageSize))
            points_1.append(
                (baseTilePixel[0] + maxImageSize, baseTilePixel[1] + maxImageSize)
            )
            points_1.append((baseTilePixel[0] + maxImageSize, baseTilePixel[1] + 0))

            bboxPolygon = geometry.Polygon(points_1)

            featureMask = np.zeros((maxImageSize, maxImageSize), dtype=np.uint8)
            totalFeatureCount = 0
            processedFiles = []
            for featureType in features:
                featureCount = 0
                for feature in features[featureType]:
                    if bboxPolygon.intersects(feature["geometry"]):
                        area = feature["geometry"].area
                        xs, ys = feature["geometry"].exterior.coords.xy
                        xs = [x - baseTilePixel[0] for x in xs]
                        ys = [y - baseTilePixel[1] for y in ys]
                        xsClipped = [min(max(x, 0), maxImageSize) for x in xs]
                        ysClipped = [min(max(y, 0), maxImageSize) for y in ys]
                        points2 = []
                        for i in range(len(xs)):
                            points2.append((xsClipped[i], ysClipped[i]))
                        clippedPolygon = geometry.Polygon(points2)
                        clippedArea = clippedPolygon.area
                        if area > 0:
                            if not (
                                os.path.exists(
                                    "%s/%06d" % (dataset, processedImageCount)
                                )
                            ):
                                os.mkdir("%s/%06d" % (dataset, processedImageCount))
                            featureMask.fill(0)
                            r, c = draw.polygon(xs, ys, (maxImageSize, maxImageSize))
                            featureMask[c, r] = 255
                            io.imsave(
                                "%s/%06d/%06d-%s-%d.png"
                                % (
                                    dataset,
                                    processedImageCount,
                                    processedImageCount,
                                    featureType,
                                    featureCount,
                                ),
                                featureMask,
                                check_contrast=False
                            )
                            processedFiles.append(feature["filename"])
                            featureCount += 1
                            totalFeatureCount += 1

            if totalFeatureCount > 0:
                io.imsave(
                    "%s/%06d/%06d.jpg"
                    % (dataset, processedImageCount, processedImageCount),
                    image,
                    quality=100,
                )

                with open(
                    "%s/%06d/%06d.txt"
                    % (dataset, processedImageCount, processedImageCount),
                    "wt",
                ) as txt:
                    txt.write("%s\n" % (str(baseQuadKey)))
                    txt.write("%0.8f,%0.8f\n" % baseQuadKey.to_geo())
                    for f in processedFiles:
                        txt.write("%s\n" % (f))

                processedImageCount += 1

                print(
                    "%s - %s - tiles %d - features %d"
                    % (os.path.join(root, file), str_quadkey, count, totalFeatureCount)
                )
