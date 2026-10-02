#!/usr/bin/env python3
"""Ask questions about large technical PDF documents using Google Gemini.

The entire PDF is uploaded to the Gemini File API and placed directly in the
model's context window (no RAG, no vector database).

Usage:
    python ask_pdf.py path/to/document.pdf "My question here"
"""

import argparse
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

DEFAULT_MODEL = "gemini-2.5-flash"

# Seconds between status checks while Gemini processes the uploaded file.
POLL_INTERVAL_SECONDS = 2
# Maximum time to wait for file processing before giving up.
PROCESSING_TIMEOUT_SECONDS = 300
# Large documents can take a while to answer; the default HTTP timeout is too short.
REQUEST_TIMEOUT_SECONDS = 600

SYSTEM_PROMPT_TEMPLATE = """Du er en fagspecifik AI-assistent for en bygningskonstruktørstuderende i Danmark. Din opgave er at analysere de vedhæftede byggetekniske dokumenter og levere præcise, teknisk funderede svar.

Følg disse strenge retningslinjer:
1. Brug KUN den vedhæftede kontekst: Al information og alle tal skal kunne udledes direkte af de uploadede filer.
2. Præcise kildehenvisninger: Hver gang du angiver et krav, SKAL du skrive nøjagtig, hvor du har det fra (Sidetal, afsnit og evt. tabelnummer).
3. Ingen gætteri: Hvis dokumenterne ikke indeholder svaret, skal du sige: "Informationen findes ikke i det vedhæftede dokument."
4. Bevar teknisk præcision: Læs altid og inkludér relevante fodnoter fra tabeller (f.eks. "Forudsat fast undertag").

SPØRGSMÅL DER SKAL BESVARES:
{user_question}"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analysér et teknisk PDF-dokument med Google Gemini.",
    )
    parser.add_argument("pdf_path", type=Path, help="Sti til PDF-filen")
    parser.add_argument("question", help="Spørgsmålet der skal besvares")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Gemini-model der skal bruges (standard: {DEFAULT_MODEL})",
    )
    return parser.parse_args()


def fail(message: str) -> None:
    print(f"Fejl: {message}", file=sys.stderr)
    sys.exit(1)


def load_api_key() -> str:
    # Look for .env next to this script as well as in the current directory.
    load_dotenv(Path(__file__).resolve().parent / ".env")
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        fail("GEMINI_API_KEY mangler. Kopiér .env.example til .env og indsæt din API-nøgle.")
    return api_key


def wait_for_processing(client: genai.Client, uploaded_file: types.File) -> types.File:
    """Poll the File API until the uploaded file is ACTIVE."""
    deadline = time.monotonic() + PROCESSING_TIMEOUT_SECONDS
    while uploaded_file.state == types.FileState.PROCESSING:
        if time.monotonic() > deadline:
            raise TimeoutError("Gemini blev ikke færdig med at behandle filen i tide.")
        print("Venter på at Gemini behandler filen...", file=sys.stderr)
        time.sleep(POLL_INTERVAL_SECONDS)
        uploaded_file = client.files.get(name=uploaded_file.name)

    if uploaded_file.state != types.FileState.ACTIVE:
        raise RuntimeError(f"Filbehandling mislykkedes (status: {uploaded_file.state}).")
    return uploaded_file


def extract_text(response: types.GenerateContentResponse) -> str:
    # response.text is None when there is no text, e.g. because the answer was blocked.
    if not response.text:
        raise RuntimeError(f"Modellen returnerede intet svar. Feedback: {response.prompt_feedback}")
    return response.text


def main() -> None:
    args = parse_args()

    pdf_path: Path = args.pdf_path
    if not pdf_path.is_file():
        fail(f"Filen findes ikke: {pdf_path}")
    if pdf_path.suffix.lower() != ".pdf":
        fail(f"Filen er ikke en PDF: {pdf_path}")

    client = genai.Client(
        api_key=load_api_key(),
        http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_SECONDS * 1000),
    )
    prompt = SYSTEM_PROMPT_TEMPLATE.format(user_question=args.question)

    print(f"Uploader {pdf_path.name}...", file=sys.stderr)
    try:
        uploaded_file = client.files.upload(
            file=pdf_path,
            config=types.UploadFileConfig(mime_type="application/pdf", display_name=pdf_path.name),
        )
    except errors.APIError as exc:
        fail(f"Upload mislykkedes: {exc}")

    try:
        uploaded_file = wait_for_processing(client, uploaded_file)
        print(f"Analyserer dokumentet med {args.model}...\n", file=sys.stderr)
        response = client.models.generate_content(
            model=args.model,
            contents=[uploaded_file, prompt],
        )
        print(extract_text(response))
    except errors.APIError as exc:
        if exc.code == 404:
            fail(f"Modellen '{args.model}' blev ikke fundet. Prøv en anden med --model. ({exc})")
        fail(str(exc))
    except (RuntimeError, TimeoutError) as exc:
        fail(str(exc))
    finally:
        # Always clean up the uploaded file, even if generation failed.
        try:
            client.files.delete(name=uploaded_file.name)
            print("\nDen uploadede fil er slettet fra Gemini.", file=sys.stderr)
        except errors.APIError as exc:
            print(f"Advarsel: Kunne ikke slette filen {uploaded_file.name}: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
