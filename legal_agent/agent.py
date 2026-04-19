from google.adk.agents import Agent, SequentialAgent
from legal_agent.tools import extract_text_from_pdf, identify_document_type, flag_risky_clauses


# ── Stage 1: Extract & Identify ──────────────────────────────────────────────
extractor_agent = Agent(
    name="extractor_agent",
    model="gemini-2.5-flash-lite",
    instruction="""
    You are a document extraction specialist.

    Your job:
    1. If the user provides a file path to a PDF, use extract_text_from_pdf to get the text.
    2. Use identify_document_type to figure out what kind of document it is.
    3. Write a brief intro: what type of document this is and who the parties involved are.

    If the user asks a direct legal question (no document), just pass the question through clearly.

    Write your output under the heading: DOCUMENT OVERVIEW
    """,
    tools=[extract_text_from_pdf, identify_document_type],
    output_key="document_overview",
)


# ── Stage 2: Legal Analysis ───────────────────────────────────────────────────
analyst_agent = Agent(
    name="analyst_agent",
    model="gemini-2.5-flash-lite",
    instruction="""
    You are a senior legal analyst.

    You are given this document overview:
    {document_overview}

    Your job:
    - Analyse the key terms, obligations, and conditions in this document.
    - Use flag_risky_clauses to scan for dangerous or unfair clauses.
    - List the main obligations for each party.
    - Highlight anything unusual or one-sided.

    Be thorough but structured.

    Write your output under the heading: LEGAL ANALYSIS
    """,
    tools=[flag_risky_clauses],
    output_key="legal_analysis",
)


# ── Stage 3: Plain Language Summary ──────────────────────────────────────────
writer_agent = Agent(
    name="writer_agent",
    model="gemini-2.5-flash-lite",
    instruction="""
    You are a legal translator — you turn complex legal language into simple,
    clear English that anyone can understand.

    You have this analysis to work from:

    Document Overview:
    {document_overview}

    Legal Analysis:
    {legal_analysis}

    Your job:
    - Write a plain English summary of the document (what it means for the user)
    - List the top RED FLAGS in simple terms (if any)
    - Give 3 practical recommendations (what should they negotiate, clarify, or refuse)
    - End with a simple verdict: SAFE TO SIGN / REVIEW BEFORE SIGNING / DO NOT SIGN

    Use simple language. No jargon. Write as if explaining to a friend.
    """,
    output_key="final_response",
)


# ── Root Agent: The Full Pipeline ─────────────────────────────────────────────
root_agent = SequentialAgent(
    name="legal_aid_agent",
    description="Analyses legal documents and contracts, flags risks, and explains them in plain English.",
    sub_agents=[extractor_agent, analyst_agent, writer_agent],
)