"""
Dit script zoekt de zoekopdracht op in pubmed via Entrez en Pubtator en verwerkt deze zo dat
deze kan worden gebruikt voor de visualisatie.
Verder zoekt dit naar synoniemen van gennamen in HGNC en berekent dit een score per artikel.
Gemaakt door: Annemieke Schönthaler
Versie: 2.0
Gemaakt op: 09-06-2020
"""

from Bio import Entrez, Medline
import time
import mysql.connector
from mysql.connector import Error
import pubtator
import json
from datetime import datetime
from datetime import date
import datetime as datetimewhole
from time import strptime

# Hier staat de datum in van vandaag en van tot wanneer
mindate = ""
maxdate = ""

# Dit zijn alle termen die voorkomen in alle artikelen van de gezochte termen en daar de accessiecodes van
alleTermen = []


def main(searchList, geneList, email, searchDate, today, organism, maxArticles):
    # searchList is de lijst met de ingevoerde synoniemen
    # geneList is de lijst met de ingevoerde genen
    # searchDate is de datum tot waar artikelen moeten worden gezocht
    # today is de datum van vandaag
    # organism is het ingevoerde organisme
    # maxArticles is hoeveel artikelen ik maximaal op wil halen

    # Ik meet hoe lang het duurt om dit script te runnen
    start = time.time()

    global mindate
    global maxdate
    # Ik verander de globale waarde naar de ingevoerde waarde
    mindate = str(searchDate).replace("-", "/")
    maxdate = str(today).replace("-", "/")
    # zodat mindate altijd een waarde heeft
    if mindate == "":
        mindate = "01/01/1500"

    # I set the email to the given email
    Entrez.email = email

    # Zodat alle waarden bij elke run worden geleegd
    global alleTermen
    alleTermen = []
    pubmedEntry.allAnnotations = {}
    pubmedEntry.instancesDict = {}

    # Ik voeg het organisme toe aan de searchList
    searchList.append(organism)

    # I add the genes to a dict to keep track of gene and synonym
    dictSynonyms = {}
    for gene in geneList:
        if not gene in dictSynonyms.keys():
            dictSynonyms[gene] = []
    # I call a function to formulate a query
    # searchTerm contains this query
    # geneList is the list with the synonyms added to it
    searchTerm, geneList = makeQuery(searchList, geneList, dictSynonyms)

    print("De query is ook geformuleerd")

    # I look for articles with the formulated query
    maxResults = getAmountOfResults(searchTerm)
    print("Ik heb gekeken hoeveel id's er kunnen worden opgehaald")
    # Het maximale wat kan is 500.000, daarna komt er een MemoryError
    maxArticles = int(maxArticles)
    if int(maxResults) > maxArticles:
        print("Ik heb ingegrepen en dit aantal naar beneden gehaald")
        maxResults = maxArticles
    print("Het aantal mogelijke resultaten is " + str(maxResults))
    # Ik controleer of er resultaten kunnen zijn met deze term
    if int(maxResults) != 0:
        print("En ik ben ermee aan de slag gegaan")
        idList = getPubmedIDs(maxResults, searchTerm)
        ArticleInfoRetriever(idList, searchTerm, geneList, searchList)
    else:
        print("Er zijn geen resultaten met deze term")
    print("Dit duurt " + str(time.time() - start) + " secondes")


"""Deze functie maakt van de lijsten met termen een zoekterm die in pubmed gezocht kan worden.
Het gebruikt hiervoor de volgende variabelen:
searchList = de lijst met de klinische termen
geneList = de lijst met genen
dictsynonym = Een dict die gebruikt word om de synoniemen van termen te houden. Deze wordt hier gevuld.
dictsynonym ziet er uit als {gen:[synoniem]}
"""


def makeQuery(searchList, geneList, dictsynonym):
    searchTerm = "{}"

    for term in searchList:
        term = term + " OR {} "
        searchTerm = searchTerm.format(str(term))
    searchTerm = searchTerm.replace(" OR {}", "")
    searchTerm += " AND {}"

    # Ik roep een functie aan om synoniemen te zoeken
    try:
        geneList = findSynonyms(geneList, dictsynonym)
    except:
        print("Er is een error opgetreden in het vinden van de synoniemen")
    # This code formulates a query
    for gene in geneList:
        searchTerm = searchTerm.format(gene + " OR {}")
    # Zodat er geen or en and in de query blijft staan
    searchTerm = searchTerm.replace("OR {}", "")
    searchTerm = searchTerm.replace("AND {}", "")
    searchTerm = searchTerm.replace("OR    ", "")
    print(searchTerm)
    return searchTerm, geneList


"""Deze functie zoekt synoniemen in de genlijst en voegt ze toe aan de genlijst en aan dictSynonyms, zodat
ze mee kunnen worden genomen in de query.
De functie wordt dan ook aangeroepen vanuit de functie om de query te maken, genaamd makeQuery
De variabelen zijn:
geneList = de lijst met genen
dictSynonyms = een dict om de genen en synoniemen uit elkaar te houden
"""


def findSynonyms(geneList, dictSynonyms):
    records = ""
    connection = mysql.connector.connect(
        host='hannl-hlo-bioinformatica-mysqlsrv.mysql.database.azure.com',
        db='owe7_pg1',
        user='owe7_pg1@hannl-hlo-bioinformatica-mysqlsrv',
        password="blaat1234")
    cursor = connection.cursor()
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
    # Dit is absoluut niet de snelste manier maar om een of andere reden vind mysql de syntax niet leuk om op een gen te
    # zoeken en dit duurt nu nog geen seconde en de database gaat niet groeien
    for record in records:
        if record[0] in geneList:
            if record[1] not in synonyms and not record[1] == "":
                geneList.append(record[1])
                dictSynonyms.get(str(record[0])).append(record[1])
            synonyms.append(record[1])
    # Ik voeg dictSynonms toe aan een class zodat application.py er ook mee kan werken
    pubmedEntry.dictSynonyms = dictSynonyms
    return geneList


"""Deze functie kijkt hoeveel resultaten er maximaal op kunnen worden gehaald met de zoekterm zodat dit
in andere functies als retmax kan worden gegeven. Als dit er meer zijn dat het maximaal aantal wat de gebruiker
wilt dan wordt dit later nog naar beneden gehaald om snelheid te bewaren
"""


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


"""Deze functie haalt de pubmedId's op uit pubmed met de zoekterm. Het heeft als retmax de maxResults die eerder
is vastgesteld.
"""


def getPubmedIDs(maxResults, searchTerm):
    print(mindate, maxdate)
    handle = Entrez.esearch(db="pubmed", term=searchTerm, retmax=maxResults, datetype='pdat', mindate=mindate,
                            maxdate=maxdate)
    record = Entrez.read(handle)
    handle.close()
    # Ik wil alleen de id's
    idlist = record["IdList"]
    print("got id's")
    return idlist


"""Deze functie staat in principe los van de flow van dit programma en wordt dan ook niet aanroepen binnen dit script.
Dit is voor als application.py een genpanel heeft gekregen.
Het maakt van het genpanel een dictionary met als structuur {gen:[termen]} zodat application.py hiermee kan
werken. Het retouneerd dit dict direct
"""


def readGenePanels(stringPanel):
    # In deze variabele komt het genpanel met als format {gen:[termen]}
    panels = {}
    for regel in stringPanel.split("\n"):
        try:
            gene = regel.split("\t")[0]
            panel = regel.split("\t")[1]
            if not gene in panels.keys():
                panels[gene] = [panel]
            else:
                print("Er horen geen dubbele genen in te zitten. Ik bewaar alleen de laatste")
        except:
            print("Dit format is niet supported")
    print(panels)
    return panels


"""Deze functie geeft de lijst met Id's die eerder zijn verkregen aan pubtator.py, zodat deze daaruit annotatie kan
halen.
Het gebruikt hiervoor de volgende variabelen:
idList = de lijst met Id's
Deze variabelen zijn er zodat ze door kunnen worden gegeven aan de volgende functie:
searchTerm = de query
geneList = de lijst met genen
searchList = de lijst met klinische termen
"""


def ArticleInfoRetriever(idList, searchTerm, geneList, searchList):
    print("Oke ik begin met pubtator")
    # allAnnotations bevat alle annotaties van alle artikelen  en ziet er uit als {id:{type:[annotaties]}}
    allAnnotations = {}
    idList = list(idList)
    # Ik haal alle dubbele er uit
    idList = set(idList)
    idList = list(idList)
    slice = 500
    remainingIds = set(idList)
    # Als er niet met slices wordt gewerkt, wordt alles wat niet in een slice past niet gebruikt
    if len(idList) > slice:
        for i in range(slice, len(idList), slice):
            output = pubtator.SubmitPMIDList(idList[i - slice:i], "biocjson",
                                             "gene, disease, chemical, species, proteinmutation, dnamutation")
            if not output is None:
                # Ik roep een functie aan die van de JSON file bruikbare data maakt en dat in een class stopt
                articleInfoProcessor(output, searchTerm, allAnnotations, geneList, searchList)
    else:
        output = pubtator.SubmitPMIDList(idList, "biocjson",
                                         "gene, disease, chemical, species, proteinmutation, dnamutation")
        if not output is None:
            articleInfoProcessor(output, searchTerm, allAnnotations, geneList, searchList)

    print("En ik ben klaar met pubtator")
    # Ik stop allAnnotations in de class
    pubmedEntry.allAnnotations = allAnnotations

    # Ik haal alle overige id's op en gooi deze in Entrez, aangezien pubtator niet voor elk id annotations kan vinden
    allAnnotationIds = set(allAnnotations.keys())
    remainingIds = remainingIds.difference(allAnnotationIds)
    getPubmedArticlesByID(list(remainingIds), searchTerm)


"""Dit maakt gebruik van de entrez functie om de artikelen op te halen.
Dit wordt alleen gebruikt als er geen match was met pubtator
"""


def getPubmedArticlesByID(idList, searchTerm):
    print("pubtator had geen match")
    handle = Entrez.efetch(db="pubmed", id=idList, rettype="medline",
                           retmode="text")
    records = Medline.parse(handle)
    records = list(records)
    for record in records:
        pubmedEntryInstance = pubmedEntry(record.get("PMID"), searchTerm, record.get("AU"))
        # om de datum om te zetten naar een werkbaar format
        date = record.get("DP")
        if date is not None:
            date = str(date).split(" ")
            # Omdat niet alle datums compleet zijn met jaar,maand,dag
            if len(date) == 1:
                date.append("Jan")
                date.append("01")
            elif len(date) == 2:
                date.append("01")
            # Het date format van Entrez is niet optimaal..
            datemonth = date[1].split("-")[0]
            datemonth = datemonth.split("/")[0]
            # Zodat ik het maandnummer heb ipv de maandnaam
            try:
                datetime_object = datetimewhole.datetime.strptime(datemonth, "%b")
                month_number = datetime_object.month
            except ValueError:
                # deze exeption is er voor als ik het maandnummer in een onverwacht format krijg
                month_number = "01"
            date = date[0] + "/" + str(month_number) + "/" + date[2]

        pubmedEntryInstance.setDatePublication(date)
        pubmedEntryInstance.setAbout(record.get("AB"))
        pubmedEntryInstance.setTitle(record.get("TI"))


"""Deze functie haalt de nuttige informatie uit het JSON bestand wat uit pubtator komt en stopt deze informatie
in de class zodat dit in application.py kan worden gebruikt. Hierna roept het een functie aan om een score te 
berekenen voor het artikel
De variabelen zijn:
pubatoroutput = het json bestand met de output
searchTerm = de query waar op is gezocht
allAnnotations = een dict met alle annotaties ({id:{type:[annotaties]}})
geneList = een lijst met alle genen
searchList = een lijst met alle klinische termen
"""


def articleInfoProcessor(pubtatoroutput, searchTerm, allAnnotations, geneList, searchList):
    if not len(pubtatoroutput) == 0:
        # pubtator geef allemaal json files terug met een enter ertussen, niet 1 grote
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
                datePublished = str(datePublished)
                datePublished = datePublished.split("-")
                datePublished = datePublished[0] + "/" + datePublished[1] + "/" + datePublished[2].split(" ")[0]
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
                            accessionDict[identifier] = [[name], 1]
                        else:
                            if not name in accessionDict[identifier][0]:
                                accessionDict[identifier][0].append(name)
                            accessionDict[identifier][1] += 1

                        if not type in allAnnotations[pubmedid].keys():
                            allAnnotations[pubmedid][type] = [name]
                        else:
                            if not name in allAnnotations[pubmedid][type]:
                                allAnnotations[pubmedid][type].append(name)

                pubmedEntryInstance.usedPubtator()
                pubmedEntryInstance.setScore(calculateScores(termsList, accessionDict, pubmedEntryInstance))


"""Deze functie berekent de score van het artikel
"""


def calculateScores(termsList, accessionDict, pubmedInstance):
    # voorkomensTermen bevat van alle genen hoe vaak het voorkomt
    voorkomensTermen = 0
    for item in alleTermen:
        if item in accessionDict.keys():
            aantalvoorkomensItem = accessionDict.get(item)[1]
            voorkomensTermen += aantalvoorkomensItem

    # dit bevat alle genen die genoemt zijn, dus een count met alle genen
    alleTermenVoorkomens = 0
    for value in accessionDict.values():
        alleTermenVoorkomens += value[1]

    # Dit is allemaal zodat ik een score kan hangen aan de datum
    today = datetime.today()
    then = pubmedInstance.getDatePublication()
    then = then.split("/")
    monthsAgo = (today.year - int(then[0])) * 12 + (today.month - int(then[1]))

    mindateSplit = mindate.split("/")
    maxdateFormatted = date(int(mindateSplit[0]), int(mindateSplit[1]), int(mindateSplit[2]))
    # maxdateFormatted = date(int(mindateSplit[2]), int(mindateSplit[1]), int(mindateSplit[0]))

    # Ik deel het aantal maanden geleden door het maximaal aantal maanden geleden, zodat de waarde kleiner is als
    # het korter geleden is
    maxMonthsAgo = (today.year - maxdateFormatted.year) * 12 + (today.month - maxdateFormatted.month)

    try:
        # De scoreberekening
        score = (((voorkomensTermen / alleTermenVoorkomens) + 1) + (
            (len(termsList) / (len(accessionDict.keys()) + 1)))) / (
                        (monthsAgo / maxMonthsAgo + 1) + 1)
    except ZeroDivisionError:
        # Voor als alle waarden 0 zijn
        score = 0
    return score


"""Deze class bevat alle informatie om op te halen in application.py
"""


class pubmedEntry:
    # The __ makes this a private attribute to encapsulate it
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


# main(["variant", "variants", "mutation", "mutations", "substitutions", "substitution", "loss of function" , "loss-of-function" , "haplo-insufficiency" , "haploinsufficiency" , "bi-allelic" , "biallelic" , "recessive" , "homozygous" , "heterozygous" , "de novo" , "dominant" ,  "X-linked" , "intellectual" , "mental retardation" , "cognitive" , "developmental" , "neurodevelopmental"], ["KDM3B"], "annemiekeschonthaler@gmail.com", "06-12-2019", "06-12-2020", "", 500000)
# main(["Homo sapiens"], [], "kip@kip.nl", "06-12-2019", "06-12-2020", "", 5000)
