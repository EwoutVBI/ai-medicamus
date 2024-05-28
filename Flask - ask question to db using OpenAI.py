from werkzeug.utils import url_quote
from flask import Flask, request, jsonify
from openai import OpenAI
import os
import pyodbc
import re

app = Flask(__name__)

apiKey = os.getenv('apiKey')
sqlPwd = os.getenv('sqlPwd')

user_question = input("Welke vraag wil je stellen aan de data?")
# Function to query the OpenAI API
def ask_openai(my_client):
    response = my_client.chat.completions.create(
    messages=[
        {
            "role": "system",
            "content": '''Convert the following natural language question to a T-SQL query executable on an Azure SQL Server database.
Database Schema Information:

    Patients:
        Table: dwh_his.Dim_Patient
        Primary Key: Patient_Key
        Columns: Patient_Key, Patient_BKey, Patient_Geslacht, Patient_Leeftijd, Patient_Overleden
    Medication:
        Table: dwh_his.Fct_Medicijnverstrekkingen
        Primary Key: None
        Foreign Keys: Patient_Key
        Columns: ATC_Key, Patient_Key, Medicijnverstrekking_Startdatum, Medicijnverstrekking_Einddatum, Medicijnverstrekking_Opiaat
    Medication Variations:
        Table: dwh_his.Dim_ATC
        Primary Key: ATC_Key
        Columns: ATC_Key, ATC_BKey, ATC_Niveau
    Diagnoses (ICPC):
        Unique Diagnoses Table: dwh_his.Dim_ICPC
        Primary Key: ICPC_Key
        Columns: ICPC_Key, ICPC_BKey, ICPC_Categorie, ICPC_Categorie_Naam
    Assigned Diagnoses Table: dwh_his.Fct_PatientEpisodes
        Primary Key: None
        Foreign Keys: Patient_Key, ICPC_Key
        Columns: ICPC_Key, Patient_Key, ICPC_Startdatum, ICPC_Einddatum, Attentie, Prioriteit
Relationships:

    dwh_his.Fct_PatientEpisodes links to dwh_his.Dim_Patient via Patient_Key
    dwh_his.Fct_PatientEpisodes links to dwh_his.Dim_ICPC via ICPC_Key
    dwh_his.Fct_Medicijnverstrekkingen links to dwh_his.Dim_Patient via Patient_Key
    dwh_his.Fct_Medicijnverstrekkingen links to dwh_his.Dim_ATC via ATC_Key

Instructions:

    If you know the SQL query, respond with only the SQL.
    If you don't know the SQL query, respond with "shit".
    For "How many" questions, always answer with a query returning a single row.

Examples:
    Question: "Hoeveel unieke patienten zijn er?"
    SQL query: 
    SELECT COUNT(DISTINCT(Patient_Key)) AS number_of_patients
    FROM dwh_his.Dim_Patient

    Question: "Hoeveel clienten hebben meer dan 1 diagnose?"
    SQL Query:
    SELECT COUNT(*) AS number_of_clients
    FROM (
        SELECT Patient_Key
        FROM dwh_his.Fct_PatientEpisodes
        GROUP BY Patient_Key
        HAVING COUNT(DISTINCT ICPC_Key) > 1
    ) AS multiple_diagnoses_clients;

    Question: "Hoeveel keer zijn er medicijnen voorgeschreven?"
    SQL Query:
    SELECT COUNT(*) AS number_of_medications_distributed
    FROM dwh_his.Fct_Medicijnverstrekkingen;

    Question: "Hoeveel unieke medicijnen zijn er?"
    SQL Query:
    SELECT COUNT(*) AS number_of_unique_medication_variations
    FROM dwh_his.Dim_ATC;

    Question: "Hoeveel patienten hebben medicatie A01AB06 domifeen voorgeschreven gekregen?
    SQL Query:
    SELECT COUNT(*) AS number_of_patients_with_domifeen
    FROM dwh_his.Fct_Medicijnverstrekkingen
    LEFT JOIN
    dwh_his.Dim_ATC
        ON dwh_his.Fct_Medicijnverstrekkingen.ATC_Key = dwh_his.Dim_ATC.ATC_Key
    WHERE ATC_Niveau = 'A01AB06 domifeen';

    Question: "Hoeveel patienten hebben een actieve diagnose A09.01 Nachtzweten op 5 juni 2023?"
    SQL Query:
    SELECT COUNT(DISTINCT(Patient_Key)) AS number_of_patients_with_night_sweats
    FROM dwh_his.Fct_PatientEpisodes
    LEFT JOIN dwh_his.Dim_ICPC
        ON dwh_his.Fct_PatientEpisodes.ICPC_Key = dwh_his.Dim_ICPC.ICPC_Key
    WHERE ICPC_Categorie_Naam = 'A09.01 Nachtzweten'
        AND ICPC_Start_Datum > '2023-06-05' AND (ICPC_Einddatum IS NULL OR ICPC_Einddatum >= '2023-06-05');

    Question: "Hoeveel patienten hebben in 2023 medicatie voorgeschreven gekregen?"
    SQL Query:
    SELECT COUNT(DISTINCT(Patient_Key)) AS number_of_patients_with_medications
    FROM dwh_his.Fct_Medicijnverstrekkingen
    LEFT JOIN dwh_his.Dim_ATC
        ON dwh_his.Fct_Medicijnverstrekkingen.ATC_Key = dwh_his.Dim_ATC.ATC_Key
    WHERE ICPC_Start_Datum >= '2023-01-01' AND (ICPC_Einddatum IS NULL OR ICPC_Einddatum > '2023-12-31');

    Guidelines:

    Select counts: Use COUNT(*) for counting rows in a table.
    Group and filter: Use GROUP BY and HAVING for questions involving conditions on grouped data.
    Join tables: Use JOIN to combine data from multiple tables based on relationships.
    ''',
        },
        {
            "role": "user",
            "content": {user_question},
        }
    ],
    model="gpt-4o",
    )
    sql = take_sql_from_response(str(response))

    return sql
def take_sql_from_response(response):
    regex = r"SELECT .*?;"
    match = re.search(regex, response)
    if match:
        sql_query = match.group()
        sql_query = sql_query.replace("\\n", " ")
        print(sql_query)
        return sql_query
    
# Function to execute SQL query
def execute_query(query, db_connection):
    cursor = db_connection.cursor()
    cursor.execute(query)
    result = cursor.fetchall()
    cursor.close()
    return result

# Main function
@app.route('/query', methods=['POST'])
def query():
    my_client = OpenAI(
    api_key= apiKey
    )
    sql_query = ask_openai(my_client)
    if sql_query:
        # Set up the connection to Azure SQL Server
        server = 'med-nep-sqlsrv-dataplatform-001.database.windows.net'
        database = 'med-nep-sqldb-dataplatform-001'
        username = 'aiuser'
        password = sqlPwd
        driver= '{ODBC Driver 17 for SQL Server}'
        
        connection_string = f'DRIVER={driver};SERVER={server};PORT=1433;DATABASE={database};UID={username};PWD={password}'
        db_connection = pyodbc.connect(connection_string)
        result = execute_query(sql_query, db_connection)
        db_connection.close()
        return jsonify(result)
    else:
        return jsonify({"error": "No SQL query found."}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
