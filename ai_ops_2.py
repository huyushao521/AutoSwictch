from http.client import responses
from langchain.chains.qa_with_sources.stuff_prompt import template
from langchain.chains.summarize.map_reduce_prompt import prompt_template
from langchain_core.prompts import PromptTemplate
from langchain_deepseek.chat_models import ChatDeepSeek
from langchain_core.runnables import RunnableLambda
from netmiko import ConnectHandler


deepseek_api_key = "sk-289f82b003b34950afa6ac26454107"

llm = ChatDeepSeek(model="deepseek-chat", temperature=0, api_key=deepseek_api_key)

USERNAME = "admin"
PASSWORD = "admin@123"


def run_commands_on_switch(device_ip, username, password, command):
    try:
        print(f"Connecting to {device_ip}...")
        device = {
            "device_type": "huawei",
            "ip": device_ip,
            "username": username,
            "password": password,
        }
        with ConnectHandler(**device) as ssh_conn:
            print(f"Running command: {command}")
            output = ssh_conn.send_command(command)
            return f"\n=== Output for '{command}' ===\n{output}"
    except Exception as e:
        return f"Error: {str(e)}"


prompt = PromptTemplate(
    input_variables=["user_query"],
    template="""
    you are a network assistant.Parse the user's query to extract the following:
    1.The command to run on the switch
    2.The IP address of the switch

    Query: "{user_query}"
    Response Format:
    Command:<command>
    IP:<switch_ip>
    """
)
parse_chain = RunnableLambda(
    lambda inputs: llm.invoke(prompt.format(user_query=inputs["user_query"]))
)


# Process a user query, parse it, connect to the switch and run the commands.
def process_query(user_query, username, password):
    # Step 1: Parse the query using LLM
    print("Parsing user query...")
    parsed_response = parse_chain.invoke({"user_query": user_query})
    parsed_content = parsed_response.content
    print("Parsed Response:\n", parsed_content)
    command, device_ip = None, None
    for line in parsed_content.splitlines():
        if line.startswith("Command:"):
            command = line.split("Command:")[1].strip()
        elif line.startswith("IP:"):
            device_ip = line.split("IP:")[1].strip()
    if not command or not device_ip:
        return "Could not parse the query. Ensure you specify a command and device IP."
    # Step 2: Run the command on the switch
    print(f"Executing command '{command}' on device {device_ip}...")
    result = run_commands_on_switch(device_ip, username, password, command)
    return result


if __name__ == "__main__":
    print("\n=== AInetops ===\n")
    while True:
        user_query = input("请使用合适的提示词进行提问或者输入 'exit'退出: ")
        if user_query.lower() == 'exit':
            print("Exiting... Goodbye!")
            break
        output = process_query(user_query, USERNAME, PASSWORD)
        print("\n=== Command Output ===")
        print(output)
