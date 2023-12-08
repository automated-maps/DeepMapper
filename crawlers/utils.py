# coding: utf-8

import yaml
import os, glob, sys, shutil, cv2
import logging
import numpy as np

# Loading custom libraries
libs_path = os.path.join("..", "..", "backend", "libs")

sys.path.append(libs_path)
import QuadKey.quadkey as quadkey


class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def contains_error(image_path):
    img = cv2.imread(image_path)
    image = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    contours, _ = cv2.findContours(image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(img, contours, -1, (0, 255, 0), 3)
    area = cv2.contourArea(contours[0])
    if area >= 588289.0:
        return False
    else:
        return True


def filter_coco_image(coco_dir, function="remove"):
    for _dir in os.listdir(coco_dir):
        image_path = os.path.join(coco_dir, _dir, _dir + ".jpg")
        if contains_error(image_path):
            if function == "remove":
                continue
                # TODO:
                    # maybe just move dir to another folder and put it back 
                # print(f"Removing {_dir}")
                # shutil.rmtree(os.path.join(coco_dir, _dir))
        else:
            print(f"Skipping {os.path.join(coco_dir, _dir)}")


def logger(file, lvl, message):
    logging.basicConfig(
        filename=file,
        filemode="a+",
        format="%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s",
        datefmt="%m/%d/%Y %I:%M:%S %p",
        level=logging.INFO,
    )

    options = {
        "DEBUG": lambda msg: logging.debug(msg),
        "INFO": lambda msg: logging.info(msg),
        "WARNING": lambda msg: logging.warning(msg),
        "ERROR": lambda msg: logging.error(msg),
        "CRITICAL": lambda msg: logging.critical(msg),
    }

    return options[lvl](message)


def copytree(src, dst, symlinks=False, ignore=None):
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, symlinks, ignore)
        else:
            shutil.copy2(s, d)


def load_config(file):
    """read yaml file and return the configerations
    # Arguments
        file: input  file
    """
    with open(file, "r") as data:
        try:
            raw_data = yaml.safe_load(data)
            # raw_data['database'] = os.path.join(raw_data['data_dir'] , raw_data['database'])
            # raw_data['image_database'] = os.path.join(raw_data['data_dir'] , raw_data['image_database'])
            # raw_data['dataset'] = os.path.join(raw_data['data_dir'] , raw_data['dataset'])
            # raw_data['coco_dataset'] = os.path.join(raw_data['data_dir'] , raw_data['coco_dataset'])
            return raw_data
        except yaml.YAMLError as exc:
            print(exc)
            exit(0)


def load_raw_config(file):
    """read yaml file and return the configerations
    # Arguments
        file: input  file
    """
    with open(file, "r") as data:
        try:
            raw_data = yaml.safe_load(data)
            return raw_data
        except yaml.YAMLError as exc:
            print(exc)
            exit(0)


def read_query(file):
    """read the overpass query and store in a variable
    # Arguments
        file: input query file
    """
    with open(file, "r", encoding="UTF8") as file:
        try:
            return file.read()
        except:
            exit(0)


def find_threshold(img_dir):
    # img_dir = "%s/%06d"%(train_dir,int(imgID))
    content = os.listdir(img_dir)
    pngs = list(filter(lambda png: png.endswith("png"), content))
    img1 = cv2.imread(img_dir + "/" + pngs[0], cv2.IMREAD_GRAYSCALE)
    for img in range(1, len(pngs)):
        img2 = cv2.imread(img_dir + "/" + pngs[img], cv2.IMREAD_GRAYSCALE)
        img1 = img1 + img2
    n_white_pix = np.sum(img1 == 255)
    m, n = img1.shape
    return n_white_pix / (m * n)


def find_files(path, suffix="csv"):
    result = glob.glob(f"{path}\*.{suffix}")
    return result


def find_quadkey(tile, x, y, zoom):
    pixel = (tile[0] + 256 * x, tile[1] + 256 * y)
    geo = quadkey.TileSystem.pixel_to_geo(pixel, zoom)
    pixel_quadkey = str(quadkey.from_geo(geo, zoom))
    return pixel_quadkey


def QuadKeyToTileXY(quadKey):
    tileX = 0
    tileY = 0
    quadKey = quadKey.strip()
    level = len(quadKey)

    i = level
    try:
        while i > 0:
            mask = 1 << (i - 1)
            if quadKey[level - i] == "1":
                tileX = tileX | mask
            elif quadKey[level - i] == "2":
                tileY = tileY | mask
            elif quadKey[level - i] == "3":
                tileX = tileX | mask
                tileY = tileY | mask
            i -= 1
    except:
        print("Invalid quad key")
    return tileX, tileY, level


def build_query(bbox):
    coords = bbox.replace('"', "").split(",")
    lat1, lon1, lat2, lon2 = map(float, coords)
    query = f"""[out:json][timeout:250];
(
    way["building"]({lat1},{lon1},{lat2},{lon2});
    relation["building"]({lat1},{lon1},{lat2},{lon2});
);
out body;
(._;>;);"""
    return query
