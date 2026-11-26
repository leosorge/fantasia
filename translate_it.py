"""Translate YouTube metadata locally on the runner before enqueueing."""
import re


class TranslationError(Exception):
    """The source language or translated content cannot be accepted."""


class ItalianTranslator:
    def __init__(self, target='it'):
        self.target = target
        self.model = None
        self.tokenizer = None

    def translate(self, title, description):
        import langid

        # Links and handles are weak language signals compared with the copy.
        sample = re.sub(r"https?://\S+|[@#]\w+", " ", title + "\n" + description)
        language, _ = langid.classify(sample)
        if language == self.target:
            return title, description
        if self.model is None:
            from transformers import M2M100ForConditionalGeneration, M2M100Tokenizer
            name = "facebook/m2m100_418M"
            self.tokenizer = M2M100Tokenizer.from_pretrained(name)
            self.model = M2M100ForConditionalGeneration.from_pretrained(name).eval()
        if language not in self.tokenizer.lang_code_to_id:
            raise TranslationError("lingua sorgente non supportata")
        self.tokenizer.src_lang = language
        translated = self.translate_text(title)
        if not translated.strip():
            raise TranslationError("titolo tradotto vuoto")
        return translated, self.translate_text(description)

    def translate_text(self, text):
        # Keep paragraph structure and leave source URLs intact.
        lines = []
        for line in text.split("\n"):
            pieces = re.split(r"(https?://[^\s<>]+)", line)
            lines.append("".join(piece if index % 2 else self.translate_segment(piece)
                                 for index, piece in enumerate(pieces)))
        return "\n".join(lines)

    def translate_segment(self, text):
        if not any(char.isalpha() for char in text):
            return text
        original = text.strip()
        encoded = self.tokenizer(original, return_tensors="pt", verbose=False)
        if encoded["input_ids"].shape[-1] > 380:
            middle = len(original) // 2
            boundary = original.rfind(" ", middle // 2, middle)
            if boundary == -1:
                boundary = middle
            return (self.translate_segment(original[:boundary]) + " " +
                    self.translate_segment(original[boundary:]))
        import torch
        with torch.inference_mode():
            output = self.model.generate(**encoded,
                                         forced_bos_token_id=self.tokenizer.get_lang_id(self.target),
                                         max_new_tokens=780, num_beams=3)
        decoded = self.tokenizer.decode(output[0], skip_special_tokens=True).strip()
        if not decoded:
            raise TranslationError("traduzione vuota")
        leading = text[:len(text) - len(text.lstrip())]
        trailing = text[len(text.rstrip()):]
        return leading + decoded + trailing
