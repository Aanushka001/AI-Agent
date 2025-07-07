from backend.services.agent_service import create_agent

agent = create_agent()

print(">>> You can now chat with the agent. Type 'exit' to quit.")
while True:
    user_input = input("You: ")
    if user_input.lower() in ["exit", "quit"]:
        break
    try:
        response = agent.invoke({"input": user_input})
        print("Agent:", response["output"])
    except Exception as e:
        print("Error:", str(e))
