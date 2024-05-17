def make_scrapbox_json(directory):
    """
    Read `gyazo_info.json` and make Scrapbox JSON.
    """
    json_path = os.path.join(directory, "gyazo_info.json")
    if not os.path.exists(json_path):
        print(f"Skip it because gyazo_info.json not exists.")
        return
    with open(json_path) as f:
        gyazo_info = json.load(f)

    print(f"Making Scrapbox JSON for {directory}...")
    title = os.path.split(directory)[-1]

    image_files = get_images(directory)
    if len(gyazo_info) != len(image_files):
        print(f"Skip it because not uploaded all images.")
        return

    # Concatenate images and the OCR texts into a scrapbox page.
    # Due to the Scrapbox accepts only 10000 lines per page,
    # we need to split the pages.
    scrapbox_pages = []
    page_count = 1

    def add_page(page_lines):
        nonlocal page_count
        new_title = title
        if page_count > 1:
            new_title += f" ({page_count})"
        page_lines[0] = new_title
        scrapbox_pages.append({"title": new_title, "lines": page_lines})
        page_count += 1

    page_lines = [title, f"local_path: {directory}", ""]

    for page in gyazo_info:
        page_lines.append(f"[{page['permalink_url']}]")
        if "ocr_text" in page:
            page_lines.extend(page["ocr_text"].split("\n"))
        page_lines.append("")
        if len(page_lines) > 9000:
            add_page(page_lines)
            page_lines = [title, f"local_path: {directory}", ""]
    add_page(page_lines)

    # Make the JSON
    scrapbox_json = {"pages": scrapbox_pages}

    # Save the JSON
    out_path = os.path.join(directory, "scrapbox.json")
    with open(out_path, "w") as f:
        json.dump(scrapbox_json, f, indent=2, ensure_ascii=False)
