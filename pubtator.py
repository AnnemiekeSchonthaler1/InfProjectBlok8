import io

import requests
import sys
import json as js


def SubmitPMIDList(pub_list, Format, Bioconcept):
    json = {}

    #
    # load pmids
    #

    json = {"pmids": [pmid for pmid in pub_list]}
    print(json)
    #
    # load bioconcepts
    #
    if Bioconcept != "":
        json["concepts"] = Bioconcept.split(",")

    #
    # request
    #
    r = requests.post("https://www.ncbi.nlm.nih.gov/research/pubtator-api/publications/export/" + Format, json=json)
    if r.status_code != 200:
        print("[Error]: HTTP code " + str(r.status_code))
    else:
        return r.text.encode("utf-8")

# if __name__ == "__main__":
#
#     arg_count = 0
#     for arg in sys.argv:
#         arg_count += 1
#     if arg_count < 2 or (sys.argv[2] != "pubtator" and sys.argv[2] != "biocxml" and sys.argv[2] != "biocjson"):
#         print("\npython SubmitPMIDList.py [InputFile] [Format] [BioConcept]\n\n")
#         print("\t[Inputfile]: a file with a pmid list\n")
#         print("\t[Format]: pubtator (PubTator), biocxml (BioC-XML), and biocjson (JSON-XML)\n")
#         print(
#             "\t[Bioconcept]: gene, disease, chemical, species, proteinmutation, dnamutation, snp, and cellline. Default includes all.\n")
#         print("\t* All input are case sensitive.\n\n")
#         print("Eg., python SubmitPMIDList.py examples/ex.pmid pubtator gene,disease\n\n")

# example call of funciton
Inputfile = [10720488]
Format = "biocjson"
Bioconcept = ""
output = SubmitPMIDList(Inputfile, Format, Bioconcept)

y = js.loads(output)
# print(y)
# # for z in y["passages"]: print(z["infons"])
# print(y["accessions"])
for passage in y["passages"]:
    for annotation in passage["annotations"]:
        print("-------")
        print(annotation["text"])
        print(annotation["infons"]["identifier"])
        print(annotation["infons"]["type"])


# handle = Entrez.einfo()
# record = Entrez.read(handle)
# print(record)

# tree = ET.fromstring(output)
# print(tree)
# root = tree.getroot()
# print(root)
#
# f = io.StringIO(output)
# # doc = xml.dom.minidom.parse(f)
# # passage = doc.getElementsByTagName("passage")
# # print(passage)
# # for p in passage:
# #     print(p.getAttribute("annotation"))
#
# tree = ET.parse(f)
# root = tree.getroot()
# print(root)
# for child in root:
#     if str(child.tag) == "document":
#         for childnest in child:
#             if str(childnest.tag) == "passage":
#                 for childnestpassage in childnest:
#                     if childnestpassage.tag == "annotation":
#                         print(childnestpassage.attrib)
#                         for childnestid in childnestpassage:
#                             print(childnestid.get("text"))
#                             #print(childnestid.attrib)
#                             print(childnestid.get("offset"))
#                             # #print(childnestid.tag)
#                             #print(childnestid.get("text"))
#                             # if childnestid.tag == "infon":
#                             #     print("kip")
#                             # elif childnestid.tag == "text":
#                             #     print(childnestid.find("text"))
#
# for item in root.findall("text"):
#     print(item)

