import logging
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline

class Translator(object):

    def __init__(self, model_name:str = "facebook/nllb-200-distilled-600M", src_lang: str = "eng_Latn", dst_lang: str = "fra_Latn", max_length=500):
        logging.info(f"Loading model {model_name} for {src_lang} -> {dst_lang} translations...")
        self.src_lang = src_lang
        self.dst_lang = dst_lang
        self.model_name = model_name
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        self.translator = pipeline("translation", \
                                   model=self.model, \
                                   tokenizer=self.tokenizer, \
                                   src_lang=self.src_lang, \
                                   tgt_lang=self.dst_lang, \
                                   max_length=max_length)

    @staticmethod
    def get_nllb_lang(lang):
        if lang == "de":
            return "deu_Latn"
        if lang == "en":
            return "eng_Latn"
        if lang == "es":
            return "spa_Latn"
        if lang == "fr":
            return "fra_Latn"
        if lang == "it":
            return "ita_Latn"
        if lang == "ja":
            return "jpn_Jpan"
        if lang == "ru":
            return "rus_Cyrl"
        if lang == "zh":
            return "zho_Hans"

    def translate(self, text) -> str:
        return self.translator(text)[0]["translation_text"]