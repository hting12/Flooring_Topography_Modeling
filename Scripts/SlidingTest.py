import os
import sys
import xml.etree.ElementTree as ET
import csv

# Get working directory path by going up 4 levels from the MECH directory
workingDirectory = ExtAPI.DataModel.AnalysisList[0].WorkingDir
for i in range(5):
    workingDirectory = os.path.dirname(workingDirectory)

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

# Set the User IDs of the Shoe body and Floor body Named Selections (needed for the Keyword Snippet)
namedSelections["Shoe"].LSDynaUserId = 1
namedSelections["Floor"].LSDynaUserId = 2

# Set Stiffness Behavior and Material Assignments for Shoe and Floor Bodies
ls_dyna.setupGeometry(bodies["Shoe"], bodies["Floor"])

# Add Mesh Controls and generate Mesh
meshSize = float(config["SizeScale"]) * float(config["MeshSizeFactor"])
ls_dyna.mesh(ExtAPI, meshSize, namedSelections["Floor_Contact"], namedSelections["Shoe_Contact"], namedSelections["Floor"], namedSelections["Shoe"])

# Calculate target contact pressure for Sliding Test
simIndex = int(log.find("./CurrentSimulationIndex").text)
numSims = int(config["NumberOfSimulations"])
minPressure = float(config["MinPressure"])
maxPressure = float(config["MaxPressure"])
targetPressure = (maxPressure - minPressure) / (numSims - 1) * simIndex + minPressure

# Get Top Face area and Sliding Distance and Sliding Speed from Config file
topFaceArea = float(log.find("./TopFaceArea").text)
slidingDistance = float(log.find("./SlidingDistance").text)
movementSpeed = float(config["MovementSpeed"])

# Calculate target Normal Force
targetNormalForce = targetPressure * topFaceArea

# Load Normal Force Data from Compression Test
with open(os.path.join(workingDirectory, "Results", "Force_CompressionTest.csv")) as csvFile:
    csvReader = csv.reader(csvFile, delimiter=',', quotechar='|')
    csvRows = [row for i, row in enumerate(csvReader) if i > 0]

# Determine the duration of the displacement loading step based on the compression test data
for row in csvRows:
    if abs(float(row[1])) >= targetNormalForce:
        displacementDuration = float(row[0])
        break

# Calculate target displacement
displacementDistance = displacementDuration * movementSpeed

# Calculate duration of the sliding load step
slidingDuration = slidingDistance / movementSpeed

# Calculate analysis time
analysisDuration = displacementDuration + slidingDuration

# Set analysis End Time
ls_dyna.setAnalysisEndTime(ExtAPI, analysisDuration)

# Create Displacement condition
displacement = ls_dyna.createDisplacement(ExtAPI, namedSelections["Shoe_Top"], [[0, 0], [displacementDuration, -1 * displacementDistance], [analysisDuration, -1 * displacementDistance]])

# Create Birth and Death object for Displacement condition
displacementBirthAndDeath = ls_dyna.createBirthAndDeath(ExtAPI, 0, 0, displacementDuration)

# Create Velocity condition
velocity = ls_dyna.createVelocity(ExtAPI, namedSelections["Shoe_Top"], [[0, 0], [displacementDuration, movementSpeed], [analysisDuration, movementSpeed]])

# Create Birth and Death object for Velocity condition
velocityBirthAndDeath = ls_dyna.createBirthAndDeath(ExtAPI, 1, displacementDuration, 0)

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
results = ImportExportUtilities.parseForceData(os.path.join(workingDirectory, filesFolder, "dp0", "SYS-{}".format(simIndex + 1), "MECH", "file3.nlh"))

# Writing Normal and Shear Force data to Results directory
with open(os.path.join(workingDirectory, "Results", "Force_{}.csv".format(simIndex)), 'wb') as fileObj:
    csvWriter = csv.writer(fileObj)
    csvWriter.writerow(["Time [s]", "Normal Force [N]", "Shear Force [N]"])
    for row in results:
        # Only export data after the initial displacement loading step is finished
        if float(row[0]) < displacementDuration:
            continue
        csvWriter.writerow(row)

# Save the current simulation's target contact pressure in the Log file
simPressure = ET.SubElement(log, "SimulationPressure{}".format(simIndex), unit="Pa")
simPressure.text = str(targetPressure)

# Save Log xml file
with open(logFilePath, 'wb') as fileObj:
    logTree.write(fileObj, encoding='utf-8')
