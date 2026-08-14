# LinkedIn Wordcloud

A Streamlit app that generates grayscale/colored wordcloud banner images for
LinkedIn, Twitter/X, Facebook, or custom sizes — either from a curated
word/phrase list or from free-form text that gets auto-lemmatized.
Originally prototyped in `LinkedIn_Wordcloud.ipynb`; that notebook's logic
(sizes, grayscale color function, WordCloud params) was ported into
`app.py`.

## Files

- `app.py` — the Streamlit app (the thing to run and edit).
- `requirements.txt` — streamlit, wordcloud, matplotlib, nltk.
- `LinkedIn_Wordcloud.ipynb` — original prototype notebook. Kept for
  reference; not used at runtime. (Note: this file is synced via a
  corporate MAM/Intune policy and may appear encrypted/unreadable on disk
  depending on which copy is present — if `Read` fails with a JSON parse
  error, it's the encrypted variant.)
- `wordlist.txt` — user's sample word list (comma-separated phrases,
  duplicates included on purpose to weight certain phrases larger).
- `linkedin3.txt` — private/encrypted personal input file, not used by the
  app directly.
- `background.png` — a sample generated output image.
- `images/zais_logo_mark_transparent.svg` — ZAIS Analytics logo mark, used
  for in-app branding (sidebar masthead + browser favicon).
- `gitignore` — present but named without the leading dot, so git does not
  actually treat it as `.gitignore`. Left as-is; flag to the user if this
  becomes a problem (e.g. venvs or generated PNGs getting committed).

## Running the app

The virtualenv is deliberately kept **outside** the project directory, at
`~/.venvs/linkedin_wordcloud` — see Gotchas below for why.

```bash
cd /Users/markm.zais/Documents/AI_Projects/linkedin_wordcloud
~/.venvs/linkedin_wordcloud/bin/streamlit run app.py
```

If the venv doesn't exist yet (fresh machine):

```bash
python3 -m venv ~/.venvs/linkedin_wordcloud
~/.venvs/linkedin_wordcloud/bin/pip install -r requirements.txt
~/.venvs/linkedin_wordcloud/bin/python -c "
import nltk
for pkg in ['punkt','punkt_tab','averaged_perceptron_tagger','averaged_perceptron_tagger_eng','wordnet','omw-1.4']:
    nltk.download(pkg, quiet=True)
"
```

## App architecture (current state)

Two input modes, both ultimately build a `{phrase: frequency}` dict and call
`WordCloud.generate_from_frequencies()` (not `.generate()`), so multi-word
phrases never get silently split apart:

- **Word list mode** (default): user types or uploads a `.txt` file of
  comma/newline-separated words or phrases. Each entry is used verbatim as
  one atomic unit — "machine learning" stays together with no special
  syntax needed. Repeating an entry (or having it repeat in an uploaded
  file) raises its frequency count.
- **Text mode**: user uploads/pastes free-form prose. Runs through the
  original notebook's NLTK pipeline (`word_tokenize` → POS-tag →
  `WordNetLemmatizer`, e.g. "leading" → "lead") before being turned into a
  frequency dict. Supports an optional `~` syntax (`machine~learning`) to
  lock a phrase together through the tokenizer/lemmatizer; the tilde is
  stripped and shown as a space in the final image.

Sizing uses `relative_scaling=0` (from the original notebook), meaning font
size is driven by **rank of frequency**, not the raw count — the
highest-frequency entry gets the largest size, next-highest gets slightly
smaller, etc., down to `min_font_size`. This is explained in-app via a
caption near the word-list controls.

Size presets: LinkedIn banner (1584×396), Twitter/X banner (1263×421),
Facebook cover (820×312), condensed LinkedIn (960×396, room for a profile
photo), or custom width/height. Color schemes: grayscale (notebook
default), blue-toned, or full color. Background color and font-size range
are user-adjustable.
Output renders inline with a PNG download button.

## Gotchas

- **Never put the venv inside the project directory.** This machine's NLTK
  install ships a CWE-427 import-hijack guard
  (`nltk/inisec.py`/`NLTKSafeImportFinder`) that blocks any import
  resolving to a path under the current working directory, when NLTK is an
  ancestor in the call stack. A venv's `site-packages` living inside the
  project dir trips this (`Blocked import of regex from current working
  directory...`) as soon as you `cd` into the project and run
  `streamlit run app.py` normally. Fix used here: venv lives at
  `~/.venvs/linkedin_wordcloud`, outside the repo, so it's never "under"
  cwd no matter where you launch from. Don't re-create `.venv/` inside the
  repo without remembering this.
- `nltk.download()` calls should avoid running with cwd set to the project
  dir for the same reason as above (though pure downloads without importing
  `nltk` from cwd context are generally fine — the failure mode is specifically
  the *import*, not the download).

## Session log

(Append a new dated entry each session; keep this file updated at the end
of significant work so the next session can pick up context quickly.)

- **2026-08-02/04** — Reviewed original notebook (had to get a
  non-MAM-encrypted copy from the user first). Built the initial Streamlit
  app: word-list and text input modes, 3 size presets + custom, grayscale
  color function ported from notebook, PNG download. Hit and fixed the
  NLTK CWE-427 venv-location issue (see Gotchas). Verified both input modes
  end-to-end with a headless-Chromium/Playwright smoke test.
- **2026-08-04** — Renamed title to "Wordcloud Banner App" /
  subtitle "LinkedIn | Twitter | Custom". Made Word list the default input
  mode (was Text mode), added per-option captions on the mode radio, and
  added a tooltip on the file uploader spelling out the `.txt`/UTF-8
  requirement.
- **2026-08-10** — Fixed multi-word phrases (e.g. "machine learning")
  getting split apart. Word list mode now also accepts a `.txt` file
  upload (same comma/newline format as the text box) so a curated phrase
  list can be uploaded directly without going through NLTK tokenizing.
  Text mode gained an optional `~` syntax (`machine~learning`) to lock a
  phrase together through the lemmatization pipeline; fixed a bug where
  trailing punctuation (e.g. a comma right after a locked phrase) was
  leaking into the displayed phrase. Reworded the "repeat an entry" hint to
  explain rank-based sizing instead of implying fixed importance tiers.
  Both fixes verified against the user's real `wordlist.txt` via Playwright.
- **2026-08-14** — Added a Facebook cover preset (820 x 312), positioned as
  the third option (after Twitter/X, before Condensed LinkedIn and Custom).
  Used 820 x 312, matching Facebook's actual on-page cover render size
  rather than the 851 x 315 upload spec that gets center-cropped. Updated
  the header caption to "LinkedIn | Twitter | Facebook | Custom". Verified
  preset dropdown order via Playwright against the running app.
- **2026-08-14** — Added ZAIS Analytics branding: the logo mark (dropped
  into `images/`) now shows in a small sidebar masthead ("Z" icon + "ZAIS
  ANALYTICS" text above "1. Input") and doubles as the browser-tab favicon
  via `st.set_page_config(page_icon=...)` — Streamlit 1.60 supports SVG
  file paths directly for both `st.image` and `page_icon` (confirmed by
  reading `image_utils.py`; no PNG conversion needed). Also added a
  pre-rendered example banner (`build_example_banner()`, `@st.cache_data`)
  shown in the output area before the user clicks "Generate wordcloud", so
  the initial screen isn't empty and new users see what the finished
  product looks like. Used the existing blue-toned color scheme (not
  grayscale) on a curated analytics/leadership-themed word list so it
  reads as a deliberate example rather than a placeholder. Verified both
  changes visually via a Playwright screenshot and by checking the
  rendered `<link rel="icon">` href.
