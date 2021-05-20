import face_recognition
import os
import io
import cv2
from picamera import PiCamera
from PIL import Image
import time
from datetime import datetime
import pytz
import numpy as np
from picar_4wd.servo import Servo
from picar_4wd.pwm import PWM
import socket
import json


# instantiate the lock as a servo controlled by pin 0
lock = Servo(PWM("P0"), offset=0)
lock.set_angle(0) # Start servo in "locked" position (servo angle 0)

def unlock(name):
    """ Unlock the lock and log who unlocked the lock and at what time """
    # rotate servo, aka the lock, 90 degrees
    lock.set_angle(-90)
    print(f'{name} Unlocked!')

    # Log the name of the person that unlocked it and the time it was unlocked
    with open('log.txt', 'a') as f:
        utc = pytz.utc.localize(datetime.utcnow())
        pst = utc.astimezone(pytz.timezone('America/Los_Angeles'))
        f.write(f'{name} - {pst.isoformat()}\n')

# Directory containg images of faces that have authorization to open lock
faces_dir = 'Known_Faces'

known_face_encodings = []
names_known_faces = []

# Go through all files in the Known_Faces directory
# The directory is organized into folders with teh same name as the authorized users.
# They contain photos of the face of the authorized user.
for name in os.listdir(faces_dir):
    for img_fn in os.listdir(f"{faces_dir}/{name}"):
        img = face_recognition.load_image_file(f"{faces_dir}/{name}/{img_fn}")
        
        # Append encoding of face in image of known face
        known_face_encodings.append(face_recognition.face_encodings(img)[0])
        names_known_faces.append(name)


HOST = "192.168.86.31" # IP address of your Raspberry Pi
PORT = 65432           # Port to listen on

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen() # Allow server to accept connections
    try:
        while True:
            with PiCamera(resolution=(640, 480), framerate=30) as camera:
                
                client, clientInfo = s.accept()
                print("server recv from: ", clientInfo)
                data = client.recv(1024) # receive 1024 Bytes of message in binary format
                
                # Decode data
                d = json.loads(data)
                is_locked = d['isLocked']
                print(f"lock status: {is_locked}")
                
                # If lock is unlocked
                if not is_locked and name:
                    # Unlock the lock
                    unlock(name)


                while is_locked:
                    
                    # Lock the lock. This will lock the lock if it was previously unlocked.
                    lock.set_angle(0)

                    # If the lock is locked run facial recognition
                    stream = io.BytesIO()
                    for _ in camera.capture_continuous(stream, format='jpeg', use_video_port=True):
                        stream.seek(0)
                        
                        # Get frame from stream buffer and convert to numpy array
                        buffer = np.frombuffer(stream.getvalue(), dtype=np.uint8)
                        frame = cv2.imdecode(buffer, 1)

                        start_time = time.monotonic()

                        # Return the bounding boxes for faces in frame.
                        # Using hog model because better at running on CPU
                        locations = face_recognition.face_locations(frame, model='hog')
                        
                        # Get the 128-dimensional face encoding for each face in the frame
                        encodings = face_recognition.face_encodings(frame, locations)

                        #for face_encoding_to_check, face_location in zip(encodings, locations): # Uncomment if you want to see boxes in camera preview
                        for face_encoding_to_check in encodings:
                            # Compare known faces to faces located in frame
                            results = face_recognition.compare_faces(known_face_encodings, face_encoding_to_check, tolerance=0.6)
                            name = None
                            # If known face is matched to a face in the frame
                            if results[0]:

                                # Clear encodings because it does not matter if there are multiple authorized individuals in frame
                                encodings = []
                                face_encoding_to_check = None

                                # Get the name of the known face that is in the frame
                                name = names_known_faces[results.index(True)]

                                data = json.dumps({
                                    'name': name
                                }).encode('utf-8')
                                client.sendall(data)

                        # Now that the name of the authorized user has been sent, we need to get the response from the
                        # user that will initiate the lock
                        client, clientInfo = s.accept()
                        print("server recv from: ", clientInfo)
                        data = client.recv(1024) # receive 1024 Bytes of message in binary format
                        
                        # Decode data
                        d = json.loads(data)
                        is_locked = d['isLocked']
                        print(f"lock status: {is_locked}")
                        
                        # unlock the lock and stop image recognition
                        if not is_locked:
                            # Unlock the lock
                            unlock(name)
                            break

                        elapsed_ms = (time.monotonic() - start_time) * 1000
                        print('%.1fms' % (elapsed_ms))

                        # Prepare for next frame
                        stream.seek(0)
                        stream.truncate()
    except: 
        print("Closing socket")
        client.close()
        s.close()
