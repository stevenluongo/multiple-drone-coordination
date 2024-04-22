# Multiple Drone Coordination

## Quickstart Guide

## Demo

[![LINK](https://img.youtube.com/vi/V-0VrzgA3gU/0.jpg)](https://www.youtube.com/watch?v=V-0VrzgA3gU)

[Link](https://www.youtube.com/watch?v=V-0VrzgA3gU)

<br/>
<br/>
<br/> 


## Simulation (WINDOWS ONLY)

### Download link [here](https://drive.google.com/drive/folders/1TMvFTw8GzIdN1YOBVLKzeoZbFfwe0Hjy?usp=sharing)

Run this .exe file

![Capture2](https://github.com/stevenluongo/multiple-drone-coordination/assets/53283472/35ea7615-1505-472d-95e8-3f380d362516)

If it asks to download anything just click yes and continue, simulation should boot up and look like this:

![drone](https://github.com/stevenluongo/multiple-drone-coordination/assets/53283472/c71eef67-26bc-429c-9339-8215973ca693)

<br/>
<br/>
<br/> 


## Environment Variables

### Create .env file and add the following:

#### ACCESS_KEY
This is the AWS Access Key ID used to authenticate requests to your AWS account with administrative permissions to S3.
You can obtain this key by creating a new IAM user in your AWS Management Console with the necessary S3 permissions,
and then generating a new Access Key ID for that user.

#### SECRET_KEY
This is the secret key paired with your AWS Access Key ID, used to securely authenticate requests.
Obtain this secret key at the same time you create the Access Key ID in your AWS IAM dashboard.

#### BUCKET_NAME
This is the name of the S3 bucket where your files will be stored. Ensure the bucket is in the same region as your application to reduce latency.
Create a bucket in the S3 section of your AWS Management Console or use an existing bucket's name.
BUCKET_NAME=your_s3_bucket_name

#### APPLICATION_ID
This is the unique identifier for your application on Back4App, used to connect and interact with your cloud services.
You can find this ID in your application settings on the Back4App website after you have registered and created an application.


#### DATABASE_SECRET_KEY
This key is used to authenticate access to your database on Back4App. It ensures that only your application can interact with its data.
Similar to the Application ID, you can find this key in the settings of your application on the Back4App website.

<br/>
<br/>
<br/> 

## Drone Survey & Segmentation

### Running the Survey

Once the simulation environment is active, make sure to add in the environment variables and proceed by executing the `drone.py` file to initiate the drone's operations. Here’s what happens when you run the file:

1. **Start of Survey**: The drone will launch and begin the survey process automatically.
2. **Real-Time People Detection**: As the drone navigates through the environment, it will detect and analyze people in real time using its onboard sensors and algorithms.

Ensure that your system meets all hardware and software requirements for optimal performance during these tasks. This setup is designed to facilitate efficient data collection and processing in dynamic environments.


<br/>
<br/>
<br/> 

## Multiple Drones Setup

### Important: Resource Intensive Operation
**Please note**: Operating more than one drone simultaneously is very demanding on your system's GPU and CPU. Ensure your hardware is capable of handling this load before proceeding.

### Configuration Steps
To configure your system to manage up to four drones, follow these steps for each additional drone you wish to operate:

1. **Duplicate the Script**: Copy the `drone.py` file for each drone you want to add, making sure not to exceed a total of four drones.
  
2. **Modify the Drone Identifier**:
   In each duplicated file, find and update the line where the `SurveyNavigator` is initialized:
   ```python
   drone = SurveyNavigator(args, 'Drone1')
   ```
   Replace 'Drone1' with the appropriate drone name based on the number of the drone (i.e., Drone2, Drone3, or Drone4).

These steps will allow you to efficiently manage multiple drones, keeping in mind the significant resource requirements needed for smooth operation.
