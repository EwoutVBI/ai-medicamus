from flask import Flask, request, jsonify, render_template
from openai import OpenAI
import os
import pyodbc
import re
import sqlparse

# Flask - ask question to db using OpenAI
app = Flask(__name__)

apiKey = os.getenv('API_KEY_AI')
sqlPwd = os.getenv('SQL_PWD_AI')

with open('system_prompt.txt', 'r') as file:
    sys_prompt = file.read()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    user_prompt = request.form['user_prompt']
    # Process the input (e.g., save to database)
    return render_template('query.html', user_prompt=user_prompt)

# Function to query the OpenAI API
def ask_openai(my_client, user_question):
    response = my_client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": sys_prompt,
            },
            {
                "role": "user",
                "content": user_question,
            }
        ],
        model="gpt-4o"
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
    user_prompt = request.form['user_prompt']
    my_client = OpenAI(api_key=apiKey)
    sql_query = ask_openai(my_client, user_prompt)
    
    if sql_query:
        # Maak de verbinding met Azure SQL Server
        server = 'med-nep-sqlsrv-dataplatform-001.database.windows.net'
        database = 'med-nep-sqldb-dataplatform-001'
        username = 'aiuser'
        password = sqlPwd
        driver= '{ODBC Driver 17 for SQL Server}'
        
        connection_string = f'DRIVER={driver};SERVER={server};PORT=1433;DATABASE={database};UID={username};PWD={password}'
        db_connection = pyodbc.connect(connection_string)
        result = execute_query(sql_query, db_connection)
        db_connection.close()
        
        # Pyodbc geeft het antwoord als [(2,)]
        result = str(result)
        comma_index = result.find(',')

        # Pak het resultaat tussen () voor de 1e komma
        result = f" Er zijn {result[result.find('(') + 1:comma_index]} patienten gevonden, die voldoen aan de vraag {user_prompt}."

        formatted_sql_query = sqlparse.format(sql_query, reindent=True, keyword_case='upper')
        # Open de resultaatpagina
        return render_template('result.html', query=formatted_sql_query, result=result)
    else:
        return render_template('result.html', query='Niet van toepassing', result=f"Bij de vraag    {user_prompt}    konden wij nog geen antwoord vinden, neem a.u.b. zonodig contact op met support.")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
