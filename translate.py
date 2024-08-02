import logging
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline

class Translator(object):

    def __init__(self, model_name:str = "facebook/nllb-200-distilled-600M", src_lang: str = "eng_Latn", dst_lang: str = "fra_Latn", max_length=500):
        logging.info(f"Loading model {model_name}...")
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
    def correct_text(text: str) -> str:
        if text is None:
            return None
        return text.replace("|", "I")

    def translate(self, text) -> str:
        return self.translator(text)[0]["translation_text"]