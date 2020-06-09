"""
Dit script zoekt de ids bij een gen naam in een database
Gemaakt door: Sanne van Staveren
Versie: 2.0
Gemaakt op: 09-06-2020
"""
import mysql
from mysql.connector import Error


def main(gene_list):
    find_in_database(gene_list)


def find_in_database(gene_list):
    """
    takes in a list of genes and checks if they are in the database, if they are the NCBI, uniprot and OMIM ids are
    collected and put into a list connected to the gene
    :param gene_list: list of genes
    :return: dictionary met de ids gelinked aan de genes
    """
    # instance variables
    omim_id_dic = {}
    big_string = []
    connection = ""
    cursor = ""
    for gene in gene_list:
        string = "symbool like '{}' ".format(gene)
        big_string.append(string)
    biggest_string = "or ".join(big_string)
    print(biggest_string)
    query = "select symbool, omimId,uniprotId, NCBIid from huidig_symbool where {}".format(biggest_string)
    print(query)
    try:
        connection = mysql.connector.connect(
            host='hannl-hlo-bioinformatica-mysqlsrv.mysql.database.azure.com',
            db='rucia',
            user='rucia@hannl-hlo-bioinformatica-mysqlsrv',
            password="kip")
        if connection.is_connected():
            db_Info = connection.get_server_info()
            print("Connected to MySQL Server version ", db_Info)
            cursor = connection.cursor()
            cursor.execute(query)
            records = cursor.fetchall()
            for record in records:
                record = list(record)
                record[1] = record[1].strip("\n")
                omim = record[1]
                uni = record[2]
                ncbi = record[3]
                if record[1] != "":
                    omim_id_dic[record[0]] = []
                    omim_id_dic[record[0]].append(omim)
                    omim_id_dic[record[0]].append(uni)
                    omim_id_dic[record[0]].append(ncbi)

    except Error as e:
        print("Error while connecting to MySQL", e)
    finally:
        if (connection.is_connected()):
            cursor.close()
            connection.close()
            print("MySQL connection is closed")

    return omim_id_dic


