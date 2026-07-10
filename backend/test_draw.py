import fitz

def test():
    # create a dummy pdf
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Hello ________ world")
    
    # search for the blank
    rects = page.search_for("________")
    if not rects:
        print("Blank not found")
        return
    rect = rects[0]
    
    # 1. redact
    page.add_redact_annot(rect, fill=(1, 1, 1))
    page.apply_redactions()
    
    # 2. insert text
    f_size = max(10, rect.height * 0.9)
    # The text baseline is usually slightly above the bottom of the bounding box
    point = fitz.Point(rect.x0, rect.y1 - (rect.height * 0.15))
    
    try:
        page.insert_text(
            point,
            "Chinur Abhiram",
            fontsize=f_size,
            fontname="tiro",
            color=(0, 0, 0)
        )
        print("insert_text called")
    except Exception as e:
        print("Error inserting text:", e)
        
    doc.save("test_out2.pdf")
    print("Saved test_out2.pdf")

if __name__ == "__main__":
    test()
