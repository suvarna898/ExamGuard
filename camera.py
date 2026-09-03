# #openCV open source computer vision library
# working on camera, images, videos, face detection, object detection, image processingand more. It is widely used in various applications such as robotics, surveillance, augmented reality, and autonomous vehicles.
# openCV does not take a photo itself, just it connects to your default webcam and receives continuously video frames and we shouls choose one frame to save as an image.
# python -m pip install opencv-python
# import cv2
# import os
# import datetime
# import numpy as np
# upload_FOLDER = "static/uploads"
# def capture_photo():
#     os.makedirs("static/uploads",exist_ok=True)
#     camera = cv2.VideoCapture(0) #(open camera) video capture is a method to open the default camera of your syster , here 0 defines the default camera, 1 defines the multiple cameras when we are plug in 
#     while True:
#         success,frame = camera.read() #here tells wheather the camera successfull give the frame

#         if not success:
#             camera.release() #stop the camera
#             cv2.destroyAllWindows()  #it closes the all window related to open cv
#             return None

#         cv2.imshow("capture photo",frame) #reads the camera shows photo
#         key=cv2.waitKey(1) #candidate keyboard events

#         if key==ord("s"):
#             filename = f"candidate{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg" #nameing convention
#             photo_path= os.path.join("static/uploads",filename) #here we are joining the photo path 
#             cv2.imwrite(photo_path,frame) # save the photo in exisiting folder
#             print("photo was captured")

#             camera.release()
#             cv2.destroyAllWindows()
#             return photo_path
#         elif key == ord("q"):
#             camera.release()  
#             cv2.destroyAllWindows()
#             return None

# path = capture_photo()
# if path:
#     print(f" photo save location{path}")
# else:
#     print("photo not captured")
# def capture_photo(image_data):
#     os.makedirs(upload_FOLDER, exist_ok=True)
#     image_arry=np.frombuffer(image_data, np.uint8)
#     image = cv2.imdecode(image_arry, cv2.IMREAD_COLOR)
#     if image is None:
#            return None
#     filename = f"candidate_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
#     photo_path = os.path.join("static/uploads", filename)
#     cv2.imwrite(photo_path, image)
#     return photo_path
import cv2
import os
import datetime
import numpy as np
UPLOAD_FOLDER = "static/uploads"
def capture_photo(image_data):
    os.makedirs(UPLOAD_FOLDER,exist_ok=True)
    image_arry=np.frombuffer(image_data,np.uint8)   #covert image bites into array
    img=cv2.imdecode(image_arry,cv2.IMREAD_COLOR)   #covert array into image frame
    if img is None:
        return None
    filename=(f"candidate{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.jpg")
    photo_path=os.path.join("static/uploads",filename)
    cv2.imwrite(photo_path,img) #here we are adding capature file with existing filename
    return photo_path     #saved a photo in existing file

    