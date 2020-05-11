import mysql
from Bio import Entrez, Medline
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
                    print(omim_id_dic)
                else:
                    id_found = textmine_in_OMIM(record[0])
                    omim_id_dic.update({record[0]: [id_found]})
    except Error as e:
        print("Error while connecting to MySQL", e)
    finally:
        if (connection.is_connected()):
            cursor.close()
            connection.close()
            print("MySQL connection is closed")

    return omim_id_dic


def textmine_in_OMIM(term):
    found_id = ""
    Entrez.email = 'A.N.Other@example.com'
    handle = Entrez.esearch(db="omim", term=term)
    record = Entrez.read(handle)
    handle.close()
    idlist = record["IdList"]
    print("idlist = ", idlist)
    for item in idlist:
        found_id = item
    return found_id


genelist = ["A12M1", "A1BG-AS1","A1BG","A2ML1"]
find_in_database(genelist)
