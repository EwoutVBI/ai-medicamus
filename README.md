# General
An Azure web app is the user interface to ask questions to GPT and the database. The question flows are:

User question in Azure web app → sent to OpenAI → OpenAI replies with SQL query
SQL query response → is sent to SQL database → SQL database gives results back to Azure web app → Azure displays result to the user

I created a Python script in the back-end that is listening for a question and then use the LLM (large language model) and OpenAI libraries to interpret the question based on a system prompt, containing the database structure, cues and examples, translates the question into a SQL statement.
