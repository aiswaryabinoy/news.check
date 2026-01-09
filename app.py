import streamlit as st
import requests
import torch
import spacy
import pytextrank
import re


from transformers import PegasusTokenizer, PegasusForConditionalGeneration
from api import API_KEY

# ==============================
# CONFIG
# ==============================
NEWS_API_URL = "https://gnews.io/api/v4/top-headlines"
GNEWS_SEARCH_URL = "https://gnews.io/api/v4/search"

COUNTRY = "us"
MAX_ARTICLES = 5

PARAPHRASE_MODEL = "tuner007/pegasus_paraphrase"
SUMMARY_MODEL = "google/pegasus-cnn_dailymail"

# ==============================
# Load Models
# ==============================
@st.cache_resource
def load_models():
    para_tokenizer = PegasusTokenizer.from_pretrained(PARAPHRASE_MODEL)
    para_model = PegasusForConditionalGeneration.from_pretrained(PARAPHRASE_MODEL)

    sum_tokenizer = PegasusTokenizer.from_pretrained(SUMMARY_MODEL)
    sum_model = PegasusForConditionalGeneration.from_pretrained(SUMMARY_MODEL)

    nlp = spacy.load("en_core_web_sm")
    nlp.add_pipe("textrank")

    return para_tokenizer, para_model, sum_tokenizer, sum_model, nlp


para_tokenizer, para_model, sum_tokenizer, sum_model, nlp = load_models()

# ==============================
# TextRank Ranking (3rd best)
# ==============================
def rank_with_textrank(original, candidates, rank=3):
    if not candidates:
        return original

    doc = nlp(original)
    key_terms = {p.text.lower() for p in doc._.phrases[:10]}

    scored = []
    for text in candidates:
        doc_c = nlp(text)
        cand_terms = {p.text.lower() for p in doc_c._.phrases}
        scored.append((text, len(key_terms & cand_terms)))

    scored.sort(key=lambda x: x[1], reverse=True)
    index = min(rank - 1, len(scored) - 1)
    return scored[index][0]

# ==============================
# Headline Paraphrase
# ==============================
def paraphrase_headline(text):
    if not text or len(text.split()) < 4:
        return text

    inputs = para_tokenizer(text, return_tensors="pt", truncation=True)

    with torch.no_grad():
        outputs = para_model.generate(
            **inputs,
            max_length=40,
            num_beams=10,
            num_return_sequences=5,
            temperature=1.3,
            no_repeat_ngram_size=2
        )

    paraphrases = list({
        para_tokenizer.decode(o, skip_special_tokens=True)
        for o in outputs
    })

    return rank_with_textrank(text, paraphrases, rank=3)

# ==============================
# Article Summarization
# ==============================
def summarize_article(text):
    if not text or len(text.split()) < 30:
        return text

    text = text.replace("...", "").replace("[", "").replace("chars]", "")
    text = re.sub(r"WARNING:.*", "", text)

    min_len = max(60, int(len(text.split()) * 0.6))

    inputs = sum_tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=512
    )

    with torch.no_grad():
        summary_ids = sum_model.generate(
            **inputs,
            max_length=220,
            min_length=min_len,
            num_beams=5,
            no_repeat_ngram_size=3,
            early_stopping=True
        )

    summary = sum_tokenizer.decode(summary_ids[0], skip_special_tokens=True)
    summary = summary.replace("<n>", "")

    return summary


# ==============================
# Fetch News (Top Headlines)
# ==============================
def fetch_latest_news():
    params = {
        "token": API_KEY,
        "lang": "en",
        "country": COUNTRY,
        "max": MAX_ARTICLES
    }

    r = requests.get(NEWS_API_URL, params=params)
    r.raise_for_status()
    return r.json()["articles"]

# ==============================
# Fetch News by Search / Category
# ==============================
def search_news(query):
    params = {
        "q": query,
        "lang": "en",
        "country": COUNTRY,
        "max": MAX_ARTICLES,
        "token": API_KEY
    }

    r = requests.get(GNEWS_SEARCH_URL, params=params)
    r.raise_for_status()
    return r.json()["articles"]

# ==============================
# Streamlit UI
# ==============================
st.set_page_config(page_title="AI News Reader", layout="wide")

st.title("📰 AI News Reader")

# 🔍 Search + Category
search_query = st.text_input("Search news ")

category = st.selectbox(
    "Select Category",
    ["Top Headlines", "Local News", "Movies", "International", "Sports", "Politics"]
)

if st.button("Load News"):
    with st.spinner("Fetching and summarizing news..."):

        if search_query:
            articles = search_news(search_query)

        elif category == "Local News":
            articles = search_news("Kerala")

        elif category == "Movies":
            articles = search_news("movies OR cinema OR film")

        elif category == "International":
            articles = search_news("international world")

        elif category == "Sports":
            articles = search_news("sports")  

        elif category == "Politics":
            articles = search_news("politics")      

        else:
            articles = fetch_latest_news()

    for i, article in enumerate(articles, 1):
        title = article.get("title", "")
        content = article.get("content") or article.get("description") or ""
        url = article.get("url")
        source = article.get("source", {}).get("name")

        rewritten_title = paraphrase_headline(title)
        rewritten_summary = summarize_article(content)

        st.subheader(f"{i}. {rewritten_title}")
        st.write(rewritten_summary)

        st.caption(f"Source: {source}")
        st.markdown(f"[🔗 Read original article]({url})")

        st.divider()
