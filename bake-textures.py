###########################################################################
# 
# Author      : Kevin Perez
# Description : Unifies multiple texture maps into one,
#               outputs new UV unwrapped 3D model with single texture
###########################################################################

# BLENDER module
import bpy


# selects single object in the scene, will clear all other selections
def selectObj(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)


# makes object the active one
def makeActive(obj):
    bpy.context.view_layer.objects.active = obj
    

# selects all objects on the screen
def selectAll():
    bpy.ops.object.select_all(action='SELECT')
    

# delete selected objects
def deleteSelected():
    bpy.ops.object.delete(use_global=False)
    

# imports OBJ file into scene, returns (obj,import status)
def importObj(file_loc):
    import_model_stat = bpy.ops.import_scene.obj(filepath=file_loc)
    obj = bpy.context.editable_objects[-1]
    return (obj, import_model_stat)


# exports OBJ file from scene
def exportObj(obj, export_loc):
    selectObj(obj)
    export_model_stat = bpy.ops.export_scene.obj(filepath=export_loc, use_selection=True)
    return export_model_stat


# exports texture image
def exportTexture(image, export_loc):
    image.filepath_raw = export_loc
    image.save()


# create copy of given model, return reference to copy
def duplicate(obj):
    selectObj(obj)
    bpy.ops.object.duplicate()
    obj = bpy.context.editable_objects[-1]
    return obj


# gets poly count of mesh object
def getPolyCount(obj):
    face_count = len(obj.to_mesh().polygons)
    return face_count


# add and apply decimate modifier to given object
def decimate(obj, ratio):
    dm = obj.modifiers.new('Decimate','DECIMATE')
    dm.ratio = ratio
    selectObj(obj)
    makeActive(obj) # object must be active before applying modifier
    bpy.ops.object.modifier_apply(apply_as='DATA', modifier="Decimate")
  

# add and apply subdivide surfce modifier to given object, will match poly count of target object
def subSurfToTarget(obj, target):
    
    # get poly count of original model
    originalPolyCount = getPolyCount(target)
    
    # get current poly count of copy model
    startingPolyCount = getPolyCount(obj)

    # calculate optimal level of subdivision
    level = 1
    estimated_poly_count = startingPolyCount * ((4**(level-1)) * 3)
    while(estimated_poly_count < originalPolyCount):
        level += 1
        estimated_poly_count = startingPolyCount * ((4**(level-1)) * 3)
    
    # create and apply sub surf
    sm = obj.modifiers.new('Subsurf','SUBSURF')
    sm.use_creases = True
    sm.subdivision_type = 'SIMPLE'
    sm.levels = level
    selectObj(obj)
    makeActive(obj) # object must be active before applying modifier
    bpy.ops.object.modifier_apply(apply_as='DATA', modifier="Subsurf")
    

# add shrink wrap modifier to object using target
def shrinkWrap(obj, target):
    swm = obj.modifiers.new('ShrinkWrap','SHRINKWRAP')
    swm.target = target
    selectObj(obj)
    makeActive(obj) # object must be active before applying modifier
    bpy.ops.object.modifier_apply(apply_as='DATA', modifier="ShrinkWrap")


# delete all materials for given object
def purgeMaterials(obj):
    obj.active_material_index = 0
    for i in range(len(obj.material_slots)):
        bpy.ops.object.material_slot_remove({'object': obj})
        
        
# create new material and return it
def createMaterial(myName = "New Material"):
    material = bpy.data.materials.new(name = myName)
    material.use_nodes = True
    return material


# create blank image and return it
def createImage(myWidth, myHeight, myName = "Blank Image"):
    image = bpy.data.images.new(name=myName, width=myWidth, height=myHeight)
    return image


# UV unwrap object using smart UV project function
def smartUV(obj):
    selectObj(obj)
    makeActive(obj)
    bpy.ops.uv.smart_project(stretch_to_bounds=False)
    
    
# change render engine
def setRenderEngine(engine):
    bpy.context.scene.render.engine = engine
    
        
# create and assign new material texture for given object
def makeNewTexture(obj):
    # make blank material and image
    material = createMaterial()
    image = createImage(1024, 1024)
    
    # Access the BSDF node
    bsdfNode = material.node_tree.nodes["Principled BSDF"]
    
    # Create new image texture node and add blank image
    texImageNode = material.node_tree.nodes.new("ShaderNodeTexImage")
    texImageNode.image = image
    
    # set new image texture node to active in node tree
    node_tree = bpy.data.materials['Material'].node_tree                                           
    texImageNode.select = True
    node_tree.nodes.active = texImageNode
    
    # Link texture image node to BSDF
    material.node_tree.links.new(bsdfNode.inputs["Base Color"],texImageNode.outputs["Color"])
    
    # Assign material to object
    obj.data.materials.append(material)
    
    return image
    

# bake image details from obj to target blank image
def bake(obj, target):
    
    # set engine to cycles for baking
    setRenderEngine("CYCLES")
    
    # select all objects for baking
    selectAll()
    
    # set active the object to bake to
    makeActive(target)
    
    # bake
    bpy.ops.object.bake(type = 'DIFFUSE',
                        pass_filter={'AO', 'COLOR', 'EMIT', 'DIFFUSE', 'GLOSSY', 'TRANSMISSION', 'SUBSURFACE'},
                        width = 1024,
                        height = 1024,
                        margin = 2,
                        use_selected_to_active = True,
                        cage_extrusion = 0.05,
                        save_mode = 'INTERNAL')



###########################################################################
# MAIN WORKFLOW
###########################################################################

# clear all objects in scene
selectAll()
deleteSelected()


# import model, use \\ on windows (escape the escape characters)
file_loc = "C:\\Users\\Kevin\\Documents\\test_models\\3dmodel.obj"
importedModel = importObj(file_loc)[0]


# copy imported model
modelCopy = duplicate(importedModel)


# purge all materials (textures) from copy
purgeMaterials(modelCopy)


# decimate copy if face count greater than 100,000 polygons
decimated = False
if getPolyCount(modelCopy) > 100000:
    decimate(modelCopy, ratio = 0.01)
    decimated = True


# UV unwrap model copy using smart UV project
smartUV(modelCopy)


# if the copy was decimated, get back lost detail
if decimated:
    
    # subdivide surface of copy to match triangle count from original
    subSurfToTarget(modelCopy, importedModel)
    
    # shrink wrap model copy to the surface of original model - gets back lost detail
    shrinkWrap(modelCopy, importedModel)


# create and store new material texture for copy
newTexture = makeNewTexture(modelCopy)


# bake image details from original model to copy
bake(importedModel, modelCopy)


# export new model and texture
export_loc = "C:\\Users\\Kevin\\Documents\\test_models\\new3dmodel.obj"
exportObj(modelCopy, export_loc)
exportTexture(newTexture, export_loc+".jpg")
