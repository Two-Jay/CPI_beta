import streamlit as st
import openai
import json
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from utils import read_file
from models import *

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
    
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(0.2), retry=retry_if_exception_type(Exception))
    def inference_chat(self, user_input : str) -> str:
        memory = self.memory.get_memory()
        temp = [{"role" : "system", "content" : self.system_prompt}] + memory.copy()
        temp.append({"role" : "user", "content" : user_input})
        response = self.client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=temp,
            response_format=DetectivePrompt,
        )
        content = response.choices[0].message.parsed
        print(content)
        if content.response is None:
            raise Exception("response not in content")
        self.memory.add_memory("user", user_input)
        self.memory.add_memory("assistant", content.response)
        return content


class PromptRequirementsSummarizer:
    def __init__(self, memory : Memory, client = None, system_prompt = None):
        self.memory = memory
        self.client = client
        self.system_prompt = system_prompt
    
    def inference(self, history : str) -> str:
        response = self.client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": str(history)}
            ],
            response_format=PromptRequirementsSummary
        )
        return response.choices[0].message.parsed

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
                if response.is_end:
                    print("끝났어요!")
                    summarized = st.session_state.summarizer.inference(inferencer.memory.get_memory())
                    print(summarized)
                    st.session_state.summary = summarized

        with c2:
            if clicked := st.button("Clear"):
                reset()
                # st.rerun()

    with history_container:
        display_history(inferencer.memory, history_container)


class PromptEnhancer:
    def __init__(self, memory : Memory, client = None, system_prompt = None):
        self.memory = memory
        self.client = client
        self.system_prompt = system_prompt

    def inference(self, summary : PromptRequirements) -> str:
        temp_system_prompt = self.system_prompt.replace("<user_dialog_summary>", str(summary.requirements))
        response = self.client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": temp_system_prompt}
            ],
            response_format=PromptRequirements
        )
        return response.choices[0].message.parsed

def display_panel():
    console_container = st.container(height=300)
    summary_container = st.container(height=300)

    with console_container:
        need_enhancing = st.toggle("Need Enhancing")
        iteration_turn_count = st.number_input("Iteration Turn Count", min_value=1, max_value=10,value=1)
        test_dialog_turn_count = st.number_input("Test Dialog Turn Count", min_value=1, max_value=10,value=1)
        need_diversity_in_test_dialog = st.toggle("Need Diversity in Test Dialog")

        st.session_state.iteration_turn_count = iteration_turn_count
        st.session_state.test_dialog_turn_count = test_dialog_turn_count
        st.session_state.need_diversity_in_test_dialog = need_diversity_in_test_dialog
        st.session_state.iteration_sections = [f"Iteration {i+1}" for i in range(iteration_turn_count)]

    if need_enhancing:
        if st.session_state.summary is not None:
            enhanced = st.session_state.enhancer.inference(st.session_state.summary)
            print(enhanced)
            st.session_state.summary = enhanced

    with summary_container:
        st.write("프롬프트 생성 기반 정보")

        if st.session_state.summary is not None:
            for key, value in st.session_state.summary.__dict__.items():
                if key != "reasoning":
                    st.write(f"{key} : {value}")
        else:
            st.write("프롬프트 생성 기반 정보가 없습니다.")
    
    if generate_button := st.button("Generate"):
        if st.session_state.summary is not None:
            st.session_state.iteration_sections = [f"Iteration {i+1}" for i in range(st.session_state.iteration_turn_count)]
            st.session_state.generation_started = True

def main_page():
    st.title("Conversation Prompt Generator_v0.1")
    col1, col2 = st.columns([0.8, 0.2])
    with col1:
        run_chat(st.session_state.inferencer)
    with col2:
        display_panel()

def reset():
    st.session_state.memory.clear_memory()

def init():
    st.set_page_config(page_title="Conversation Prompt Generator_v0.1", page_icon="🧊", layout="wide")
    st.session_state.summary = None
    st.session_state.iteration_sections = []
    st.session_state.generation_started = False
    st.session_state.iteration_turn_count = 1
    st.session_state.test_dialog_turn_count = 1
    st.session_state.need_diversity_in_test_dialog = False
    if "memory" not in st.session_state:
        st.session_state.memory = Memory()
    if "inferencer" not in st.session_state:
        st.session_state.inferencer = Inferencer(st.session_state.memory, oai_client, read_file("resources/prompts/prompt_requirements_detective.md"))
    if "summarizer" not in st.session_state:
        st.session_state.summarizer = PromptRequirementsSummarizer(st.session_state.memory, oai_client, read_file("resources/prompts/prompt_requirements_summary.md"))
    if "enhancer" not in st.session_state:
        st.session_state.enhancer = PromptEnhancer(st.session_state.memory, oai_client, read_file("resources/prompts/prompt_requirement_enhancing.md"))

def run_iteration(iteration_data):
    with st.container(height=300):
        st.write(iteration_data["resource"])

def generate_page():
    if st.session_state.summary is None and len(st.session_state.iteration_sections) == 0:
        st.write("프롬프트 생성 기반 정보가 없습니다.")
    else:
        section_list = st.session_state.iteration_sections
        section_list = list(st.tabs(section_list))
        iteration_data = {
            "resource" : st.session_state.summary
        }
        if len(st.session_state.iteration_sections) > 0 and st.session_state.generation_started:
            for section in section_list:
                run_iteration(iteration_data)
        else:
            st.write("아직 생성이 시작되지 않았습니다.")

if __name__ == "__main__":
    init()
    tab = st.tabs(["Chat", "Generate"])
    with tab[0]:
        main_page()
    with tab[1]:
        generate_page()