import os
import sys
import argparse
from crawlers.utils  import contains_error

def filter_coco_image(coco_dir, gan_dir, error_dir):
    # make sure error_dir and success_dir exists
    if not os.path.exists(error_dir):
        os.makedirs(error_dir)
    
    for _dir in os.listdir(coco_dir):
        image_path = os.path.join(coco_dir, _dir, _dir + ".jpg")
        if contains_error(image_path):
            # move image to error dir
            try:
                os.rename(os.path.join(gan_dir, _dir+".jpg"), os.path.join(error_dir, _dir+".jpg"))
            except:
                print(f"Error moving {os.path.join(gan_dir, _dir+'.jpg')} to {os.path.join(error_dir, _dir+'.jpg')}")
        else:
            print(f"Skipping {os.path.join(gan_dir, _dir+'.jpg')}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--coco_dir", type=str, help="Path to coco images")
    # parser.add_argument("--gan_dir", type=str, help="Path to osm-gan images")
    # parser.add_argument("--error_dir", type=str, help="Path to error images")
    args = parser.parse_args()
    coco_dir = os.path.join(args.coco_dir, "coco_images")
    gan_dir = os.path.join(args.coco_dir, "osm-gan", "test")
    error_dir = os.path.join(args.coco_dir, "osm-gan", "error")

    filter_coco_image(coco_dir, gan_dir, error_dir)