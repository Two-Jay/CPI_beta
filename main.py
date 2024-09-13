import streamlit as st
import openai
import json
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception
from utils import read_file

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
    def __init__(self, memory : Memory, client = None, system_prompt = None):
        self.memory = memory
        self.client = client
        self.system_prompt = system_prompt

    def inference(self, user_input : str) -> str:
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": user_input}
            ]
        )
        return response.choices[0].message.content
    
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2), retry=retry_if_exception(lambda e: "response" not in dir(e)))
    def inference_chat(self, user_input : str) -> str:
        memory = self.memory.get_memory()
        memory.append({"role": "user", "content": user_input})
        temp = [{"role" : "system", "content" : self.system_prompt}] + memory
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=temp,
            temperature=0.56,
            max_tokens=350
        )
        content = response.choices[0].message.content

        if "response" not in dir(response):
            raise Exception("response not in dir(response)")
        if '```json' in content:
            content = content.replace('```json\n', '').replace('\n```', '')
            content = json.loads(content)
        self.memory.add_memory("assistant", content["response"])
        return content


def inference(user_input : str, me) -> str :
    response = oai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": user_input}
        ]
    )
    return response.choices[0].message.content

def display_history(memory : Memory, history_container : st.container):
    with history_container:
        for message in memory.get_memory():
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

def run_chat(inferencer : Inferencer):
    history_container = st.container(height=700)
    input_container = st.container(height=120)
    if len(inferencer.memory.get_memory()) == 0:
        inferencer.memory.add_memory("assistant", "안녕하세요. 저는 CPI입니다. 어떤 프롬프트를 만들기를 원하시나요? ")

    with input_container:
        c1,c2 = st.columns([0.8, 0.2])
        with c1:
            if prompt := st.chat_input("What is up?"):
                response = inferencer.inference_chat(prompt)

        with c2:
            if clicked := st.button("Clear"):
                reset()
                st.rerun()

    with history_container:
        display_history(inferencer.memory, history_container)

def main():
    st.title("AI 채팅 어시스턴트")
    run_chat(st.session_state.inferencer)

def reset():
    st.session_state.memory.clear_memory()

def init():
    if "memory" not in st.session_state:
        st.session_state.memory = Memory()
    if "system_prompt" not in st.session_state:
        st.session_state.system_prompt = read_file("resources/prompts/prompt_requirements_detective.md")
    if "inferencer" not in st.session_state:
        st.session_state.inferencer = Inferencer(st.session_state.memory, oai_client, st.session_state.system_prompt)

if __name__ == "__main__":
    init()
    main()