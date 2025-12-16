# -------------------------------------------------
#  Movie News Fetcher – Beautiful UI (Streamlit)
#  FIXED: Only REAL Movie & Entertainment News
# -------------------------------------------------
import streamlit as st
import requests
from datetime import datetime

# ==============================================
#            YOUR NEWS API KEY
# ==============================================
API_KEY = "c78b7e496e7c45f083c1201412c796b5"   # Replace if needed

# ==============================================
# TRUSTED MOVIE/ENTERTAINMENT SOURCES ONLY
# ==============================================
TRUSTED_DOMAINS = [
    "variety.com", "hollywoodreporter.com", "deadline.com", "indiewire.com",
    "screenrant.com", "collider.com", "empireonline.com", "rottentomatoes.com",
    "thewrap.com", "comingsoon.net", "joblo.com", "fandango.com",
    "ign.com", "cinemablend.com", "digitalspy.com", "ew.com", "thr.com",
    "bbc.co.uk/entertainment", "theguardian.com/film", "nytimes.com/movies",
    "latimes.com/entertainment", "boxofficemojo.com", "imdb.com"
]

# Negative keywords to filter OUT junk results
BLOCKED_KEYWORDS = [
    "trump", "biden", "election", "politics", "covid", "vaccine", "war", "israel",
    "palestine", "football", "cricket", "nfl", "nba", "stock market", "bitcoin"
]

# Movie-specific boost keywords
MOVIE_BOOST_KEYWORDS = "film OR movie OR cinema OR hollywood OR bollywood OR actor OR actress OR director OR trailer OR review OR box office OR oscar OR netflix OR disney OR marvel OR dc OR premiere"

# ==============================================
# PAGE CONFIG + STYLES
# ==============================================
st.set_page_config(page_title="Movie News", layout="wide")

st.markdown("""
<style>
    body {background: linear-gradient(135deg, #0d0d0d, #1a1a1a);}
    .title {font-size: 50px; text-align: center; color: #ff4d4d; font-weight: 800;}
    .news-card {
        background: rgba(255, 255, 255, 0.08); padding: 20px; border-radius: 16px;
        backdrop-filter: blur(10px); margin-bottom: 20px; transition: transform 0.2s;
        border: 1px solid rgba(255,255,255,0.15);
    }
    .news-card:hover {transform: scale(1.02);}
    .news-title {font-size: 22px; font-weight: 700; color: #ffffff; margin-bottom: 5px;}
    .news-desc {color: #d9d9d9; font-size: 16px;}
    .news-meta {color: #ff9999; font-size: 14px; margin-bottom: 10px;}
    .news-img {border-radius: 12px; width: 100%; height: 180px; object-fit: cover; margin-bottom: 10px;}
    .stButton>button {background-color: #ff4d4d; color: white; border-radius: 10px; border: none;}
    .stButton>button:hover {background-color: #ff1a1a;}
</style>
""", unsafe_allow_html=True)

# ==============================================
# TITLE
# ==============================================
st.markdown("<div class='title'>🎬 Movie News</div>", unsafe_allow_html=True)
st.write("")

# ==============================================
# SEARCH BAR (Category selection removed)
# ==============================================
query = st.text_input("🔎 Search movie, actor, director, or title:", 
                      value=st.session_state.get("query", "movies"),
                      key="search_input")

col1, col2 = st.columns([1, 4])
with col1:
    refresh = st.button("🔄 Refresh")

# ==============================================
# SMART QUERY BUILDER
# ==============================================
def build_smart_query(user_query: str) -> str:
    q = user_query.strip()
    if len(q.split()) <= 4:
        return f'"{q}" ({MOVIE_BOOST_KEYWORDS})'
    else:
        return f"{q} ({MOVIE_BOOST_KEYWORDS})"

final_query = build_smart_query(query)

# ==============================================
# FETCH + FILTER NEWS
# ==============================================
@st.cache_data(ttl=600)
def fetch_and_filter_news(q: str, page_size=30):
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": q,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": page_size,
        "apiKey": API_KEY,
    }
    try:
        r = requests.get(url, params=params, timeout=15)
        data = r.json()
        if data.get("status") != "ok":
            st.error(f"API Error: {data.get('message')}")
            return []

        articles = data["articles"]
        filtered = []

        for a in articles:
            title = (a.get("title") or "").lower()
            desc = (a.get("description") or "").lower()
            url = a.get("url", "")

            # 1. Block junk
            if any(bad in title or bad in desc for bad in BLOCKED_KEYWORDS):
                continue

            # 2. Trusted domains
            if any(domain in url.lower() for domain in TRUSTED_DOMAINS):
                filtered.append(a)
                continue

            # 3. Movie-related signals
            movie_signals = sum(
                1 for word in [
                    "movie", "film", "actor", "actress", "director", "trailer",
                    "review", "premiere", "oscar", "box office", "cinema",
                    "hollywood", "bollywood"
                ]
                if word in title or word in desc
            )
            if movie_signals >= 2:
                filtered.append(a)

        return filtered[:20]

    except Exception as e:
        st.error(f"Request failed: {e}")
        return []

# ==============================================
# LOAD NEWS
# ==============================================
if refresh or "articles" not in st.session_state or st.session_state.get("last_query") != query:
    with st.spinner(f"Fetching real movie news for **{query}**... 🍿"):
        clean_articles = fetch_and_filter_news(final_query)
        st.session_state.articles = clean_articles
        st.session_state.last_query = query

articles = st.session_state.articles

# ==============================================
# DISPLAY RESULTS
# ==============================================
st.write("")
if articles:
    st.success(f"🎉 Found {len(articles)} genuine movie/entertainment articles for **{query}**")
else:
    st.warning("😔 No movie news found. Try searching for a specific title, actor, or 'Trailers'!")

for a in articles:
    title = a.get("title", "No title")
    desc = a.get("description", "No description.")
    img = a.get("urlToImage")
    src = a["source"]["name"] if a.get("source") else "Unknown"
    pub = a.get("publishedAt", "")[:19]
    url = a.get("url", "#")

    try:
        pretty_date = datetime.strptime(pub.split("Z")[0], "%Y-%m-%dT%H:%M:%S").strftime("%b %d, %Y • %I:%M %p")
    except:
        pretty_date = pub.split("T")[0] if pub else "Recently"

    st.markdown("<div class='news-card'>", unsafe_allow_html=True)

    if img and "placeholder" not in img:
        st.image(img, use_column_width=True)

    st.markdown(f"<div class='news-title'>{title}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='news-meta'>{src} • {pretty_date}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='news-desc'>{desc}</div>", unsafe_allow_html=True)
    st.markdown(f"[🔗 Read Full Article]({url})")

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("---")

st.caption("Powered by NewsAPI • Only verified movie & entertainment sources")
