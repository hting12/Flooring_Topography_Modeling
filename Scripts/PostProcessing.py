# This script handles the post processing steps of the workflow
# All external force tracker data from the LS-Dyna Sliding Test simulations is loaded in
# Average normal force, average shear force, average contact pressure, and average COF is calculated
# Results are exported to a CSV file
# Results are then used to construct an LS-Dyna Keyword Snippet that captures the COF vs Pressure relationship of the data in a pressure-dependent friction condition
# The Keyword Snippet is then saved in a text file

import os
import xml.etree.ElementTree as ET
import csv
import ImportExportUtilities

def run(workingDirectory):
    # Parse the workflow log file
    logFilePath = os.path.join(workingDirectory, "Logs", "Log.xml")
    logTree = ET.parse(logFilePath)
    log = logTree.getroot()

    topFaceArea = float(log.find("./TopFaceArea").text)

    # List of force tracker data files
    files = os.listdir(os.path.join(workingDirectory, "Results"))
    files.sort()
    if "Force_CompressionTest.csv" in files: files.remove("Force_CompressionTest.csv")
    if "Results.csv" in files: files.remove("Results.csv")
    if "Keyword Snippet.txt" in files: files.remove("Keyword Snippet.txt")

    # Import data from files
    data = []
    for file in files:
        with open(os.path.join(workingDirectory, "Results", file)) as csvFile:
            csvReader = csv.reader(csvFile, delimiter=',', quotechar='|')
            csvRows = [row for i, row in enumerate(csvReader) if i > 0]
            data.append(csvRows)

    # Extract average COF and pressure values from each set of normal and shear force data
    header = ["Average Normal Force [N]", "Average Shear Force [N]", "Average Pressure [Pa]", "Average COF [-]"]
    results = []
    for dataSet in data:
        normal = [-float(row[1]) for row in dataSet]
        shear = [float(row[2]) for row in dataSet]
        averageNormal = sum(normal) / len(normal)
        averageShear = sum(shear) / len(shear)
        averagePressure = averageNormal / topFaceArea
        averageCof = averageShear / averageNormal
        results.append([averageNormal, averageShear, averagePressure, averageCof])

    with open(os.path.join(workingDirectory, "Results", "Results.csv"), 'wb') as csvFile:
            csvWriter = csv.writer(csvFile)
            csvWriter.writerow(header)
            csvWriter.writerows(results)

    # Create LS-DYNA keyword code to define a pressure dependant friction based on the COF and Pressure results
    # boundary condition based on the curve fitting results
    tableNum = 1;
    curveStartNum = 100;
    keywordSnippet = "*CONTACT_AUTOMATIC_SURFACE_TO_SURFACE\n"
    keywordSnippet += "$ ssid,msid,sstyp,mstyp,sboxid,mboxid,spr,mpr\n"
    keywordSnippet += "1,2,3,3,0,0,1,1\n"
    keywordSnippet += "$ fs,fd,dc,vc,vdc,penchk,bt,dt\n"
    keywordSnippet += "2,1,0,0,10,0,0,0\n"
    keywordSnippet += "$ sfs,sfm,sst,mst,sfst,sfmt,fsf,vsf\n"
    keywordSnippet += "0,0,0,0,0,0,0,0\n"
    keywordSnippet += "$ soft,softscl,lcidab,maxpar,sbopt,depth,bsort,frcfrq\n"
    keywordSnippet += "2,0.1,0,0,3,5,0,0\n"
    keywordSnippet += "$ penmax,tkhopt,shlthk,snlog,isym,i2d3d,sldthk,sldstf\n"
    keywordSnippet += "0,0,0,0,0,0,0,0\n"
    keywordSnippet += "*DEFINE_TABLE\n{}\n$ Pressure value vs Curve ID\n".format(tableNum)
    for i, result in enumerate(results):
        keywordSnippet += "{},{}\n".format(result[2], curveStartNum + i)
    for i, result in enumerate(results):
        keywordSnippet += "*DEFINE_CURVE\n{}\n$ Relative velocity vs COF\n0,{}\n100,{}\n".format(curveStartNum + i, result[3], result[3])

    # Save the keyword snippet
    with open(os.path.join(workingDirectory, "Results", "Keyword Snippet.txt"), 'w') as fileObj:
        fileObj.write(keywordSnippet)
