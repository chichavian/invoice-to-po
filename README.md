# Invoice to Lightspeed PO

This tool scans PDF invoices from board game distributors (e.g., Asmodee, Universal, ÎLO), extracts line items, and prepares them for purchase order creation and receiving in Lightspeed Retail.

## Features
- 📄 Upload invoice PDFs
- 🔍 Auto-detect distributor (Asmodee, Universal, ÎLO)
- 🧾 Extract item list, quantities, and pricing
- 🚀 (Coming Soon) Create and receive POs via Lightspeed API

## Usage (CLI)
```bash
python app.py path/to/invoice.pdf
```

## Usage (Web UI)
Coming soon via Streamlit

## Directory Structure
```
project_root/
├── app.py
├── utils/
│   └── pdf_extractor.py
├── parsers/
│   ├── asmodee.py
│   ├── universal.py
│   └── ilo.py
```

## Requirements
See `requirements.txt`

## License
MIT
