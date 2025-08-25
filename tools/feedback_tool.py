# start of tools/feedback_tool.py
import requests
import logging
from langchain.tools import tool
import asyncio
from config import settings
from utils.api_translator import to_api_format

logger = logging.getLogger(__name__)

def get_nocodb_headers():
    return {"xc-token": settings.NOCODB_API_TOKEN}

@tool
async def record_feedback(user_phone: str, query: str, response: str, rating: str) -> str:
    """
    Directly records user feedback to the NocoDB database.
    """
    table_id = settings.NOCODB_TABLE_IDS["Feedbacks"]
    url = f"{settings.NOCODB_BASE_URL}/api/v2/tables/{table_id}/records"
    
    # --- THE FIX ---
    # The API requires the Persian equivalent for the rating.
    # We will translate "good" to "خوب" and "bad" to "بد".
    persian_rating = "خوب" if rating.lower() == "good" else "بد"

    internal_payload = {
        "User": user_phone,
        "Query": query,
        "Response": response,
        "Rating": persian_rating # Use the translated value
    }
    api_payload = to_api_format(internal_payload, settings.FEEDBACK_FIELD_MAP)
    
    try:
        res = await asyncio.to_thread(
            requests.post, 
            url, 
            headers=get_nocodb_headers(), 
            json=api_payload
        )
        res.raise_for_status()
        logger.info(f"Successfully recorded feedback with rating: {rating} for user {user_phone}")
        return "بازخورد شما با موفقیت ثبت شد. متشکریم!"
        
    except requests.exceptions.RequestException as e:
        error_text = e.response.text if e.response is not None else "No response from server"
        logger.error(f"Failed to record feedback to NocoDB. Error: {e}, Response: '{error_text}', Payload: {api_payload}")
        return "خطایی در ثبت بازخورد شما رخ داد. لطفاً بعداً دوباره تلاش کنید."