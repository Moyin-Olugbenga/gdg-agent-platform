import requests
import csv
import os
from dotenv import load_dotenv

load_dotenv()

SERPER_API_KEY = os.getenv("SERPER_API_KEY")


def search_lead(query: str) -> dict:
    """
    Searches the web for information about a lead, their company, or industry.
    Use this to research a person's role, their company's products, recent news,
    funding rounds, or pain points. Pass a specific search query.
    Returns a list of search results with titles, snippets, and links.
    """
    try:
        response = requests.post(
            "https://google.serper.dev/search",
            headers={
                "X-API-KEY": SERPER_API_KEY,
                "Content-Type": "application/json"
            },
            json={"q": query, "num": 5}
        )
        data = response.json()
        results = []
        for item in data.get("organic", []):
            results.append({
                "title": item.get("title"),
                "snippet": item.get("snippet"),
                "link": item.get("link")
            })
        return {"status": "success", "results": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def parse_leads_csv(file_path: str) -> dict:
    """
    Reads a CSV file containing leads and returns a list of lead records.
    The CSV should have columns: name, company, email, role.
    Use this at the start to load all leads before processing them.
    """
    try:
        leads = []
        with open(file_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                leads.append(dict(row))
        return {"status": "success", "leads": leads}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def score_lead(company_info: str, product_description: str) -> dict:
    """
    Scores a lead based on how well their company profile matches the product.
    Returns a score of HOT, WARM, or COLD with a reason.
    Use this after researching a lead to determine priority.
    """
    company_lower = company_info.lower()
    product_lower = product_description.lower()

    # Extract keywords from product description
    tech_keywords = ["software", "saas", "tech", "digital", "platform", "api", "cloud", "ai", "data"]
    sales_keywords = ["sales", "revenue", "growth", "expand", "scale", "team", "hire"]
    size_keywords = ["startup", "series", "funded", "enterprise", "scale"]

    score = 0

    for keyword in tech_keywords:
        if keyword in company_lower:
            score += 1

    for keyword in sales_keywords:
        if keyword in company_lower:
            score += 2

    for keyword in size_keywords:
        if keyword in company_lower:
            score += 1

    if score >= 4:
        rating = "HOT"
        reason = "Strong alignment — company profile matches product perfectly."
    elif score >= 2:
        rating = "WARM"
        reason = "Moderate alignment — some relevant signals detected."
    else:
        rating = "COLD"
        reason = "Low alignment — limited signals of product fit."

    return {"status": "success", "score": rating, "reason": reason}


def save_report(report_content: str, output_path: str = "sdr_report.md") -> dict:
    """
    Saves the final SDR report to a markdown file.
    Use this at the very end after all leads have been processed.
    Pass the complete report content as a string.
    """
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_content)
        return {"status": "success", "message": f"Report saved to {output_path}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}