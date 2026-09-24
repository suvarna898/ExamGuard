#for monitoring the face presence here we use a machine learning method called haar cascades
#this method id useful for detecting the object in the vedio or image
#haar cascades detector is a simple reactangular patterns called harrer features 
#image > simple check >more detailed checks > classifer >objected detected
#haar cascade looks for the patterns of light and the dark regions that resemble the object it trained to reconize.It is fast and easy to use .

import cv2

def start_face_monitoring():
    #Load face detector 
    face_cascade=cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    #open camera
    camera=cv2.VideoCapture(0)

    while True:
        success, frame=camera.read()
        if not success:
            print("Failed to capture frame from camera. Exiting...")
            break

        #convert frame to grayscale
        gray=cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        #detect faces
        faces=face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

        #draw rectangle around faces
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        #display the frame
        cv2.imshow("Face Monitoring", frame)

        #press 'q' to exit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    camera.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    start_face_monitoring()
   