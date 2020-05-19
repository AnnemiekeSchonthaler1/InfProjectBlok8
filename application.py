import base64
import calendar
from io import BytesIO

from flask import Flask, render_template, request
import platform
import datetime

import Omim
import Pubmed
import Graphs

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
        print(gene_list, disease_char, mail)
        Pubmed.main(searchList=search_list, geneList=gene_list, email=mail, searchDate=search_date, today=today)
        omim_ids = Omim.find_in_database(gene_list=gene_list)
        # get a complete list of gene names
        Synonymdict = Pubmed.pubmedEntry.dictSynonyms
        print("uhm im a synonym dict: ",Synonymdict)
        # make a dictionary to save the counts and the articles per gene
        gene_dic, recipe_data = make_genedic_and_count(Synonymdict)

        # make the graph of amount of results per gene found mmmmmm donut
        plt = Graphs.Graph(recipe_data)
        plot_url = save_to_url(plt)
        infodic = Pubmed.pubmedEntry.annotations
        for item in Pubmed.pubmedEntry.instancesList:
            url = Graphs.wordcloud(item.MLinfo)
            URL_dic.update({item.pubmedID: url})
            for key, value in item.MLinfo.items():
                infodic[item.pubmedID][key] = set(value)
        print("url dic", URL_dic)
        print("info dic ", infodic)
        # dictionary with synonyms for the searchterm?
        # make a complete dictionary with all information
        full_dicy.update({"articles": gene_dic})
        full_dicy.update({"omim_id": omim_ids})
        full_dicy.update({"amount_found": recipe_data})

    # Embed the result in the html output.
    return render_template("Searchpage.html", genedic=full_dicy, plot=plot_url, infodic=infodic, url_dic=URL_dic)


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
    annotation_dic = Pubmed.pubmedEntry.annotations
    for item in Pubmed.pubmedEntry.instancesList:
        item.setMLinfo()

    gene_dic = {}
    for gene, synonyms in Synonymdict.items():
        if gene != '':
            gene_dic.update({gene: {gene: []}})
            for s in synonyms:
                if s != '':
                    gene_dic[gene][s] = []

    for item in Pubmed.pubmedEntry.instancesList:
        for dic in gene_dic.values():
            for gene in dic.keys():
                if gene in item.MLinfo['Gene']:
                    gene_dic[gene][gene].append(item)
                    if gene in recipe_data:
                        recipe_data[gene] += 1
                    else:
                        recipe_data.update({gene: 1})
    return gene_dic, recipe_data


def do_MATH_months(sourcedate, months):
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
