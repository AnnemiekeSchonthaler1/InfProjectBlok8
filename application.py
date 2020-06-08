import calendar
import collections

from flask import Flask, render_template, request
import datetime

import Omim
import Pubmed
from collections import Counter
import re

app = Flask(__name__)


@app.route('/', methods=['POST', 'GET'])
def hello_world():
    """
    Hello world loads up the homepage of the application with no other functionalities
    :return: home page html
    """
    gene_dic = {}
    return render_template("Mainpage.html", genedic=gene_dic)


@app.route('/result', methods=['POST', 'GET'])
def results():
    """
    The results function processes the user input and sends it off to the pubmed and pubtator search function
    the data gathered from there is then edited into a useable format for the template and returns a searchpage with
    the results shown once the search form is submitted
    :return: search page html with or without results
    """
    # instance all variables
    show_result = False
    full_dicy = {}
    annotation_entries = {}
    pubmed_entries = {}
    count_data = {}
    data = {}
    gene_panel = ""
    today = datetime.date.today()
    csv_data = ""
    plot_data = False

    # get all data from the form once its posted
    if request.method == 'POST':
        show_result = True
        result = request.form
        pub_date, disease_char, gene_list, mail, search_date, organism, search_list, gene_panel, amount_of_articles, plot_data = getForm_data(
            result)

        print(pub_date, disease_char, gene_list, mail, search_date, organism, search_list,
              amount_of_articles)
        # send all pre processed form data to Pubmed search
        Pubmed.main(searchList=search_list, geneList=gene_list, email=mail, searchDate=search_date, today=today,
                    organism=organism, maxArticles=amount_of_articles)
        # collect gathered data from Pubmed Search (all articles, annotation of articles, synonyms of genes)
        pubmed_entries = Pubmed.pubmedEntry.instancesDict
        annotation_entries = Pubmed.pubmedEntry.allAnnotations
        synonyms = Pubmed.pubmedEntry.dictSynonyms

        # make a gene list if there was none provided from the gathered annotation
        if len(gene_list) == 0:
            for id, dictionary in annotation_entries.items():
                # if genes were found in the article take the most common one and put it in the list
                if 'Gene' in dictionary.keys():
                    common = most_frequent(dictionary['Gene'])
                    if common not in gene_list:
                        gene_list.append(common)

        # once all genes are gathered find the ids of OMIM, Uniprot and NCBI in the database and return these in a dic
        omim_ids = Omim.find_in_database(gene_list=gene_list)

        # if there was no gene list there will be no synonyms so the gene list is equal to the synonyms
        if len(synonyms) == 0:
            synonyms = gene_list

        # make a dictionary with the genes and their synonyms and then sort the articles based on genes occurring
        gene_dic = make_genedic(synonyms)
        # also count the amount of articles and add to the annotation if necessary
        gene_dic, count_data, annotation_entries = fill_genedic(gene_dic, annotation_entries, gene_panel)

        # make a dataframe for the wordclouds in the application with the frequency per word (disease, gene, mutation)
        data = {}
        data = make_wordcloud_dataframe(data, annotation_entries)

        # add some dictionaries together for easy access
        full_dicy.update({"articles": gene_dic})
        full_dicy.update({"omim_id": omim_ids})
        full_dicy.update({"amount_found": count_data})

        # make a csv string to download from the website
        csv_data = make_csv_data(annotation_entries)

    return render_template("Searchpage.html", genedic=full_dicy, infodic=annotation_entries,
                           recipe_dict=count_data, entries=pubmed_entries, data=data, csv_data=csv_data,
                           gene_panel=gene_panel, show_result=show_result, plot_data=plot_data)


def getForm_data(result):
    """
    getForm_data takes in the result dictionary of the form and then writes the values off to variables and returns them
    :param result: dictionary with form data
    :return: pub_date, disease_char, gene_list, mail, search_date, organism, search_list, gene_panel, amount_of_articles
    """
    # instance all variables
    pub_date = "1000"
    disease_char = ""
    gene_list = []
    mail = ""
    search_date = ""
    organism = ""
    search_list = []
    gene_panel = ""
    amount_of_articles = None
    today = datetime.date.today()
    plot_data = True

    # get all data from the form by key and value
    for key, value in result.items():
        if key == "publication_date":
            pub_date = value
            # for some reason the form couldn't deal with 3 so yes..
            if pub_date == "2":
                pub_date = "3"
            # if the publication date is more than 9 months turn the plot visualisation off for memory issues
            # (might not be implemented)
            if int(pub_date) > 9:
                plot_data = False
            # calculate the date
            search_date = do_MATH_months(today, -int(pub_date))
        elif key == "gene_panel":
            gene_panel = value
            if gene_panel:
                gene_panel = Pubmed.readGenePanels(gene_panel)
            else:
                gene_panel = {}
        elif key == "disease_characteristic":
            disease_char = value
            # make a list by splitting everything on the ,
            search_list = disease_char.split(",")
        elif key == "organism":
            organism = value
        elif key == "amount_articles":
            amount_of_articles = value
        elif key == "mail":
            mail = value

        elif key == "gene_list":
            # make the gene_list string into a list and take out nonsense
            values = value.split("\n")
            for thing in values:
                thing = thing.strip("\r")
                thing = thing.strip(" ")
                if thing != " " and thing != "":
                    gene_list.append(thing)
    # if there was no publication date given take publication date 1000 doubt you need to search further back than that
    if "publication_date" not in result.keys():
        plot_data = False
        search_date = do_MATH_months(today, -int(pub_date))
    return pub_date, disease_char, gene_list, mail, search_date, organism, search_list, gene_panel, amount_of_articles, plot_data


def most_frequent(List):
    """
    most_frequent takes in a list with all genes found in an article
    and then returns the most frequent gene in that list
    :param List: list with all genes of an article
    :return: the most common gene in the list
    """
    """for value in List:
        if " " in value or "-" in value or "=" in value:
            List.remove(value)"""
    if List:
        occurence_count = Counter(List)
        return occurence_count.most_common(1)[0][0]


def make_genedic(Synonymdict):
    """
    make_genedic makes a dictionary with all genes and synonyms with as value an empty list later to be filled
    :param Synonymdict: dictionary with gene as key and a list with synonyms as value
    :return: gene dic {key = genename : value = {key = genename or synonym, value = list [] }}
    """
    # make a gene dic with all genes and their synonyms with empty lists for the article objects to go in
    gene_dic = {}
    # if there was no gene_list/synonym dict we do it slightly different
    if type(Synonymdict) is list:
        for gene in Synonymdict:
            gene_dic.update({gene: {gene: []}})
    # if there was a gene list there will be synonyms so they will be added too
    else:
        for gene, synonyms in Synonymdict.items():
            if gene != '':
                gene_dic.update({gene: {gene: []}})
                for s in synonyms:
                    if s != '':
                        gene_dic[gene][s] = []

    return gene_dic


def check_genepanel(gene, genepanel):
    """
    check genepanel checks if a gene is in the genepanel and returns what gene panel it is in if it is
    :param gene: gene name, like 'CHD8'
    :param genepanel: gene panel dictionary {key = gene_name , value = [panels containing gene]}
    :return: panels the searched gene is in
    """
    # check if in gene panel genes
    if gene in genepanel.keys():
        return genepanel[gene]


def add_to_count(item, gene, count_data, gene_panel):
    """
    add to count, counts the amount of articles there are per gene and checks if they are in a gene panel.
    this data is then added to a list with the count and panels of a gene. When a gene is not in a gene panel
    the score gets raised by 0.5
    :param item: pubmed entry object
    :param gene: gene name
    :param count_data: dictionary with gene, count and panels {key = gene, value = [count, [panels]]}
    :param gene_panel: dictionary of gene panel {key = gene, value = [panels]}
    :return: updated count_data
    """
    # if the gene is in there and you find an article you add 1
    if gene in count_data:
        count_data[gene][0] += 1
    # if the gene was not yet in there add 1 and search if it is in the gene panel
    else:
        count_data.update({gene: [1, []]})
        if gene_panel:
            panel = check_genepanel(gene, gene_panel)
            count_data[gene][1] = panel
            # if it isn't in the gene panel raise the score
            if panel is not None:
                score = item.getScore()
                item.setScore(score + 0.5)


def fill_genedic(gene_dic, infodic, gene_panel):
    """
    fill genedic fills up de empty lists in the dictionary values with pubmed entries(articles) by looking through
    the annotation provided by pubtator. if there is no annotation then a regex will be used to determine genes in the
    abstract of the article. these are all added to the list related to the genes found in the article.
    :param gene_dic: dictionary with genes and their synonyms and the articles that contain them
    {key = gene, value = {key = gene or synonym, value = [pubmed_entry(articles)]}}
    :param infodic: dictonary with all annotations of every article,
    {key = pubmed_id, value = {key = type_of_annotation, value = [annotation]}}
    :param gene_panel: dictionary of gene panel {key = gene, value = [panels]}
    :return: filled gene dic, the counts of articles per gene and their panels, updated annotations(added to by regex)
    """
    # instance variables
    count_data = {}
    # go through all articles and see if they have annotation then add them to the corresponding gene found in it
    for item in Pubmed.pubmedEntry.instancesDict.values():
        id_entry = item.pubmedID
        if infodic.get(id_entry):
            for basic_gene, dic in gene_dic.items():
                for gene in dic.keys():
                    if 'Gene' in infodic[id_entry].keys() and gene in infodic[id_entry]['Gene'] \
                                                          and item not in gene_dic[basic_gene][gene]:
                        # if it has annotation and the searched gene is in the annotation we put it in the gene dic
                        gene_dic[basic_gene][gene].append(item)
                        # it also gets added to the amount of articles per gene
                        add_to_count(item, gene, count_data, gene_panel)

        else:
            # if there is no annotation we will try to at least annotate the genes found in the abstract with regex
            gene_found = search_for_genes_regex(item, infodic)
            # all genes found are in a list and will be added to the gene dic and the amount per gene
            for gene_name in gene_found:
                add_to_count(item, gene_name, count_data, gene_panel)
                if gene_name not in gene_dic.keys():
                    gene_dic.update({gene_name: {gene_name: [item]}})
                else:
                    if item not in gene_dic[gene_name][gene_name]:
                        gene_dic[gene_name][gene_name].append(item)
    return gene_dic, count_data, infodic


def search_for_genes_regex(item, infodic):
    """
    this function searches for genes with regex and sets the score of the article to -1. the found data is added to
    the annotations dictionary and the personal annotation dictionary of the object
    :param item: pubmed entry
    :param infodic: dictionary of all annotations of all pubmed entries
    {key = pubmed_id, value = {key = type, value = [annotation]}}
    :return: list of genes found with the regex
    """
    # all items without annotation get a score of -1
    item.setScore(-1)
    # instance variables
    gene_found = []
    about = item.getAbout()
    id_entry = item.pubmedID

    # find the genes in the abstract
    x = re.findall('[A-Z0-9]*', about)
    # for all the genes found check if they're actually useful
    for value in x:
        if len(value) > 2 and x.count(
                value) > 1 and \
                value not in ["RNA", "DNA", "BMI", "MIM", "MRI", "ICU"] and \
                value.isdigit() is False \
                and value not in gene_found:
            # then check if it was found between brackets this usually means it is an illness rather than a gene
            # (not always true but for the sake of more accurate genes)
            if "({})".format(value) not in about and "({}s)".format(value) not in about:
                gene_found.append(value)
                # update the dictionary with the new annotation info
                infodic.update({id_entry: {"Gene": gene_found}})
    return gene_found


def do_MATH_months(sourcedate, months):
    """
    this function calculates the date after subtracting or adding a given amount of months to the current date
    :param sourcedate: date of today
    :param months: amount of months to add or subtract (input a negative number to subtract)
    :return: the date with the amount added or subtracted
    """
    # just calculate the date
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])
    return datetime.date(year, month, day)


def make_wordcloud_dataframe(data, annotation_entries):
    """
    makes a dataframe for the wordcloud of each entry by counting the frequency of every word in the annotation
    :param data: empty dictionary
    :return: filled data, {key = pubmed_id, value = [word, frequency, type of annotation]}
    """
    # for all annotations in the dictionary update the data with the entry
    for id_entry, dictionary in annotation_entries.items():
        data.update({id_entry: []})
        # add to the value of the entry the words with their corresponding frequency
        for type_annotation, listy in dictionary.items():
            frequency = collections.Counter(listy)
            for word in listy:
                frequency_word = frequency[word]
                list_for_dic = [word, frequency_word, type_annotation]
                if list_for_dic not in data[id_entry]:
                    data[id_entry].append(list_for_dic)
    return data


def make_csv_data(data):
    """
    makes data that can be downloaded from the website in the form of a txt file that can be used in Excel
    :param data: annotation of all entries
    :return: big string of all the annotations seperated the columns with ,
                                                     and the words with /
                                                    every line ends with \n
    """
    # instance variables
    sentence = []
    thing = ['', '', '', '', '']
    # add the stuff to the right place and join it with the right separator
    for id_entry, dic in data.items():
        thing = ['', '', '', '', '']
        thing[0] = id_entry
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
        # separate the columns with a comma
        thing = ", ".join(thing)
        sentence.append(thing)
    # make sure all of the entries are on a different line by using \n
    sentence = "\n".join(sentence)
    # add the string to a list
    sentence = [sentence]

    return sentence


@app.errorhandler(404)
def page_not_found(e):
    """
    error handler for page not found
    :param e: error 404
    :return: template for 404 error
    """
    return render_template('404.html'), 404


@app.errorhandler(410)
def page_gone(e):
    """
        error handler for page gone
        :param e: error 410
        :return: template for 410 error
        """
    return render_template('410.html'), 410


@app.errorhandler(500)
def internal_error(e):
    """
        error handler for internal
        :param e: error 500
        :return: template for 500 error
        """
    return render_template('500.html'), 500


if __name__ == '__main__':
    app.run()
