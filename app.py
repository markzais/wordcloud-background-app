"""LinkedIn / Twitter wordcloud banner generator (Streamlit app)."""

import base64
import io
import random
import re
import string
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import nltk
import streamlit as st
from wordcloud import WordCloud, STOPWORDS

APP_DIR = Path(__file__).parent
LOGO_PATH = APP_DIR / "images" / "zais_logo_mark_transparent.svg"
GOLD = "#D4AF37"  # matches the "AI" emphasis color on zaisanalytics.com

PHRASE_LOCK_PATTERN = re.compile(r"[^\s~]+(?:~[^\s~]+)+")

SIZE_PRESETS = {
    "LinkedIn banner (1584 x 396)": (1584, 396),
    "Twitter/X banner (1263 x 421)": (1263, 421),
    "Facebook cover (820 x 312)": (820, 312),
    "Condensed LinkedIn (960 x 396)": (960, 396),
}

EXAMPLE_FREQUENCIES = {
    "data science": 6,
    "machine learning": 5,
    "analytics": 5,
    "strategy": 4,
    "leadership": 4,
    "innovation": 3,
    "growth": 3,
    "insight": 3,
    "artificial intelligence": 2,
    "optimization": 2,
    "mentorship": 2,
    "storytelling": 1,
    "impact": 1,
    "collaboration": 1,
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


def lock_phrases(text: str) -> tuple[str, dict]:
    """Replace ~-joined phrases (e.g. 'machine~learning') with a placeholder
    token that survives tokenizing/lemmatizing intact, so the phrase can be
    restored as a single unit afterward instead of being split apart."""
    mapping = {}

    def replace(match: re.Match) -> str:
        phrase = match.group(0)
        placeholder = f"phraselock{len(mapping)}"
        mapping[placeholder] = phrase.replace("~", " ").strip(string.punctuation + " ")
        return placeholder

    return PHRASE_LOCK_PATTERN.sub(replace, text), mapping


def normalize_case(word: str) -> str:
    return word if (word.isupper() and len(word) > 1) else word.lower()


def parse_word_list_frequencies(raw: str, filter_stopwords: bool) -> dict:
    """Each comma/newline-separated entry is kept as one atomic phrase, so
    multi-word entries like 'machine learning' stay together instead of
    being split into separate words."""
    phrases = [p.strip() for line in raw.splitlines() for p in line.split(",")]
    phrases = [p for p in phrases if p]
    if filter_stopwords:
        phrases = [p for p in phrases if p.lower() not in STOPWORDS]
    return dict(Counter(phrases))


def build_frequencies_from_text(text: str, filter_stopwords: bool) -> dict:
    """Tokenize/POS-tag/lemmatize free-form text into a word-frequency dict,
    keeping any ~-joined phrases together as single entries."""
    locked_text, mapping = lock_phrases(text)
    lemmatized = lemmatize_text(locked_text)

    freq: Counter = Counter()
    for token in lemmatized.split():
        if token in mapping:
            word = mapping[token]
        else:
            word = normalize_case(token.strip(string.punctuation))
        if not word:
            continue
        if filter_stopwords and word.lower() in STOPWORDS:
            continue
        freq[word] += 1
    return dict(freq)


def grayscale_color_func(word, font_size, position, orientation, random_state=None, **kwargs):
    return f"hsl(0, 0%, {random.randint(60, 100)}%)"


def blue_color_func(word, font_size, position, orientation, random_state=None, **kwargs):
    return f"hsl(210, 70%, {random.randint(45, 85)}%)"


COLOR_FUNCS = {
    "Grayscale": grayscale_color_func,
    "Blue-toned": blue_color_func,
    "Full color (random)": None,
}


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


@st.cache_data(show_spinner=False)
def build_example_banner() -> bytes:
    """Pre-render a sample banner (blue-toned, not grayscale) shown before the
    user generates their own, so the output area isn't just empty space."""
    width, height = SIZE_PRESETS["LinkedIn banner (1584 x 396)"]
    wc = generate_wordcloud_from_frequencies(
        frequencies=EXAMPLE_FREQUENCIES,
        width=width,
        height=height,
        background_color="#000000",
        min_font_size=10,
        max_font_size=45,
        seed=7,
    )
    return render_png(wc, width, height, blue_color_func, seed=7)


def render_logo_badge():
    """A ZAIS Analytics watermark fixed to the top-right of the viewport, so
    it stays put instead of scrolling away with the sidebar or main content.
    'AI' is picked out in gold to match the emphasis used on zaisanalytics.com.
    """
    logo_b64 = base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
    st.markdown(
        f"""
        <style>
        .zais-badge {{
            position: fixed;
            top: 0.6rem;
            right: 8.5rem;
            z-index: 999999;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            pointer-events: none;
        }}
        .zais-badge img {{
            width: 34px;
            height: 34px;
        }}
        .zais-badge .zais-word {{
            font-weight: 700;
            font-size: 1.05rem;
            letter-spacing: 0.02em;
            line-height: 1.15;
        }}
        .zais-badge .zais-word .ai {{
            color: {GOLD};
        }}
        .zais-badge .zais-sub {{
            display: block;
            font-weight: 600;
            font-size: 0.55rem;
            letter-spacing: 0.18em;
            color: {GOLD};
        }}
        @media (max-width: 900px) {{
            .zais-badge {{ display: none; }}
        }}
        </style>
        <div class="zais-badge">
            <img src="data:image/svg+xml;base64,{logo_b64}" />
            <span>
                <span class="zais-word">Z<span class="ai">AI</span>S</span>
                <span class="zais-sub">ANALYTICS</span>
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main():
    st.set_page_config(
        page_title="Wordcloud Banner App", page_icon=str(LOGO_PATH), layout="wide"
    )
    ensure_nltk_data()
    render_logo_badge()

    st.title("Wordcloud Banner App")
    st.caption("LinkedIn | Twitter | Facebook | Custom")

    with st.sidebar:
        st.header("1. Input")
        input_mode = st.radio(
            "Source of words",
            ["Word list", "Text (file upload or paste)"],
            captions=[
                "Type or paste individual words/phrases, used exactly as entered.",
                "Upload a .txt file or paste free-form writing to auto-extract words from.",
            ],
        )

        raw_text = ""
        raw_word_list = ""
        filter_stopwords = True
        if input_mode == "Word list":
            uploaded_list = st.file_uploader(
                "Upload a .txt file (optional)",
                type=["txt"],
                help=(
                    "Plain-text (.txt) file only, UTF-8 encoded, formatted the same way "
                    "as the box below: words/phrases separated by commas or new lines "
                    "(e.g. 'data science, machine learning, leadership'). Each entry stays "
                    "together exactly as written — no special syntax needed. If a file is "
                    "uploaded, it's used instead of the box below."
                ),
            )
            pasted_words = st.text_area(
                "...or type/paste words or phrases here, separated by commas or new lines",
                height=150,
                placeholder="machine learning\ndata science\nstrategy, growth, mentoring",
                help=(
                    "Keep a multi-word phrase together (e.g. 'machine learning') by not "
                    "putting a comma or line break inside it."
                ),
            )
            if uploaded_list is not None:
                raw_word_list = uploaded_list.read().decode("utf-8", errors="ignore")
                st.caption(f"Using uploaded file: {uploaded_list.name}")
            else:
                raw_word_list = pasted_words
            filter_stopwords = st.checkbox(
                "Filter common stopwords (the, and, a...)", value=False
            )
            st.caption(
                "Size is based on rank by frequency, not fixed importance tiers: "
                "repeating an entry (or uploading a file where it appears more than "
                "once) increases its count, which raises its rank and makes it larger "
                "— up to the max font size set below."
            )
        else:
            uploaded = st.file_uploader(
                "Upload a .txt file",
                type=["txt"],
                help=(
                    "Plain-text (.txt) file only, UTF-8 encoded — export or save "
                    "your content as plain text first (not .docx, .pdf, or rich text). "
                    "Any prose works: the app will tokenize and lemmatize it "
                    "automatically (e.g. 'leading' becomes 'lead')."
                ),
            )
            pasted = st.text_area(
                "...or paste text here",
                height=150,
                help="Free-form writing, not individual words. Processed the same way as an uploaded file.",
            )
            st.caption(
                "To keep a multi-word phrase together (e.g. 'machine learning'), join "
                "the words with a tilde in your text: machine~learning — it will still "
                "display as 'machine learning' in the wordcloud."
            )
            if uploaded is not None:
                raw_text = uploaded.read().decode("utf-8", errors="ignore")
            elif pasted:
                raw_text = pasted

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
        is_word_list = input_mode == "Word list"
        if is_word_list:
            frequencies = parse_word_list_frequencies(raw_word_list, filter_stopwords)
            if not frequencies:
                st.warning("Add a word list first.")
                return
        else:
            text = raw_text.strip()
            if not text:
                st.warning("Add some text first.")
                return
            frequencies = build_frequencies_from_text(text, filter_stopwords)
            if not frequencies:
                st.warning("No usable words found in that text.")
                return

        with st.spinner("Generating..."):
            wc = generate_wordcloud_from_frequencies(
                frequencies=frequencies,
                width=int(width),
                height=int(height),
                background_color=background_color,
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
        st.caption("Example output — here's what a generated banner looks like:")
        st.image(build_example_banner(), use_container_width=True)


if __name__ == "__main__":
    main()
