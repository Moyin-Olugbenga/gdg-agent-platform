import fitz  # PyMuPDF
import urllib.request
import os
import re


def extract_text_from_pdf(file_path: str) -> dict:
    """
    Extracts all text from a PDF file given its local file path.
    Use this when the user uploads or provides a PDF document.
    Returns the extracted text content.
    """
    try:
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        if not text.strip():
            return {"status": "error", "message": "No text found in PDF. It may be scanned/image-based."}
        return {"status": "success", "text": text[:8000]}  # cap at 8000 chars
    except Exception as e:
        return {"status": "error", "message": str(e)}


def identify_document_type(text: str) -> dict:
    """
    Identifies what type of legal document this is based on its text content.
    Examples: employment contract, tenancy agreement, loan agreement, NDA, etc.
    Use this after extracting text to understand what kind of document is being analysed.
    """
    text_lower = text.lower()

    if any(word in text_lower for word in ["employment", "employer", "employee", "salary", "termination"]):
        doc_type = "Employment Contract"
    elif any(word in text_lower for word in ["tenancy", "landlord", "tenant", "rent", "lease", "premises"]):
        doc_type = "Tenancy Agreement"
    elif any(word in text_lower for word in ["loan", "borrower", "lender", "repayment", "interest rate"]):
        doc_type = "Loan Agreement"
    elif any(word in text_lower for word in ["non-disclosure", "confidential", "nda", "proprietary"]):
        doc_type = "Non-Disclosure Agreement (NDA)"
    elif any(word in text_lower for word in ["service", "contractor", "client", "deliverable", "scope of work"]):
        doc_type = "Service Agreement"
    else:
        doc_type = "General Legal Document"

    return {"status": "success", "document_type": doc_type}


def flag_risky_clauses(text: str) -> dict:
    """
    Scans the document text for potentially risky, unfair, or suspicious clauses.
    Returns a list of red flags with explanations.
    Use this to warn users about dangerous terms in a contract.
    """
    red_flags = []
    text_lower = text.lower()

    risk_patterns = [
        ("unlimited liability", "You may be held responsible for unlimited damages with no cap."),
        ("waive all rights", "You are giving up important legal rights."),
        ("at our sole discretion", "The other party can make decisions without any accountability to you."),
        ("non-refundable", "You will not get your money back under any circumstances."),
        ("automatic renewal", "The contract renews itself — you could be locked in without realising."),
        ("unilateral", "One party can change the terms without your agreement."),
        ("indemnify", "You may be required to cover the other party's legal costs and losses."),
        ("arbitration only", "You are giving up your right to take disputes to court."),
        ("perpetual license", "You are granting rights to your work or data forever."),
        ("terminate at will", "They can end the contract at any time for any reason."),
        ("no warranty", "No guarantees are being made — you take all the risk."),
    ]

    for pattern, explanation in risk_patterns:
        if pattern in text_lower:
            red_flags.append({
                "clause": pattern,
                "risk": explanation
            })

    if not red_flags:
        return {"status": "success", "red_flags": [], "message": "No obvious red flags detected."}

    return {"status": "success", "red_flags": red_flags}