# app.py
# This CLI-compatible fallback version avoids Streamlit dependency
import sys
import os
from pathlib import Path

# Ensure current working directory is in sys.path to allow relative imports
current_dir = Path(__file__).parent if '__file__' in globals() else Path().resolve()
sys.path.append(str(current_dir))

from game_scanner_app.utils.pdf_extractor import extract_text_from_pdf
from game_scanner_app.parsers.asmodee import parse_asmodee_invoice
from game_scanner_app.parsers.universal import parse_universal_invoice
from game_scanner_app.parsers.ilo import parse_ilo_invoice

def detect_distributor(text):
    if "Asmodee Canada" in text:
        return "Asmodee"
    elif "Invoice No: SINV" in text or "universaldist.com" in text:
        return "Universal"
    elif "ilo307.com" in text or "ÎLO" in text:
        return "ILO"
    return None

def main(path):
    if not os.path.isfile(path):
        print(f"[ERROR] File not found: {path}")
        return

    with open(path, "rb") as f:
        raw_text = extract_text_from_pdf(f)
        print("\n--- RAW TEXT PREVIEW ---\n")
        print(raw_text[:1000])

        distributor = detect_distributor(raw_text)
        if distributor == "Asmodee":
            print("\n[INFO] Asmodee invoice detected")
            data = parse_asmodee_invoice(raw_text)
        elif distributor == "Universal":
            print("\n[INFO] Universal invoice detected")
            data = parse_universal_invoice(raw_text)
        elif distributor == "ILO":
            print("\n[INFO] ÎLO invoice detected")
            data = parse_ilo_invoice(raw_text)
        else:
            print("\n[ERROR] Distributor not recognized")
            return

        print("\n--- PARSED DATA ---\n")
        from pprint import pprint
        pprint(data)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python app.py path_to_invoice.pdf")
    else:
        main(sys.argv[1])
