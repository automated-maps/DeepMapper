# First move to main directory
import os
import random
import shutil
import argparse
from tqdm import tqdm

def split_data(input_dir, train_dir, val_dir, split_ratio):
    """
    Splits images from input directory randomly into train and validation sets,
    and saves them to train and validation directories.
    
    Args:
    input_dir (str): Directory containing input images.
    train_dir (str): Directory to save training set images.
    val_dir (str): Directory to save validation set images.
    split_ratio (float): Ratio of validation images to total number of images.
    
    Returns:
    None
    """
    # Create train and validation directories if they don't exist
    if not os.path.exists(train_dir):
        os.makedirs(train_dir)
    if not os.path.exists(val_dir):
        os.makedirs(val_dir)
    
    # Get list of image file names in input directory
    file_names = os.listdir(input_dir)
    print(f"Number of images: {len(file_names)}")
    # Shuffle the file names randomly
    random.shuffle(file_names)
    
    # Calculate number of validation images based on split ratio
    num_val = int(len(file_names) * split_ratio)
    print(f"Number of validation images: {num_val}")
    print(f"Number of training images: {len(file_names) - num_val}")
    
    # Move first num_val images to validation directory

    for file_name in tqdm(file_names[:num_val]):
        src_path = os.path.join(input_dir, file_name)
        dst_path = os.path.join(val_dir, file_name)
        shutil.move(src_path, dst_path)
    
    # Move remaining images to training directory
    for file_name in tqdm(file_names[num_val:]):
        src_path = os.path.join(input_dir, file_name)
        dst_path = os.path.join(train_dir, file_name)
        shutil.move(src_path, dst_path)

if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", type=str, required=True, help="Directory containing input images")
    # parser.add_argument("--train_dir", type=str, required=True, help="Directory to save training set images")
    # parser.add_argument("--val_dir", type=str, required=True, help="Directory to save validation set images")
    parser.add_argument("--split_ratio", type=float, required=True, help="Ratio of validation images to total number of images")
    args = parser.parse_args()
    root_dir = args.input_dir #os.path.join(r"C:\Users\lasit\Desktop\DeepMapper\frontend\DeepMapper-frontend\data" , args.input_dir, "osm-gan")
    test_dir = os.path.join(root_dir, "test")
    train_dir = os.path.join(root_dir, "train")
    val_dir = os.path.join(root_dir, "val")
    print(f">>> Root directory: {root_dir}")
    print(f">>> Test directory: {test_dir}")
    print(f">>> Train directory: {train_dir}")
    print(f">>> Validation directory: {val_dir}")
    # ask for confirmation
    print(">>> Are you sure you want to split the data? (y/n)  ", end="")
    if input().lower() == "y":
        split_data(test_dir, train_dir, val_dir, args.split_ratio)
    else:
        print(">>> Exiting...")
        exit(0)
    