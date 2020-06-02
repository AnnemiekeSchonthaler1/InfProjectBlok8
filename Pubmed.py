from Bio import Entrez, Medline
import time
import mysql.connector
from mysql.connector import Error
import pubtator
import json
from datetime import datetime
from datetime import date

# I make the dates global
mindate = ""
maxdate = ""

geneclassDict = {}
alleTermen = []

def main(searchList, geneList, email, searchDate, today, organism, maxArticles):
    # Zodat de dict bij elke run wordt geleegd
    global geneclassDict
    global alleTermen
    geneclassDict = {}
    alleTermen = []

    searchList.append(organism)

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
    maxArticles = int(maxArticles)
    if int(maxResults) > maxArticles:
        print("Ik heb ingegrepen en dit aantal naar beneden gehaald")
        maxResults = maxArticles
    # There is no need to look for results if there aren't any
    print("Het aantal mogelijke resultaten is " + str(maxResults))
    if int(maxResults) != 0:
        print("En ik ben ermee aan de slag gegaan")
        idList = getPubmedIDs(maxResults, searchTerm)
        print("Ik heb nu ook de id's opgehaald en ja dit printje is dubbel maar idc oke")
        # idList = idList[0:500]
        ArticleInfoRetriever(idList, searchTerm, geneList, searchList)
    print("Dit duurt " + str(time.time() - start) + " secondes")


def makeQuery(searchList, geneList, dictsynonym):
    searchTerm = "({})"

    for term in searchList:
        term = term + " OR {} "
        searchTerm = searchTerm.format(str(term))
    searchTerm = searchTerm.replace(" OR {}", "")
    searchTerm += " AND ({})"

    geneList = findSynonyms(geneList, dictsynonym)
    print(geneList)
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
        connection = mysql.connector.connect(
            host='hannl-hlo-bioinformatica-mysqlsrv.mysql.database.azure.com',
            db='owe7_pg1',
            user='owe7_pg1@hannl-hlo-bioinformatica-mysqlsrv',
            password="blaat1234")
        cursor = connection.cursor()
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
    print(mindate, maxdate)
    handle = Entrez.esearch(db="pubmed", term=searchTerm, retmax=maxResults, datetype='pdat', mindate=mindate,
                            maxdate=maxdate)
    record = Entrez.read(handle)
    handle.close()
    idlist = record["IdList"]
    print("got id's")
    return idlist


def readGenePanels(filename):
    panels = {}
    for regel in open(filename, "r").readlines():
        gene = regel.split("\t")[0]
        panel = regel.split("\t")[1]
        if not gene in panels.keys():
            panels[gene] = [panel]
        else:
            print("Er mogen geen dubbele in zitten?????")
    return panels


def ArticleInfoRetriever(idList, searchTerm, geneList, searchList):
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
                articleInfoProcessor(output, searchTerm, allAnnotations, geneList, searchList)
    else:
        output = pubtator.SubmitPMIDList(idList, "biocjson",
                                         "gene, disease, chemical, species, proteinmutation, dnamutation")
        if not output is None:
            articleInfoProcessor(output, searchTerm, allAnnotations, geneList, searchList)

    print("En ik ben klaar met pubtator")
    pubmedEntry.allAnnotations = allAnnotations
    allAnnotationIds = set(allAnnotations.keys())
    remainingIds = remainingIds.difference(allAnnotationIds)
    getPubmedArticlesByID(list(remainingIds), searchTerm, geneList)


# Deze functie haalt de nodige informatie uit het json file
def articleInfoProcessor(pubtatoroutput, searchTerm, allAnnotations, geneList, searchList):
    # todo stop dit allemaal in de database
    if not len(pubtatoroutput) == 0:
        for entry in pubtatoroutput.split("\n"):
            # {identifier:[[names], count]}
            accessionDict = {}
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
                # Dit bevat de accessiecodes van de gezochte termen gevonden in de artikelen
                termsList = []
                for passage in y["passages"]:
                    if passage["infons"]["type"] == "title":
                        pubmedEntryInstance.setTitle(passage["text"])
                    elif passage["infons"]["type"] == "abstract":
                        pubmedEntryInstance.setAbout(passage["text"])
                    for annotation in passage["annotations"]:
                        # Dit is voor de termen die hij heeft gevonen
                        name = annotation["text"]
                        identifier = annotation["infons"]["identifier"]
                        type = annotation["infons"]["type"]

                        if name in geneList or name in searchList:
                            if not identifier in termsList:
                                termsList.append(identifier)
                                if not identifier in alleTermen:
                                    alleTermen.append(identifier)

                        # zodat er een score kan worden berekend
                        if not identifier in accessionDict.keys():
                            accessionDict[identifier] = [[name],1]
                        else:
                            if not name in accessionDict[identifier][0]:
                                accessionDict[identifier][0].append(name)
                            accessionDict[identifier][1] += 1


                        # Ik stop het in de twee dicts
                        if not type in annotations[pubmedid].keys():
                            annotations[pubmedid][type] = [name]
                        else:
                            annotations[pubmedid][type].append(name)

                        if not type in allAnnotations[pubmedid].keys():
                            allAnnotations[pubmedid][type] = [name]
                        else:
                            if not name in allAnnotations[pubmedid][type]:
                                allAnnotations[pubmedid][type].append(name)

                        # Deze code gaat zorgen dat er een class komt met per gen artikelen bedeeld ipv andersom
                        if type == "Gene":
                            if not identifier in geneclassDict.keys():
                                newGeneEntry = geneEntry(identifier)
                                newGeneEntry.addName(name)
                                newGeneEntry.addArticleId(pubmedid)
                                geneclassDict[identifier] = newGeneEntry
                            else:
                                geneclassDict[identifier].addName(name)
                                geneclassDict[identifier].addArticleId(pubmedid)

                pubmedEntryInstance.setMLinfo(annotations)
                pubmedEntryInstance.usedPubtator()
                pubmedEntryInstance.setScore(calculateScores(termsList, accessionDict, pubmedEntryInstance))


def getPubmedArticlesByID(idList, searchTerm, genelist):
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
        if not record.get("AB") is None:
            for word in record.get("AB"):
                if word in genelist:
                    print("Ik maak entries")
                    if not word in geneclassDict.keys():
                        newGeneEntry = geneEntry(word)
                        newGeneEntry.addArticleId(record.get("PMID"))
                        newGeneEntry.addName(name=word)
                        geneclassDict[word] = newGeneEntry
                    else:
                        geneclassDict[word].addArticleId(record.get("PMID"))
                        geneclassDict[word].addName(name=word)


def calculateScores(termsList, accessionDict, pubmedInstance):
    # dit zijn alle termen die voorkomen in alle artikelen
    print("alleTermen: ", alleTermen)
    # dit zijn de termen die voorkomen in dit artikel
    print("termslist: ", termsList)
    # Dit zijn alle termen die voorkomen in het artikel met hun count ({accessie:[namen, count]})
    print("accessionDict: ",accessionDict)
    print("Matchende object:")
    voorkomensTermen = 0
    for item in alleTermen:
        if item in accessionDict.keys():
            aantalvoorkomensItem = accessionDict.get(item)[1]
            voorkomensTermen += aantalvoorkomensItem
    print("voorkomensTermen: ", voorkomensTermen)

    alleTermenVoorkomens = 0
    for value in accessionDict.values():
        alleTermenVoorkomens += value[1]

    for item in termsList:
        print("item:", item)



    #print(pubmedInstance)
    yearsAgo = datetime.today().year - pubmedInstance.getDatePublication().year
    today = datetime.today()
    then = pubmedInstance.getDatePublication()
    monthsAgo = (today.year - then.year) * 12 + (today.month - then.month)
    print(monthsAgo)

    global maxdate
    print(maxdate)
    maxdateSplit = maxdate.split("/")
    maxdateFormatted = date(int(maxdateSplit[0]), int(maxdateSplit[1]), int(maxdateSplit[2]))

    maxMonthsAgo = (today.year - maxdateFormatted.year) * 12 + (today.month - maxdateFormatted.month)
    print(maxMonthsAgo)
    
    score = (((voorkomensTermen/alleTermenVoorkomens)+1) + ((len(termsList)/len(accessionDict.keys()))+1))/((monthsAgo/maxMonthsAgo)+1)
    print("score: "+str(score))
    # for key, value in pubmedEntry.instancesDict.items():
    #     id = key
    #     if value.getPubtatorStatus():
    #         yearsAgo = datetime.today().year - value.getDatePublication().year
    #         try:
    #             # Ik kijk hoeveel van de gevonden genen in mijn lijst staan
    #             alleGevondenGenen = list(value.getMlinfo()[id]["Gene"])
    #             voorkomensGezochteGen = 0
    #             for gene in geneList:
    #                 if gene in alleGevondenGenen:
    #                     voorkomensGezochteGen += alleGevondenGenen.count(gene)
    #             alleTermen = len(alleGevondenGenen)
    #         except KeyError:
    #             voorkomensGezochteGen = 0
    #             alleTermen = 0
    #             alleGevondenGenen = []
    #
    #         searchWordsFound = []
    #         voorkomensGezochteTerm = 0
    #         alleZoekTermen = 0
    #         # En ik kijk hoeveel van de gevonden zoektermen in mijn lijst staan
    #         if list(value.getMlinfo()[id].keys()).count(["Chemical"]) > 0:
    #             searchWordsFound += value.getMlinfo()[id]["Chemical"]
    #         if list(value.getMlinfo()[id].keys()).count(["Disease"]) > 0:
    #             searchWordsFound += value.getMlinfo()[id]["Disease"]
    #         if list(value.getMlinfo()[id].keys()).count(["Mutation"]) > 0:
    #             searchWordsFound += value.getMlinfo()[id]["Mutation"]
    #         for word in searchList:
    #             if word in searchWordsFound:
    #                 voorkomensGezochteTerm += searchWordsFound.count(word)
    #                 alleZoekTermen = len(searchWordsFound)
    #
    #         if not alleGevondenGenen == []:
    #             aantalGenenGematcht = 0
    #             for gene in geneList:
    #                 if gene in alleGevondenGenen:
    #                     aantalGenenGematcht += 1
    #         else:
    #             aantalGenenGematcht = 0
    #
    #         aantalTermenGematcht = 0
    #         for term in searchList:
    #             if term in searchWordsFound:
    #                 aantalTermenGematcht += 1
    #
    #         try:
    #             if organism in value.getMlinfo()[id]["Species"]:
    #                 organismeValue = 2
    #                 print("organismeleef")
    #             else:
    #                 organismeValue = 1
    #         except KeyError:
    #             organismeValue = 1
    #
    #         score = (voorkomensGezochteGen / (len(alleGevondenGenen) + 1) + (
    #                 voorkomensGezochteTerm / (alleZoekTermen + 1))
    #                  + (aantalGenenGematcht / (len(geneList) + 1)) + (aantalTermenGematcht / (len(searchList) + 1))) / (
    #                         yearsAgo + 1)
    #         value.setScore(score)
    score = 0
    return score

class geneEntry:
    __names = []
    __pubIds = []
    __id = ""
    instancesDict = {}

    def __init__(self, genId):
        self.__id = genId
        self.instancesDict[genId] = self

    def addName(self, name):
        if not name in self.__names:
            self.__names.append(name)

    def addArticleId(self, pubId):
        if not pubId in self.__pubIds:
            self.__pubIds.append(pubId)


class pubmedEntry:
    # The __ make this a private attribute to encapsulate it
    __geneID = ""
    __datePublication = 0
    __about = ""
    __title = ""
    __score = None
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
        self.__score = score

    def getScore(self):
        return self.__score

