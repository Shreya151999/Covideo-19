import numpy as np
from scipy.spatial import distance as dist
from copy import deepcopy


class Tracker():
    def __init__(self, maxAbsences=50, startID=1):

        # ID Counter
        self.nextID = startID

        # To store current objects
        self.objects = {}

        # To count how many consecutive frames an object is absent
        self.absences = {}

        # To store coordinates to return
        self.coordinates={}

        # To backup 
        self.coordinates_backup={}

        # Maximum number of consecutive absences of an object before its deletion
        self.maxAbsences = maxAbsences

    def add(self, centroid):
        # Add a new detected object and increases object counter
        self.objects[self.nextID] = centroid
        self.absences[self.nextID] = 0
        self.nextID += 1

    def remove(self, objectID):
        # Remove a disappeared object
        del self.objects[objectID]
        del self.absences[objectID]

    def refresh(self, inputObjects, imgSize, border):
        

        # If the list of input objects of the current frame is empty:
        if len(inputObjects) == 0:
            # It is necessary to add an absense to every object present in the archive
            for objectID in list(self.absences.keys()):
                self.absences[objectID] += 1

                # If an object is absent and in the last presence was at the boundaries of the picture
                # it will be deleted
                x_min, x_max, y_min, y_max = self.coordinates_backup[objectID]
                if ((x_min in range(-50,border))
                    or (x_max in range(imgSize[1]-border,imgSize[1]+50))
                    or (y_min in range(-50,border))
                    or (y_max in range(imgSize[0]-border,imgSize[0]+50))):
                    self.remove(objectID)
                    del self.coordinates_backup[objectID]
                    
                # If an object has reached the maximum number of consecutive absences, it is deleted
                elif self.absences[objectID] > self.maxAbsences:
                    self.remove(objectID)

            self.coordinates={}
                        
            return self.coordinates

        # Compute centroids for the objects in the current frame
        inputCentroids = [self.calc_centroid(inputObject) for inputObject in inputObjects] 

        # if there are no objects in the archive, all the input objects are added
        if len(self.objects) == 0:
            for i in range(0, len(inputCentroids)):
                self.coordinates[self.nextID]=inputObjects[i]
                self.coordinates_backup[self.nextID]=inputObjects[i]
                self.add(inputCentroids[i])

				

        # else it necessary to match the input objects with the already existing ones
        else:
            objectIDs = list(self.objects.keys())
            objectCentroids = list(self.objects.values())

            # compute distances between input objects and the already existing ones
            D = dist.cdist(np.array(objectCentroids), np.asarray(inputCentroids))

            # Sort and match by distance
            rows = D.min(axis=1).argsort()
            cols = D.argmin(axis=1)[rows]

            usedRows = set()
            usedCols = set()

            for (row, col) in zip(rows, cols):
                # if (row,col) had already examined, ignore them
                if row in usedRows or col in usedCols:
                    continue
                #else take for the current row the object ID and set its
                # updated centroid and reset its absences
                objectID = objectIDs[row]
                self.objects[objectID] = inputCentroids[col]
                self.coordinates[objectID]=inputObjects[col]
                self.coordinates_backup[objectID]=inputObjects[col]
                self.absences[objectID] = 0
                
                # add current col and row to the already used list 
                usedRows.add(row)
                usedCols.add(col)
                
            # get the unused rows indexes (correspondent to objects that need
            # to be removed)
            unusedRows = set(range(0, D.shape[0])).difference(usedRows)
            #get the unused columns indexes (correspondent to the input objects
            #that need to be added)
            unusedCols = set(range(0, D.shape[1])).difference(usedCols)

            # if the number of input objects is equal or lower than the number of
            # objects in the archive, it means that some objects are absent
            if D.shape[0] >= D.shape[1]:
                for row in unusedRows:
                    objectID = objectIDs[row]
                    self.absences[objectID] += 1
                    x_min, x_max, y_min, y_max = self.coordinates_backup[objectID]

                    # if in the preview frame an absent objet was at the
                    #boundary of the image, it needs to be deleted from the archive
                    # (object exiting from the picture)
                    if ((x_min in range(-border*4,border))
                        or (x_max in range(imgSize[1]-border,imgSize[1]+border*4))
                        or (y_min in range(-border*4,border))
                        or (y_max in range(imgSize[0]-border,imgSize[0]+border*4))):
                        self.remove(objectID)
                        del self.coordinates_backup[objectID]
                        del self.coordinates[objectID]
                    # an object has reached the maximum number of consecutive absenses
                    # needs to be deleted
                    elif self.absences[objectID] > self.maxAbsences:
                        self.remove(objectID)
                        if objectID in list(self.coordinates.keys()):
                            del self.coordinates[objectID]
            # else if the number of input objects is greater than the number of
            #objects in the archive of objects, new objects need to be added
            else:
                for col in unusedCols:
                    self.coordinates[self.nextID]=inputObjects[col]
                    self.coordinates_backup[self.nextID]=inputObjects[col]
                    self.add(inputCentroids[col])
		
        return self.coordinates

    def calc_centroid(self,detection):
        # calculate the centroid
        x_min, x_max, y_min, y_max = detection
        return [int((x_min+x_max)/2.0),int((y_min+y_max)/2.0)]

    def reset(self):
        self.nextID = 1
        self.objects = {}
        self.absences = {}
        self.coordinates={}
