import streamlit as st
import os

from langchain.chains import ConversationChain
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain.agents.agent_types import AgentType


# Get the snowflake connection
conn = st.connection("snowflake")


@st.cache_data(ttl=3600)
def get_snowflake_table(_conn, table_name):
    snowflake_table = _conn.session()
    return snowflake_table.table(table_name).to_pandas()


# Fetch the table
df_picks_raw = get_snowflake_table(conn, "picks")
df_picks = df_picks_raw[df_picks_raw["YEAR"] == 2024]

# Fetch the table
df_players = get_snowflake_table(conn, "players")

def main():
    """
    This function is the main entry point of the application. It sets up the Groq client, the Streamlit interface, and handles the chat interaction.
    """
    
    # Get Groq API key
    groq_api_key = os.environ['GROQ_API_KEY']

    # Display the Groq logo
    spacer, col = st.columns([5, 1])  
    with col:  
        st.image('groqcloud_darkmode.png')

    # The title and greeting message of the Streamlit application
    st.title("Chat with Groq!")
    st.write("Hello! I'm your friendly Groq chatbot. I can help answer your questions, provide information, or just chat. I'm also super fast! Let's start our conversation!")

    # Add customization options to the sidebar
    st.sidebar.title('Customization')
    model = st.sidebar.selectbox(
        'Choose a model',
        ['llama3-8b-8192', 'mixtral-8x7b-32768', 'gemma-7b-it']
    )
    conversational_memory_length = st.sidebar.slider('Conversational memory length:', 1, 10, value = 5)

    memory=ConversationBufferWindowMemory(k=conversational_memory_length)

    user_question = st.text_input("Ask a question:")

    # session state variable
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history=[]
    else:
        for message in st.session_state.chat_history:
            memory.save_context({'input':message['human']},{'output':message['AI']})



    # Generate LLM response
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are the Arbiter.  You are the judge of the game DEADPOOL. You have access to a data frame with a column called NAME, which represents celebrity picks for this year, 2024.  The PLAYERS column contains the game's participants.  When asked about the score or points in the game, you should apply the following formula (50 + (100-AGE)).  Points only count when the NAME is dead as indicated by the DEATH_DATE column being not null.  When you calculate the leaders of the game, you must only count NAMES that have a DEATH_DATE and then calculate the points with the formula.  When you deal with these dataframes, please join them together by the ID field in PLAYERS and the PICKED_BY field in PICKS.",   # noqa: E501
            ),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}"),
        ]
    )

    # Initialize Groq Langchain chat object and conversation
    groq_chat = ChatGroq(
            groq_api_key=groq_api_key, 
            model_name=model
    )
    

    # Create Pandas DataFrame Agent
    agent = create_pandas_dataframe_agent(
        groq_chat,
        [df_picks, df_players],
        verbose=True,
        agent_executor_kwargs={'handle_parsing_errors': True}
    )

    # chain = prompt | agent

    # # This code uses the dataframes but is returning an error
    # conversation = ConversationChain(
    #         llm=agent,
    #         memory=memory
    # )
    
    conversation = ConversationChain(
            llm=groq_chat,
            memory=memory
    )

    # If the user has asked a question,
    if user_question:
        
        # The chatbot's answer is generated by sending the full prompt to the Groq API.
        try:
            response = conversation(user_question)
            message = {'human':user_question,'AI':response['response']}
            st.session_state.chat_history.append(message)
            st.write("Chatbot:", response['response'])
        except Exception as e:
            st.write("Error:", e)

if __name__ == "__main__":
    main()