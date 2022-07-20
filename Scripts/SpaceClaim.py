# Python Script, API Version = V20

import os
import xml.etree.ElementTree as ET

# There does not seem to be any way to get the working directory programatically in SpaceClaim
# It needs to be hardcoded
workingDirectory = r"/ihome/kbeschorner/hti2/Flooring_Topography_Modeling"

# Check if the hardcoded working directory path is valid
# Throw an exception if it is not valid
if not os.path.isdir(workingDirectory):
    raise Exception("Working Directory path is invalid.\nUpdate the script's workingDirectory path declaration.")

# Check if Log.xml file can be located
# Throw an exception if it cannot
logFilePath = os.path.join(workingDirectory, "Logs", "Log.xml")
if not os.path.exists(logFilePath):
    raise Exception("Log.xml cannot be found.")

# Parse the workflow log file
logTree = ET.parse(logFilePath)
log = logTree.getroot()

# Get selections
shoe_top = Selection.CreateByGroups("Shoe_Top")
shoe_side = Selection.CreateByGroups("Shoe_Side")
floor_side = Selection.CreateByGroups("Floor_Side")
shoe_contact = Selection.CreateByGroups("Shoe_Contact")
floor_contact = Selection.CreateByGroups("Floor_Contact")

# Measurements
topFaceArea = MeasureHelper.MeasureArea(shoe_top)
slidingDistance = abs(MeasureHelper.GetCentroid(shoe_side).X - MeasureHelper.GetCentroid(floor_side).X)
distanceToContact = abs(MeasureHelper.DistanceBetweenObjects(shoe_contact, floor_contact).DeltaY)

# Save in Config xml
topFaceAreaNode = ET.SubElement(log, "TopFaceArea")
topFaceAreaNode.text = str(topFaceArea)
slidingDistanceNode = ET.SubElement(log, "SlidingDistance")
slidingDistanceNode.text = "{:.4e}".format(float(slidingDistance))
distanceToContactNode = ET.SubElement(log, "DistanceToContact")
distanceToContactNode.text = "{:.4e}".format(float(distanceToContact))

# Save changes to Config.xml file
with open(logFilePath, 'wb') as fileObj:
    logTree.write(fileObj, encoding='utf-8')
