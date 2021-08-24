from pymongo import MongoClient
import rdflib


def getMongoData():
    # db connection
    client = MongoClient('mongo', 27021)
    db = client['mantistable']

    # main dict to contain mongodb documents
    index_link = {"id": {}, "sub_id": {}, "links": {}, "sub_links": {}, "attr_id": {}, "attrs": {}}

    # get infotable
    collection = db['mantistable_infotable']
    docs_iterable = collection.find({})
    for document in docs_iterable:
        data = document['ne_cols']
        for num in data:
            if not ("rel" in num):
                if num["type"] is not None and num["type"] != "":
                    index_link["id"][num["index"]] = num["type"]
                    index_link["links"][num["index"]] = list()
            else:
                if num["rel"] is not None and num["rel"] != "":
                    index_link["sub_id"][num["index"]] = num["rel"]
                    index_link["sub_links"][num["index"]] = list()

        data = document['lit_cols']
        for num in data:
            if num["rel"] is not None:
                index_link["attr_id"][num["index"]] = num["rel"]
                index_link["attrs"][num["index"]] = list()

        data = document['no_ann_cols']
        for num in data:
            if num["header"] is not None:
                index_link["attr_id"][num["index"]] = num["header"]
                index_link["attrs"][num["index"]] = list()

    # get datatable
    collection = db['mantistable_tabledata']
    docs_iterable = collection.find({})
    for document in docs_iterable:
        data = document['data']
        for index in index_link["id"].keys():
            for i in range(len(data[index])):
                if "linked_entity" in data[index][i] and data[index][i]["linked_entity"] is not None and data[index][i]["linked_entity"] != "null":
                    index_link["links"][index].append({"id": i, "value": data[index][i]["linked_entity"]})

        for index in index_link["sub_id"].keys():
            for i in range(len(data[index])):
                if "linked_entity" in data[index][i] and data[index][i]["linked_entity"] is not None and data[index][i]["linked_entity"] != "null":
                    index_link["sub_links"][index].append({"id": i, "value": data[index][i]["linked_entity"]})

        for index in index_link["attr_id"].keys():
            for i in range(len(data[index])):
                if "value_original" in data[index][i] and data[index][i]["value_original"] is not None and data[index][i]["value_original"] != "null":
                    index_link["attrs"][index].append({"id": i, "value": data[index][i]["value_original"]})

    return index_link


def mongo2rdf(index_link):
    # load rdf header and footer
    # NOTE: use Assets().get_asset("export/intro.txt") instead
    with open("mantistable/private/export/intro.txt", "r", encoding="utf-8", newline="\r\n") as f:
        intro = f.read()
    with open("mantistable/private/export/outro.txt", "r", encoding="utf-8", newline="\r\n") as f:
        outro = f.read()

    # data scan and rdf string build
    rdf = intro
    for index in index_link["id"].keys():
        for item in index_link["links"][index]:
            rdf += '\r\n    <rdf:Description rdf:about="' + item["value"] + '">'
            rdf += '\r\n        <rdf:type rdf:resource="' + index_link["id"][index] + '" />'
            rdf += '\r\n        <dbo:columnId rdf:datatype="http://www.w3.org/2001/XMLSchema#integer">' + str(
                index) + '</dbo:columnId>'
            rdf += '\r\n        <dbo:rowId rdf:datatype="http://www.w3.org/2001/XMLSchema#integer">' + str(
                item["id"]) + '</dbo:rowId>'
            for sub_id in index_link["sub_id"].keys():
                rdf += '\r\n        <dbo:' + index_link["sub_id"][sub_id][
                                             index_link["sub_id"][sub_id].rfind('/') + 1:] + ' rdf:resource="' + str(
                    [j["value"] for j in index_link["sub_links"][sub_id] if j["id"] == item["id"]][0]) + '" />'
            for attr_id in index_link["attr_id"].keys():
                if index_link["attr_id"][attr_id] != "":
                    rdf += '\r\n        <dbo:' + index_link["attr_id"][attr_id][
                                                index_link["attr_id"][attr_id].rfind('/') + 1:]
                    try:
                        int(str([j["value"] for j in index_link["attrs"][attr_id] if j["id"] == item["id"]][0]).replace(",",
                                                                                                                        ""))
                        rdf += ' rdf:datatype="http://www.w3.org/2001/XMLSchema#integer">'
                    except:
                        try:
                            float(str([j["value"] for j in index_link["attrs"][attr_id] if j["id"] == item["id"]][0]))
                            rdf += ' rdf:datatype="http://www.w3.org/2001/XMLSchema#float">'
                        except:
                            if (str([j["value"] for j in index_link["attrs"][attr_id] if j["id"] == item["id"]][
                                        0]).lower() == "true" or str(
                                [j["value"] for j in index_link["attrs"][attr_id] if j["id"] == item["id"]][
                                    0]).lower() == "false"):
                                rdf += ' rdf:datatype="http://www.w3.org/2001/XMLSchema#bool">'
                            else:
                                rdf += ' rdf:datatype="http://www.w3.org/2001/XMLSchema#string">'
                    rdf += str([j["value"] for j in index_link["attrs"][attr_id] if j["id"] == item["id"]][0])
                    rdf += '</dbo:' + index_link["attr_id"][attr_id][index_link["attr_id"][attr_id].rfind('/') + 1:] + '>'
            rdf += '\r\n    </rdf:Description>'
    rdf += outro

    # debug output
    '''
    with open("out.xml", "w+", encoding="utf-8", newline="\n") as f:
        f.write(rdf)
    '''

    # build rdf graph
    graph = rdflib.Graph()
    graph.parse(data=rdf, format='xml')

    return graph


def exportXml(graph):
    # with open("conversions/xml.xml", "w+", encoding="utf-8", newline="\r\n") as f:
    # f.write(graph.serialize(format='xml').decode("utf-8"))
    return graph.serialize(format='xml').decode("utf-8")


def exportNt(graph):
    # with open("conversions/nt.nt", "w+", encoding="utf-8", newline="\r\n") as f:
    # f.write(graph.serialize(format='nt').decode("utf-8"))
    return graph.serialize(format='nt').decode("utf-8")


def exportN3(graph):
    # with open("conversions/n3.n3", "w+", encoding="utf-8", newline="\r\n") as f:
    # f.write(graph.serialize(format='n3').decode("utf-8"))
    return graph.serialize(format='n3').decode("utf-8")


def exportTurtle(graph):
    # with open("conversions/turtle.ttl", "w+", encoding="utf-8", newline="\r\n") as f:
    # f.write(graph.serialize(format='turtle').decode("utf-8"))
    return graph.serialize(format='turtle').decode("utf-8")


def exportJsonLd(graph):
    # with open("conversions/json-ld.jsonld", "w+", encoding="utf-8", newline="\r\n") as f:
    # f.write(graph.serialize(format='json-ld').decode("utf-8"))
    return graph.serialize(format='json-ld').decode("utf-8")


def exportRdf(exportType):
    mongoData = getMongoData()
    graph = mongo2rdf(mongoData)
    if exportType == 'xml':
        return exportXml(graph)
    elif exportType == 'nt':
        return exportNt(graph)
    elif exportType == 'n3':
        return exportN3(graph)
    elif exportType == 'turtle':
        return exportTurtle(graph)
    elif exportType == 'jsonld':
        return exportJsonLd(graph)
