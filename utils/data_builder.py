# import crawlers from ../crawlers
import os
import argparse
import cv2
from skimage import io
from glob import glob
from PIL import Image
from tqdm import tqdm

def osm_gan_data_builder(coco_dataset, gan_dataset):
    dirs = glob(os.path.join(coco_dataset, "*"))
    for coco_dir in tqdm(dirs):
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # get session id
    parser.add_argument("--session", type=str, help="Session id")
    args = parser.parse_args()
    root_dir = os.path.join(r"C:\Users\lasit\Desktop\DeepMapper\frontend\DeepMapper-frontend\data" , args.session)
    coco_dir = os.path.join(root_dir, "coco_images")
    gan_dir = os.path.join(root_dir, "osm-gan")
    print(f"Building osm-gan dataset for {args.session}")
    print(f"Copying coco images from {coco_dir} to {gan_dir}")
    osm_gan_data_builder(coco_dir, gan_dir)