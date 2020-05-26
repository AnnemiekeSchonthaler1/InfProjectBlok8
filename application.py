
import calendar
import collections

from flask import Flask, render_template, request
import platform
import datetime

import Omim
import Pubmed
from collections import Counter

app = Flask(__name__)


@app.route('/', methods=['POST', 'GET'])
def hello_world():
    gene_dic = {}

    print(platform.sys.version)
    return render_template("Mainpage.html", genedic=gene_dic)


@app.route('/result', methods=['POST', 'GET'])
def results():
    print("hi i got to the result function")
    full_dicy = {}
    pub_date = ""
    disease_char = ""
    gene_list = []  # miss anders opslaan ligt aan hoe we dit later gaan gebruiken
    mail = ""
    search_date = ""
    wordcloud_cutoff = ""
    organism = ""
    plot_url = ""
    search_list = []
    URL_dic = {}
    infodic={}
    pubmed_entries = None
    recipe_data = {}
    data = {}
    gene_panel = None
    amount_of_articles = None
    today = datetime.date.today()
    csv_data = ""
    if request.method == 'POST':
        print("hi i got to the loop to digest data")
        result = request.form
        for key, value in result.items():
            if key == "publication_date":
                pub_date = value
                search_date = do_MATH_months(today, -int(pub_date))
                print(search_date)
            elif key == "gene_panel":
                gene_panel = value

            elif key == "disease_characteristic":
                disease_char = value
                search_list = disease_char.split(",")
                print(search_list)
            elif key == "organism":
                organism = value
            elif key == "amount_articles":
                amount_of_articles = value
            elif key == "mail":
                mail = value

            elif key == "gene_list":
                values = value.split("\n")
                for thing in values:
                    thing = thing.strip("\r")
                    thing = thing.strip(" ")
                    if thing != " " and thing != "":
                        gene_list.append(thing)

        print("hi ik roep pubmed nu aan")
        Pubmed.main(searchList=search_list, geneList=gene_list, email=mail, searchDate=search_date, today=today,
                    organism=organism, maxArticles=amount_of_articles)
        print("ik haal nu de annotaties op")
        pubmed_entries = Pubmed.pubmedEntry.instancesDict
        infodic = Pubmed.pubmedEntry.allAnnotations
        if len(gene_list) == 0:
            print("ik ga nu een genlijst maken want die had je niet")
            for id, dictionary in infodic.items():
                if 'Gene' in dictionary.keys():
                    common = most_frequent(dictionary['Gene'])
                    if common not in gene_list:
                        gene_list.append(common)

        print("hiii ga nu ff in database omim ids enzo zoeken")
        omim_ids = Omim.find_in_database(gene_list=gene_list)
        # get a complete list of gene names
        print("ik haal ook ff het synoniemen dictionary op")
        Synonymdict = Pubmed.pubmedEntry.dictSynonyms
        if len(Synonymdict) == 0:
            Synonymdict = gene_list
        # make a dictionary to save the counts and the articles per gene
        print("hmmm we gaan nu ff door met een counter en het genedic in elkaar zetten")
        gene_dic, recipe_data = make_genedic_and_count(Synonymdict)

        # make the graph of amount of results per gene found mmmmmm donut

        print("were making graphs now... this might take a while")
        data = {}
        data = make_wordcloud_dataframe(data)
        print("ik ben klaar met wordclouds maken :(")
        # dictionary with synonyms for the searchterm?
        # make a complete dictionary with all information
        print("ik maak nu een compleet dictionary met alle inforamatie enzo")
        full_dicy.update({"articles": gene_dic})
        full_dicy.update({"omim_id": omim_ids})
        full_dicy.update({"amount_found": recipe_data})
        print("volledig dicy ", full_dicy)
    # Embed the result in the html output.
        print("genereer pagina nu maar... hopelijk")
        print(data)
        csv_data = make_csv_data(infodic)

    return render_template("Searchpage.html", genedic=full_dicy, plot=plot_url, infodic=infodic, url_dic=URL_dic, recipe_dict=recipe_data, entries=pubmed_entries, data=data, csv_data=csv_data)


def most_frequent(List):
    occurence_count = Counter(List)
    return occurence_count.most_common(1)[0][0]

def make_genedic_and_count(Synonymdict):

    #{gene : count}
    recipe_data = {}
    #{gene : {gene: [article_entery,...], synonym_of_Gene : [article entery]} gene : {gene: []}
    annotation_dic = Pubmed.pubmedEntry.allAnnotations
    print("im generating the empty gene_dic")
    gene_dic = {}
    if type(Synonymdict) is list:
        print("its a list")
        for gene in Synonymdict:
            gene_dic.update({gene: {gene: []}})
    else:
        for gene, synonyms in Synonymdict.items():
            if gene != '':
                gene_dic.update({gene: {gene: []}})
                for s in synonyms:
                    if s != '':
                        gene_dic[gene][s] = []
    print("empty genedic",gene_dic)
    print("im starting with filling the gene_dic")
    for item in Pubmed.pubmedEntry.instancesDict.values():
        MLinfo = item.getMlinfo()

        for basic_gene, dic in gene_dic.items():
            for gene in dic.keys():
                for dictionary in MLinfo.values():
                    if dictionary:
                        if 'Gene' in dictionary.keys():
                            if gene in dictionary['Gene']:
                                if item not in gene_dic[basic_gene][gene]:
                                    gene_dic[basic_gene][gene].append(item)
                                    if gene in recipe_data:
                                        recipe_data[gene] += 1
                                    else:
                                        recipe_data.update({gene: 1})

                    else:
                        print("no dictionary in MLinfo  (PUBTATOR HAS FAILED US)")
                        about = item.getAbout()
                        if gene in about:
                            print("THE GENE IS IN THE ABOUT THO SO PUBMED HAS NOT FAILED US")
                            if item not in gene_dic[basic_gene][gene]:
                                gene_dic[basic_gene][gene].append(item)
                                if gene in recipe_data:
                                    recipe_data[gene] += 1
                                else:
                                    recipe_data.update({gene: 1})

    return gene_dic, recipe_data


def do_MATH_months(sourcedate, months):
    print("ik bereken ff wat voor tijd het dan moet zijn voor de zoek opdracht")
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])
    return datetime.date(year, month, day)


def make_wordcloud_dataframe(data):

    for item in Pubmed.pubmedEntry.instancesDict.values():
        starting_dic = item.getMlinfo()
        for id, dictionary in starting_dic.items():
            data.update({id: []})
            for type, listy in dictionary.items():
                frequency = collections.Counter(listy)
                for word in listy:
                    frequency_word = frequency[word]
                    list_for_dic = [word, frequency_word, type]
                    if list_for_dic not in data[id]:
                        data[id].append(list_for_dic)
    return data
def make_csv_data(data):
    sentence = []
    thing = ['','','','','']
    for id, dic in data.items():
        thing = ['', '', '', '', '']
        thing[0] = id
        if 'Gene' in dic.keys():
            thing[1] = "/".join(dic['Gene'])
        else:
            thing[1] = ' '
        if 'Mutation' in dic.keys():
            thing[2] = "/".join(dic['Mutation'])
        else:
            thing[2] = ' '
        if 'Disease' in dic.keys():
            thing[3] = "/".join(dic['Disease'])
        else:
            thing[3] = ' '
        if 'Species' in dic.keys():
            thing[4] = "/".join(dic['Species'])
        else:
            thing[4] = ' '
        thing = ", ".join(thing)
        sentence.append(thing)
    sentence = "\n".join(sentence)
    sentence = [sentence]
        #thing.append(id)
        #for type, list in dic.items():
            #thing.append("/".join(list))
        #" , ".join(thing)
        #thing += "\n"

    print(sentence)

    return sentence

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(410)
def page_gone(e):
    return render_template('410.html'), 410


@app.errorhandler(500)
def internal_error(e):
    return render_template('500.html'), 500


if __name__ == '__main__':
    app.run()
