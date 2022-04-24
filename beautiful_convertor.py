import arcpy
import datetime
import re

arcpy.env.overwriteOutput = True
arcpy.env.addOutputsToMap = True

def check_int(str_value):
    for c in str_value:
        if not c.isdigit():
            return False
    else:
        return True

def check_field(str_value):
    if (str_value is not "FID") and (str_value is not "Shape"):
        return True
    else:
        return False

features_class_path = arcpy.GetParameterAsText(0)
order_of_fields = arcpy.GetParameterAsText(1)
field = arcpy.GetParameterAsText(2)
value = arcpy.GetParameterAsText(3)
output = arcpy.GetParameterAsText(4)
should_export_layout = arcpy.GetParameter(5)
layout_title = arcpy.GetParameterAsText(6)
layout_name = arcpy.GetParameterAsText(7)
layout_sources = arcpy.GetParameterAsText(8)

new_value = 0
value_range = 0
value_type = "Int"

field_names = [f.name for f in arcpy.ListFields(features_class_path)]

value_with_buffer_max = 0
value_with_buffer_min = 0

feature_class_describe = arcpy.Describe(features_class_path)
features_name = feature_class_describe.name.split(".shp", maxsplit=1)[0]
order_of_fields_list = [x.strip() for x in order_of_fields.split(";")]
arcpy.AddMessage(order_of_fields_list)

if value.startswith("\"") and value.endswith("\""):
    new_value = re.findall(r'"([^"]*)"', value)[0]
    value_type = "String"
    arcpy.AddMessage("Reformat Value: {}".format(new_value))
elif "-" in value:
    split_value_list = value.split('-')
    new_value = split_value_list[0]
    value_range = split_value_list[1]
    arcpy.AddMessage("Int: {} and extra {}".format(new_value, value_range))
    if check_int(new_value) and check_int(value_range):
        value_type = "Int"
        arcpy.AddMessage("After check_int is applied Int: {} and extra {}".format(new_value, value_range))
    else:
        arcpy.addError("Value's format is incorrect, please check and retry.")
else:
    arcpy.addError("Incorrect value type, please check and try again.")

if value_type == "Int":
    value_with_buffer_max = int(new_value) + int(value_range)
    value_with_buffer_min = int(new_value) - int(value_range)

arcpy.AddMessage(output)

def reorder_fields(input, output, order_of_fields, missing = True):
    old_mapping = arcpy.FieldMappings()
    old_mapping.addTable(input)
    new_mapping = arcpy.FieldMappings()

    def add_mapping(field_name):
        index = old_mapping.findFieldMapIndex(field_name)
        if index != -1:
            field_map = old_mapping.fieldMappings[index]
            new_mapping.addFieldMap(field_map)

    for fn in order_of_fields:
        if fn not in field_names:
            arcpy.AddMessage("{} Field doesn't exist or is incorrect.".format(fn))
        add_mapping(fn)

    if missing:
        missing_fields = [f for f in field_names if f not in order_of_fields]
        for fn in missing_fields:
            add_mapping(fn)

    arcpy.Merge_management(input, output, new_mapping)
    return output

def select_highlight_and_create(q):
    try:
        arcpy.SelectLayerByAttribute_management(features_name, 'NEW_SELECTION', q)
        arcpy.CopyFeatures_management(features_name, output)
    except:
        arcpy.AddError("Failed to run the select_highlight_and_create method. Try Again.")

if value_type == "Int":
    query = """{} <= "{}" AND "{}" <= {}""".format(value_with_buffer_min, field, field, value_with_buffer_max)
    arcpy.AddMessage(query)
    select_highlight_and_create(query)
elif value_type == "String":
    query = """"{}" LIKE '%{}%'""".format(field, new_value)
    arcpy.AddMessage(query)
    select_highlight_and_create(query)

reorder_fields(features_name, output, order_of_fields_list)

output_field_names = [f.name for f in arcpy.ListFields(output)]

# ----------------------------------------------------------------------------------------------------------------------
if should_export_layout:
    aprx = arcpy.mp.ArcGISProject("CURRENT")
    m = aprx.listMaps()[0]
    m.addDataFromPath(output)
    lyr = m.listLayers()[0]
    output_class_describe = arcpy.Describe(output)
    output_name = output_class_describe.name.split(".shp", maxsplit=1)[0]
    for tempLayer in m.listLayers():
        if tempLayer.name != output_name:
            tempLayer.visibility = False

    lyt = aprx.listLayouts()[0]
    titleText = lyt.listElements("TEXT_ELEMENT", "Text")[0]
    scaleBar = lyt.listElements(wildcard="Scale Bar")[0]
    northArrow = lyt.listElements(wildcard="North Arrow")[0]
    legend = lyt.listElements(wildcard="Legend")[0]

    titleText.text = layout_title

    otherInfoText = titleText.clone("_clone")
    date = datetime.datetime.now()
    current_date = "{}-{}-{}".format(date.month, date.day, date.year)
    otherInfoText.text = "Name: {}, Date: {}, Sources: {}".format(layout_name, current_date, layout_sources)

    legendText = titleText.clone("_clone")
    legendText.text = "Legend"

    mf = lyt.listElements("mapframe_element", "Map Frame")[0]
    mf.camera.setExtent(mf.getLayerExtent(lyr, False, True))
    mf.elementWidth = 7.0
    mf.elementHeight = 4.0
    mf.elementPositionY = 5.0
    mf.elementPositionX = 1.0

    scaleBar.elementPositionY = 3.5
    scaleBar.elementPositionX = 1.0

    northArrow.elementPositionY = 2.5
    northArrow.elementPositionX = 1.0

    legendText.elementPositionY = 4.0
    legendText.elementPositionX = 5.0
    legend.elementPositionY = 3.5
    legend.elementPositionX = 5.0

    titleText.elementPositionY = 10.0
    titleText.elementPositionX = 1.0

    otherInfoText.elementPositionY = 1.5
    otherInfoText.elementPositionX = 1.0
    otherInfoText.elementWidth = 7.0

    lyt.exportToPDF(r"C:\Temp\beautiful_convertor_pdf.pdf")
    arcpy.AddMessage("PDF Generated at C:/Temp/beautiful_convertor_pdf.pdf")

    for elm in lyt.listElements(wildcard="_clone"):
        elm.delete()
        
    del aprx
