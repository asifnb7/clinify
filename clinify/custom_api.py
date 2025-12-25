import frappe
import google.generativeai as genai

@frappe.whitelist()
def generate_ai_summary(visit_name):
    """Generate AI summary for Clinify Patient Visit"""
    doc = frappe.get_doc("Clinify Patient Visit", visit_name)

    # Get Gemini API key from settings
    settings = frappe.get_single("Clinify Settings")
    api_key = settings.get("gemini_api_key")

    if not api_key:
        return {"status": "error", "message": "Gemini API Key missing in Clinify Settings"}

    genai.configure(api_key=api_key)

    prompt = f"""
    Create a medical summary from this data:
    Patient Name: {doc.patient}
    Visit Reason: {doc.visit_reason}
    Notes: {doc.notes}
    """

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        summary = response.text

        doc.ai_summary = summary
        doc.save()

        return {"status": "success", "message": summary}

    except Exception as e:
        return {"status": "error", "message": str(e)}
@frappe.whitelist()
def generate_ai_summary(visit_name):
    """Generate AI summary for Clinify Patient Visit"""
    import google.generativeai as genai

    doc = frappe.get_doc("Clinify Patient Visit", visit_name)

    # Get Gemini API key from settings
    settings = frappe.get_single("Clinify Settings")
    api_key = settings.get("gemini_api_key")

    if not api_key:
        return {"status": "error", "message": "Gemini API Key missing in Clinify Settings"}

    genai.configure(api_key=api_key)

    prompt = f"""
    Create a medical summary from this data:
    Patient Name: {doc.patient}
    Visit Reason: {doc.visit_reason}
    Notes: {doc.notes}
    """

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        summary = response.text

        doc.ai_summary = summary
        doc.save()

        return {"status": "success", "message": summary}

    except Exception as e:
        return {"status": "error", "message": str(e)}
import frappe
import google.generativeai as genai

@frappe.whitelist()
def generate_ai_summary(visit_name):
    """Generate AI summary for Clinify Patient Visit"""

    # Load visit document
    doc = frappe.get_doc("Clinify Patient Visit", visit_name)

    # Get Gemini API Key from settings
    settings = frappe.get_single("Clinify Settings")
    api_key = settings.get("gemini_api_key")

    if not api_key:
        return {"status": "error", "message": "Gemini API Key missing in Clinify Settings"}

    genai.configure(api_key=api_key)

    # Build prompt
    prompt = f"""
    Create a medical summary from this data:

    Patient Name: {doc.patient}
    Visit Reason: {doc.visit_reason}
    Notes: {doc.notes}

    Provide a clear clinical summary.
    """

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        summary = response.text

        # Save summary
        doc.ai_summary = summary
        doc.save()

        return {"status": "success", "message": summary}

    except Exception as e:
        return {"status": "error", "message": str(e)}
