def buildChangeSet(featureName, coordinates, config):
    version = config["CHANGESET"]["version"]
    generator = config["CHANGESET"]["generator"]
    osm_version = config["CHANGESET"]["osm_version"]
    version = 1.0
    generator = 'DeepMapper by TU Dublin GIS Research Group (c) 2023'
    osm_version = 0.6
    osm_xml = ""
    osm_xml+=f"<?xml version=\"{version}\" encoding=\"UTF-8\"?>\n"
    osm_xml+=f"<osm version=\"{osm_version}\" generator=\"{generator}\" >\n"
    idx = -1
    for pt in coordinates :
        #https://wiki.openstreetmap.org/wiki/Node
        osm_xml+="\t<node id=\"{}\" lat=\"{}\" lon=\"{}\" />\n".format(idx,pt[0],pt[1])
        idx -= 1

    osm_xml+="\t<way id=\"{}\" visible=\"true\">\n".format(idx)
    idx = -1
    for pt in coordinates :
        osm_xml+="\t\t<nd ref=\"{}\" />\n".format(idx)
        idx -= 1
    osm_xml+="\t<nd ref=\"{}\" />\n".format(-1)
    osm_xml+="\t<tag k=\"{}\" v=\"{}\" />\n".format("building", "yes")
    osm_xml+="\t<tag k=\"{}\" v=\"{}\" />\n".format("building", featureName)
    # Add name here from database
    osm_xml+="\t</way>\n"
    osm_xml+="</osm>\n"
    return osm_xml
