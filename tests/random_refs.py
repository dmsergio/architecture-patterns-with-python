import uuid


def random_suffix():
    return uuid.uuid4().hex[:6]


def random_element(element, name=""):
    return f"{element}-{name}-{random_suffix()}"