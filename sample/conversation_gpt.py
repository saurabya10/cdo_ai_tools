import local_settings
from local_settings import get_api_key
from langchain_openai import AzureChatOpenAI
from langchain.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory, FileChatMessageHistory

from langchain.chains import LLMChain

from dotenv import load_dotenv

load_dotenv()


def get_llm():
    if local_settings.llm_source == "bridgeIT":
        api_key = get_api_key()
        llm_model = local_settings.llm_model
        api_version = local_settings.api_version
        llm_endpoint = local_settings.llm_endpoint
        app_key = local_settings.app_key
        llm = AzureChatOpenAI(
            model=llm_model,
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=llm_endpoint,
            temperature=0.7,
            model_kwargs=dict(user='{"appkey": "' + app_key + '", "user": "user1"}'),
        )
        return llm
    

if __name__ == "__main__":
    llm = get_llm()
    file_chat_history = FileChatMessageHistory('chat_history.json')
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True,
        chat_memory=file_chat_history
    )
    
    chatPromptTemplate = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant."),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{content}")
    ]) 
    chain = LLMChain(
        llm=llm,
        prompt=chatPromptTemplate,
        memory=memory,
        verbose=True
    ) 
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            break
        response = chain.run(content=user_input)
        print(f"Assistant: {response}")