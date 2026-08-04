"""LinkedIn / Twitter wordcloud banner generator (Streamlit app)."""

import io
import random
from collections import Counter

import matplotlib.pyplot as plt
import nltk
import streamlit as st
from wordcloud import WordCloud, STOPWORDS

SIZE_PRESETS = {
    "LinkedIn banner (1584 x 396)": (1584, 396),
    "Twitter/X banner (1263 x 421)": (1263, 421),
    "Condensed LinkedIn (960 x 396)": (960, 396),
}

NLTK_PACKAGES = [
    ("tokenizers/punkt", "punkt"),
    ("tokenizers/punkt_tab", "punkt_tab"),
    ("taggers/averaged_perceptron_tagger", "averaged_perceptron_tagger"),
    ("taggers/averaged_perceptron_tagger_eng", "averaged_perceptron_tagger_eng"),
    ("corpora/wordnet", "wordnet"),
    ("corpora/omw-1.4", "omw-1.4"),
]


@st.cache_resource(show_spinner="Preparing NLTK data...")
def ensure_nltk_data():
    for find_path, package in NLTK_PACKAGES:
        try:
            nltk.data.find(find_path)
        except LookupError:
            nltk.download(package, quiet=True)


def lemmatize_text(text: str) -> str:
    from nltk.stem import WordNetLemmatizer
    from nltk.tokenize import word_tokenize

    words = word_tokenize(text.replace("\n", " "))
    tags = nltk.pos_tag(words)
    lemmatizer = WordNetLemmatizer()

    lemmatized = []
    for word, tag in tags:
        if tag.startswith("VB"):
            lemmatized.append(lemmatizer.lemmatize(word, "v"))
        else:
            lemmatized.append(lemmatizer.lemmatize(word))
    return " ".join(lemmatized)


def parse_word_list_frequencies(raw: str, filter_stopwords: bool) -> dict:
    """Each comma/newline-separated entry is kept as one atomic phrase, so
    multi-word entries like 'machine learning' stay together instead of
    being split into separate words."""
    phrases = [p.strip() for line in raw.splitlines() for p in line.split(",")]
    phrases = [p for p in phrases if p]
    if filter_stopwords:
        phrases = [p for p in phrases if p.lower() not in STOPWORDS]
    return dict(Counter(phrases))


def grayscale_color_func(word, font_size, position, orientation, random_state=None, **kwargs):
    return f"hsl(0, 0%, {random.randint(60, 100)}%)"


def blue_color_func(word, font_size, position, orientation, random_state=None, **kwargs):
    return f"hsl(210, 70%, {random.randint(45, 85)}%)"


COLOR_FUNCS = {
    "Grayscale": grayscale_color_func,
    "Blue-toned": blue_color_func,
    "Full color (random)": None,
}


def generate_wordcloud(
    text: str,
    width: int,
    height: int,
    background_color: str,
    filter_stopwords: bool,
    min_font_size: int,
    max_font_size: int,
    seed: int,
) -> WordCloud:
    kwargs = dict(
        width=width,
        height=height,
        background_color=background_color,
        min_font_size=min_font_size,
        max_font_size=max_font_size,
        repeat=True,
        relative_scaling=0,
        normalize_plurals=False,
        min_word_length=1,
        random_state=seed,
    )
    if not filter_stopwords:
        kwargs["stopwords"] = set()
    return WordCloud(**kwargs).generate(text)


def generate_wordcloud_from_frequencies(
    frequencies: dict,
    width: int,
    height: int,
    background_color: str,
    min_font_size: int,
    max_font_size: int,
    seed: int,
) -> WordCloud:
    wc = WordCloud(
        width=width,
        height=height,
        background_color=background_color,
        min_font_size=min_font_size,
        max_font_size=max_font_size,
        repeat=True,
        relative_scaling=0,
        normalize_plurals=False,
        min_word_length=1,
        random_state=seed,
    )
    return wc.generate_from_frequencies(frequencies)


def render_png(wc: WordCloud, width: int, height: int, color_func, seed: int) -> bytes:
    dpi = 100
    fig = plt.figure(figsize=(width / dpi, height / dpi), dpi=dpi, facecolor=None)
    image = wc.recolor(color_func=color_func, random_state=seed) if color_func else wc
    plt.imshow(image, interpolation="bilinear")
    plt.axis("off")
    plt.tight_layout(pad=0)

    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", pad_inches=0)
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def main():
    st.set_page_config(page_title="Wordcloud Banner Generator", layout="wide")
    ensure_nltk_data()

    st.title("LinkedIn / Twitter Wordcloud Banner Generator")

    with st.sidebar:
        st.header("1. Input")
        input_mode = st.radio(
            "Source of words",
            ["Text (file upload or paste)", "Word list"],
            help=(
                "Text mode runs your content through tokenizing, POS-tagging and "
                "lemmatizing (e.g. 'leading' -> 'lead'). Word list mode uses your "
                "words exactly as typed, with no processing."
            ),
        )

        raw_text = ""
        pasted_words = ""
        filter_stopwords = True
        if input_mode == "Text (file upload or paste)":
            uploaded = st.file_uploader("Upload a .txt file", type=["txt"])
            pasted = st.text_area("...or paste text here", height=150)
            if uploaded is not None:
                raw_text = uploaded.read().decode("utf-8", errors="ignore")
            elif pasted:
                raw_text = pasted
        else:
            pasted_words = st.text_area(
                "Enter words or phrases, separated by commas or new lines. "
                "Keep a multi-word phrase together (e.g. 'machine learning') "
                "by not putting a comma or line break inside it. "
                "Repeat an entry to make it larger.",
                height=150,
                placeholder="machine learning\ndata science\nstrategy, growth, mentoring",
            )
            filter_stopwords = st.checkbox(
                "Filter common stopwords (the, and, a...)", value=False
            )

        st.header("2. Size")
        size_choice = st.selectbox("Preset", list(SIZE_PRESETS.keys()) + ["Custom"])
        if size_choice == "Custom":
            width = st.number_input("Width (px)", min_value=100, max_value=4000, value=1200, step=10)
            height = st.number_input("Height (px)", min_value=100, max_value=4000, value=400, step=10)
        else:
            width, height = SIZE_PRESETS[size_choice]
            st.caption(f"{width} x {height} px")

        st.header("3. Style")
        color_choice = st.selectbox("Color scheme", list(COLOR_FUNCS.keys()))
        background_color = st.color_picker("Background color", "#000000")
        min_font_size, max_font_size = st.slider(
            "Font size range (px)", min_value=5, max_value=200, value=(20, 50)
        )
        seed = st.number_input("Random seed (layout)", min_value=0, max_value=9999, value=34)

        generate = st.button("Generate wordcloud", type="primary", use_container_width=True)

    if generate:
        is_word_list = input_mode != "Text (file upload or paste)"
        if is_word_list:
            frequencies = parse_word_list_frequencies(pasted_words, filter_stopwords)
            if not frequencies:
                st.warning("Add a word list first.")
                return
        else:
            text = raw_text.strip()
            if not text:
                st.warning("Add some text first.")
                return

        with st.spinner("Generating..."):
            if is_word_list:
                wc = generate_wordcloud_from_frequencies(
                    frequencies=frequencies,
                    width=int(width),
                    height=int(height),
                    background_color=background_color,
                    min_font_size=min_font_size,
                    max_font_size=max_font_size,
                    seed=int(seed),
                )
            else:
                text = lemmatize_text(text)
                wc = generate_wordcloud(
                    text=text,
                    width=int(width),
                    height=int(height),
                    background_color=background_color,
                    filter_stopwords=filter_stopwords,
                    min_font_size=min_font_size,
                    max_font_size=max_font_size,
                    seed=int(seed),
                )
            png_bytes = render_png(
                wc, int(width), int(height), COLOR_FUNCS[color_choice], int(seed)
            )

        st.image(png_bytes, use_container_width=True)
        st.download_button(
            "Download PNG",
            data=png_bytes,
            file_name="wordcloud.png",
            mime="image/png",
        )
    else:
        st.info("Fill in the sidebar and click **Generate wordcloud** to get started.")


if __name__ == "__main__":
    main()
