import mysql
from bio import Entrez, Medline
from mysql.connector import Error

def main(gene_list):
    find_in_database(gene_list)

def find_in_database(gene_list):
    omim_id_dic = {}
    big_string = []
    biggest_string = ""
    for gene in gene_list:
        string = "symbool like '{}' ".format(gene)
        big_string.append(string)
    biggest_string = "or ".join(big_string)
    print(biggest_string)
    query = "select symbool, omimId from huidig_symbool where {}".format(biggest_string)
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
                omim_id_dic.update({record[0]: record[1]})
    except Error as e:
        print("Error while connecting to MySQL", e)
    finally:
        if (connection.is_connected()):
            cursor.close()
            connection.close()
            print("MySQL connection is closed")

    return omim_id_dic
def idk():
    Entrez.email = 'A.N.Other@example.com'
    handle = Entrez.esearch(db="omim", term="ATP8")
    record = Entrez.read(handle)
    handle.close()
    idlist = record["IdList"]
    print(record)
    return idlist

def idk2(idList):
    handle = Entrez.efetch(db="omim", id="617530", retmode="text")
    print(handle.readline().strip())


