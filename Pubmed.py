from Bio import Entrez
from Bio import Medline

# I made the searchTerm global because it is referenced in every method
searchTerm = "orchid"


def main():
    # I tell the databases who I am
    Entrez.email = "annemiekeschonthaler@gmail.com"
    # this term could be a gene or a description
    # searchTerm = "orchid"
    maxResults = getAmountOfResults()
    print(maxResults)
    # There is no need to look for results if there aren't any
    if maxResults != 0:
        idList = getPubmedIDs(maxResults)
        getPubmedArticlesByID(idList)


# This method checks how many potential results there are with a query. This is needed to give a maximum of results
# to pubmed, to fetch.
def getAmountOfResults():
    # Dit is om te zoeken in alle databases op de term "orchid"
    handle = Entrez.egquery(term=searchTerm)
    # Deze regel is om de output die terug komt te lezen
    record = Entrez.read(handle)
    # I make sure that maxResults had a value
    maxResults = 0
    for row in record["eGQueryResult"]:
        if row["DbName"] == "pubmed":
            maxResults = row["Count"]

    return maxResults


def getPubmedIDs(maxResults):
    handle = Entrez.esearch(db="pubmed", term=searchTerm, retmax=maxResults)
    record = Entrez.read(handle)
    handle.close()
    idlist = record["IdList"]
    return idlist


def getPubmedArticlesByID(idList):
    handle = Entrez.efetch(db="pubmed", id=idList, rettype="medline",
                           retmode="text")
    records = Medline.parse(handle)
    records = list(records)
    for record in records:
        # todo fix this and add all the output thingies needed
        pubmedEntryInstance = pubmedEntry(record, searchTerm)


# todo maak deze class af met alle gevraagde dingen

class pubmedEntry():
    # The __ make this a private attribute to encapsule it
    __geneID = ""

    def __init__(self, pubmedID, searchterm):
        # todo this kip print is only here to know that is works okay don't judge me plz
        print("kip")

    def setGeneID(self, geneIDIncoming):
        self.geneID = geneIDIncoming
        # todo maak hier misschien iets wat controleert of er een recenter synoniem is van de gennaam


main()
