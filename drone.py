import airsim
import math
import time
import cv2
import numpy as np
import time
from threading import Thread
import os
import boto3
import uuid
import asyncio
import argparse
import requests
import json
import pprint
from dotenv import load_dotenv
import sys

# Load the .env file
load_dotenv()

# Accessing variables
ACCESS_KEY = os.getenv('ACCESS_KEY')
SECRET_KEY = os.getenv('SECRET_KEY')
BUCKET_NAME = os.getenv('BUCKET_NAME')
APPLICATION_ID = os.getenv('APPLICATION_ID')
DATABASE_SECRET_KEY = os.getenv('DATABASE_SECRET_KEY')

# DATABASE ENDPOINT URL
ENDPOINT_URL = 'https://parseapi.back4app.com/classes/Drone'

# Construct the absolute path to the directory of this script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Use the absolute paths for the YOLO config and weight files
yolo_config_path = os.path.join(script_dir, "yolov3.cfg")
yolo_weights_path = os.path.join(script_dir, "yolov3.weights")
coco_names_path = os.path.join(script_dir, "coco.names")

# read class names from text file
classes = None
with open(coco_names_path, 'r') as f:
    classes = [line.strip() for line in f.readlines()]

# generate different colors for different classes 
COLORS = np.random.uniform(0, 255, size=(len(classes), 3))

def push_data(image, drone_id, status, people_found, coordinates):
    data = {
        'droneId': drone_id,
        'status': status,
        'peopleFound': people_found,
        'coordinates': coordinates,
        'droneImageUrl': image,  # Include the uploaded image URL
    }
    headers = {
        'X-Parse-Application-Id': APPLICATION_ID,
        'X-Parse-REST-API-Key': DATABASE_SECRET_KEY,
        'Content-Type': 'application/json'
    }
    response = requests.post(ENDPOINT_URL, headers=headers, data=json.dumps(data))
    if response.status_code == 201:
        print('Data pushed successfully')
    else:
        print(f'Error: {response.status_code}. Message: {response.text}')

def generate_random_name_uuid(extension='.jpg'):
    extension='.jpg'
    folder='images/'
    # Generate a random UUID and convert to a string
    random_name = str(uuid.uuid4())
    return folder + random_name + extension

# function to draw bounding box on the detected object with class name
def draw_bounding_box(img, class_id, confidence, x, y, x_plus_w, y_plus_h):
    label = str(classes[class_id])
    color = COLORS[class_id]
    cv2.rectangle(img, (x,y), (x_plus_w,y_plus_h), color, 2)
    cv2.putText(img, label, (x-10,y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

def detect_people(image):
    # Load YOLO
    net = cv2.dnn.readNet(yolo_weights_path, yolo_config_path)
    layer_names = net.getLayerNames()
    try:
        # Try to accommodate different OpenCV versions:
        # Older versions return indices in a flat array.
        output_layers = [layer_names[i - 1] for i in net.getUnconnectedOutLayers().flatten()]
    except AttributeError:
        # Fallback for other versions
        output_layers = [layer_names[i[0] - 1] for i in net.getUnconnectedOutLayers()]

    # Load COCO class names
    with open(coco_names_path, "r") as f:
        classes = [line.strip() for line in f.readlines()]

    # Assuming image is already loaded
    height, width, channels = image.shape

    # Detecting objects
    blob = cv2.dnn.blobFromImage(image, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
    net.setInput(blob)
    outs = net.forward(output_layers)

    # Information to hold detected persons
    class_ids = []
    confidences = []
    boxes = []
    for out in outs:
        for detection in out:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id]
            if confidence > 0.4 and class_id == 0:  # Filter by 'person' class
                # Object detected
                center_x = int(detection[0] * width)
                center_y = int(detection[1] * height)
                w = int(detection[2] * width)
                h = int(detection[3] * height)

                # Rectangle coordinates
                x = int(center_x - w / 2)
                y = int(center_y - h / 2)

                boxes.append([x, y, w, h])
                confidences.append(float(confidence))
                class_ids.append(class_id)

    indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)
    for i in range(len(boxes)):
        if i in indexes:
            x, y, w, h = boxes[i]
            cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)

    people_count = len(indexes)
    # Return modified image with detected people highlighted
    return image, people_count

async def compute_survey_path(x, z, boxsize, stripewidth):
    # now compute the survey path required to fill the box 
    path = []
    distance = 0
    while x < boxsize:
        distance += boxsize 
        path.append(airsim.Vector3r(x, boxsize, z))
        x += stripewidth            
        distance += stripewidth 
        path.append(airsim.Vector3r(x, boxsize, z))
        distance += boxsize 
        path.append(airsim.Vector3r(x, -boxsize, z)) 
        x += stripewidth  
        distance += stripewidth 
        path.append(airsim.Vector3r(x, -boxsize, z))
        distance += boxsize 
    return path, distance

def segmentation(client: airsim.MultirotorClient, vehicle_name: str):
    while True:
        # Capture image from the scene
        responses = client.simGetImages([airsim.ImageRequest("0", airsim.ImageType.Scene, False, False)], vehicle_name=vehicle_name)
        raw_image = responses[0].image_data_uint8
        # Capture an image in PNG format

        if raw_image is not None:
            # Convert raw image to a format compatible with OpenCV
            image = np.frombuffer(raw_image, dtype=np.uint8).reshape(responses[0].height, responses[0].width, -1)


            cv2.imshow('RAW', image)
            cv2.waitKey(1)  # Display the window for a short time

            # Detect people in the captured image
            detected_image, people_count = detect_people(image)

            # person detected
            if people_count > 0:
                # generate random file name
                filename = generate_random_name_uuid()
                # write image to file
                cv2.imwrite(filename, detected_image)

                # upload image to AWS S3 bucket
                try:
                    # create client
                    s3 = boto3.client('s3', aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY)
                    # upload file
                    s3.upload_file(filename, BUCKET_NAME, filename)
                    # format image URL
                    uploaded_image_url = f'https://{BUCKET_NAME}.s3.amazonaws.com/{filename}'
                    print('upload successful')
                except Exception as e:
                    print(f"Unexpected error during upload: {e}")

                # get coordinates from lidar sensor
                lidar_data = client.getLidarData(lidar_name=f'{vehicle_name}Lidar', vehicle_name=vehicle_name)
                print("\t\tlidar x position: %s" % (pprint.pformat(int(lidar_data.pose.position.x_val))))
                print("\t\tlidar y position: %s" % (pprint.pformat(int(lidar_data.pose.position.y_val))))
                coordinates = f'{int(lidar_data.pose.position.x_val)}, {int(lidar_data.pose.position.y_val)}'

                # push data to mobile app
                try:
                    push_data(uploaded_image_url, vehicle_name, 'Living', people_count, coordinates)
                except Exception as e:
                    print(f"Unexpected error during upload: {e}")

                print("Person detected!")
                # Show the image with detected people
                cv2.imshow('Detected People', detected_image)
                cv2.waitKey(1)  # Display the window for a short time
                
        time.sleep(0.25)  # Capture an image every second

def moveOnPath(client, velocity, vehicle_name, path, trip_time):
    client.moveOnPathAsync(path, velocity, trip_time, airsim.DrivetrainType.ForwardOnly, airsim.YawMode(False,0), velocity + (velocity/2), 1, vehicle_name=vehicle_name)

class SurveyNavigator:
    def __init__(self, args, vehicle_name):
        self.coords = args.coords
        self.velocity = args.speed
        self.stripewidth = args.stripewidth
        self.altitude = args.altitude
        self.vehicle_name = vehicle_name
        self.client = airsim.MultirotorClient()
        self.client.confirmConnection()
        self.client.enableApiControl(True, vehicle_name=vehicle_name)
        self.boxsize = self.calculate_dimensions()

    
    def fly_back_to_home(self):
        # stop threads
        print("flying back home")
        self.client.moveToPositionAsync(0, 0, self.altitude, self.velocity).join()
        
        if self.altitude < -5:
            print("descending")
            self.client.moveToPositionAsync(0, 0, -5, 2).join()

        print("landing...")
        self.client.landAsync().join()

        print("disarming.")
        self.client.armDisarm(False)

        exit()

    def calculate_dimensions(self):
        # Calculate the length and width of the survey area based on corner1_coords
        length = abs(self.coords[0])  # X dimension
        width = abs(self.coords[1])  # Y dimension
        # Optionally calculate the diagonal distance (boxsize) for other uses
        boxsize = math.sqrt(length ** 2 + width ** 2)
        return boxsize

    async def start(self):
        print('start')
            # print("arming the drone...")

        self.client.armDisarm(True, vehicle_name=self.vehicle_name)

        landed = self.client.getMultirotorState(vehicle_name=self.vehicle_name).landed_state
        if landed == airsim.LandedState.Landed:
            print("taking off...")
            self.client.takeoffAsync(vehicle_name=self.vehicle_name).join()

        landed = self.client.getMultirotorState(vehicle_name=self.vehicle_name).landed_state
        if landed == airsim.LandedState.Landed:
            print("takeoff failed - check Unreal message log for details")
            exit()

        # AirSim uses NED coordinates so negative axis is up.
        x = -self.boxsize
        z = -self.altitude

        print("climbing to altitude: " + str(self.altitude))
        self.client.moveToPositionAsync(0, 0, z, self.velocity, vehicle_name=self.vehicle_name).join()

        print("flying to first corner of survey box")
        self.client.moveToPositionAsync(x, -self.boxsize, z, self.velocity, vehicle_name=self.vehicle_name).join()

        # let it settle there a bit.
        self.client.hoverAsync(vehicle_name=self.vehicle_name).join()
        time.sleep(2)

        # after hovering we need to re-enabled api control for next leg of the trip
        self.client.enableApiControl(True, vehicle_name=self.vehicle_name)


        path, distance = await compute_survey_path(x=x, z=z, boxsize=self.boxsize, stripewidth=self.stripewidth)

        self.path = path
        
        print("starting survey, estimated distance is " + str(distance))
        trip_time = distance / self.velocity
        print("estimated survey time is " + str(trip_time))
        self.trip_time = trip_time

    def get_trip_time(self):
        return self.trip_time
    
    def survey(self):
        self.client.simSetTraceLine(color_rgba=(1, 0.722, 0, 1), thickness=70, vehicle_name=self.vehicle_name)
        thread_1 = Thread(target=segmentation, args=(self.client, self.vehicle_name,))
        thread_2 = Thread(target=moveOnPath, args=(self.client, self.velocity, self.vehicle_name, self.path, self.trip_time,))
        thread_1.start()
        thread_2.start()

# Running the asynchronous function
async def main():
    # Initialize the argument parser with a description
    arg_parser = argparse.ArgumentParser(description="Survey Navigator: Navigate a drone to survey an area defined between spawn point and a given corner.")
    arg_parser.add_argument("--speed", type=float, help="Speed of survey (in meters/second)", default=12)
    arg_parser.add_argument("--stripewidth", type=float, help="Stripe width of survey (in meters)", default=10)
    arg_parser.add_argument("--altitude", type=float, help="Altitude of survey (in positive meters)", default=8)
    arg_parser.add_argument("--coords", default=(45, -45, -12))
    args = arg_parser.parse_args()

    drone = SurveyNavigator(args, 'Drone1')
    # await drone to start
    await drone.start()
    # start drone surveying
    drone.survey()
    # fetch survey trip time
    trip_time = drone.get_trip_time()
    # await trip time
    await asyncio.sleep(trip_time)



# Python 3.7+
asyncio.run(main())

