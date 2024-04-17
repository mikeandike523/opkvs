def file_get_text_contents(filename, encoding="utf-8"):
    with open(filename, "r", encoding=encoding) as f:
        return f.read()
