# from __future__ import annotations  
  
# import logging  
# import re  
# from functools import lru_cache  
  
# from sumy.nlp.tokenizers import Tokenizer  
# from sumy.parsers.plaintext import PlaintextParser  
# from sumy.summarizers.text_rank import TextRankSummarizer  
  
# from app.services.ai.chunking import chunk_document  
  
# logger = logging.getLogger(__name__)  
  
# MODEL_NAME = 'sshleifer/distilbart-cnn-12-6'  
# MAP_MAX_LENGTH = 120  
# MAP_MIN_LENGTH = 40  
# REDUCE_MAX_LENGTH = 160  
# REDUCE_MIN_LENGTH = 50  
# EXTRACTIVE_SENTENCE_COUNT = 6  
  
# def _simple_sentence_split(text):  
#     return [part.strip() for part in re.split(r'(?<=[.!?])\s+', text.strip()) if part.strip()]  
  
# def _simple_extractive(text, sentences_count=EXTRACTIVE_SENTENCE_COUNT):  
#     return ' '.join(_simple_sentence_split(text)[:sentences_count]).strip()  
  
# def extractive_summary(text, sentences_count=EXTRACTIVE_SENTENCE_COUNT):  
#     if not text or not str(text).strip():  
#         return ''  
#     try:  
#         parser = PlaintextParser.from_string(str(text).strip(), Tokenizer('english'))  
#         summarizer = TextRankSummarizer()  
#         summary = ' '.join(str(sentence) for sentence in summarizer(parser.document, sentences_count)).strip()  
#         if summary:  
#             return summary  
#     except LookupError as exc:  
#         logger.info('TextRank tokenizer assets unavailable, using fallback: %s', exc)  
#     except Exception as exc:  
#         logger.warning('TextRank failed: %s', exc)  
#     return _simple_extractive(str(text), sentences_count=sentences_count) 
  
# @lru_cache(maxsize=1)  
# def _summarizer_components():  
#     import torch  
#     from transformers import AutoModelForSeq2SeqLM, AutoTokenizer  
  
#     tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)  
#     model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)  
#     device = 'cuda' if torch.cuda.is_available() else 'cpu'  
#     model.to(device)  
#     model.eval()  
#     return model, tokenizer, device  
  
# def _generate_summary(text, max_length, min_length):  
#     if not text or not str(text).strip():  
#         return ''  
#     import torch  
  
#     model, tokenizer, device = _summarizer_components()  
#     encoded = tokenizer(  
#         str(text).strip(),  
#         max_length=min(1024, getattr(tokenizer, 'model_max_length', 1024)),  
#         truncation=True,  
#         return_tensors='pt',  
#     )  
#     encoded = {key: value.to(device) for key, value in encoded.items()}  
#     with torch.no_grad():  
#         tokens = model.generate(  
#             input_ids=encoded['input_ids'],  
#             attention_mask=encoded.get('attention_mask'),  
#             max_length=max_length,  
#             min_length=min_length,  
#             num_beams=4,  
#             do_sample=False,  
#             no_repeat_ngram_size=3,  
#             early_stopping=True,  
#         )  
#     return tokenizer.decode(tokens[0], skip_special_tokens=True).strip()  
  
# def map_abstractive_summaries(chunks):  
#     partial_summaries = []  
#     for chunk in chunks or []:  
#         try:  
#             summary = _generate_summary(chunk, MAP_MAX_LENGTH, MAP_MIN_LENGTH)  
#         except Exception as exc:  
#             logger.warning('Map summarization failed: %s', exc)  
#             summary = extractive_summary(chunk, sentences_count=3)  
#         if summary:  
#             partial_summaries.append(summary)  
#     return partial_summaries 
  
# def reduce_abstractive_summary(partial_summaries):  
#     if not partial_summaries:  
#         return ''  
#     if len(partial_summaries) == 1:  
#         return partial_summaries[0]  
#     blocks = list(partial_summaries)  
#     while len(blocks) > 1:  
#         reduced_blocks = []  
#         index = 0  
#         while index < len(blocks):  
#             group = blocks[index:index + 6]  
#             combined = ' '.join(group)  
#             try:  
#                 reduced = _generate_summary(combined, REDUCE_MAX_LENGTH, REDUCE_MIN_LENGTH)  
#             except Exception as exc:  
#                 logger.warning('Reduce summarization failed: %s', exc)  
#                 reduced = extractive_summary(combined, sentences_count=4)  
#             if reduced:  
#                 reduced_blocks.append(reduced)  
#             index += 6  
#         if not reduced_blocks:  
#             return ' '.join(partial_summaries[:3])  
#         blocks = reduced_blocks  
#     return blocks[0]  
  
# def build_abstractive_summary(cleaned_text, chunks=None):  
#     if not cleaned_text or not str(cleaned_text).strip():  
#         return '', []  
#     actual_chunks = chunks or chunk_document(cleaned_text)  
#     partial_summaries = map_abstractive_summaries(actual_chunks)  
#     final_summary = reduce_abstractive_summary(partial_summaries)  
#     return final_summary, partial_summaries 

from __future__ import annotations

import logging
import re
from functools import lru_cache

from sumy.nlp.tokenizers import Tokenizer
from sumy.parsers.plaintext import PlaintextParser
from sumy.summarizers.text_rank import TextRankSummarizer

from app.services.ai.chunking import chunk_document

logger = logging.getLogger(__name__)

MODEL_NAME = "sshleifer/distilbart-cnn-12-6"

# MAP stage settings
MAP_MAX_LENGTH = 160
MAP_MIN_LENGTH = 60

# REDUCE stage settings (slightly increased for better summaries)
REDUCE_MAX_LENGTH = 220
REDUCE_MIN_LENGTH = 80

EXTRACTIVE_SENTENCE_COUNT = 6


# --------------------------------------------------
# BASIC TEXT CLEANING
# --------------------------------------------------

def _normalize_text(text: str) -> str:
    """Basic cleanup before sending text to models."""
    text = str(text)

    text = re.sub(r"\n+", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# --------------------------------------------------
# SIMPLE EXTRACTIVE FALLBACK
# --------------------------------------------------

def _simple_sentence_split(text):
    return [
        part.strip()
        for part in re.split(r"(?<=[.!?])\s+", text.strip())
        if part.strip()
    ]


def _simple_extractive(text, sentences_count=EXTRACTIVE_SENTENCE_COUNT):
    return " ".join(_simple_sentence_split(text)[:sentences_count]).strip()


# --------------------------------------------------
# TEXTRANK EXTRACTIVE SUMMARY
# --------------------------------------------------

def extractive_summary(text, sentences_count=EXTRACTIVE_SENTENCE_COUNT):
    if not text or not str(text).strip():
        return ""

    text = _normalize_text(text)

    try:
        parser = PlaintextParser.from_string(text, Tokenizer("english"))
        summarizer = TextRankSummarizer()

        summary = " ".join(
            str(sentence)
            for sentence in summarizer(parser.document, sentences_count)
        ).strip()

        if summary:
            return summary

    except LookupError as exc:
        logger.info(
            "TextRank tokenizer assets unavailable, using fallback: %s", exc
        )

    except Exception as exc:
        logger.warning("TextRank failed: %s", exc)

    return _simple_extractive(text, sentences_count=sentences_count)


# --------------------------------------------------
# LOAD TRANSFORMER MODEL (CACHED)
# --------------------------------------------------

@lru_cache(maxsize=1)
def _summarizer_components():
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)

    device = "cuda" if torch.cuda.is_available() else "cpu"

    model.to(device)
    model.eval()

    logger.info("Loaded summarization model on device: %s", device)

    return model, tokenizer, device


# --------------------------------------------------
# GENERATE SUMMARY USING TRANSFORMER
# --------------------------------------------------

def _generate_summary(text, max_length, min_length):
    if not text or not str(text).strip():
        return ""

    import torch

    model, tokenizer, device = _summarizer_components()

    text = (
    "Summarize this legal contract. Include:\n"
    "- parties involved\n"
    "- lease duration\n"
    "- rent and deposit amounts\n"
    "- tenant and landlord obligations\n\n"
    + _normalize_text(text)
)

    try:
        encoded = tokenizer(
            text,
            max_length=1024,
            truncation=True,
            padding="longest",
            return_tensors="pt",
        )

        encoded = {k: v.to(device) for k, v in encoded.items()}

        with torch.no_grad():
            tokens = model.generate(
                input_ids=encoded["input_ids"],
                attention_mask=encoded.get("attention_mask"),

                max_length=max_length,
                min_length=min_length,

                # CPU friendly decoding
                num_beams=2,
                do_sample=False,

                no_repeat_ngram_size=3,
                early_stopping=True,
            )

        summary = tokenizer.decode(
            tokens[0],
            skip_special_tokens=True
        ).strip()

        return summary

    except Exception as exc:
        logger.error("Transformer summarization failed: %s", exc)
        raise


# --------------------------------------------------
# MAP STEP
# --------------------------------------------------

def map_abstractive_summaries(chunks):

    partial_summaries = []

    for chunk in chunks or []:

        if not chunk or not chunk.strip():
            continue

        try:
            summary = _generate_summary(
                chunk,
                MAP_MAX_LENGTH,
                MAP_MIN_LENGTH
            )

        except Exception as exc:
            logger.warning("Map summarization failed: %s", exc)

            summary = extractive_summary(chunk, sentences_count=3)

        if summary:
            partial_summaries.append(summary)

    return partial_summaries


# --------------------------------------------------
# REDUCE STEP
# --------------------------------------------------

def reduce_abstractive_summary(partial_summaries):

    if not partial_summaries:
        return ""

    if len(partial_summaries) == 1:
        return partial_summaries[0]

    blocks = list(partial_summaries)

    while len(blocks) > 1:

        reduced_blocks = []

        index = 0

        while index < len(blocks):

            group = blocks[index:index + 6]

            combined = " ".join(group)

            try:
                reduced = _generate_summary(
                    combined,
                    REDUCE_MAX_LENGTH,
                    REDUCE_MIN_LENGTH,
                )

            except Exception as exc:
                logger.warning("Reduce summarization failed: %s", exc)

                reduced = extractive_summary(
                    combined,
                    sentences_count=4,
                )

            if reduced:
                reduced_blocks.append(reduced)

            index += 6

        if not reduced_blocks:
            return " ".join(partial_summaries[:3])

        blocks = reduced_blocks

    return blocks[0]


# --------------------------------------------------
# FULL ABSTRACTVIE PIPELINE
# --------------------------------------------------

def build_abstractive_summary(cleaned_text, chunks=None):

    if not cleaned_text or not str(cleaned_text).strip():
        return "", []

    cleaned_text = _normalize_text(cleaned_text)

    actual_chunks = chunks or chunk_document(cleaned_text)

    partial_summaries = map_abstractive_summaries(actual_chunks)

    final_summary = reduce_abstractive_summary(partial_summaries)

    return final_summary, partial_summaries