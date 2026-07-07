import frappe
import google.generativeai as genai

@frappe.whitelist()
def generate_ai_summary(visit_name):
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
