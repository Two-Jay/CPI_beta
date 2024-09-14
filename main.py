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
            generate_page()
            

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

antagonist_prompt = read_file("resources/prompts/dialog/antagonist.md")
protaganist_prompt = read_file("resources/prompts/dialog/protagonist.md")
extraction_prompt = read_file("resources/prompts/dialog/extraction_customer_action.md")

requirement_extention_prompt = read_file("resources/prompts/process/requirement_extention.md")
output_input_definition_prompt = read_file("resources/prompts/process/output_input_definition.md")
draft_prompt = read_file("resources/prompts/process/draft_prompt.md")

reflextion_making_prompt = read_file("resources/prompts/reflextion/reflextion_making.md")
reflextion_application_prompt = read_file("resources/prompts/reflextion/reflextion_application.md")
reflextion_dialog_prompt = read_file("resources/prompts/reflextion/reflextion_dialog.md")


def single_inference(prompt : str, temperature : float = 0.56, max_token : int = 1024) -> str:
    response = oai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=temperature,
        max_tokens=max_token
    )
    return response.choices[0].message.content

from typing import List, Dict

def reflextion(prompt : str, dialog_history : List[Dict[str, str]]) -> str:
    reflextion_prompt = str(reflextion_dialog_prompt)
    reflextion_prompt = reflextion_prompt.replace("<dialog_history>", str(dialog_history))
    reflextion_prompt = reflextion_prompt.replace("<prompt>", str(prompt))
    reflextion_prompt = single_inference(reflextion_prompt)
    return reflextion_prompt

def run_case(
    data : dict,
    is_singleturn : bool = False,
    test_dialog_turn_count : int = 1
) -> dict:
    resource = data["resource"]
    prompt_base_1 = str(requirement_extention_prompt)
    prompt_base_2 = str(output_input_definition_prompt)
    draft_prompt = str(draft_prompt)

    prompt_base_1 = prompt_base_1.replace("<resource>", str(resource), temperature=0.56, max_token=1500)
    prompt_base_2 = prompt_base_2.replace("<resource>", str(resource), temperature=0.4, max_token=1500)

    prompt_base_1 = single_inference(prompt_base_1)
    prompt_base_2 = single_inference(prompt_base_2)
    draft_prompt = draft_prompt.replace("<prompt_base_1>", prompt_base_1)
    draft_prompt = draft_prompt.replace("<prompt_base_2>", prompt_base_2)        

    return {
        "prompt" : draft_prompt,
        "prompt_base_1" : prompt_base_1,
        "prompt_base_2" : prompt_base_2,
        "reflextion" : None
    }
    

def run_iterations(iteration_list, data):
    data["prompt"] = ""
    data["prompt_base_1"] = ""
    data["prompt_base_2"] = ""
    data["reflextion"] = ""
    for section in iteration_list:
        with section:
            data = run_case(
                data,
                is_singleturn=data["resource"].turn_count == 1,
                test_dialog_turn_count=st.session_state.test_dialog_turn_count
            )
            st.write(data)
    st.write(data)

def generate_page():
    if st.session_state.summary is None:
        st.write("프롬프트 생성 기반 정보가 없습니다.")
    else:
        section_list = st.session_state.iteration_sections
        section_list = list(st.tabs(section_list))
        iteration_data  = {
            "resource" : st.session_state.summary
        }
        if len(st.session_state.iteration_sections) > 0 and st.session_state.generation_started:
            run_iterations(section_list, iteration_data)
        else:
            st.write("아직 생성이 시작되지 않았습니다.")

if __name__ == "__main__":
    init()
    main_page()