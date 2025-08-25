import pytest
import requests
import json
import random
import string
import time

pytestmark = pytest.mark.integration

from tools.nocodb_tools import get_open_job_positions, get_job_details, get_application_status
from tools.feedback_tool import record_feedback
from config import settings

def random_string(length=8):
    """Generates a random string for unique test data."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def get_api_headers():
    """Returns the authentication headers for NocoDB."""
    return {"xc-token": settings.NOCODB_API_TOKEN}

def delete_record_directly(table_name: str, record_id: int):
    """Helper to delete a record from a NocoDB table to clean up after tests."""
    table_id = settings.NOCODB_TABLE_IDS[table_name]
    url = f"{settings.NOCODB_BASE_URL}/api/v2/tables/{table_id}/records"
    try:
        response = requests.delete(url, headers=get_api_headers(), json={"Id": record_id})
        response.raise_for_status()
        print(f"Cleaned up record {record_id} from {table_name}")
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to clean up record {record_id} from {table_name}. Error: {e}")

@pytest.fixture(scope="function")
def test_job_opportunity():
    """Creates a temporary job opportunity and guarantees its deletion."""
    table_id = settings.NOCODB_TABLE_IDS["JobOpportunities"]
    url = f"{settings.NOCODB_BASE_URL}/api/v2/tables/{table_id}/records"
    job_title = f"Test Job {random_string()}"
    
    job_payload = {
        settings.JOB_OPPORTUNITY_FIELD_MAP["Title"]: job_title,
        settings.JOB_OPPORTUNITY_FIELD_MAP["Description"]: "Automated test description.",
        settings.JOB_OPPORTUNITY_FIELD_MAP["FullDescription"]: "Full description for the automated test job.",
        settings.JOB_OPPORTUNITY_FIELD_MAP["Status"]: "باز"
    }

    response = requests.post(url, headers=get_api_headers(), json=job_payload)
    response.raise_for_status()
    created_job = response.json()
    job_id = created_job['Id']
    
    yield {"id": job_id, "title": job_title}
    
    delete_record_directly("JobOpportunities", job_id)

@pytest.fixture(scope="function")
def test_candidate_and_hiring_record(test_job_opportunity):
    """Creates a temporary candidate and hiring record, then guarantees deletion."""
    candidate_table_id = settings.NOCODB_TABLE_IDS["Candidates"]
    candidate_url = f"{settings.NOCODB_BASE_URL}/api/v2/tables/{candidate_table_id}/records"
    
    phone = "09353447066"
    
    candidate_payload = {
        settings.CANDIDATE_FIELD_MAP["PhoneNumber"]: phone,
        settings.CANDIDATE_FIELD_MAP["FirstName"]: "Test",
        settings.CANDIDATE_FIELD_MAP["LastName"]: "User"
    }
    cand_res = requests.post(candidate_url, headers=get_api_headers(), json=candidate_payload)
    cand_res.raise_for_status()
    created_candidate = cand_res.json()
    candidate_id = created_candidate['Id']

    hiring_table_id = settings.NOCODB_TABLE_IDS["HiringRecords"]
    hiring_url = f"{settings.NOCODB_BASE_URL}/api/v2/tables/{hiring_table_id}/records"
    job_id = test_job_opportunity["id"]
    status = "اقدام شده"

    # --- THE DEFINITIVE FIX ---
    # The API log shows that 'تایید اولیه', 'رد کردن', and 'استخدام' are virtual columns.
    # We must remove them from the POST request payload.
    hiring_payload = {
        "عنوان": f"Test Application for {test_job_opportunity['title']}",
        "وضعیت": status,
        "nc__0jr___کاندیدها_id": candidate_id,
        "nc__0jr___فرصت های شغلی_id": job_id
    }
    hiring_res = requests.post(hiring_url, headers=get_api_headers(), json=hiring_payload)
    
    if hiring_res.status_code != 200:
        print("Error creating hiring record. Payload:", json.dumps(hiring_payload, indent=2, ensure_ascii=False))
        print("API Response:", hiring_res.text)

    hiring_res.raise_for_status()
    created_hiring_record = hiring_res.json()
    hiring_record_id = created_hiring_record['Id']

    yield {
        "phone_number": phone,
        "expected_status": status,
        "expected_job_title": test_job_opportunity["title"],
        "candidate_id": candidate_id,
        "hiring_record_id": hiring_record_id
    }

    delete_record_directly("HiringRecords", hiring_record_id)
    delete_record_directly("Candidates", candidate_id)


### The Tests ###

def test_get_open_job_positions_integration(test_job_opportunity):
    result_json = get_open_job_positions.invoke({})
    result_data = json.loads(result_json)
    assert isinstance(result_data, list)
    assert len(result_data) > 0
    found_job = next((job for job in result_data if job['Id'] == test_job_opportunity['id']), None)
    assert found_job is not None
    assert found_job['Title'] == test_job_opportunity['title']

def test_get_job_details_integration(test_job_opportunity):
    job_id = test_job_opportunity['id']
    result_json = get_job_details.invoke({"position_id": str(job_id)})
    result_data = json.loads(result_json)
    assert result_data['Id'] == job_id
    assert result_data['Title'] == test_job_opportunity['title']
    assert "Full description for the automated test job" in result_data['FullDescription']

def test_get_application_status_integration():
    """
    Tests the get_application_status tool against a specific, pre-existing user
    known to have application records in the database.
    """
    # Arrange: Use the specific phone number you provided.
    phone_number_with_cases = "09353447066"

    # Act: Call the tool to get the status.
    result_json = get_application_status.invoke({"phone_number": phone_number_with_cases})
    
    print(f"\nAPI Response for user {phone_number_with_cases}: {result_json}")

    # Assert: Check that the response is valid and contains meaningful data.
    
    # 1. Ensure the tool did not return an error or "not found" message.
    assert "خطا" not in result_json, "The tool returned an error message."
    assert "یافت نشد" not in result_json, "The tool reported that the user was not found."

    # 2. Parse the JSON response.
    try:
        result_data = json.loads(result_json)
    except json.JSONDecodeError:
        pytest.fail(f"The tool's response was not valid JSON: {result_json}")

    # 3. Check for the expected structure and valid data.
    assert isinstance(result_data, dict), "The response should be a dictionary."
    assert "Status" in result_data, "Response must contain a 'Status' key."
    assert "JobTitle" in result_data, "Response must contain a 'JobTitle' key."
    
    # 4. Check that the tool found real data, not the default "not found" values.
    assert result_data["Status"] is not None and result_data["Status"] != "نامشخص", "Status should not be empty or 'نامشخص'."
    assert result_data["JobTitle"] is not None and result_data["JobTitle"] != "نامشخص", "JobTitle should not be empty or 'نامشخص'."

    print(f"Successfully validated status '{result_data['Status']}' for job '{result_data['JobTitle']}'")

@pytest.mark.asyncio
async def test_record_feedback_integration():
    feedback_id_to_delete = None
    phone = "09353447067" # Using a different static number to avoid conflicts
    query = f"Test query from integration test {random_string()}"
    payload = {
        "user_phone": phone,
        "query": query,
        "response": "Test response.",
        "rating": "good"
    }
    try:
        result_message = await record_feedback.ainvoke(payload)
        assert "بازخورد شما با موفقیت ثبت شد" in result_message
        time.sleep(1)
        table_id = settings.NOCODB_TABLE_IDS["Feedbacks"]
        url = f"{settings.NOCODB_BASE_URL}/api/v2/tables/{table_id}/records"
        params = {"where": f"({settings.FEEDBACK_FIELD_MAP['Query']},eq,{query})"}
        response = requests.get(url, headers=get_api_headers(), params=params)
        response.raise_for_status()
        records = response.json().get("list", [])
        assert len(records) > 0
        feedback_id_to_delete = records[0]['Id']
    finally:
        if feedback_id_to_delete:
            # delete_record_directly("Feedbacks", feedback_id_to_delete) # <-- COMMENT OUT THIS LINE
            print(f"SKIPPED Deleting feedback record {feedback_id_to_delete} for manual verification.")
        else:
            print(f"WARNING: Could not find feedback with query '{query}' to clean up.")