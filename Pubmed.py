from Bio import Entrez
from Bio import Medline
import time
import mysql.connector
from mysql.connector import Error

dictMonths = {'Jan': '/01/', 'Feb': '/02/', 'Mar': '/03/',
              'Apr': '/04/', 'May': '/05/', 'Jun': '/06/',
              'Jul': '/07/', 'Aug': '/08/', 'Sep': '/09/',
              'Oct': '/10/', 'Nov': '/11/', 'Dec': '/12/',
              '': '/01/'}
mindate = "1990/01/01"
maxdate = "2020/01/01"


def main(searchList, geneList, email, searchDate, today):
    dictSynonyms = {}
    global mindate
    mindate = str(searchDate).replace("-", "/")
    print(mindate)
    global maxdate
    maxdate = str(today).replace("-", "/")
    start = time.time()
    # I add the genes to a dict to keep track of gene and synonym
    for gene in geneList:
        if not gene in dictSynonyms.keys():
            dictSynonyms[gene] = []
        else:
            print("Waarom krijg ik dubbele wat is deze")
            # todo werp een exception op als dit gebeurt
    # I call a function to formulate a query
    searchTerm = makeQuery(searchList, geneList, dictSynonyms)
    print(dictSynonyms)
    # I set the email
    Entrez.email = email
    maxResults = getAmountOfResults(searchTerm)
    # There is no need to look for results if there aren't any
    if int(maxResults) != 0:
        idList = getPubmedIDs(maxResults, searchTerm)
        if not len(idList) == 0:
            getPubmedArticlesByID(idList, searchTerm)
    pubmedEntry.dictSynonyms = dictSynonyms
    print("Elapsed time: " + str((time.time() - start)))


def makeQuery(searchList, geneList, dictsynonym):
    searchTerm = "({})"

    for term in searchList:
        term = term + " OR {} "
        searchTerm = searchTerm.format(str(term))
    searchTerm = searchTerm.replace(" OR {}", "")
    searchTerm += " AND ({})"

    geneList = findSynonyms(geneList, dictsynonym)
    # This code formulates a query
    for gene in geneList:
        searchTerm = searchTerm.format(gene + " OR {}")
    searchTerm = searchTerm.replace("OR {}", "")
    print(searchTerm)
    return searchTerm


# Deze functie breidt de genlijst uit met de synoniemen.
def findSynonyms(geneList, dictSynonyms):
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
    handle = Entrez.esearch(db="pubmed", term=searchTerm, retmax=maxResults, datetype='pdat', mindate=mindate,
                            maxdate=maxdate)
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
        print(record)
        pubmedEntryInstance = pubmedEntry(record.get("PMID"), searchTerm, record.get("AU"), record.get("MH"))
        pubmedEntryInstance.setDatePublication(record.get("DP"))
        pubmedEntryInstance.setAbout(record.get("AB"))
        pubmedEntryInstance.setTitle(record.get("TI"))


class pubmedEntry():
    # The __ make this a private attribute to encapsule it
    __geneID = ""
    __datePublication = 0
    __about = ""
    __title = ""
    instancesList = []
    dictSynonyms = {}

    def __init__(self, pubmedID, searchterm, author, mhTerms):
        self.pubmedID = pubmedID
        self.searchTerm = searchterm
        self.author = author
        self.mhTerms = mhTerms
        pubmedEntry.instancesList.append(self)

    def setGeneID(self, geneIDIncoming):
        self.__geneID = geneIDIncoming

    def setDatePublication(self, date):
        # so it will split into at least 3 parts
        # date += "  "
        # dateList = str(date).split(" ")
        # dateList[1] = dictMonths.get(dateList[1])
        # if dateList[2] == '':
        #     dateList[2] = '01'
        # date = ''.join(dateList)
        # date = date.replace(" ", "")
        self.__datePublication = date

    def setAbout(self, about):
        if about is not None:
            self.__about = about

    def getAbout(self):
        return self.__about

    def getSynonyms(self):
        # this returns a dict with as key the given geneid and as value the synonyms
        return self.dictSynonyms

    def setTitle(self, title):
        self.__title = title

    def getTitle(self):
        return self.__title


#main("Homo sapiens", ["ATP8", "A2ML1"], "annemiekeschonthaler@gmail.com")
# print(pubmedEntry.instancesList)
# for item in pubmedEntry.instancesList:
#     print(item.author)
