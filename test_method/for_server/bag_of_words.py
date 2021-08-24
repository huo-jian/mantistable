import urllib.parse

import transformer

def get_name_from_entity(entity):
    def decode_uri_component(uri):
        return urllib.parse.unquote(uri)

    entity = decode_uri_component(entity)
    name = " ".join(entity[28:].split("_")).lower()

    return transformer.transformer(name)[0]
