def file_get_text_contents(filename, encoding="utf-8"):
    with open(filename, "r", encoding=encoding) as f:
        return f.read()


def file_put_text_contents(filename, contents, encoding="utf-8"):
    with open(filename, "w", encoding=encoding) as f:
        f.write(contents)
