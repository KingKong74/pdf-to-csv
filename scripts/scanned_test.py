from extractor_scanned import extract_transactions_scanned

PDF_PATH = r"C:\PDF_Converter\pdf-to-csv\Anz_CC_Statement.pdf"

df = extract_transactions_scanned(PDF_PATH)
print(df.head(10))
