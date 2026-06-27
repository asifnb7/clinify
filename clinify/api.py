import frappe


@frappe.whitelist()
def generate_ai_summary(visit_name):
    """
    Generate an AI summary for a Clinify Patient Visit.

    The Gemini SDK is imported only when this API is called,
    allowing the remainder of the application to function even
    if the SDK is not installed.
    """
    try:
        import google.generativeai as genai
    except ImportError:
        frappe.throw(
            "Google Generative AI SDK is not installed on this server."
        )

    visit = frappe.get_doc("Clinify Patient Visit", visit_name)

    settings = frappe.get_doc("Clinify Settings")
    api_key = settings.gemini_api_key

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-pro")

    prompt = f"""
    Generate a medical visit summary for:
    Patient: {visit.patient}
    Doctor: {visit.doctor}
    Symptoms: {visit.symptoms}
    Diagnosis: {visit.diagnosis}
    Prescription: {visit.prescription}
    """

    response = model.generate_content(prompt)
    return response.text


def force_enable_server_script(*args, **kwargs):
    return True
