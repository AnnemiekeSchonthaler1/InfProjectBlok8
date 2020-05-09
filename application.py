from flask import Flask
#from Bio import Entrez
app = Flask(__name__)

@app.route("/")
def hello():
    return "Hello World!"
