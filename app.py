from flask import Flask, request, jsonify, render_template
from openai import OpenAI
import os
import pyodbc
import re

# Flask - ask question to db using OpenAI
app = Flask(__name__)

apiKey = os.getenv('apiKey')
sqlPwd = os.getenv('sqlPwd')
sys_prompt = os.getenv('prompt')

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
        
        # Render the result page and show the results
        return render_template('result.html', result=result)
    else:
        return jsonify({"error": "No SQL query found."}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
