from Bio import Entrez
from Bio import Medline
import time
import weakref


def main(searchTerm, geneList):
    # This code formulates a query
    searchTerm = searchTerm+" AND ({})"
    for gene in geneList:
        searchTerm = searchTerm.format(gene + " OR {}")
    searchTerm = searchTerm.replace("OR {}", "")

    start = time.time()
    # I tell the databases who I am
    Entrez.email = "annemiekeschonthaler@gmail.com"
    # this term could be a gene or a description
    # searchTerm = "orchid"
    maxResults = getAmountOfResults(searchTerm)
    # There is no need to look for results if there aren't any
    if maxResults != 0:
        idList = getPubmedIDs(maxResults, searchTerm)
        getPubmedArticlesByID(idList, searchTerm)
    print("Elapsed time: "+str((time.time() - start)))


# This method checks how many potential results there are with a query. This is needed to give a maximum of results
# to pubmed, to fetch.
def getAmountOfResults(searchTerm):
    # Dit is om te zoeken in alle databases op de term "orchid"
    handle = Entrez.egquery(term=searchTerm)
    # Deze regel is om de output die terug komt te lezen
    record = Entrez.read(handle)
    # I make sure that maxResults had a value
    maxResults = 0
    for row in record["eGQueryResult"]:
        if row["DbName"] == "pubmed":
            maxResults = row["Count"]
    print(maxResults)
    return maxResults


def getPubmedIDs(maxResults, searchTerm):
    handle = Entrez.esearch(db="pubmed", term=searchTerm, retmax=maxResults)
    record = Entrez.read(handle)
    handle.close()
    idlist = record["IdList"]
    return idlist


def getPubmedArticlesByID(idList, searchTerm):
    pubmedList = []
    handle = Entrez.efetch(db="pubmed", id=idList, rettype="medline",
                           retmode="text")
    records = Medline.parse(handle)
    records = list(records)
    for record in records:
        # todo fix this and add all the output thingies needed
        pubmedEntryInstance = pubmedEntry(record.get("PMID"), searchTerm, record.get("AU"), record.get("MH"))
        pubmedEntryInstance.setDatePublication(record.get("DP"))
        pubmedEntryInstance.setAbout(record.get("AB"))
        print(record.get("AB"))


# todo maak deze class af met alle gevraagde dingen

class pubmedEntry():
    # The __ make this a private attribute to encapsule it
    __geneID = ""
    __datePublication = 0
    __about = ""
    instancesList = []

    def __init__(self, pubmedID, searchterm, author, mhTerms):
        self.pubmedID = pubmedID
        self.searchTerm = searchterm
        self.author = author
        self.mhTerms = mhTerms
        pubmedEntry.instancesList.append(self)

    def setGeneID(self, geneIDIncoming):
        self.__geneID = geneIDIncoming
        # todo maak hier misschien iets wat controleert of er een recenter synoniem is van de gennaam

    def setDatePublication(self, date):
        self.__datePublication = date
        # todo zorg dat alle dates on hetzelfde format zijn, wat sorteerbaar is

    def setAbout(self, about):
        if about is not None:
            self.__about = about


main("Developmental delay", ["POLR3B", "CHD8", "KDM3B"])

# print(pubmedEntry.instancesList)
# for item in pubmedEntry.instancesList:
#     print(item.author)
