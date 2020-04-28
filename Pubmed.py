from Bio import Entrez
from Bio import Medline
import time
import mysql.connector
from mysql.connector import Error

dictSynonyms = {}


def main(searchTerm, geneList, email):
    start = time.time()
    # I add the genes to a dict to keep track of gene and synonym
    for gene in geneList:
        if not gene in dictSynonyms.keys():
            dictSynonyms[gene] = []
        else:
            print("Waarom krijg ik dubbele wat is deze")
            # todo werp een exception op als dit gebeurt
    # I call a function to formulate a query
    searchTerm = makeQuery(searchTerm, geneList)
    print(dictSynonyms)
    # I set the email
    Entrez.email = email
    maxResults = getAmountOfResults(searchTerm)
    # There is no need to look for results if there aren't any
    if maxResults != 0:
        idList = getPubmedIDs(maxResults, searchTerm)
        getPubmedArticlesByID(idList, searchTerm)
    print("Elapsed time: " + str((time.time() - start)))


def makeQuery(searchTerm, geneList):
    geneList = findSynonyms(geneList)
    # This code formulates a query
    searchTerm = searchTerm + " AND ({})"
    for gene in geneList:
        searchTerm = searchTerm.format(gene + " OR {}")
    searchTerm = searchTerm.replace("OR {}", "")
    print(searchTerm)
    return searchTerm


# Deze functie breidt de genlijst uit met de synoniemen.
def findSynonyms(geneList):
    try:
        connection = mysql.connector.connect(
            host='hannl-hlo-bioinformatica-mysqlsrv.mysql.database.azure.com',
            db='rucia',
            user='rucia@hannl-hlo-bioinformatica-mysqlsrv',
            password="kip")
        if connection.is_connected():
            db_Info = connection.get_server_info()
            print("Connected to MySQL Server version ", db_Info)
            cursor = connection.cursor()
            cursor.execute("select symbool, vorig_symbool "
                           "from huidig_symbool join vorig_symbool on (symbool=huidig_symbool_symbool);")
            records = cursor.fetchall()
    except Error as e:
        print("Error while connecting to MySQL", e)
    finally:
        if (connection.is_connected()):
            cursor.close()
            connection.close()
            print("MySQL connection is closed")
    synonyms = []
    for record in records:
        if record[0] in geneList:
            if not record[1] in synonyms and not record[1] == "":
                geneList.append(record[1])
                dictSynonyms.get(str(record[0])).append(record[1])
            synonyms.append(record[1])
    return geneList


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
        pubmedEntryInstance = pubmedEntry(record.get("PMID"), searchTerm, record.get("AU"), record.get("MH"))
        pubmedEntryInstance.setDatePublication(record.get("DP"))
        pubmedEntryInstance.setAbout(record.get("AB"))
        print(record.get("AB"))


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

    def setDatePublication(self, date):
        self.__datePublication = date
        # todo zorg dat alle dates on hetzelfde format zijn, wat sorteerbaar is

    def setAbout(self, about):
        if about is not None:
            self.__about = about

    def getAbout(self):
        return self.__about

    def getSynonyms(self):
        # this returns a dict with as key the given geneid and as value the synonyms
        return dictSynonyms


main("Homo sapiens", ["ATP8", "POLR3B"], "annemiekeschonthaler@gmail.com")
# print(pubmedEntry.instancesList)
# for item in pubmedEntry.instancesList:
#     print(item.author)
