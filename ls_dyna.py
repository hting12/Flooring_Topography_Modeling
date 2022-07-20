import Ansys.Mechanical.DataModel.Enums.StiffnessBehavior as StiffnessBehavior
import Ansys.Core.Units.Quantity as Quantity
import Ansys.ACT.Mechanical.Fields.VariableDefinitionType as VariableDefinitionType
import Ansys.Mechanical.DataModel.Enums.NormalOrientationType as NormalOrientationType

# Returns references
# ExtAPI = ExtAPI reference
def getReferences(ExtAPI):
    project = ExtAPI.DataModel.Project
    selectionManager = ExtAPI.SelectionManager
    dataModel = ExtAPI.DataModel
    model = ExtAPI.DataModel.Project.Model
    mesh = ExtAPI.DataModel.Project.Model.Mesh
    analysis = ExtAPI.DataModel.AnalysisList[0]
    analysisSettings = ExtAPI.DataModel.GetObjectsByName("Analysis Settings")[0]
    solution = ExtAPI.DataModel.GetObjectsByName("Solution")[0]
    solutionInformation = ExtAPI.DataModel.GetObjectsByName("Solution Information")[0]

    return project, selectionManager, dataModel, model, mesh, analysis, analysisSettings, solution, solutionInformation

# Returns dictionary of Named Selection references
# ExtAPI = ExtAPI reference
# names = list of NamedSelection Names
def getNamedSelections(ExtAPI, names):
    model = ExtAPI.DataModel.Project.Model

    namedSelections = {}
    for name in names:
        namedSelections[name] = [selection for selection in model.NamedSelections.Children if selection.Name == name][0]

    return namedSelections

# Returns dictionary of Body references
# ExtAPI = ExtAPI reference
# namedSelections = list of NamedSelection references
def getBodies(ExtAPI, namedSelections):
    dataModel = ExtAPI.DataModel
    model = ExtAPI.DataModel.Project.Model
    selectionManager = ExtAPI.SelectionManager

    bodies = {}
    for namedSelection in namedSelections:
        selectionManager.NewSelection(namedSelection)
        bodies[namedSelection.Name] = model.Geometry.GetBody(dataModel.GeoData.GeoEntityById(selectionManager.CurrentSelection.Ids[0]))
        selectionManager.ClearSelection()

    return bodies

# Set desired geometry properties
# shoe = Body reference to shoe
# floor = Body reference to floor
def setupGeometry(shoe, floor):
    # Set Stiffness Behavior of Shoe and Floor bodies
    shoe.StiffnessBehavior = StiffnessBehavior.Flexible
    floor.StiffnessBehavior = StiffnessBehavior.Rigid

    # Viscoelastic Rubber material to the Shoe body
    shoe.Material = "Viscoelastic Rubber"

# Add desired mesh controls and generate mesh
# ExtAPI = ExtAPI reference
# meshSize = size of mesh in meters
# floorContact = NamedSelection reference to floor contact
# shoeContact = NamedSelection reference to shoe contact
# floor = NamedSelection reference to floor
# shoe = NamedSelection reference to shoe
def mesh(ExtAPI, meshSize, floorContact, shoeContact, floor, shoe):
    mesh = ExtAPI.DataModel.Project.Model.Mesh
    selectionManager = ExtAPI.SelectionManager

    # Add Face Meshing control
    faceMeshing = mesh.AddFaceMeshing()
    selectionManager.NewSelection(floorContact)
    selectionManager.AddSelection(shoeContact)
    selection = selectionManager.CurrentSelection
    selectionManager.ClearSelection()
    faceMeshing.Location = selection

    # Add Body Sizing mesh control
    sizing = mesh.AddSizing()
    selectionManager.NewSelection(floor)
    selectionManager.AddSelection(shoe)
    selection = selectionManager.CurrentSelection
    sizing.Location = selection
    selectionManager.ClearSelection()
    sizing.ElementSize = Quantity(meshSize, "m")

    # Generate Mesh
    mesh.GenerateMesh()

# Set analysis End time
# ExtAPI = ExtAPI reference
# endTime = analysis End Time in seconds
def setAnalysisEndTime(ExtAPI, endTime):
    analysis = ExtAPI.DataModel.GetObjectsByName("Analysis Settings")[0]
    analysisSettings = ExtAPI.DataModel.GetObjectsByName("Analysis Settings")[0]

    analysisSettings.PropertyByName("Step Controls/Endtime").InternalValue = endTime

# Creates and returns reference to Displacement Boundary Condition
# ExtAPI = ExtAPI reference
# namedSelection = NamedSelection reference to scope condition to
# tabularData = nested list of time and displacement pairs in seconds and meters
def createDisplacement(ExtAPI, namedSelection, tabularData):
    analysis = ExtAPI.DataModel.AnalysisList[0]

    timeValues = [Quantity("{} [sec]".format(str(element[0]))) for element in tabularData]
    displacementValues = [Quantity("{} [m]".format(str(element[1]))) for element in tabularData]

    displacement = analysis.AddDisplacement()
    displacement.Location = namedSelection
    displacement.XComponent.Output.DefinitionType =  VariableDefinitionType.Discrete
    displacement.YComponent.Output.DefinitionType =  VariableDefinitionType.Discrete
    displacement.ZComponent.Output.DefinitionType =  VariableDefinitionType.Discrete
    displacement.YComponent.Inputs[0].DiscreteValues = timeValues
    displacement.YComponent.Output.DiscreteValues = displacementValues

    return displacement

# Creates and returns reference to Velocity Boundary Condition
# ExtAPI = ExtAPI reference
# namedSelection = NamedSelection reference to scope condition to
# tabularData = nested list of time and velocity pairs in seconds and meters/second
def createVelocity(ExtAPI, namedSelection, tabularData):
    analysis = ExtAPI.DataModel.AnalysisList[0]

    timeValues = [Quantity("{} [sec]".format(str(element[0]))) for element in tabularData]
    velocityValues = [Quantity("{} [m/s]".format(str(element[1]))) for element in tabularData]

    velocity = analysis.AddVelocity()
    velocity.Location = namedSelection
    velocity.XComponent.Output.DefinitionType =  VariableDefinitionType.Discrete
    velocity.YComponent.Output.DefinitionType =  VariableDefinitionType.Discrete
    velocity.ZComponent.Output.DefinitionType =  VariableDefinitionType.Discrete
    velocity.XComponent.Inputs[0].DiscreteValues = timeValues
    velocity.XComponent.Output.DiscreteValues = velocityValues

    return velocity
 
# Creates and returns reference to Birth and Death object
# ExtAPI = ExtAPI reference
# index = index of boundary condition to scope to. This will correspond to the order that eligible condtions were created in the model
# birthTime = analyis time to activate the condition
# deathTime = analysis time to deactivate the condition
def createBirthAndDeath(ExtAPI, index, birthTime, deathTime):
    analysis = ExtAPI.DataModel.AnalysisList[0]

    birthAndDeath = analysis.CreateLoadObject("BirthAndDeath","LSDYNA")
    property = birthAndDeath.Properties['Boundary Condition']
    property.Value = property.Options[index]
    birthAndDeath.Properties['Birth Time'].Value = birthTime
    birthAndDeath.Properties['Death Time'].Value = deathTime

    return birthAndDeath

# Creates and returns reference to Rigid Body Constraint Boundary Condition
# ExtAPI = ExtAPI reference
# namedSelection = NamedSelection reference to scope condition to
def createRigidBodyConstraint(ExtAPI, namedSelection):
    analysis = ExtAPI.DataModel.AnalysisList[0]

    rigidBodyConstraint = analysis.CreateLoadObject("Rigid Constraint","LSDYNA")
    rigidBodyConstraint.Properties["Geometry/DefineBy/Geo"].Value = namedSelection

    return rigidBodyConstraint

# Suppresses the default Body Interaction. Needed when using a Keyword Snippet to define a custom friction condition
# ExtAPI = ExtAPI reference
def suppressDefaultBodyInteraction(ExtAPI):
    dataModel = ExtAPI.DataModel

    dataModel.GetObjectsByName("Body Interaction")[0].PropertyByName("Suppressed").InternalValue = 1

# Creates and returns a reference to a keyword snippet that defines a frictionless, surface-to-surface contact
# This is needed as this body interaction option is not supported in the Ansys Mechanical/LS-Dyna ACT package
def createDefaultContact(ExtAPI):
    snippet = """*CONTACT_AUTOMATIC_SURFACE_TO_SURFACE 
$     ssid      msid     sstyp     mstyp    sboxid    mboxid       spr       mpr
            1         2         3         3         0         0         1         1
$       fs        fd        dc        vc       vdc    penchk        bt        dt
            0         0         0         0        10         0         0         0
$      sfs       sfm       sst       mst      sfst      sfmt       fsf       vsf
            0         0         0         0         0         0         0         0
$     soft   softscl    lcidab    maxpar     sbopt     depth     bsort    frcfrq
            2       0.1         0         0         3         5         0         0
$   penmax    tkhopt    shlthk     snlog      isym     i2d3d    sldthk    sldstf
            0         0         0         0         0         0         0         0
"""

    return createKeywordSnippet(ExtAPI, snippet)

# Creates and returns reference to Keyword Snippet
# ExtAPI = ExtAPI reference
# text = keyword commands to store in snippet
def createKeywordSnippet(ExtAPI, text):
    analysis = ExtAPI.DataModel.AnalysisList[0]

    keywordSnippet = analysis.AddCommandSnippet()
    keywordSnippet.Input = text

    return keywordSnippet

# Creates and returns references to Result objects
# ExtAPI = ExtAPI reference
# displacement = Displacement Boundary Condition reference
def createResults(ExtAPI, displacement):
    solution = ExtAPI.DataModel.GetObjectsByName("Solution")[0]
    solutionInformation = ExtAPI.DataModel.GetObjectsByName("Solution Information")[0]

    # Create Equivalent Stress result
    equivalentStress = solution.AddEquivalentStress()

    # Create Normal Force result
    normalForce = solutionInformation.AddExternalForce()
    normalForce.BoundaryCondition = displacement
    normalForce.NormalOrientation = NormalOrientationType.YAxis
    normalForce.Name = "Normal Force"

    # Create Shear Force result
    shearForce = solutionInformation.AddExternalForce()
    shearForce.BoundaryCondition = displacement
    shearForce.NormalOrientation = NormalOrientationType.XAxis
    shearForce.Name = "Shear Force"

    return equivalentStress, normalForce, shearForce
