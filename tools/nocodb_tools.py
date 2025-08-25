# start of tools/nocodb_tools.py
import requests
import json
import logging
from langchain.tools import tool

# Import configurations and the translator utility
from config import settings
from utils.api_translator import from_api_format

logger = logging.getLogger(__name__)

# --- NocoDB API Helper ---
def get_nocodb_headers():
    """Returns the standard headers for NocoDB API requests."""
    return {"xc-token": settings.NOCODB_API_TOKEN}

# --- Tool Definitions ---

def get_candidate_details_by_id(candidate_id: int) -> dict | None:
    """
    Internal helper to fetch a candidate's full details using their ID.
    Returns a dictionary with English keys.
    """
    table_id = settings.NOCODB_TABLE_IDS["Candidates"]
    url = f"{settings.NOCODB_BASE_URL}/api/v2/tables/{table_id}/records/{candidate_id}"
    
    try:
        response = requests.get(url, headers=get_nocodb_headers())
        response.raise_for_status()
        api_data = response.json()
        
        # Translate the API response (Persian keys) to our internal format (English keys)
        return from_api_format(api_data, settings.CANDIDATE_FIELD_MAP)
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to get candidate details for ID {candidate_id}: {e}")
        return None
    
@tool
def get_open_job_positions() -> str:
    """
    Use this tool to find all currently open job positions available for candidates.
    It returns a list of jobs with their titles and IDs.
    """
    table_id = settings.NOCODB_TABLE_IDS["JobOpportunities"]
    url = f"{settings.NOCODB_BASE_URL}/api/v2/tables/{table_id}/records"
    
    status_field = settings.JOB_OPPORTUNITY_FIELD_MAP["Status"]
    title_field = settings.JOB_OPPORTUNITY_FIELD_MAP["Title"]
    id_field = settings.JOB_OPPORTUNITY_FIELD_MAP["Id"]
    
    params = {
        "where": f"({status_field},eq,باز)", # Use the correct Persian value
        "fields": f"{title_field},{id_field}",
        "limit": 25
    }
    
    try:
        response = requests.get(url, headers=get_nocodb_headers(), params=params)
        response.raise_for_status()
        api_data = response.json().get("list", [])
        
        if not api_data:
            return "متاسفانه در حال حاضر هیچ موقعیت شغلی بازی وجود ندارد."
        
        translated_jobs = [from_api_format(job, settings.JOB_OPPORTUNITY_FIELD_MAP) for job in api_data]
        return json.dumps(translated_jobs, ensure_ascii=False)

    except requests.exceptions.RequestException as e:
        logger.error(f"NocoDB API request failed in get_open_job_positions: {e}")
        return "خطا در برقراری ارتباط با سیستم مشاغل. لطفاً بعداً دوباره امتحان کنید."

@tool
def get_job_details(position_id: str) -> str:
    """
    Use this tool to get the detailed description and requirements of a specific job
    when you have its unique ID.
    """
    if not position_id:
        return "خطا: برای دریافت جزئیات شغل، به شناسه موقعیت (ID) نیاز است."

    table_id = settings.NOCODB_TABLE_IDS["JobOpportunities"]
    url = f"{settings.NOCODB_BASE_URL}/api/v2/tables/{table_id}/records/{position_id}"

    try:
        response = requests.get(url, headers=get_nocodb_headers())
        response.raise_for_status()
        api_data = response.json()

        translated_job = from_api_format(api_data, settings.JOB_OPPORTUNITY_FIELD_MAP)
        translated_job["FullDescription"] = api_data.get(settings.JOB_OPPORTUNITY_FIELD_MAP["FullDescription"], "")
        
        return json.dumps(translated_job, ensure_ascii=False)

    except requests.exceptions.RequestException as e:
        logger.error(f"NocoDB API request failed for job ID {position_id}: {e}")
        return "موقعیت شغلی با این شناسه یافت نشد یا در ارتباط با سیستم خطایی رخ داده است."

def get_candidate_id_by_phone(phone_number: str) -> str | None:
    """Queries the Candidates table to find the ID for a given phone number."""
    table_id = settings.NOCODB_TABLE_IDS["Candidates"]
    url = f"{settings.NOCODB_BASE_URL}/api/v2/tables/{table_id}/records"
    
    phone_field = settings.CANDIDATE_FIELD_MAP["PhoneNumber"]
    id_field = settings.CANDIDATE_FIELD_MAP["Id"]
    params = {"where": f"({phone_field},eq,{phone_number})", "fields": f"{id_field}", "limit": 1}

    try:
        response = requests.get(url, headers=get_nocodb_headers(), params=params)
        response.raise_for_status()
        data = response.json().get("list", [])
        if data:
            return data[0].get(id_field)
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to get candidate ID for phone {phone_number}: {e}")
        return None

@tool
def get_application_status(phone_number: str) -> str:
    """
    Use this tool to check the status of ALL applications for a candidate using their phone number.
    It returns a list of all their active applications.
    """
    if not phone_number:
        return "خطا: برای بررسی وضعیت، به شماره تلفن کاربر نیاز است."

    candidate_id = get_candidate_id_by_phone(phone_number)
    if not candidate_id:
        return "کاندیدی با این شماره تلفن یافت نشد."

    table_id = settings.NOCODB_TABLE_IDS["HiringRecords"]
    url = f"{settings.NOCODB_BASE_URL}/api/v2/tables/{table_id}/records"

    candidate_link_field = "nc__0jr___کاندیدها_id"
    job_relation_field = settings.HIRING_RECORD_FIELD_MAP["JobOpportunity"]
    job_title_field = settings.JOB_OPPORTUNITY_FIELD_MAP["Title"]
    status_field = settings.HIRING_RECORD_FIELD_MAP["Status"]

    # --- THE FIX: Fetch all records, not just one ---
    params = {
        "where": f"({candidate_link_field},eq,{candidate_id})",
        "limit": 25 # Set a reasonable limit for number of applications
    }

    try:
        response = requests.get(url, headers=get_nocodb_headers(), params=params)
        response.raise_for_status()
        api_data = response.json().get("list", [])
        
        if not api_data:
            return "هیچ درخواست فعالی برای این شماره تلفن یافت نشد."

        # --- THE FIX: Process the entire list of records ---
        all_statuses = []
        for hiring_record in api_data:
            status_info = {
                "Status": hiring_record.get(status_field, "نامشخص"),
                "JobTitle": hiring_record.get(job_relation_field, {}).get(job_title_field, "نامشخص")
            }
            all_statuses.append(status_info)
        
        # Return a JSON string of the list
        return json.dumps(all_statuses, ensure_ascii=False)

    except requests.exceptions.RequestException as e:
        logger.error(f"NocoDB API request failed for status check on {phone_number}: {e}")
        return "خطا در برقراری ارتباط با سیستم. لطفاً بعداً دوباره امتحان کنید."

@tool
def apply_for_job_position(position_id: int, candidate_id: int) -> str:
    """
    Use this tool to apply a candidate for a specific job position.
    This creates a new 'Hiring Record' linking the candidate and the job.
    """
    try:
        # Step 1: Get Job Title
        job_details_json = get_job_details.invoke({"position_id": str(position_id)})
        job_title = json.loads(job_details_json).get("Title", "N/A")
        if job_title == "N/A":
             return "خطا: موقعیت شغلی مورد نظر برای ثبت درخواست یافت نشد."

        # Step 2: Get Candidate's Full Name using the new helper function
        candidate_details = get_candidate_details_by_id(candidate_id)
        if not candidate_details:
            return f"خطا: اطلاعات کارجو با شناسه {candidate_id} یافت نشد و درخواست ثبت نگردید."
        
        first_name = candidate_details.get("FirstName", "")
        last_name = candidate_details.get("LastName", "")
        candidate_full_name = f"{first_name} {last_name}".strip()

        # Step 3: Construct the new, user-friendly title
        hiring_record_title = f"{candidate_full_name} - {job_title}"

        # Step 4: Construct the payload
        table_id = settings.NOCODB_TABLE_IDS["HiringRecords"]
        url = f"{settings.NOCODB_BASE_URL}/api/v2/tables/{table_id}/records"
        payload = {
            settings.HIRING_RECORD_FIELD_MAP["Title"]: hiring_record_title,
            settings.HIRING_RECORD_FIELD_MAP["Status"]: "اقدام شده",
            "nc__0jr___کاندیدها_id": candidate_id,
            "nc__0jr___فرصت های شغلی_id": position_id
        }

        # Step 5: Create the Hiring Record
        response = requests.post(url, headers=get_nocodb_headers(), json=payload)
        response.raise_for_status()
        
        logger.info(f"Successfully created hiring record for candidate {candidate_id} ({candidate_full_name}) and job {position_id}")
        return f"درخواست شما برای موقعیت شغلی '{job_title}' با موفقیت ثبت شد. به زودی نتیجه آن به شما اطلاع داده خواهد شد."

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to create hiring record for candidate {candidate_id} and job {position_id}: {e}")
        return "متاسفانه در ثبت درخواست شما مشکلی پیش آمد. لطفاً دقایقی دیگر مجددا تلاش کنید."
    except Exception as e:
        logger.error(f"An unexpected error occurred in apply_for_job_position: {e}")
        return "یک خطای پیش‌بینی نشده در فرآیند ثبت درخواست رخ داد."