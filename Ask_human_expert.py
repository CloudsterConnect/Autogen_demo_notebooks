
#!pip install pyautogen==0.2.27
import autogen
from dotenv import load_dotenv
import os
from typing import Annotated


#Variables

# %%
load_dotenv()
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
AUTOGEN_USE_DOCKER=False
DEFAULT_PATH="./tmp/"


#LLM Configurations

config_list = [
    {
        "model": "gpt-4o",
        "base_url": "https://api.openai.com/v1",
        "api_type": "openai",
        "api_key": OPENAI_API_KEY,
        "tags": ["gpt4", "openai"]
    },
]

llm_config = {
    "temperature": 0,
    "config_list": config_list,
    "timeout": 120,
}


#Functions

def is_termination_msg(content) -> bool:
    have_content = content.get("content", None) is not None
    if have_content and "TERMINATE" in content["content"]:
        return True
    return False

def read_file(dir,filename):
    try:
        task_file_path = os.path.join(dir, filename)
        with open(task_file_path, 'r',encoding='utf-8') as file:
            content = file.read()
        return content
    except Exception as e:
        return f"An error occurred while reading the file: {e}"

#Agents

user_proxy = autogen.UserProxyAgent(
    name="user_proxy",# The name is flexible, but should not contain spaces to work in group chat.
    human_input_mode='NEVER',#['ALWAYS', 'TERMINATE', 'NEVER']
    is_termination_msg=is_termination_msg,
    code_execution_config={
        "last_n_messages": 1,
        "work_dir": DEFAULT_PATH,
        "use_docker": False,
    }
)

engineer = autogen.AssistantAgent(
    name="Engineer",# The name is flexible, but should not contain spaces to work in group chat.
    is_termination_msg=is_termination_msg,
    human_input_mode= 'NEVER',#['ALWAYS', 'TERMINATE', 'NEVER']
    llm_config=llm_config,
    system_message="""Engineer. You write python/shell code to solve tasks. Wrap the code in a code block that specifies the script type. The user can't modify your code. So do not suggest incomplete code which requires others to modify. Don't use a code block if it's not intended to be executed by the executor.
    If the error can't be fixed or if the task is not solved even after the code is executed successfully, ask human expert for help.
    """,
    description="An expert coder who writes and tests code in small increments, ensuring Docker runs successfully and the code is fully functional. Provides clear, executable code blocks and updates requirements.txt, Dockerfile, and README.md instructions accordingly."
)


#Skills

@engineer.register_for_llm(description="Ask question from the human expert")
@user_proxy.register_for_execution()
def ask_human_expert(question: Annotated[str, "The question you want to ask the human expert."]) -> Annotated[str, "Answer"]:
    # Path to the sound file
    answer = input(f"Please answer the question: {question}\n")
    return answer



@user_proxy.register_for_execution()
@engineer.register_for_llm(description="To install new Python modules using pip.")
def pip_install(
    module_name: Annotated[str, "The name of the module to install."], 
    shell_command: Annotated[str, "The shell command to install the module using pip."]
):
    try:
        # Construct the pip install command
        pip_command = f"pip install {module_name}"

        # Use the default path if provided
        if DEFAULT_PATH:
            pip_command = f"cd {DEFAULT_PATH} && {pip_command}"

        # Execute the pip install command
        run_result = subprocess.run(shell_command or pip_command, shell=True, capture_output=True, text=True)

        if run_result.returncode == 0:
            return 0, f"Successful:\n{run_result.stdout}"
        else:
            return run_result.returncode, f"Failed:\n{run_result.stderr}"
    except Exception as e:
        return 1, str(e)


#create_file_with_code: Creates a new file with the given code.
@user_proxy.register_for_execution()
@engineer.register_for_llm(description="Create a new file with code.")
def create_file_with_code(
    filename: Annotated[str, "Name and path of file to create."], code: Annotated[str, "Code to write in the file."]
):
    with open(DEFAULT_PATH +'/'+ filename, "w") as file:
        file.write(code)
    return 0, "File created successfully"



#Chat

chat_result = autogen.initiate_chats(
    [
        
        {
            "recipient": engineer,
            "sender": user_proxy,
            "message": "Create a flask app with login page.",
            "max_turns": 20, #rounds between user proxy and engineer
            "max_consecutive_auto_reply":2,
            "clear_history": True,
            "silent": False,
            "summary_method": "last_msg",
            "work_dir": DEFAULT_PATH ,
        },
        
    ]
) 

#Delete the assistant
gpt_assistant.delete_assistant()


