# app.py
# Interactive CLI app with menu-based PDF selection
import sys
import os
from pathlib import Path

# Ensure local imports work
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

def list_pdf_files(folder):
    return sorted([f for f in os.listdir(folder) if f.lower().endswith(".pdf")])

def choose_file_menu(pdf_files):
    print("\nAvailable Invoices:\n")
    for idx, fname in enumerate(pdf_files, start=1):
        print(f"[{idx}] {fname}")
    while True:
        try:
            choice = int(input("\nChoose a file [1-{}]: ".format(len(pdf_files))))
            if 1 <= choice <= len(pdf_files):
                return pdf_files[choice - 1]
        except ValueError:
            pass
        print("Invalid choice. Try again.")

def main():
    folder = "invoices"
    os.makedirs(folder, exist_ok=True)

    pdf_files = list_pdf_files(folder)
    if not pdf_files:
        print("[ERROR] No PDF files found in 'invoices/' folder.")
        return

    selected_file = choose_file_menu(pdf_files)
    pdf_path = os.path.join(folder, selected_file)

    with open(pdf_path, "rb") as f:
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
    main()
