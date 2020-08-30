# Import packages 
import os
import cv2
import numpy as np
import tensorflow as tf
import sys
import time
import json
from copy import deepcopy
from datetime import datetime,date, timedelta
import pickle
import threading, queue

from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

from playsound import playsound

from lib.tracker import Tracker
from lib.reports import *
from lib.proximity_detector import *

class ObjectDetection(QMainWindow):

    def __init__(self, *args, **kwargs):
        super(ObjectDetection, self).__init__(*args, **kwargs)

        self.DATA_FILE='data/DATA.bin'
        self.CONFIG_FILE='data/CONFIG.json'
        
        self.running=True
        self.opened_settings=False


        self.crowd_list={}
        self.alarm_time=1 # 1 second
        self.alarm_list=set()
        self.alarm_on=False
        
        self.t1=time.time()
        self.t2=time.time()
        self.t3=time.time()


        # Load records
        if os.path.exists(self.DATA_FILE):
            f = open(self.DATA_FILE, "rb")

            if True:
                self.DATA = pickle.load(f)
                if self.DATA!={}:
                    last=datetime.datetime.utcfromtimestamp(list(self.DATA.keys())[-1])
                    now=datetime.datetime.now()
                    tmp=[now.year,now.month,now.day,now.hour]
                    tmp2=[last.year,last.month,last.day,last.hour]
                    new=last
                    while tmp2!=tmp:
                        new= new + datetime.timedelta(seconds = 3600)
                        tmp2=[new.year,new.month,new.day,new.hour]
                        timestamp=new.timestamp()
                        timestamp=round(timestamp,6)
                        self.DATA[timestamp]={"NM":[],"M":[]}
            else:
                self.DATA={}
            f.close()
        else:
            self.DATA={}

        
        # Load settings
        with open(self.CONFIG_FILE) as json_file:
            self.CONFIGS = json.load(json_file)

        # Import settings from configuration file
        self.maxAbsences=self.CONFIGS["maxAbsences"]
        self.categories =self.CONFIGS["categories"]        
        self.colors =[tuple(x) for x in self.CONFIGS["colors"]]
        self.min_scores=self.CONFIGS["min_score"]
        self.border_pxl=self.CONFIGS["border"]
        self.models_path=self.CONFIGS["models_path"]
        self.models=os.listdir(self.models_path)
        self.models=['.'.join(x.split('.')[:-1]) for x in self.models]
        self.default_model=self.CONFIGS["default_model"]
        self.min_score=self.min_scores[self.default_model]
        self.path_to_ckpt = self.models_path+'\\'+self.default_model+'.pb'
        self.show_scores=bool(self.CONFIGS["show_scores"])
        self.show_IDs=bool(self.CONFIGS["show_IDs"])

        # Load counts from temp directory
        self.tmppath = 'C:\\Users\\{}\\AppData\\Local\\Temp'.format(os.getlogin()) + '\\COVIDEO_cnts.txt'
        if os.path.exists(self.tmppath):
            with open(self.tmppath, 'r') as file:
                data = file.readline().split(',')
                self.cntMTot = int(data[0])
                self.cntVTot = int(data[1])
        else:
            with open(self.tmppath, 'w+') as file:
                self.cntMTot=0
                self.cntVTot=0
                file.write('%d,%d' %(self.cntMTot, self.cntVTot))

        # Init an istance of a tracker for each class
        self.masked_tracker=Tracker(maxAbsences=self.maxAbsences, startID=(self.cntMTot+1))
        self.unmasked_tracker=Tracker(maxAbsences=self.maxAbsences, startID=(self.cntVTot+1))

        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.setWindowTitle('COVIDEO v3')
        self.setWindowIcon(QIcon('img\\Icon.jpg'))
        self.setGeometry(100, 100, 1280, 720)
        self.setStyleSheet("background-color:white")
        self.setMinimumWidth(1280)
        self.setMaximumWidth(1280)
        self.setMaximumHeight(720)
        self.setMinimumHeight(720)
        self.pic = QLabel(self)
        self.pic.setGeometry(0, 0, 1280, 720)
        self.logo = QLabel(self)
        self.logo.setGeometry(0, 690, 180, 30)
        self.logo.setStyleSheet("background-color:transparent;")
        self.logo.setPixmap(QPixmap('img\\logo_white.png'))
        self.logo.setScaledContents(True)
        self.textCM = QPushButton(self)

        self.textCM.setStyleSheet("background-color:black; color:"+('#%02x%02x%02x' % self.colors[1])+"; font:bold; border-style:outset;\
        border-width:1px; border-radius:5px")
        self.textCM.setText('Current Number of People '+self.categories[1]+': 0')
        self.textCM.setGeometry(1030, 5, 250, 15)
        self.textCV = QPushButton(self)

        self.textCV.setStyleSheet("background-color:black; color:"+('#%02x%02x%02x' % self.colors[0])+"; font:bold; border-style:outset;\
        border-width:1px; border-radius:5px")
        self.textCV.setText('Current Number of People '+self.categories[0]+': 0')
        self.textCV.setGeometry(1030, 22.5, 250, 15)
        self.textTM = QPushButton(self)

        self.textTM.setStyleSheet("background-color:black; color:"+('#%02x%02x%02x' % self.colors[1])+"; font:bold; border-style:outset;\
        border-width:1px; border-radius:5px")
        self.textTM.setText('Total Number of People '+self.categories[1]+': 0')
        self.textTM.setGeometry(1030, 40, 250, 15)
        self.textTV = QPushButton(self)

        self.textTV.setStyleSheet("background-color:black; color:"+('#%02x%02x%02x' % self.colors[0])+"; font:bold; border-style:outset;\
        border-width:1px; border-radius:5px")
        self.textTV.setText('Total Number of People '+self.categories[0]+': 0')
        self.textTV.setGeometry(1030, 57.5, 250, 15)                
        self.b1 = QPushButton(self)

        self.b1.setStyleSheet("QPushButton{background-color:black; color:red; font:bold; border-style:outset;\
        border-width:2px; border-radius:10px}"\
                         "QPushButton:hover{background-color:red; color:black; font:bold; border-style:outset;\
        border-width:2px; border-radius:10px}"\
                         "QPushButton:pressed{background-color:black; color:red; font:bold; border-style:outset;\
        border-width:2px; border-radius:10px}")
        
        self.b1.clicked.connect(self.reset_cnts)
        self.b1.setText('Reset Totals')
        self.b1.setGeometry(1175, 685, 100, 30)

        self.b2 = QPushButton(self)
        self.b2.setStyleSheet("QPushButton{background-color:black; color:white; font:bold; border-style:outset;\
        border-width:2px; border-radius:10px}"\
                         "QPushButton:hover{background-color:white; color:black; font:bold; border-style:outset;\
        border-width:2px; border-radius:10px}"\
                         "QPushButton:pressed{background-color:black; color:white; font:bold; border-style:outset;\
        border-width:2px; border-radius:10px}")
        self.b2.clicked.connect(self.change_settings)
        self.b2.setText('Settings')
        self.b2.setGeometry(1175, 650, 100, 30)

        self.b3 = QPushButton(self)
        self.b3.setStyleSheet("QPushButton{background-color:black; color:green; font:bold; border-style:outset;\
        border-width:2px; border-radius:10px}"\
                         "QPushButton:hover{background-color:green; color:black; font:bold; border-style:outset;\
        border-width:2px; border-radius:10px}"\
                         "QPushButton:pressed{background-color:black; color:green; font:bold; border-style:outset;\
        border-width:2px; border-radius:10px}")
        self.b3.clicked.connect(self.export)
        self.b3.setText('Export')
        self.b3.setGeometry(1175, 615, 100, 30)

        #Load categories
        self.category_index={1: {'id': 1, 'name': self.categories[0]}, 2: {'id': 2, 'name': self.categories[1]}}

        # Run main functions        
        self.load_model()
        self.define_io_tensors()
        self.video_setting()
        self.show()
        self.start()


    def closeEvent(self, event):
        # close app
        close = QMessageBox.question(self,"QUIT","Are you sure you want to stop the process?",QMessageBox.Yes | QMessageBox.No)
        if close == QMessageBox.Yes:
            self.save_data()
            self.video.release()
            cv2.destroyAllWindows()
            event.accept()
        else:
            event.ignore()
                
    def reset_cnts(self):
        # Reset data
        self.running=False
        ans = QMessageBox.question(self,"RESET","Are you sure you want to reset the total counts?",QMessageBox.Yes | QMessageBox.No)
        if ans == QMessageBox.Yes:
            self.masked_tracker.reset()
            self.unmasked_tracker.reset()
            self.cntMTot=0
            self.cntVTot=0
            f=open(self.DATA_FILE, 'wb')
            f.close()
            self.DATA={}            
        else:
            pass
        self.running=True
        self.start()

    def selectionchange(self):
        selected=self.comboBox.currentText()
        self.minscoreEdit.setText(str(self.min_scores[selected]*100))

    def change_settings(self):

        # Graphical interface for settings
 
        self.win = QWidget()
        self.win.setWindowIcon(QIcon('img\\Icon.jpg'))
        self.maxabsLabel = QLabel("Maximum number of absences:")
        self.maxabsEdit = QLineEdit()
        self.maxabsEdit.setText(str(self.maxAbsences))
        self.minscoreLabel = QLabel("Minimum score (%):")
        self.minscoreEdit = QLineEdit()
        self.minscoreEdit.setText(str(self.min_score*100))
        self.borderLabel = QLabel("Pixels of border:")
        self.borderEdit = QLineEdit()
        self.borderEdit.setText(str(self.border_pxl))
        self.modelLabel = QLabel("Model:")
        self.comboBox = QComboBox()
        self.comboBox.addItems(self.models)
        self.comboBox.setCurrentIndex(self.models.index(self.default_model))
        self.comboBox.currentIndexChanged.connect(self.selectionchange)

        self.colorLabe0 = QLabel(self.categories[0]+" color:")
        self.color0_button = QPushButton()
        self.color0_button.clicked.connect(lambda: self.get_color(0))
        self.color0_button.setStyleSheet("background-color:rgb"+str(self.colors[0]))

        self.colorLabel1 = QLabel(self.categories[1]+" color:")
        self.color1_button = QPushButton()        
        self.color1_button.clicked.connect(lambda: self.get_color(1))
        self.color1_button.setStyleSheet("background-color:rgb"+str(self.colors[1]))

        self.checkbox1 = QCheckBox("Show scores")
        self.checkbox1.setChecked(self.show_scores)
        self.checkbox2 = QCheckBox("Show IDs")
        self.checkbox2.setChecked(self.show_IDs)

        
        self.ok = QPushButton()
        self.ok.setText('Save')
        self.ok.clicked.connect(self.restart)

        self.Label1 = QLabel("- OBJECT DETECTION:")
        self.Label1.setStyleSheet("font-weight: bold")
        self.Label2 = QLabel("- TRACKING:")
        self.Label2.setStyleSheet("font-weight: bold")
        self.Label3 = QLabel("- DESIGN:")
        self.Label3.setStyleSheet("font-weight: bold")
        self.Label4 = QLabel("")

        # Put the widgets in a layout (now they start to appear):
        self.layout = QGridLayout()
        self.layout.addWidget(self.Label1, 0, 0)
        self.layout.addWidget(self.minscoreLabel, 1, 0)
        self.layout.addWidget(self.minscoreEdit, 1, 1)
        self.layout.addWidget(self.modelLabel, 2, 0)
        self.layout.addWidget(self.comboBox, 2, 1)
        self.layout.addWidget(self.Label2, 3, 0)
        self.layout.addWidget(self.maxabsLabel, 4, 0)
        self.layout.addWidget(self.maxabsEdit, 4, 1)

        self.layout.addWidget(self.borderLabel, 5, 0)
        self.layout.addWidget(self.borderEdit, 5, 1)
        self.layout.addWidget(self.Label3, 6, 0)
        self.layout.addWidget(self.colorLabe0, 7, 0)
        self.layout.addWidget(self.color0_button, 7, 1)
        self.layout.addWidget(self.colorLabel1, 8, 0)
        self.layout.addWidget(self.color1_button, 8, 1)
        self.layout.addWidget(self.checkbox1, 9, 0)
        self.layout.addWidget(self.checkbox2, 9, 1)
        self.layout.addWidget(self.Label4, 10, 0)
        self.layout.addWidget(self.ok, 11, 1)
        self.win.setLayout(self.layout)
        self.win.setGeometry(100,100,300,300)
        self.win.setWindowTitle("Settings")
        self.tmp_colors=[deepcopy(x) for x in self.colors]
        self.win.show()

    def get_color(self,i):
        self.tmp_colors[i] = QColorDialog.getColor().getRgb()
        if i ==0:
            self.color0_button.setStyleSheet("background-color:rgb"+str(self.tmp_colors[i]))
        
        else:
            self.color1_button.setStyleSheet("background-color:rgb"+str(self.tmp_colors[i]))
           
       


    def restart(self):
        self.running=False
        try:
            tmp=int(self.maxabsEdit.text())
            if tmp>=0:
                self.maxAbsences=tmp
                self.masked_tracker.maxAbsences=self.maxAbsences
                self.unmasked_tracker.maxAbsences=self.maxAbsences

        except:
            self.maxabsEdit.setText(str(self.maxAbsences))

        try:
            tmp=float(self.minscoreEdit.text())
            if tmp>=0 and tmp<=100:
                self.min_score=tmp/100
        except:
            self.minscoreEdit.setText(str(self.min_score*100))

        try:
            tmp=int(self.borderEdit.text())
            if tmp>=0:
                self.border_pxl=tmp
        except:
            self.maxabsEdit.setText(str(self.border_pxl))
        
        self.border_pxl=int(self.borderEdit.text())
        self.colors=[tuple(list(x)[:3]) for x in self.tmp_colors]

        self.textCM.setStyleSheet("background-color:black; color:"+('#%02x%02x%02x' % self.colors[1])+"; font:bold; border-style:outset;\
        border-width:1px; border-radius:5px")
        self.textCV.setStyleSheet("background-color:black; color:"+('#%02x%02x%02x' % self.colors[0])+"; font:bold; border-style:outset;\
        border-width:1px; border-radius:5px")
        self.textTM.setStyleSheet("background-color:black; color:"+('#%02x%02x%02x' % self.colors[1])+"; font:bold; border-style:outset;\
        border-width:1px; border-radius:5px")
        self.textTV.setStyleSheet("background-color:black; color:"+('#%02x%02x%02x' % self.colors[0])+"; font:bold; border-style:outset;\
        border-width:1px; border-radius:5px")

        if self.checkbox1.isChecked():
            self.show_scores=True
        else:
            self.show_scores=False

        if self.checkbox2.isChecked():
            self.show_IDs=True
        else:
            self.show_IDs=False
        
        if self.default_model!=self.comboBox.currentText():
            self.default_model=self.comboBox.currentText()
            self.path_to_ckpt = self.models_path+'\\'+self.default_model+'.pb'
            self.load_model()
            self.define_io_tensors()

        self.running=True
        self.start()

    def is_valid_filename(self,filename):
        invalid=['\\', '/', ':', '*', '?', '"', '<', '>', '|']
        for i in invalid:
            if i in filename:
                return False
        return True

    def export(self):
        # Generate and export statistics
        date=datetime.datetime.now()
        name = QFileDialog.getSaveFileName(self, 'Save File', str(date.strftime("%Y-%m-%d_%H-%M-%S")), "XLSX (*.xlsx)")
        if name[0]=='' or self.DATA=={}:
            pass
        
        elif self.is_valid_filename(name[0].split('/')[-1]):
            export_records(name[0], self.DATA)
        else:
            self.export()
            
        

    def load_model(self):
        # Load the Tensorflow model into memory.
        self.detection_graph = tf.Graph()
        with self.detection_graph.as_default():
            od_graph_def = tf.compat.v1.GraphDef()
            with tf.io.gfile.GFile(self.path_to_ckpt, 'rb') as fid:
                serialized_graph = fid.read()
                od_graph_def.ParseFromString(serialized_graph)
                tf.import_graph_def(od_graph_def, name='')

            self.sess = tf.compat.v1.Session(graph=self.detection_graph)

    def define_io_tensors(self):
        # Define input and output tensors (i.e. data) for the object detection classifier
        # Input tensor is the image
        self.image_tensor = self.detection_graph.get_tensor_by_name('image_tensor:0')
        # Output tensors are the detection boxes, scores, and classes
        # Each box represents a part of the image where a particular object was detected
        self.detection_boxes = self.detection_graph.get_tensor_by_name('detection_boxes:0')
        # Each score represents level of confidence for each of the objects.
        # The score is shown on the result image, together with the class label.
        self.detection_scores = self.detection_graph.get_tensor_by_name('detection_scores:0')
        self.detection_classes = self.detection_graph.get_tensor_by_name('detection_classes:0')
        # Number of objects detected
        self.num_detections = self.detection_graph.get_tensor_by_name('num_detections:0')

    def video_setting(self):
        # Initialize webcam feed
        self.video = cv2.VideoCapture(0,cv2.CAP_DSHOW)
        self.ret = self.video.set(3, 1280)
        self.ret = self.video.set(4, 720)


    def save_data(self):
        # Save data
        f=open(self.DATA_FILE, 'wb')
        pickle.dump(self.DATA,f)
        f.close()
            
        with open(self.tmppath, 'w+') as f:
            f.write('%d,%d' %(self.cntMTot, self.cntVTot))
        


    def start(self):
        time.sleep(2)
      
        
        while(self.running):

            try:
                # Acquire frame and expand frame dimensions to have shape: [1, None, None, 3]
                # i.e. a single-column array, where each item in the column has the pixel RGB value
                ret, frame = self.video.read()
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame_expanded = np.expand_dims(frame_rgb, axis=0)

                # Perform the actual detection by running the model with the image as input
                (boxes, scores, classes, num) = self.sess.run(
                    [self.detection_boxes, self.detection_scores, self.detection_classes, self.num_detections],
                    feed_dict={self.image_tensor: frame_expanded})

                faces=[]
                labels=[]
                for i,score in enumerate(scores[0]):
                    if score>self.min_score:
                        ymin=int(boxes[0][i][0]*frame.shape[0])
                        xmin=int(boxes[0][i][1]*frame.shape[1])
                        ymax=int(boxes[0][i][2]*frame.shape[0])
                        xmax=int(boxes[0][i][3]*frame.shape[1])
                        lab=self.categories[int(classes[0][i])-1]
                        faces.append([xmin,xmax,ymin,ymax])
                        labels.append(lab)

                        
                        ind=int(classes[0][i])-1
                        # Draw the results of the detection
                        cv2.rectangle(frame, (xmin, ymin), (xmax, ymax),tuple((list(self.colors[ind])[:3])[::-1]), 2)
                        if self.show_scores:
                            text=lab+': '+str(int(score*100))+'%'
                            font_scale = (xmax-xmin)/frame.shape[1]*3
                            (text_width, text_height) = cv2.getTextSize(text, self.font, fontScale=font_scale, thickness=2)[0]
                            text_offset_x = xmin
                            text_offset_y = ymin
                            box_coords = ((text_offset_x, text_offset_y), (text_offset_x + text_width + 2, text_offset_y - text_height - 2))
                            cv2.rectangle(frame, box_coords[0], box_coords[1], tuple((list(self.colors[ind])[:3])[::-1]), cv2.FILLED)
                            cv2.putText(frame, text, (text_offset_x, text_offset_y), self.font, fontScale=font_scale, color=(0, 0, 0), thickness=2,lineType=2)
                            
                                    

                # Get the list of all masked faces
                masked_faces=[faces[i] for i, x in enumerate(labels) if x == self.categories[1]]
                # Get the list of all not masked faces
                unmasked_faces=[faces[i] for i, x in enumerate(labels) if x == self.categories[0]]
                # Tracking
                masked_people=self.masked_tracker.refresh(masked_faces,[frame.shape[0],frame.shape[1]],border=self.border_pxl)
                unmasked_people=self.unmasked_tracker.refresh(unmasked_faces,[frame.shape[0],frame.shape[1]],border=self.border_pxl)

                # Check proximity between people
                result=proximity_detector(masked_people, unmasked_people)

                # if near people are detected, results are reported and sound and graphical alarms are activated
                for r in result:
                    if r in list(self.crowd_list.keys()):
                        if (time.time()-self.crowd_list[r])>self.alarm_time:
                            self.alarm_list.add(r)
                            
                    else:
                        self.crowd_list[r]=time.time()
                tmp=deepcopy(self.crowd_list)
                for k in list(tmp.keys()):
                    if k not in result:
                        del self.crowd_list[k]
                        if k in self.alarm_list:
                            self.alarm_list.remove(k)
                         

                # run sound alarm
                if len(self.alarm_list)>0 and not self.alarm_on:
                    thread1 = threading.Thread(target = self.alarm)
                    thread1.start()        
                        
                
                # loop over the tracked masked people
                for (objectID, box) in masked_people.items():
                    # draw both the ID of the object and the centroid of the
                    # object on the output frame
                    if self.show_IDs:
                        xmin,xmax,ymin,ymax=box
                        text = "M{}".format(objectID)
                        font_scale = (xmax-xmin)/frame.shape[1]*3
                        (text_width, text_height) = cv2.getTextSize(text, self.font, fontScale=font_scale, thickness=2)[0]
                        text_offset_x = xmin
                        text_offset_y = ymax
                        box_coords = ((text_offset_x, text_offset_y), (text_offset_x + text_width + 2, text_offset_y - text_height - 2))
                        cv2.rectangle(frame, box_coords[0], box_coords[1], tuple((list(self.colors[1])[:3])[::-1]), cv2.FILLED)
                        cv2.putText(frame, text, (text_offset_x, text_offset_y), self.font, fontScale=font_scale, color=(0, 0, 0), thickness=2,lineType=2)
                        # if people are too near, a red rectangle is drawn
                        for alarm in self.alarm_list:
                            if alarm[0]==text or alarm[1]==text:
                                cv2.rectangle(frame, (xmin,ymin), (xmax,ymax), (0,0,255), thickness = 5)
                  #update total number of masked              
                    if objectID>self.cntMTot:
                        self.cntMTot=objectID
                        
                    

                # loop over the tracked unmasked people
                for (objectID, box) in unmasked_people.items():
                    # draw both the ID of the object and the centroid of the
                    # object on the output frame
                    if self.show_IDs:
                        xmin,xmax,ymin,ymax=box
                        text = "NM{}".format(objectID)
                        font_scale = (xmax-xmin)/frame.shape[1]*3
                        (text_width, text_height) = cv2.getTextSize(text, self.font, fontScale=font_scale, thickness=2)[0]
                        text_offset_x = xmin
                        text_offset_y = ymax
                        box_coords = ((text_offset_x, text_offset_y), (text_offset_x + text_width + 2, text_offset_y - text_height - 2))
                        cv2.rectangle(frame, box_coords[0], box_coords[1], tuple((list(self.colors[0])[:3])[::-1]), cv2.FILLED)
                        cv2.putText(frame, text, (text_offset_x, text_offset_y), self.font, fontScale=font_scale, color=(0, 0, 0), thickness=2,lineType=2)
                        # if people are too near, a red rectangle is drawn
                        for alarm in self.alarm_list:
                            if alarm[0]==text or alarm[1]==text:
                                cv2.rectangle(frame, (xmin,ymin), (xmax,ymax), (0,0,255), thickness = 5)
                    # update total number of unmasked
                    if objectID>self.cntVTot:
                        self.cntVTot=objectID
                
                # Update graphical statistics
                self.cntM = labels.count('With Mask')
                self.cntV = labels.count('Without Mask')
                self.textCM.setText('Current Number of People '+self.categories[1]+': %d' %self.cntM)
                self.textCV.setText('Current Number of People '+self.categories[0]+': %d' %self.cntV)
                self.textTM.setText('Total Number of People '+self.categories[1]+': %d' %self.cntMTot)
                self.textTV.setText('Total Number of People '+self.categories[0]+': %d' %self.cntVTot)


                self.timestamp=time.time()
                # Save samples each second
                if self.timestamp-self.t1>1:
                    self.DATA[round(self.timestamp,6)]={"NM":list(unmasked_people.keys()),"M":list(masked_people.keys())}
                    self.t1=self.timestamp
                
                # Write data to file every 60 seconds
                if self.timestamp-self.t2>60:
                    self.save_data()
                    self.t2=self.timestamp

                
                if not self.isVisible():
                    exit()


                # All the results have been drawn on the frame, so it's time to display it.                
                height, width, channel = frame.shape
                bytesPerLine = 3 * width
                self.qImg = QImage(frame.data, width, height, bytesPerLine, QImage.Format_RGB888).rgbSwapped()
                self.pic.setPixmap(QPixmap(self.qImg))                
                if cv2.waitKey(1) == ord('q'):
                    break

            except:
                with open(self.tmppath, 'w+') as file:
                    file.write('%d,%d' %(self.cntMTot, self.cntVTot))
                exit()
          
    def alarm(self):
        self.alarm_on=True
        playsound('data/beep.mp3')
        self.alarm_on=False
    
       
if __name__=='__main__':

    app = QApplication(sys.argv)

    window = ObjectDetection()
    window.show()

    app.exec_()
