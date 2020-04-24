from flask import Flask, render_template, request
import platform
import pubmed_search

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

    if request.method == 'POST':
        result = request.form
        for key, value in result.items():
            if key == "publication_date":
                pub_date = value
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
    pubmed_search.main(searchTerm=disease_char, geneList=gene_list)
    for gene in gene_list:
        gene_dic.update({gene: []})
        for item in pubmed_search.pubmedEntry.instancesList:
            if gene in item.getAbout():
                gene_dic[gene].append(item)

    print(gene_dic)
    return render_template("Mainpage.html", genedic=gene_dic)


if __name__ == '__main__':
    app.run()
