import os
import time
import requests
import streamlit as st

from dotenv import load_dotenv
from pypdf import PdfReader
from docx import Document


# =========================================================
# LOAD ENVIRONMENT VARIABLES
# =========================================================

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="AI Notes Summarizer",
    page_icon="📚",
    layout="wide"
)


# =========================================================
# PDF TEXT EXTRACTION
# =========================================================

def extract_pdf_text(file):
    """Extract text from a PDF file."""

    reader = PdfReader(file)

    text = []

    for page in reader.pages:

        page_text = page.extract_text()

        if page_text:
            text.append(page_text)

    return "\n\n".join(text)


# =========================================================
# DOCX TEXT EXTRACTION
# =========================================================

def extract_docx_text(file):
    """Extract text from a DOCX file."""

    document = Document(file)

    text = []

    for paragraph in document.paragraphs:

        if paragraph.text.strip():
            text.append(paragraph.text)

    return "\n\n".join(text)


# =========================================================
# TXT TEXT EXTRACTION
# =========================================================

def extract_txt_text(file):
    """Extract text from a TXT file."""

    return file.read().decode("utf-8")


# =========================================================
# FILE TEXT EXTRACTION
# =========================================================

def extract_text(file):
    """Detect file type and extract its text."""

    filename = file.name.lower()

    if filename.endswith(".pdf"):

        return extract_pdf_text(file)

    elif filename.endswith(".docx"):

        return extract_docx_text(file)

    elif filename.endswith(".txt"):

        return extract_txt_text(file)

    else:

        raise ValueError(
            "Unsupported file type. Please upload PDF, DOCX or TXT."
        )


# =========================================================
# GEMINI API SUMMARIZATION
# =========================================================

def summarize_notes(notes):
    """Send notes to Gemini and generate an exam-friendly summary."""

    # -----------------------------------------------------
    # CHECK API KEY
    # -----------------------------------------------------

    if not GEMINI_API_KEY:

        raise ValueError(
            "Gemini API key not found. "
            "Please add GEMINI_API_KEY to your .env file."
        )


    # -----------------------------------------------------
    # PROMPT
    # -----------------------------------------------------

    prompt = f"""
You are an AI academic notes summarizer.

Summarize the following student notes.

Use exactly this structure:

## Main Summary

Give a clear and simple summary of the notes.

## Key Points

Give the most important points as bullet points.

## Important Concepts

List important terms, concepts and definitions.

## Quick Revision

Give short points useful for exam revision.

## Important Questions

Generate 5 possible questions based only on the given notes.

Rules:

- Use simple student-friendly language.
- Do not add information that is not present in the notes.
- Preserve important technical terms.
- Do not remove important concepts.
- Avoid unnecessary repetition.
- Make the result useful for exam preparation.

STUDENT NOTES:

{notes}
"""


    # -----------------------------------------------------
    # GEMINI API URL
    # -----------------------------------------------------

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/"
        f"models/{GEMINI_MODEL}:generateContent"
    )


    # -----------------------------------------------------
    # REQUEST HEADERS
    # -----------------------------------------------------

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY
    }


    # -----------------------------------------------------
    # REQUEST DATA
    # -----------------------------------------------------

    data = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "maxOutputTokens": 3000
        }
    }


    # -----------------------------------------------------
    # AUTOMATIC RETRY SETTINGS
    # -----------------------------------------------------

    max_retries = 4


    # -----------------------------------------------------
    # SEND REQUEST
    # -----------------------------------------------------

    for attempt in range(max_retries):

        try:

            response = requests.post(
                url,
                headers=headers,
                json=data,
                timeout=120
            )

        except requests.RequestException as error:

            if attempt == max_retries - 1:

                raise RuntimeError(
                    f"Network error while contacting Gemini: {error}"
                )

            wait_time = 2 ** attempt

            st.warning(
                f"Temporary connection problem. "
                f"Retrying in {wait_time} seconds..."
            )

            time.sleep(wait_time)

            continue


        # -------------------------------------------------
        # SUCCESS
        # -------------------------------------------------

        if response.status_code == 200:

            result = response.json()

            try:

                return (
                    result["candidates"][0]
                    ["content"]["parts"][0]["text"]
                )

            except (KeyError, IndexError, TypeError):

                raise RuntimeError(
                    "Unexpected response received from Gemini API."
                )


        # -------------------------------------------------
        # TEMPORARY ERRORS
        # -------------------------------------------------

        if response.status_code in [429, 500, 502, 503, 504]:

            if attempt == max_retries - 1:

                try:

                    error_details = response.json()

                except Exception:

                    error_details = response.text

                raise RuntimeError(
                    f"Gemini is temporarily unavailable after "
                    f"{max_retries} attempts: {error_details}"
                )


            wait_time = 2 ** attempt

            st.warning(
                f"Gemini is temporarily busy. "
                f"Retrying automatically in {wait_time} seconds..."
            )

            time.sleep(wait_time)

            continue


        # -------------------------------------------------
        # OTHER API ERRORS
        # -------------------------------------------------

        try:

            error_details = response.json()

        except Exception:

            error_details = response.text

        raise RuntimeError(
            f"Gemini API Error: {error_details}"
        )


    # -----------------------------------------------------
    # FINAL FAILURE
    # -----------------------------------------------------

    raise RuntimeError(
        "Unable to generate summary after multiple attempts."
    )


# =========================================================
# APPLICATION TITLE
# =========================================================

st.title("📚 AI Notes Summarizer")

st.write(
    "Convert lengthy study material into simple, "
    "exam-friendly notes using AI."
)


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.header("📥 Input Method")

input_method = st.sidebar.radio(
    "Choose how you want to provide your notes:",
    [
        "Paste Notes",
        "Upload File"
    ]
)

st.sidebar.info(
    """
Supported file formats:

📄 PDF
📝 DOCX
📃 TXT
"""
)


# =========================================================
# INPUT SECTION
# =========================================================

notes = ""


# =========================================================
# PASTE NOTES
# =========================================================

if input_method == "Paste Notes":

    st.subheader("📝 Enter Your Notes")

    notes = st.text_area(
        "Paste your study material here:",
        height=350,
        placeholder="Paste your notes here..."
    )


# =========================================================
# UPLOAD FILE
# =========================================================

else:

    st.subheader("📂 Upload Your Notes")

    uploaded_file = st.file_uploader(
        "Choose a file",
        type=["pdf", "docx", "txt"]
    )

    if uploaded_file:

        try:

            with st.spinner("📖 Reading document..."):

                notes = extract_text(uploaded_file)


            if notes.strip():

                st.success(
                    f"Successfully read: {uploaded_file.name}"
                )

                with st.expander(
                    "👀 Preview Extracted Text"
                ):

                    st.text_area(
                        "Extracted text:",
                        notes[:5000],
                        height=250
                    )

            else:

                st.warning(
                    "No readable text was found in this file."
                )


        except Exception as error:

            st.error(
                f"Error reading file: {error}"
            )


# =========================================================
# GENERATE SUMMARY BUTTON
# =========================================================

st.divider()

if st.button(
    "✨ Generate AI Summary",
    use_container_width=True
):

    # -----------------------------------------------------
    # CHECK INPUT
    # -----------------------------------------------------

    if not notes.strip():

        st.warning(
            "⚠️ Please enter notes or upload a file first."
        )


    else:

        # Limit very large input
        notes_to_process = notes[:50000]


        # -------------------------------------------------
        # GENERATE SUMMARY
        # -------------------------------------------------

        with st.spinner(
            "🤖 AI is analyzing your notes..."
        ):

            try:

                summary = summarize_notes(
                    notes_to_process
                )

                # Store summary
                st.session_state["summary"] = summary

                st.success(
                    "✅ Summary generated successfully!"
                )

            except Exception as error:

                st.error(
                    f"Unable to generate summary: {error}"
                )


# =========================================================
# DISPLAY SUMMARY
# =========================================================

if "summary" in st.session_state:

    st.divider()

    st.subheader(
        "📖 AI Generated Summary"
    )

    st.markdown(
        st.session_state["summary"]
    )


    # -----------------------------------------------------
    # DOWNLOAD BUTTON
    # -----------------------------------------------------

    st.download_button(
        label="⬇️ Download Summary",
        data=st.session_state["summary"],
        file_name="AI_Notes_Summary.txt",
        mime="text/plain"
    )


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "AI Notes Summarizer | Python + Streamlit + Gemini API"
)