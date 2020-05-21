from Bio import Entrez, Medline
import time
import mysql.connector
from mysql.connector import Error
import pubtator
import json
from datetime import datetime

# I make a connection with the database
connection = mysql.connector.connect(
    host='hannl-hlo-bioinformatica-mysqlsrv.mysql.database.azure.com',
    db='rucia',
    user='rucia@hannl-hlo-bioinformatica-mysqlsrv',
    password="kip")
cursor = connection.cursor()

# I make the dates global
mindate = ""
maxdate = ""


def main(searchList, geneList, email, searchDate, today):
    print("Pubtator is zijn ding gaan doen")
    start = time.time()
    pubmedEntry.allAnnotations = {}

    # I set the dates to the entered values
    global mindate
    global maxdate
    mindate = str(searchDate).replace("-", "/")
    maxdate = str(today).replace("-", "/")

    # I set the email to the given email
    Entrez.email = email

    # I add the genes to a dict to keep track of gene and synonym
    dictSynonyms = {}
    for gene in geneList:
        if not gene in dictSynonyms.keys():
            dictSynonyms[gene] = []
    # I call a function to formulate a query
    # searchTerm contains this query
    searchTerm, geneList = makeQuery(searchList, geneList, dictSynonyms)

    print("De query is ook geformuleerd")

    # I look for articles with the formulated query
    maxResults = getAmountOfResults(searchTerm)
    print("Ik heb gekeken hoeveel id's er kunnen worden opgehaald")
    # Het maximale wat kan is 500.000
    plafond = 5000
    if int(maxResults) > plafond:
        print("Ik heb ingegrepen en dit aantal naar beneden gehaald")
        maxResults = plafond
    # There is no need to look for results if there aren't any
    print("Het aantal mogelijke resultaten is " + str(maxResults))
    if int(maxResults) != 0:
        print("En ik ben ermee aan de slag gegaan")
        idList = getPubmedIDs(maxResults, searchTerm)
        print("Ik heb nu ook de id's opgehaald en ja dit printje is dubbel maar idc oke")
        # idList = idList[0:500]
        ArticleInfoRetriever(idList, searchTerm)
    calculateScores(searchList, geneList)
    print("Dit duurt " + str(time.time() - start) + " secondes")


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
    searchTerm = searchTerm.replace("AND {}", "")
    return searchTerm, geneList


# Deze functie breidt de genlijst uit met de synoniemen.
def findSynonyms(geneList, dictSynonyms):
    records = ""
    try:
        if connection.is_connected():
            db_Info = connection.get_server_info()
            print("Connected to MySQL Server version ", db_Info)
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
            if record[1] not in synonyms and not record[1] == "":
                geneList.append(record[1])
                dictSynonyms.get(str(record[0])).append(record[1])
            synonyms.append(record[1])
    pubmedEntry.dictSynonyms = dictSynonyms
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
    return maxResults


def getPubmedIDs(maxResults, searchTerm):
    handle = Entrez.esearch(db="pubmed", term=searchTerm, retmax=maxResults, datetype='pdat', mindate=mindate,
                            maxdate=maxdate)
    record = Entrez.read(handle)
    handle.close()
    idlist = record["IdList"]
    print("got id's")
    return idlist


def ArticleInfoRetriever(idList, searchTerm):
    print("Oke ik begin met pubtator")
    allAnnotations = {}
    idList = list(idList)
    # Ik haal alle dubbele er uit
    idList = set(idList)
    idList = list(idList)
    slice = 500
    remainingIds = set(idList)
    if len(idList) > slice:
        for i in range(slice, len(idList), slice):
            output = pubtator.SubmitPMIDList(idList[i - slice:i], "biocjson",
                                             "gene, disease, chemical, species, proteinmutation, dnamutation")
            if not output is None:
                articleInfoProcessor(output, searchTerm, allAnnotations)
    else:
        output = pubtator.SubmitPMIDList(idList, "biocjson",
                                         "gene, disease, chemical, species, proteinmutation, dnamutation")
        if not output is None:
            articleInfoProcessor(output, searchTerm, allAnnotations)

    print("En ik ben klaar met pubtator")
    pubmedEntry.allAnnotations = allAnnotations
    allAnnotationIds = set(allAnnotations.keys())
    remainingIds = remainingIds.difference(allAnnotationIds)
    getPubmedArticlesByID(list(remainingIds), searchTerm)


# Deze functie haalt de nodige informatie uit het json file
def articleInfoProcessor(pubtatoroutput, searchTerm, allAnnotations):
    # todo stop dit allemaal in de database
    if not len(pubtatoroutput) == 0:
        for entry in pubtatoroutput.split("\n"):
            annotations = {}
            # Hij mag niet leeg zijn want anders wordt json boos
            if not len(entry) == 0:
                y = json.loads(entry)
                pubmedid = y["pmid"]
                pubmedid = str(pubmedid)
                annotations[pubmedid] = {}
                allAnnotations[pubmedid] = {}
                datePublished = y["created"]["$date"]
                datePublished = datetime.fromtimestamp(datePublished / 1000.0)
                author = y["authors"]
                pubmedEntryInstance = pubmedEntry(pubmedid, searchTerm, author)
                pubmedEntryInstance.setDatePublication(datePublished)
                for passage in y["passages"]:
                    if passage["infons"]["type"] == "title":
                        pubmedEntryInstance.setTitle(passage["text"])
                    elif passage["infons"]["type"] == "abstract":
                        pubmedEntryInstance.setAbout(passage["text"])
                    for annotation in passage["annotations"]:
                        name = annotation["text"]
                        identifier = annotation["infons"]["identifier"]
                        type = annotation["infons"]["type"]
                        if not type in annotations[pubmedid].keys():
                            annotations[pubmedid][type] = [name]
                        else:
                            annotations[pubmedid][type].append(name)
                        if not type in allAnnotations[pubmedid].keys():
                            allAnnotations[pubmedid][type] = [name]
                        else:
                            if not name in allAnnotations[pubmedid][type]:
                                allAnnotations[pubmedid][type].append(name)
                pubmedEntryInstance.setMLinfo(annotations)
                pubmedEntryInstance.usedPubtator()


def getPubmedArticlesByID(idList, searchTerm):
    print("pubtator had geen match")
    handle = Entrez.efetch(db="pubmed", id=idList, rettype="medline",
                           retmode="text")
    records = Medline.parse(handle)
    records = list(records)
    for record in records:
        pubmedEntryInstance = pubmedEntry(record.get("PMID"), searchTerm, record.get("AU"))
        pubmedEntryInstance.setDatePublication(record.get("DP"))
        pubmedEntryInstance.setAbout(record.get("AB"))
        pubmedEntryInstance.setTitle(record.get("TI"))


def calculateScores(searchList, geneList):
    for key, value in pubmedEntry.instancesDict.items():
        id = key
        if value.getPubtatorStatus():
            yearsAgo = datetime.today().year - value.getDatePublication().year
            try:
                # Ik kijk hoeveel van de gevonden genen in mijn lijst staan
                genenGevonden = list(value.getMlinfo()[id]["Gene"])
                voorkomensTerm = 0
                for gene in geneList:
                    if gene in genenGevonden:
                        voorkomensTerm += genenGevonden.count(gene)
                alleTermen = len(genenGevonden)
            except KeyError:
                voorkomensTerm = 0
                alleTermen = 0

            searchWords = []
            # En ik kijk hoeveel van de gevonden zoektermen in mijn lijst staan
            if list(value.getMlinfo()[id].keys()).count(["Chemical"]) > 0:
                searchWords += value.getMlinfo()[id]["Chemical"]
            if list(value.getMlinfo()[id].keys()).count(["Disease"]) > 0:
                searchWords += value.getMlinfo()[id]["Disease"]
            if list(value.getMlinfo()[id].keys()).count(["Mutation"]) > 0:
                searchWords += value.getMlinfo()[id]["Mutation"]
            for word in searchList:
                if word in searchWords:
                    voorkomensTerm += searchWords.count(word)
                    alleTermen += len(searchWords)

            allValues = []
            for mlValue in value.getMlinfo()[id].values():
                allValues += mlValue

            foundTerms = 0
            for term in (geneList + searchList):
                if term in allValues:
                    foundTerms += 1

            if not alleTermen == 0:
                print(id)
                print("score: " + str(
                    ((voorkomensTerm / alleTermen) + (foundTerms / len(geneList + searchList)) * 2) - yearsAgo))
                value.setScore(score=((voorkomensTerm / alleTermen) + (foundTerms / len(geneList + searchList)) * 2) - yearsAgo)
            else:
                print(id)
                print("score: " + str((0 + (foundTerms / len(geneList + searchList)) * 2) - yearsAgo))
                value.setScore(score=(0 + (foundTerms / len(geneList + searchList)) * 2) - yearsAgo)


class pubmedEntry():
    # The __ make this a private attribute to encapsulate it
    __geneID = ""
    __datePublication = 0
    __about = ""
    __title = ""
    __withPubtator = False
    instancesDict = {}
    dictSynonyms = {}
    __MLinfo = {}
    allAnnotations = {}
    ML_single = {}

    def __init__(self, pubmedID, searchterm, author):
        self.pubmedID = str(pubmedID)
        self.searchTerm = searchterm
        self.author = author

        pubmedEntry.instancesDict[pubmedID] = self

    def setGeneID(self, geneIDIncoming):
        self.__geneID = geneIDIncoming

    def setDatePublication(self, date):
        self.__datePublication = date

    def getDatePublication(self):
        return self.__datePublication

    def setAbout(self, about):
        if about is not None:
            self.__about = about

    def setMLinfo(self, annotations):
        self.__MLinfo = annotations

    def getMlinfo(self):
        return self.__MLinfo

    def getAbout(self):
        return self.__about

    def getSynonyms(self):
        # this returns a dict with as key the given geneid and as value the synonyms
        return self.dictSynonyms

    def setTitle(self, title):
        self.__title = title

    def getTitle(self):
        return self.__title

    def usedPubtator(self):
        self.__withPubtator = True

    def getPubtatorStatus(self):
        return self.__withPubtator

    def setScore(self, score):
        self.score = score
        
    def getScore(self):
        return self.score

# main(["Homo sapiens"], ["ABCD1", "Aardappel"], "annemiekeschonthaler@gmail.com", "01-01-1900", "13-05-2020")
