import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables from the .env file in the project root
load_dotenv()

# --- ADDED: Define absolute paths for reliability ---
# This gets the path of the directory where settings.py is located (e.g., .../agent/config)
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
# This goes up one level to get the project's root directory (e.g., .../agent)
PROJECT_ROOT = os.path.dirname(CONFIG_DIR)

logger.info(f"PROJECT_ROOT calculated as: {PROJECT_ROOT}")

# --- LLM & Embedding Model Configuration ---
OPENAI_API_MODEL = "gpt-5-nano"
OPENAI_EMBEDDING_MODEL = "text-embedding-3-large"
N8N_SMS_WEBHOOK_URL = os.getenv("N8N_SMS_WEBHOOK_URL")
# --- Vector Store Configuration ---
VECTOR_STORE_PATH = os.path.join(PROJECT_ROOT, "vectorstore")
DOCUMENT_SOURCE_PATH = os.path.join(PROJECT_ROOT, "data")

logger.info(f"VECTOR_STORE_PATH is set to: {VECTOR_STORE_PATH}")

# --- API Keys & Base URL (loaded from .env) ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NOCODB_API_TOKEN = os.getenv("NOCODB_API_TOKEN")
# IMPORTANT: This should be your self-hosted URL from the .env file
NOCODB_BASE_URL = os.getenv("NOCODB_BASE_URL", "https://mihan-hr.nilva.ir") 

# --- NocoDB Table IDs (from your API documentation) ---
# This dictionary maps our internal names to the actual table IDs from your API.
NOCODB_TABLE_IDS = {
    "Candidates": "mbqi7qv0oe7vfsu",
    "JobOpportunities": "mnh7jhgpra68t9u",
    "HiringRecords": "m8cfjywwovld9tt",
    "Feedbacks": "m71yu5bw07ddiz5",
    "Departments": "mq40mr29d1telx0",
    "Documents": "m12o92ka2y65srb"
}

# --- Field Name Mappings (The "Translation Layer") ---
# These dictionaries map our internal English keys to the API's Persian keys.

CANDIDATE_FIELD_MAP = {
    "Id": "Id",
    "PhoneNumber": "شماره تماس",
    "FirstName": "نام",
    "LastName": "نام خانوادگی",
    "WorkExperience": "سابقه کار",
    "Expertise": "تخصص و مهارت"
}

JOB_OPPORTUNITY_FIELD_MAP = {
    "Id": "Id",
    "Title": "عنوان",
    "Description": "توضیحات", # Matches 'توضیحات' field
    "FullDescription": "شرح وظابف", # New key for the detailed description
    "Status": "وضعیت",
    "Department": "دپارتمان ها"
}

HIRING_RECORD_FIELD_MAP = {
    "Id": "Id",
    "Status": "وضعیت",
    "Candidate": "کاندیدها",
    "JobOpportunity": "فرصت های شغلی",
    "Title": "عنوان" 
}

FEEDBACK_FIELD_MAP = {
    "User": "کاربر", 
    "Query": "پبام",       # Maps to "Message" in the API
    "Response": "پاسخ",    # Maps to "Response" in the API
    "Rating": "وضعیت"     # Maps to "Status" in the API, we'll use 'good'/'bad'
}

# --- Sanity Checks ---
if not OPENAI_API_KEY:
    raise ValueError("FATAL ERROR: OPENAI_API_KEY is not set in the .env file.")

if not NOCODB_API_TOKEN:
    raise ValueError("FATAL ERROR: NOCODB_API_TOKEN is not set in the .env file.")