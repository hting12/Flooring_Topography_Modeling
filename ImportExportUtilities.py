import csv
import xml.etree.ElementTree as ET

# Import Configuration file and return a dictionary of values extracted from the file
# path = path to the configuration file
def importConfig(path):
    rows = []
    with open(path, 'r') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            rows.append(row)

    config = {}
    for i in range(len(rows[0])):
        data = [row[i] for row in rows[1:] if not row[i] == '']
        config[rows[0][i]] = data if len(data) > 1 else data[0]

    return config

# Parse the raw data file of the External Force Tracker results
def parseForceData(path):
    forceTrackerTree = ET.parse(path)
    forceTracker = forceTrackerTree.getroot()
    forceTracker.find("COLDATA").text
    rawResults = [element.split(' ') for element in forceTracker.find("COLDATA").text.splitlines()[1:]]
    results = []
    row = []
    for rawRow in rawResults:
        for element in rawRow:
            if (not element == ''):
                if len(row) < 3:
                    row.append("{:.4e}".format(float(element)))
                else:
                    results.append(row)
                    row = ["{:.4e}".format(float(element))]
    return results
