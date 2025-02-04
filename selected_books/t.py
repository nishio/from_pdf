import os

import json
import tiktoken

gpt4o = tiktoken.encoding_for_model("gpt-4o")  # <Encoding 'o200k_base'>
gpt4 = tiktoken.encoding_for_model("gpt-4")  # <Encoding 'cl100k_base'>


def collect_all_book_info():
    books = []
    for d in os.listdir(".."):
        if not d.startswith("out_book"):
            continue
        print(d)
        for book in os.listdir(f"../{d}"):
            if book.endswith(".json"):
                continue
            if book == ".DS_Store":
                continue
            for f in os.listdir(f"../{d}/{book}"):
                if f.endswith(".jpg"):
                    continue
                # if f == "gyazo_info.json":
                #     print(f"  {f}")
                #     break
                if f == "scrapbox.json":
                    continue
                assert f == "gyazo_info.json"
                print(f"../{d}/{book}/{f}")
                books.append(
                    {
                        "book": book,
                        "gyazo_info": os.path.abspath(f"../{d}/{book}/{f}"),
                    }
                )

            # if f == "gyazo_info.json":
            #     print(f"  {f}")
            #     break
    json.dump(books, open("all_book_info.json", "w"), indent=2, ensure_ascii=False)


def stat():
    """
    num book 336
    num page 98526
    num char 63668699
    """
    books = json.load(open("all_book_info.json"))
    print("num book", len(books))
    num_page = 0
    num_char = 0
    num_token_gpt4o = 0
    num_token_gpt4 = 0
    for book in books:
        with open(book["gyazo_info"]) as f:
            gyazo_info = json.load(f)
        num_page += len(gyazo_info)
        for page in gyazo_info:
            if "ocr_text" in page:
                num_char += len(page["ocr_text"])
                num_token_gpt4o += len(gpt4o.encode(page["ocr_text"]))
                num_token_gpt4 += len(gpt4.encode(page["ocr_text"]))
    print("num page", num_page)
    print("num char", num_char)
    print("num token gpt4o", num_token_gpt4o)
    print("num token gpt4", num_token_gpt4)


def select():
    books = json.load(open("all_book_info.json"))
    num_book = 0
    num_page = 0
    num_char = 0

    def cond(book):
        title = book["book"]
        if "100分de名著" in title:
            return True

    selected_books = []
    for book in filter(cond, books):
        num_book += 1
        with open(book["gyazo_info"]) as f:
            gyazo_info = json.load(f)
        num_page += len(gyazo_info)
        for page in gyazo_info:
            if "ocr_text" in page:
                num_char += len(page["ocr_text"])
        selected_books.append(book)
    print("num book", num_book)
    print("num page", num_page)
    print("num char", num_char)
    """
    num book 34
    num page 5348
    num char 2731400
    """
    json.dump(
        selected_books, open("selected_books.json", "w"), indent=2, ensure_ascii=False
    )


# select()
# stat()


def stat_intellitech():
    pages = json.load(open("../out_intellitech/intellitech/gyazo_info.json"))
    num_char = 0
    num_token_gpt4o = 0
    num_token_gpt4 = 0
    for page in pages:
        if "ocr_text" in page:
            num_char += len(page["ocr_text"])
            num_token_gpt4o += len(gpt4o.encode(page["ocr_text"]))
            num_token_gpt4 += len(gpt4.encode(page["ocr_text"]))
    print("num page", len(pages))
    print("num char", num_char)
    print("num token gpt4o", num_token_gpt4o)
    print("num token gpt4", num_token_gpt4)


stat_intellitech()
