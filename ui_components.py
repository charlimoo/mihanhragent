# start of ui_components.py
import chainlit as cl
import json
import logging

logger = logging.getLogger(__name__)

async def display_job_listings(jobs_json: str):
    """Parses and displays job listings with 'View Details' buttons."""
    try:
        jobs = json.loads(jobs_json)
        if not isinstance(jobs, list) or not jobs:
            await cl.Message(content="در حال حاضر هیچ موقعیت شغلی بازی یافت نشد.").send()
            return
        
        for job in jobs:
            job_text = f"**عنوان شغلی:** {job.get('Title', 'N/A')}\n"
            actions = [
                cl.Action(
                    name="view_job_details",
                    label="مشاهده جزئیات",
                    # FIX: The agent instruction is now inside the payload. The 'value' parameter is removed.
                    payload={"agent_instruction": f"show details for job with ID {job.get('Id', '')}"}
                )
            ]
            await cl.Message(content=job_text, author="هوشمند", actions=actions).send()
    except Exception as e:
        logger.error(f"Error in display_job_listings: {e}")
        await cl.Message(content="یک خطای پیش‌بینی نشده در نمایش مشاغل رخ داد.").send()


async def display_job_details(details_json: str):
    """Parses and displays a single job's details."""
    try:
        details = json.loads(details_json)
        
        content = f"### جزئیات شغل: {details.get('Title', 'N/A')}\n\n"
        content += f"**شناسه شغل:** `{details.get('Id', 'N/A')}`\n\n---\n\n"
        content += f"**شرح وظایف:**\n{details.get('FullDescription', 'شرحی ارائه نشده است.')}\n\n"
        
        actions = [
            cl.Action(
                name="apply_for_job", 
                label="ارسال درخواست برای این شغل",
                # FIX: The agent instruction is now inside the payload.
                payload={"agent_instruction": f"من می‌خواهم برای این شغل با شناسه {details.get('Id')} درخواست دهم"}
            )
        ]
        await cl.Message(content=content, author="هوشمند", actions=actions).send()
    except Exception as e:
        logger.error(f"Error in display_job_details: {e}")
        await cl.Message(content="یک خطای پیش‌بینی نشده در نمایش جزئیات شغل رخ داد.").send()


async def display_application_status(status_json: str):
    """Parses and displays application status."""
    try:
        status_info = json.loads(status_json)
        if not status_info:
             await cl.Message(content="هیچ درخواست فعالی برای شما یافت نشد.").send()
             return

        job_title = status_info.get('JobTitle', 'نامشخص')
        status = status_info.get('Status', 'نامشخص')
        
        response_content = f"وضعیت درخواست فعال شما:\n\n- **{job_title}**: {status}"
        
        await cl.Message(content=response_content, author="هوشمند").send()
    except Exception as e:
        logger.error(f"Error in display_application_status: {e}")
        await cl.Message(content="یک خطای پیش‌بینی نشده در نمایش وضعیت درخواست رخ داد.").send()
# end of ui_components.py