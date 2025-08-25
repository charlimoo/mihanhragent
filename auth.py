import chainlit as cl

# We will use the NocoDB table `OTPs` to store and verify codes.
# This assumes you have a table in NocoDB named 'OTPs' with columns:
# - PhoneNumber (Text)
# - Code (Number)
# - Expiry (DateTime)

# Note: The actual n8n workflows for setting/getting OTPs from NocoDB
# need to be created on your n8n instance. This code assumes they exist.

async def authentication_flow():
    """
    Manages the multi-step phone + OTP authentication flow.
    Returns the authenticated phone number or None if authentication fails.
    """
    # --- Step 1: Ask for Phone Number ---
    phone_res = None
    while phone_res is None:
        phone_res = await cl.AskUserMessage(
            content="برای ورود یا ثبت‌نام، لطفاً شماره تلفن همراه خود را با فرمت 09123456789 وارد کنید:",
            timeout=120, # 2 minutes
            author="سیستم احراز هویت"
        ).send()

    phone_number = phone_res['output'].strip()
    
    # Simple validation (can be improved with regex for production)
    if not (phone_number.startswith('09') and len(phone_number) == 11 and phone_number.isdigit()):
        await cl.Message(content="فرمت شماره تلفن نامعتبر است. لطفاً دوباره تلاش کنید.").send()
        return None # End the flow

    await cl.Message(content=f"در حال ارسال کد تایید به شماره {phone_number}...").send()

    # --- Step 2: Trigger OTP SMS via the Agent ---
    # We use the agent to call the n8n tool, keeping all external actions consistent.
    agent_executor = cl.user_session.get("agent_executor")
    otp_response = await agent_executor.ainvoke(
        {"input": f"Send an OTP to the phone number {phone_number}"}
    )
    
    # Check if the tool execution was successful (you can make this more robust)
    if "خطا" in otp_response.get("output", ""):
        await cl.Message(content="متاسفانه در ارسال کد با مشکل مواجه شدیم. لطفاً دقایقی دیگر مجددا تلاش کنید.").send()
        return None

    await cl.Message(content=otp_response.get("output", "کد تایید برای شما ارسال شد.")).send()
    
    # --- Step 3: Ask for OTP Code ---
    otp_res = None
    while otp_res is None:
        otp_res = await cl.AskUserMessage(
            content="لطفاً کد ۶ رقمی ارسال شده را وارد کنید:",
            timeout=180, # 3 minutes
            author="سیستم احراز هویت"
        ).send()
    
    otp_code = otp_res['output'].strip()

    # --- Step 4: Verify OTP Code via the Agent ---
    await cl.Message(content="در حال بررسی کد...").send()
    verification_response = await agent_executor.ainvoke(
        {"input": f"Verify OTP code {otp_code} for phone number {phone_number}"}
    )
    
    # The output from the agent/tool will determine success or failure
    final_output = verification_response.get("output", "")

    if "موفق" in final_output: # Check for a success keyword
        await cl.Message(content="احراز هویت با موفقیت انجام شد! حالا می‌توانید وضعیت درخواست خود را بررسی کنید.").send()
        return phone_number # Return the number on success
    else:
        await cl.Message(content="کد وارد شده نامعتبر است یا منقضی شده است. لطفاً دوباره تلاش کنید.").send()
        return None # Return None on failure