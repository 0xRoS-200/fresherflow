import os

def create_pdf(filename, text):
    # Minimal PDF structure containing plain text
    content_stream = f"BT\n/F1 12 Tf\n72 712 Td\n({text}) Tj\nET"
    content_len = len(content_stream)
    
    # Objects structure
    obj1 = "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    obj2 = "2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    obj3 = "3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n"
    obj4 = f"4 0 obj\n<< /Length {content_len} >>\nstream\n{content_stream}\nendstream\nendobj\n"
    
    header = "%PDF-1.4\n"
    
    # Calculate byte offsets
    offset1 = len(header)
    offset2 = offset1 + len(obj1)
    offset3 = offset2 + len(obj2)
    offset4 = offset3 + len(obj3)
    xref_offset = offset4 + len(obj4)
    
    xref = (
        "xref\n"
        "0 5\n"
        "0000000000 65535 f \n"
        f"{offset1:010d} 00000 n \n"
        f"{offset2:010d} 00000 n \n"
        f"{offset3:010d} 00000 n \n"
        f"{offset4:010d} 00000 n \n"
    )
    
    trailer = (
        "trailer\n"
        "<< /Size 5 /Root 1 0 R >>\n"
        "startxref\n"
        f"{xref_offset}\n"
        "%%EOF\n"
    )
    
    pdf_content = header + obj1 + obj2 + obj3 + obj4 + xref + trailer
    
    with open(filename, "wb") as f:
        f.write(pdf_content.encode("latin1"))
    
    print(f"Created PDF {filename}")

if __name__ == "__main__":
    text = "Rohit Kumar Singh Skills: python, java, javascript, react, docker, sql, git, postgresql"
    create_pdf("test_resume.pdf", text)
    
    # Test reading with pdfplumber
    try:
        import pdfplumber
        with pdfplumber.open("test_resume.pdf") as pdf:
            print("Extracted Text:")
            for page in pdf.pages:
                print(repr(page.extract_text()))
    except Exception as e:
        print("pdfplumber parsing failed:", e)
