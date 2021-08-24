from tokenizer import TokenTagEnum, Tokenizer
from nltk.corpus import stopwords

stopwords_cache = stopwords.words('english')

def transformer(text):
    clean_text = get_clean_text(text)
    words = [word.strip() for word in clean_text.split(" ")]
    tokens = list(filter(lambda item: len(item) > 3 or (len(item) == 3 and item not in stopwords_cache), words))

    if len(tokens) == 0:
        tokens = words
        text_for_query = f'"{" ".join(tokens)}"'
    else:
        text_for_query = " AND ".join([f'"{token}"'for token in tokens])

    if text_for_query == '""':
        text_for_query = ""

    return clean_text, text_for_query


def get_clean_text(text):
    def get_token(tokens, idx):
        if len(tokens) <= idx:
            return None

        return tokens[idx]

    clean_text = ""
    tokens = Tokenizer().tokenize(text)

    i = 0
    token = get_token(tokens, i)
   
    while token is not None:
        value = token.value
        tag = token.tag

        if tag == TokenTagEnum.WORD or tag == TokenTagEnum.NUMBER:
            if "'" in value:
                index = value.find("'")
                value = value[0:index]
                    
            if value != "":
                clean_text += value + " "
        elif value == "(":  # NOTE: skip parenthesis (...)
            j = i + 1
            forward_token = get_token(tokens, j)
            while forward_token is not None and forward_token.value != ")":
                j += 1
                forward_token = get_token(tokens, j)

            i = j
        elif value == "[":  # NOTE: skip parenthesis [...]
            j = i + 1
            forward_token = get_token(tokens, j)
            while forward_token is not None and forward_token.value != "]":
                j += 1
                forward_token = get_token(tokens, j)

            i = j

        i += 1
        token = get_token(tokens, i)

    return clean_text.strip().lower()
