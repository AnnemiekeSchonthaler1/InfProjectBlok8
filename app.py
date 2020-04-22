from flask import Flask, render_template, request

app = Flask(__name__)


@app.route('/', methods=['POST', 'GET'])
def hello_world():
    return render_template("Mainpage.html")


@app.route('/result', methods=['POST', 'GET'])
def results():
    pub_date = ""
    disease_char = ""
    gene_list = []  # miss anders opslaan ligt aan hoe we dit later gaan gebruiken
    if request.method == 'POST':
        result = request.form
        for key, value in result.items():
            if key == "publication_date":
                pub_date = value
            elif key == "disease_characteristic":
                disease_char = value
            elif key == "gene_list":
                values = value.split("\n")
                for thing in values:
                    thing = thing.strip("\r")
                    thing = thing.strip(" ")
                    if thing != " " and thing != "":
                        gene_list.append(thing)
    print(pub_date)
    print(disease_char)
    print(gene_list)
    return render_template("Mainpage.html")


if __name__ == '__main__':
    app.run()
