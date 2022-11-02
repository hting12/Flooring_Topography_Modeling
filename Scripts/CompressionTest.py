import os
import sys
import csv
import xml.etree.ElementTree as ET

# There does not seem to be any way to get the working directory programatically in SpaceClaim
# It needs to be hardcoded
workingDirectory = r"C:\Users\HTI2\OneDrive - University of Pittsburgh\Desktop\HMBL\Original"

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
    
# Add Scripts directory to local import path
scriptFolderPath = os.path.join(workingDirectory, "Scripts")
sys.path.append(scriptFolderPath)

import ls_dyna
import ImportExportUtilities

# Parse the workflow configuration file
config = ImportExportUtilities.importConfig(os.path.join(workingDirectory, "Config", "Config.csv"))

# Parse the workflow log file
logFilePath = os.path.join(workingDirectory, "Logs", "Log.xml")
logTree = ET.parse(logFilePath)
log = logTree.getroot()

# Retrieve references 
project, selectionManager, dataModel, model, mesh, analysis, analysisSettings, solution, solutionInformation = ls_dyna.getReferences(ExtAPI)
namedSelections = ls_dyna.getNamedSelections(ExtAPI, ["Floor", "Shoe", "Floor_Contact", "Shoe_Contact", "Shoe_Top", "Floor_Side", "Shoe_Side"])
bodies = ls_dyna.getBodies(ExtAPI, [namedSelections["Floor"], namedSelections["Shoe"]])

# Measurements
topFaceArea = 2.94e-6
slidingDistance = 5.3463e-3
distanceToContact = 3.1013e-4

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
    
# Set the User IDs of the Shoe body and Floor body Named Selections (needed for the Keyword Snippet)
namedSelections["Shoe"].LSDynaUserId = 1
namedSelections["Floor"].LSDynaUserId = 2

# Set Stiffness Behavior and Material Assignments for Shoe and Floor Bodies
ls_dyna.setupGeometry(bodies["Shoe"], bodies["Floor"])

# Add Mesh Controls and generate Mesh
meshSize = float(config["SizeScale"]) * float(config["MeshSizeFactor"])
ls_dyna.mesh(ExtAPI, meshSize, namedSelections["Floor_Contact"], namedSelections["Shoe_Contact"], namedSelections["Floor"], namedSelections["Shoe"])

# Calculate displacement distance and analysis time
displacementDistance = float(config["SizeScale"]) * float(config["CompressionTestDisplacementFactor"]) + float("{:.4e}".format(float(log.find("./DistanceToContact").text)))
analysisTime = displacementDistance / float(config["MovementSpeed"])

# Set analysis End Time
ls_dyna.setAnalysisEndTime(ExtAPI, analysisTime)

# Create Displacement condition
displacement = ls_dyna.createDisplacement(ExtAPI, namedSelections["Shoe_Top"], [[0, 0], [analysisTime, -1 * displacementDistance]])

# Create Rigid Body Constraint and apply to Floor body
rigidBodyConstraint = ls_dyna.createRigidBodyConstraint(ExtAPI, namedSelections["Floor"])

# Checking if Keyword Snippet is available in working directory
# If Snippet file exists, then load the file, create a Keyword Snippet, and suppress the default frictionless contact
# If not, create the necessary snippet to define a frictionless, surface-to-surface contact condition
# This is needed because this type of contact is not currently hooked up inside the Ansys Mechanical/LS-Dyna ACT package
keywordSnippetPath = os.path.join(workingDirectory, "Keyword Snippet", "Keyword Snippet.txt")
if os.path.exists(keywordSnippetPath):
    with open(keywordSnippetPath, 'r') as fileObj:
        snippetText = fileObj.read()

    keywordSnippet = ls_dyna.createKeywordSnippet(ExtAPI, snippetText)
else:
    keywordSnippet = ls_dyna.createDefaultContact(ExtAPI)

ls_dyna.suppressDefaultBodyInteraction(ExtAPI)

# Create results
equivalentStress, normalForce, shearForce = ls_dyna.createResults(ExtAPI, displacement)

# Solve the analysis
analysis.Solve()

# Access raw data file for External Force Trackers (needed due to limitations in the Mechanical Scripting API)
# First, find the _files directory
folders = os.listdir(workingDirectory)
filesFolder = [folder for folder in folders if folder.endswith("_files")][0]

# Parse the raw data file
results = ImportExportUtilities.parseForceData(os.path.join(workingDirectory, filesFolder, "dp0", "SYS", "MECH", "file3.nlh"))

# Create Results folder if it does not exist already
resultsFolderPath = os.path.join(workingDirectory, "Results")
if not os.path.exists(resultsFolderPath):
    os.mkdir(resultsFolderPath)

# Writing Normal and Shear Force data to Results directory
with open(os.path.join(workingDirectory, "Results", "Force_CompressionTest.csv"), 'wb') as fileObj:
    csvWriter = csv.writer(fileObj)
    csvWriter.writerow(["Time [s]", "Normal Force [N]", "Shear Force [N]"])
    for row in results:
        # Only export data that occurs following the initial contact between the two bodies
        if float(row[0]) < float(log.find("./DistanceToContact").text) / float(config["MovementSpeed"]):
            continue
        csvWriter.writerow(row)
