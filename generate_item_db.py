# WARNING
# Requires torch (install via https://pytorch.org/ if you have cuda/cudnn, or via pip install torch to use CPU).

import json
import logging
import os
import re
import typing

from translate import Translator

translation_model = "facebook/nllb-200-distilled-600M"

item_db_src = ["neondb/items.db"]
abyss_db_src = "neondb/sources/abyssexplorer/items.json"

output_path = "neondb/items.db"
languages = ["de", "es", "fr", "it", "ja", "ru", "zh"]


def json_path(obj, *args):
    if obj is None:
        return None

    if len(args) <= 0:
        return obj

    if args[0] in obj:
        return json_path(obj[args[0]], *args[1:])

    return None


def json_insert(dst: typing.Dict, dst_path: typing.List, value):
    for p in dst_path[:-1]:
        if not p in dst:
            dst[p] = dict()
        dst = dst[p]
    dst[dst_path[-1]] = value


def translate_field(item: typing.Dict, abyss_item: typing.Dict, field_path: typing.List, abyss_field: str = None, language: str = "fr", translator: Translator = None):
    if not abyss_field:
        abyss_field = field_path[-1]

    already_translated = json_path(item, "translations", language, *field_path) is not None \
                         or json_path(item, "translations", "llm", language, *field_path) is not None
    if already_translated:
        return

    abyss_value = json_path(abyss_item, abyss_field, language)
    item_value = json_path(item, *field_path)

    if abyss_value:
        logging.info(f"Using abyssexplorer translation of item {item['name']} {abyss_field} for {language} language")
        json_insert(item, ["translations", language] + field_path, abyss_value)

    elif item_value and translator:
        logging.info(f"Generating translation of item {item['name']} {abyss_field} for {language} language")
        json_insert(item, ["translations", "llm", language] + field_path, translator.translate(item_value))


def translate_item(item: typing.Dict, abyss_db: typing.List[typing.Dict], language: str, translator: Translator):
    slug = item["slug"]

    abyss_slug = re.sub("[^a-z0-9]", "-", slug.lower()).strip('-')
    abyss_items = [i for i in abyss_db if i["slug"].lower() == abyss_slug]
    abyss_item = abyss_items[0] if len(abyss_items) > 0 else None

    for field_path in [["name"], ["desc"], ["passive"]]:
        translate_field(item, abyss_item, field_path, None, language, translator)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logging.info("Reading BD...")

    item_db = []
    for db in item_db_src:
        with open(db, "r", encoding='utf-8') as f:
            item_db.extend(json.load(f))

    with open(abyss_db_src, "r", encoding='utf-8') as f:
        abyss_db = json.load(f)

    for item in item_db:
        if json_path(item, "translations", "llm", "en"):
            del item["translations"]["llm"]["en"]

    for lang in languages:
        translator = Translator(
            model_name=translation_model,
            src_lang=Translator.get_nllb_lang("en"),
            dst_lang=Translator.get_nllb_lang(lang)
        )

        for item in item_db:
            translate_item(item, abyss_db, lang, translator)

            with open(f"{output_path}.tmp", "w") as f:
                json.dump(item_db, f, indent=2)
            os.replace(f"{output_path}.tmp", output_path)