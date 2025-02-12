import streamlit as st
from pathlib import Path
import sqlite3
from langchain.sql_database import SQLDatabase
import sqlalchemy
from sqlalchemy import create_engine

from langchain.agents import create_sql_agent
from langchain.agents.agent_types import AgentType
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain_groq import ChatGroq
from langchain.callbacks import StreamlitCallbackHandler

LOCALDB="USE_LOCALDB"
MYSQL="USE_MYSQL"

st.set_page_config(page_title="LangChain: Chat with SQL DB",page_icon="🦜")
st.title("🦜 LangChain: Chat with SQL DB")

radio_opt=['Use Sqlite3 - Student DB','Use MySQL DB']
selected_opt=st.sidebar.radio(label='choose the DB which you want to chat',options=radio_opt)

if radio_opt.index(selected_opt)==1:
    db_uri=MYSQL
    mysql_host=st.sidebar.text_input(label='MySQL Host')
    mysql_user=st.sidebar.text_input(label='MySQL User')
    mysql_password=st.sidebar.text_input(label='MySQL Password',type='password')
    mysql_db=st.sidebar.text_input(label='MySQL DB')
else:
    db_uri=LOCALDB


api_key=st.sidebar.text_input(label='Enter GROQ API Key:',type='password')

if not db_uri:
    st.info('Please provide the database information and URI')

if not api_key:
    st.info('Please provide the GROQ API Key')

@st.cache_resource(ttl='2h')    # total time limit = 2 hours
def configure_db(db_uri,host=None,user=None,password=None,db=None):
    if db_uri==LOCALDB:
        dbfilepath=(Path(__file__).parent/"student.db").absolute()
        creator=lambda: sqlite3.connect(f"file:{dbfilepath}?mode=ro",uri=True)
        return SQLDatabase(create_engine('sqlite:///',creator=creator))
    
    elif db_uri==MYSQL:
        if not (mysql_host and mysql_user and mysql_password and mysql_db):
            st.error('Please provide all MySQL Connection details')
            st.stop()
        return SQLDatabase(create_engine(f"mysql+mysqlconnector://{mysql_user}:{mysql_password}@{mysql_host}/{mysql_db}"))
    

if db_uri==MYSQL:
    db=configure_db(db_uri=db_uri,host=mysql_host,user=mysql_user,password=mysql_password,db=mysql_db)
else:
    db=configure_db(db_uri=db_uri)    


# llm model
llm=ChatGroq(model_name='Llama3-8b-8192',groq_api_key=api_key,streaming=True)

# toolkit
toolkit=SQLDatabaseToolkit(db=db,llm=llm)

#agent
agent=create_sql_agent(llm=llm,toolkit=toolkit,verbose=True,agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION)


if 'messages' not in st.session_state or st.sidebar.button(label='clear message history'):
    st.session_state['messages']=[{'role':'assistant','content':'How can i help you?'}]

for msg in st.session_state.messages:
    st.chat_message(msg.get('role')).write(msg.get('content'))    

user_query=st.chat_input(placeholder='Ask any information from the database')    

if user_query:
    st.session_state.messages.append({'role':'user','content':user_query})
    st.chat_message('user').write(user_query)

    with st.chat_message('assistant'):
        st_cb=StreamlitCallbackHandler(st.container())
        response=agent.run(user_query,callbacks=[st_cb])
        st.session_state.messages.append({'role':'assistant','content':response})
        st.write(response)


