import os
import cv2
import numpy as np
from imutils.object_detection import non_max_suppression


# Path to the input image
base_path = r"C:\Users\lasit\Desktop\DeepMapper\frontend\DeepMapper-frontend\data\e129c381-1086-4322-b2eb-ce84f442d3f0\coco_images"
iid = "004503"
image_path = os.path.join(base_path, iid,  f"{iid}.jpg")

# Load the input image
input_image = cv2.imread(image_path)
print(input_image.shape)
cv2.imshow('Input Image', input_image)

# Convert the input image to grayscale
gray_image = cv2.cvtColor(input_image, cv2.COLOR_BGR2GRAY)

# Create the template (100x100 black square)
template = cv2.imread('template.jpg')
W, H = template.shape[:2]
thresh = 0.9

gray_template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
cv2.imshow('Template', gray_template)

# Passing the image to matchTemplate method 
match = cv2.matchTemplate(image=gray_image, templ=gray_template, method=cv2.TM_CCOEFF_NORMED)

# Select rectangles with
# confidence greater than threshold
(y_points, x_points) = np.where(match >= thresh)
  
# initialize our list of bounding boxes
boxes = list()
  
# store co-ordinates of each bounding box
# we'll create a new list by looping
# through each pair of points
for (x, y) in zip(x_points, y_points):
    
    # update our list of boxes
    boxes.append((x, y, x + W, y + H))

# loop over the final bounding boxes
for (x1, y1, x2, y2) in boxes:
    
    # draw the bounding box on the image
    cv2.rectangle(gray_image, (x1, y1), (x2, y2),
                  (255, 0, 0), 3)
  
# Show the template and the final output
cv2.imshow("before NMS", gray_image)

# apply non-maxima suppression to the rectangles
# this will create a single bounding box
# boxes = non_max_suppression(np.array(boxes))
  
# # loop over the final bounding boxes
# for (x1, y1, x2, y2) in boxes:
    
#     # draw the bounding box on the image
#     cv2.rectangle(gray_image, (x1, y1), (x2, y2),
#                   (255, 0, 0), 3)
  
# # Show the template and the final output
# cv2.imshow("After NMS", gray_image)
cv2.waitKey(0)
  
# destroy all the windows 
# manually to be on the safe side
cv2.destroyAllWindows()

