import time
import cv2
import imutils
import platform
import numpy as np
from threading import Thread
from queue import Queue

class RaonStreamer :
    
    def __init__(self ):
        
        if cv2.ocl.haveOpenCL() :
            cv2.ocl.setUseOpenCL(True)
        print('[raonzena] ', 'OpenCL : ', cv2.ocl.haveOpenCL())
            
        self.capture = None
        self.thread = None
        self.width = 540
        self.height = 360
        self.stat = False
        self.current_time = time.time()
        self.preview_time = time.time()
        self.sec = 0
        self.Q = Queue(maxsize=128)
        self.started = False
        self.stopFlag = False
        
    def run(self, src = 0) :
        
        self.stop()
        
        if platform.system() == 'Windows' :        
            self.capture = cv2.VideoCapture( src , cv2.CAP_DSHOW )
        
        else :
            self.capture = cv2.VideoCapture( src )
            
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        
        if self.thread is None :
            self.thread = Thread(target=self.update, args=())
            self.thread.daemon = False
            self.thread.start()
        
        self.started = True
    
    def stop(self):                
        self.started = True
        print('stop!')
        
        # if self.capture is not None :            
        #     self.capture.release()
        #     self.clear()
            
    def update(self):
                    
        while True:
            if self.started :
                (grabbed, frame) = self.capture.read()
                
                if grabbed : 
                    self.Q.put(frame)
                          
    def clear(self):        
        with self.Q.mutex:
            self.Q.queue.clear()
            
    def read(self):
        return self.Q.get()        

    def blank(self):        
        return np.ones(shape=[self.height, self.width, 3], dtype=np.uint8)
    
    def bytescode(self, userid = "", timer = 0):        
        if not self.capture.isOpened():            
            frame = self.blank()
        else :
            frame = imutils.resize(self.read(), width=int(self.width) )
            if timer % 10000 == 0:
                currentTime = int(time.time())
                fileName = "/data/raonzena_capture/" + userid + "/" + str(currentTime) + ".jpg"
                cv2.imwrite(fileName,frame)
            else:
                pass
            if self.stat :  
                cv2.rectangle( frame, (0,0), (120,30), (0,0,0), -1)
                fps = 'FPS : ' + str(self.fps())
                cv2.putText  ( frame, fps, (10,20), cv2.FONT_HERSHEY_PLAIN, 1, (0,0,255), 1, cv2.LINE_AA)            
            
        return cv2.imencode('.jpg', frame )[1].tobytes()
    
    def fps(self):
        
        self.current_time = time.time()
        self.sec = self.current_time - self.preview_time
        self.preview_time = self.current_time
        
        if self.sec > 0 :
            fps = round(1/(self.sec),1)            
        else :
            fps = 1
            
        return fps
                   
    def __exit__(self) :
        print( '* streamer class exit')
        self.capture.release()
