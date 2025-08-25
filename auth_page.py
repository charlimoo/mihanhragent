# start of auth_page.py
import chainlit as cl
import requests
import logging
import random
import re

# Import configurations and the translator utility
from config import settings
from utils.api_translator import to_api_format, from_api_format

logger = logging.getLogger(__name__)

# --- Direct API Helpers ---

def check_user_exists(phone_number: str):
    """Directly queries NocoDB to check if a candidate exists."""
    table_id = settings.NOCODB_TABLE_IDS["Candidates"]
    url = f"{settings.NOCODB_BASE_URL}/api/v2/tables/{table_id}/records"
    
    phone_field = settings.CANDIDATE_FIELD_MAP["PhoneNumber"]
    params = {"where": f"({phone_field},eq,{phone_number})", "limit": 1}
    
    headers = {"xc-token": settings.NOCODB_API_TOKEN}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json().get("list", [])
        
        if not data:
            return None
        
        api_profile = data[0]
        return from_api_format(api_profile, settings.CANDIDATE_FIELD_MAP)
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to check user existence in NocoDB: {e}")
        return None

def create_new_candidate(profile: dict):
    """Directly creates a new candidate record."""
    table_id = settings.NOCODB_TABLE_IDS["Candidates"]
    url = f"{settings.NOCODB_BASE_URL}/api/v2/tables/{table_id}/records"
    
    headers = {"xc-token": settings.NOCODB_API_TOKEN}
    
    # Translate our internal profile dictionary to the API's expected format
    api_payload = to_api_format(profile, settings.CANDIDATE_FIELD_MAP)
    
    try:
        response = requests.post(url, headers=headers, json=api_payload)
        response.raise_for_status()
        logger.info(f"Successfully created new candidate: {profile.get('PhoneNumber')}")
        
        created_api_profile = response.json()
        return from_api_format(created_api_profile, settings.CANDIDATE_FIELD_MAP)

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to create new candidate in NocoDB: {e}")
        return None

async def run_auth_and_onboarding_flow():
    """Manages the entire pre-chat authentication and new user onboarding process."""
    phone_number = None
    while True:
        phone_res = await cl.AskUserMessage(
            content="برای ورود یا ثبت‌نام، لطفاً شماره تلفن همراه خود را با فرمت 09123456789 وارد کنید:",
            timeout=180
        ).send()
        
        if not phone_res: return None 
            
        phone_input = phone_res['output'].strip()

        if re.match(r"^09\d{9}$", phone_input):
            phone_number = phone_input
            break
        else:
            await cl.Message(
                content=f"فرمت شماره «{phone_input}» نامعتبر است. لطفاً یک شماره ۱۱ رقمی صحیح وارد کنید."
            ).send()

    try:
        otp_code = str(random.randint(100000, 999999))
        cl.user_session.set("otp_code", otp_code)
        logger.info(f"Generated OTP {otp_code} for {phone_number}")

        sms_message = f"کد ورود شما به سیستم استخدام: {otp_code}"
        payload = {"sms": sms_message, "who": phone_number}
        
        await cl.Message(content="در حال ارسال کد تایید...").send()
        send_res = requests.post(settings.N8N_SMS_WEBHOOK_URL, json=payload)
        send_res.raise_for_status()
        
        otp_res = await cl.AskUserMessage(content="کد ۶ رقمی ارسال شده را وارد کنید:", timeout=180).send()
        if not otp_res: return None
        user_entered_code = otp_res['output'].strip()

        saved_otp = cl.user_session.get("otp_code")
        cl.user_session.set("otp_code", None)

        if user_entered_code != saved_otp:
            await cl.Message(content="کد وارد شده نامعتبر است. لطفاً صفحه را رفرش کرده و دوباره تلاش کنید.").send()
            return None

    except requests.exceptions.RequestException as e:
        logger.error(f"OTP flow failed during API call: {e}")
        await cl.Message(content="مشکلی در فرآیند ارسال کد پیش آمد. لطفاً دقایقی دیگر مجددا تلاش کنید.").send()
        return None

    await cl.Message(content="احراز هویت با موفقیت انجام شد!").send()
    
    user_profile = check_user_exists(phone_number)
    
    if user_profile:
        logger.info(f"Returning user authenticated: {phone_number}")
        return user_profile
    else:
        # --- ENHANCED ONBOARDING FLOW ---
        logger.info(f"New user detected: {phone_number}. Starting onboarding.")
        await cl.Message(content="به نظر می‌رسد شما کاربر جدید هستید. برای ساخت پروفایل، لطفاً به چند سوال پاسخ دهید.").send()
        
        first_name_res = await cl.AskUserMessage(content="نام شما چیست؟", timeout=120).send()
        if not first_name_res: return None
        
        last_name_res = await cl.AskUserMessage(content="نام خانوادگی شما چیست؟", timeout=120).send()
        if not last_name_res: return None

        expertise_res = await cl.AskUserMessage(
            content="بسیار عالی. لطفاً تخصص و مهارت‌های اصلی خود را به طور خلاصه بنویسید (مثلاً: برنامه‌نویس پایتون، کارشناس فروش).", 
            timeout=180
        ).send()
        if not expertise_res: return None

        experience_res = await cl.AskUserMessage(
            content="و در نهایت، سابقه کار خود را به طور خلاصه شرح دهید (مثلاً: ۵ سال توسعه نرم‌افزار، ۲ سال مدیریت پروژه).", 
            timeout=180
        ).send()
        if not experience_res: return None
        
        new_profile_data = {
            "FirstName": first_name_res['output'].strip(),
            "LastName": last_name_res['output'].strip(),
            "PhoneNumber": phone_number,
            "Expertise": expertise_res['output'].strip(),
            "WorkExperience": experience_res['output'].strip()
        }
        
        created_profile = create_new_candidate(new_profile_data)
        if not created_profile:
             await cl.Message(content="متاسفانه در ساخت پروفایل شما مشکلی پیش آمد.").send()
             return None

        await cl.Message(content="پروفایل شما با موفقیت ساخته شد!").send()
        return created_profile
# end of auth_page.py