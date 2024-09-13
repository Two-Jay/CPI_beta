import streamlit as st
import openai

# OpenAI API 키 설정 (실제 사용 시 환경 변수로 관리하는 것이 좋습니다)
api_key = st.secrets["OPENAI_API_KEY"]
oai_client = openai.OpenAI(api_key=api_key)

class Memory:
    def __init__(self):
        self.memory = []

    def add_memory(self, role, content):
        self.memory.append({"role": role, "content": content})

    def get_memory(self):
        return self.memory
    
    def clear_memory(self):
        self.memory = []

class Inferencer:
    def __init__(self, memory : Memory, client = None):
        self.memory = memory
        self.client = client

    def inference(self, user_input : str) -> str:
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": user_input}
            ]
        )
        return response.choices[0].message.content
    
    def inference_with_memory(self, user_input : str) -> str:
        memory = self.memory.get_memory()
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": user_input}
            ]
        )
        self.memory.add_memory("assistant", response.choices[0].message.content)
        return response.choices[0].message.content


def inference(user_input : str, me) -> str :
    response = oai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": user_input}
        ]
    )
    return response.choices[0].message.content


# import streamlit as st
# from openai import OpenAI

# st.title("ChatGPT-like clone")

# # Set OpenAI API key from Streamlit secrets
# client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# # Set a default model
# if "openai_model" not in st.session_state:
#     st.session_state["openai_model"] = "gpt-3.5-turbo"

# # Initialize chat history
# if "messages" not in st.session_state:
#     st.session_state.messages = []

# # Display chat messages from history on app rerun
# for message in st.session_state.messages:
#     with st.chat_message(message["role"]):
#         st.markdown(message["content"])

# # Accept user input
# if prompt := st.chat_input("What is up?"):
#     # Add user message to chat history
#     st.session_state.messages.append({"role": "user", "content": prompt})
    # Display user message in chat message container
    # with st.chat_message("user"):
        # st.markdown(prompt)


def run_chat(inferencer : Inferencer):
    for message in st.session_state.memory.get_memory():
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("What is up?"):
        response = inferencer.inference_with_memory(prompt)
        with st.chat_message("user"):
            st.markdown(prompt)

def main():
    st.title("AI 채팅 어시스턴트")

    run_chat(st.session_state.inferencer)

def init():
    st.session_state.is_display = False
    st.session_state.memory = Memory()
    st.session_state.inferencer = Inferencer(st.session_state.memory, oai_client)

if __name__ == "__main__":
    init()
    main()