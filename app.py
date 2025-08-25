# start of app.py
import chainlit as cl
import json
import logging
import os
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferWindowMemory

from config import settings
from config.logging_config import setup_logging
from ingest import ingest_data
from tools.rag_tool import query_knowledge_base
from tools.nocodb_tools import (
    get_open_job_positions, 
    get_job_details, 
    get_application_status,
    apply_for_job_position
)
from tools.feedback_tool import record_feedback 
from auth_page import run_auth_and_onboarding_flow
from ui_components import display_job_listings

setup_logging()
logger = logging.getLogger(__name__)

vector_store_path = settings.VECTOR_STORE_PATH
logger.info(f"Checking for vector store at path: '{vector_store_path}'")
if not (os.path.isdir(vector_store_path) and os.listdir(vector_store_path)):
    logger.info("Vector store path does not exist or is empty. Running ingestion process.")
    ingest_data()
else:
    logger.info("Vector store directory exists and is not empty. Skipping ingestion.")
    
# --- THE FIX: ESCAPE CURLY BRACES IN THE PROMPT ---
AGENT_SYSTEM_PROMPT = """
You are a specialized AI assistant trained to provide accurate information based on a collection of internal company documents for "میهن" company. Your knowledge is strictly confined to the content within this provided knowledge base.
You are a smart, friendly, professional, and empathetic HR assistant for our company.
Your primary goal is to provide a seamless and helpful experience for candidates, making them feel welcomed and supported.

**Your Persona:**
- **Conversational & Natural:** Speak like a helpful colleague, not a robot. Avoid technical jargon.
- **Proactive:** Anticipate the user's needs. If you provide job details, suggest the next logical step, like applying.
- **Knowledgeable:** Use the knowledge base to answer questions about company culture, benefits, and processes.

**Core Instructions:**
1.  **You know the user:** You are speaking to an authenticated user. You already know who they are. **Never ask for their name, phone number, or ID.** Act as if you have their file right in front of you. Do not mention their internal ID number or phone number in your responses.
2.  **Be User-Friendly:** Always communicate in a clear and human-readable way. When you use a tool and get information back, summarize it and present it beautifully using Markdown. **Never show raw data like JSON to the user.**
3.  **Know your capabilities:** You can help users by:
    - Finding open job positions.
    - Providing detailed information about a specific job.
    - Applying for a job on their behalf when they ask.
    - Checking their application status.
    - Answering general questions about the company.

**Boundaries and Limitations (Very Important):**
- **Only offer actions you can actually perform.** You have tools to apply for jobs and check status. You DO NOT have tools for other tasks like applying for leave, changing personal data, etc.
- **If asked to do something you cannot do,** you must state your limitation clearly and politely, then guide the user to the correct process. For example: "من نمی‌توانم درخواست مرخصی را ثبت کنم، اما طبق اطلاعات من، شما باید برای این کار با واحد منابع انسانی به طور مستقیم در تماس باشید." (I cannot register a leave request, but according to my information, you should contact the HR department directly for this.)
"""

def create_hr_agent():
    tools = [
        query_knowledge_base, 
        get_open_job_positions, 
        get_job_details,
        get_application_status, 
        record_feedback,
        apply_for_job_position
    ]
    llm = ChatOpenAI(model=settings.OPENAI_API_MODEL, temperature=0.1, api_key=settings.OPENAI_API_KEY)
    prompt = ChatPromptTemplate.from_messages([
        ("system", AGENT_SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True)

@cl.on_chat_start
async def start_chat():
    await cl.Message(content="به سیستم استخدام خوش آمدید. لطفاً ابتدا احراز هویت کنید.").send()
    user_profile = await run_auth_and_onboarding_flow()
    
    if not user_profile:
        logger.warning("User failed or abandoned the authentication flow.")
        await cl.Message(content="احراز هویت ناموفق بود. لطفاً برای تلاش مجدد، صفحه را رفرش کنید.").send()
        return
        
    logger.info(f"User authenticated. Profile: {user_profile}")
    cl.user_session.set("user_profile", user_profile)
    
    agent_executor = create_hr_agent()
    cl.user_session.set("agent_executor", agent_executor)
    
    memory = ConversationBufferWindowMemory(k=5, return_messages=True, memory_key="chat_history")
    cl.user_session.set("memory", memory)
    
    first_name = user_profile.get("FirstName", "کاربر")
    await cl.Message(
        content=f"سلام **{first_name}**! پروفایل شما تکمیل شد. به دستیار هوشمند استخدام خوش آمدید.",
        author="هوشمند"
    ).send()

    await cl.Message(
        content="شما می‌توانید سوالات خود را در مورد شرکت بپرسید یا برای موقعیت‌های شغلی موجود درخواست دهید. \n\nدر اینجا لیست موقعیت‌های شغلی باز فعلی آمده است:",
        author="هوشمند"
    ).send()
    
    jobs_json_string = get_open_job_positions.invoke({})
    await display_job_listings(jobs_json_string)

@cl.on_message
async def main(message: cl.Message):
    agent_executor = cl.user_session.get("agent_executor")
    memory = cl.user_session.get("memory")
    user_profile = cl.user_session.get("user_profile")
    
    if not all([agent_executor, memory, user_profile]):
        await cl.Message(content="سیستم آماده نیست یا احراز هویت انجام نشده. لطفاً صفحه را رفرش کنید.").send()
        return
        
    phone_number = user_profile.get("PhoneNumber")
    candidate_id = user_profile.get("Id")
    
    memory_variables = memory.load_memory_variables({})
    
    agent_input = {
        "input": f"User's phone number is {phone_number} and their candidate_id is {candidate_id}. User's query is: {message.content}",
        "chat_history": memory_variables.get("chat_history", [])
    }
    
    response_msg = cl.Message(content="", author="هوشمند")
    final_answer = ""
    
    async for chunk in agent_executor.astream(agent_input):
        token = chunk.get("output", "")
        if token:
            final_answer += token
            await response_msg.stream_token(token)

    if final_answer:
        response_msg.content = final_answer
        
    cl.user_session.set("last_query", message.content)
    cl.user_session.set("last_response", final_answer)

    feedback_actions = [
        cl.Action(name="feedback_good", value="good", label="👍 پاسخ خوب بود", payload={}),
        cl.Action(name="feedback_bad", value="bad", label="👎 پاسخ خوب نبود", payload={}),
    ]
    response_msg.actions = feedback_actions
    await response_msg.update()

    memory.save_context({"input": message.content}, {"output": final_answer})

@cl.action_callback("view_job_details")
@cl.action_callback("apply_for_job")
async def on_action(action: cl.Action):
    agent_instruction = action.payload.get("agent_instruction")
    if agent_instruction:
        msg = cl.Message(content=agent_instruction, author="user")
        await main(msg)
    else:
        logger.warning(f"Action '{action.name}' was clicked but had no agent_instruction in payload.")

@cl.action_callback("feedback_good")
@cl.action_callback("feedback_bad")
async def on_feedback(action: cl.Action):
    message = cl.context.current_step
    if message and message.actions:
        message.actions = []
        await message.update()

    last_query = cl.user_session.get("last_query")
    last_response = cl.user_session.get("last_response")
    rating = "good" if action.name == "feedback_good" else "bad"
    
    user_profile = cl.user_session.get("user_profile")
    phone_number = user_profile.get("PhoneNumber", "unknown") if user_profile else "unknown"

    if not all([last_query, last_response]):
        await cl.Message(content="خطایی در بازیابی پیام قبلی برای ثبت بازخورد رخ داد.").send()
        return
        
    feedback_payload = {
        "user_phone": phone_number, "query": last_query,
        "response": last_response, "rating": rating
    }
    response_message = await record_feedback.ainvoke(feedback_payload)
    await cl.Message(content=response_message).send()
# end of app.py