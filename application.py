import base64
import calendar
from io import BytesIO

from flask import Flask, render_template, request
import platform
import datetime

import Omim
import Pubmed
import Graphs
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
    plot_url = ""
    search_list = []
    URL_dic = {}
    infodic={}
    today = datetime.date.today()
    if request.method == 'POST':
        print("hi i got to the loop to digest data")
        result = request.form
        for key, value in result.items():
            if key == "publication_date":
                pub_date = value
                search_date = do_MATH_months(today, -int(pub_date))
                print(search_date)

            elif key == "disease_characteristic":
                disease_char = value
                search_list = disease_char.split(",")
                print(search_list)

            elif key == "mail":
                mail = value

            elif key == "gene_list":
                values = value.split("\n")
                for thing in values:
                    thing = thing.strip("\r")
                    thing = thing.strip(" ")
                    if thing != " " and thing != "":
                        gene_list.append(thing)
            elif key == "wordcloud_cutoff":

                if key is not "" or key is not "all":
                    wordcloud_cutoff = value
                else:
                    wordcloud_cutoff = 500000
                print(wordcloud_cutoff)

        print("hi ik roep pubmed nu aan")
        Pubmed.main(searchList=search_list, geneList=gene_list, email=mail, searchDate=search_date, today=today)
        print("ik haal nu de annotaties op")
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
        print("we maken nu een grafiek van de count data")
        plt = Graphs.Graph(recipe_data)
        print("we saven de grafiek")
        plot_url = save_to_url(plt)
        print("were making graphs now... this might take a while")
        current = len(Pubmed.pubmedEntry.instancesDict)
        length = len(Pubmed.pubmedEntry.instancesDict)
        if int(length) <= int(wordcloud_cutoff):
            print("ik heb besloten om wordclouds te maken vandaag")
            for item in Pubmed.pubmedEntry.instancesDict.values():
                current = current - 1
                print(current, "to gaan!!!")
                if len(item.getMlinfo()) != 0:
                    url = Graphs.wordcloud(item.getMlinfo())
                    URL_dic.update({item.pubmedID: url})
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
    return render_template("Searchpage.html", genedic=full_dicy, plot=plot_url, infodic=infodic, url_dic=URL_dic)


def most_frequent(List):
    occurence_count = Counter(List)
    return occurence_count.most_common(1)[0][0]

def save_to_url(plt):
    img = BytesIO()
    plt.savefig(img, format='png')
    plt.close()
    img.seek(0)
    plot_url = base64.b64encode(img.getvalue()).decode('utf8')
    return plot_url


def make_genedic_and_count(Synonymdict):

    #{gene : count}
    recipe_data = {}
    #{gene : {gene: [article_entery,...], synonym_of_Gene : [article entery]} gene : {gene: []}
    annotation_dic = Pubmed.pubmedEntry.allAnnotations
    print("im generating the empty gene_dic")
    gene_dic = {}
    if type(Synonymdict) is list:
        for gene in Synonymdict:
            gene_dic.update({gene: {gene: []}})
    else:
        for gene, synonyms in Synonymdict.items():
            if gene != '':
                gene_dic.update({gene: {gene: []}})
                for s in synonyms:
                    if s != '':
                        gene_dic[gene][s] = []
    print("im starting with filling the gene_dic")
    for item in Pubmed.pubmedEntry.instancesDict.values():
        MLinfo = item.getMlinfo()

        for dic in gene_dic.values():
            for gene in dic.keys():
                for dictionary in MLinfo.values():
                    if 'Gene' in dictionary.keys():
                        if gene in dictionary['Gene']:
                            if item not in gene_dic[gene][gene]:
                                gene_dic[gene][gene].append(item)
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
