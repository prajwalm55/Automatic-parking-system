# importing libraries 
import numpy as np 
import cv2 
  
# creating object 
fgbg1 = cv2.bgsegm.createBackgroundSubtractorMOG();    

# capture frames from a camera  
cap = cv2.VideoCapture(1);
count=1
while(1): 
    # read frames 
    ret, bkg = cap.read();
    count+=1
    if count==20:
        break
import requests
import time
initial_frame_gray= cv2.cvtColor(bkg, cv2.COLOR_BGR2GRAY)
while(1): 
    # read frames 
    ret, img = cap.read(); 
    frame_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    difference = cv2.subtract( frame_gray,initial_frame_gray )
    # apply mask for background subtraction 
    
    ret, imB = cv2.threshold(difference , 200, 200, cv2.THRESH_BINARY)
    mask = cv2.morphologyEx(imB, cv2.MORPH_CLOSE, kernel=np.ones((8,8),dtype=np.uint8))

    nb_components, output, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
    sizes = stats[1:, -1]; nb_components = nb_components - 1
    min_size = 1000
    img2 = np.zeros((output.shape))
    for i in range(0, nb_components):
        if sizes[i] > min_size :
            img2[output == i + 1] = 255

    #cv2.imshow("Mask1", img2)
    img=img2
    img1=img2
    img[120:350,:]=0
    img[0:120,190:210]=0
    img[0:120,440:460]=0
    img[350:480,190:210]=0
    img[350:480,440:460]=0
    
    img = img.astype(np.uint8)
    nb_components, output, stats, centroids = cv2.connectedComponentsWithStats(img, connectivity=8)
##    if contours != None:
##        print(len(contours))
##    else:
##        print('0')
    print(nb_components-1)
    
    url = 'https://api.thingspeak.com/update?api_key=M64NHBJ8ZQMTD15B&field1='+str(nb_components-1)
    x = requests.post(url)
    print(x.text)
    time.sleep(.1)
    cv2.imshow('Original', frame_gray); 
    cv2.imshow('mask', img); 
    k = cv2.waitKey(30) & 0xff; 
    if k == 27: 
        break; 
  
cap.release(); 
cv2.destroyAllWindows()
