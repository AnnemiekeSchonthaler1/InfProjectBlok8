import requests


def SubmitPMIDList(pub_list, Format, Bioconcept):
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
