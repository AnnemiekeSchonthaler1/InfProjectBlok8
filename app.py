import base64
import calendar
from io import BytesIO

from flask import Flask, render_template, request
import platform
import datetime
import Pubmed
import pubmed_search
import Graphs
app = Flask(__name__)


@app.route('/', methods=['POST', 'GET'])
def hello_world():
    gene_dic = {}

    print(platform.sys.version)
    return render_template("Mainpage.html", genedic=gene_dic)


@app.route('/result', methods=['POST', 'GET'])
def results():
    pub_date = ""
    disease_char = ""
    gene_list = []  # miss anders opslaan ligt aan hoe we dit later gaan gebruiken
    mail = ""
    gene_dic = {}
    recipe_data = {}
    search_date = ""
    plot_url =""
    today = datetime.date.today()
    if request.method == 'POST':
        result = request.form
        for key, value in result.items():
            if key == "publication_date":
                pub_date = value
                search_date = do_MATH_months(today, -int(pub_date))
                print(search_date)

            elif key == "disease_characteristic":
                disease_char = value
            elif key == "mail":
                mail = value
            elif key == "gene_list":
                values = value.split("\n")
                for thing in values:
                    thing = thing.strip("\r")
                    thing = thing.strip(" ")
                    if thing != " " and thing != "":
                        gene_list.append(thing)
        Pubmed.main(searchTerm=disease_char, geneList=gene_list, email=mail, searchDate=search_date, today=today)
        Synonymdict = Pubmed.dictSynonyms

        for gene, synonyms in Synonymdict.items():
            if gene != '':
                gene_dic.update({gene: {gene: []}})
                for s in synonyms:
                    if s != '':
                        gene_dic[gene][s] = []
                for item in Pubmed.pubmedEntry.instancesList:
                    if gene in item.getAbout():
                        if gene in recipe_data:
                            recipe_data[gene] += 1
                        else:
                            recipe_data.update({gene: 1})
                        gene_dic[gene][gene].append(item)
                    for s in synonyms:
                        if s in item.getAbout():
                            if s != '':
                                if s in recipe_data:
                                    recipe_data[s] += 1
                                else:
                                    recipe_data.update({s: 1})
                                gene_dic[gene][s].append(item)
        img = BytesIO()
        plt = Graphs.Graph(recipe_data)
        plt.savefig(img, format='png')
        plt.close()
        img.seek(0)
        plot_url = base64.b64encode(img.getvalue()).decode('utf8')
    # Embed the result in the html output.

    return render_template("Searchpage.html", genedic=gene_dic, plot=plot_url)


def do_MATH_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])
    return datetime.date(year, month, day)


# dict = {genename : { genename : [values] , synonymname : [values], synonymname : [values]}, othergene : { } }
if __name__ == '__main__':
    app.run()
