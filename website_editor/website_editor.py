import html
import re
import tempfile
import webbrowser
import tkinter as tk

from pathlib import Path
from tkinter import ttk, filedialog, messagebox
from urllib.parse import urlparse


SITE_NAME = "Ali Akbarzade"
GITHUB_URL = "https://github.com/aliakbarzadegog2-ui"

HERO_TEXT = (
    "Curious about almost everything. I build, experiment, break things, "
    "fix them, and occasionally create something completely unnecessary. :)"
)

DEFAULT_ABOUT = HERO_TEXT

DEFAULT_SKILLS = """🐧 | Linux | Systems, terminals, servers and experiments.
🐍 | Python | Automation, tools, experiments and projects.
🤖 | AI | AI tools, agents and computer-use experiments.
🎮 | Game Dev | Building games and weird interactive ideas.
⚙️ | Automation | Connecting tools and making computers do the boring stuff.
🧩 | Minecraft | Commands, redstone, experiments and questionable ideas."""

DEFAULT_PROJECTS = """🌌 | Universe Creator | A game where you don't play the universe — you create it. | https://github.com/aliakbarzadegog2-ui
🎮 | Eloria | An experimental game project built with Godot. | https://github.com/aliakbarzadegog2-ui
🤖 | AI Experiments | Experiments with AI agents, automation and computer-use systems. | https://github.com/aliakbarzadegog2-ui"""


# =========================================================
# Custom text commands
# =========================================================

COMMAND_RE = re.compile(
    r"/nl|/link\(([^)]*)\)|/c\(([^)]*)\)",
    re.IGNORECASE,
)


def escape(value):
    return html.escape(str(value), quote=True)


def safe_url(value):
    value = value.strip()

    if not value:
        raise ValueError("A link URL cannot be empty.")

    parsed = urlparse(value)

    if parsed.scheme:
        if parsed.scheme.lower() not in ("https", "http", "mailto"):
            raise ValueError(
                f"Unsupported URL scheme:\n{value}\n\n"
                "Only http://, https:// and mailto: are allowed."
            )
        return value

    if value.startswith(("/", "#")):
        return value

    if re.fullmatch(r"[\w.-]+\.[A-Za-z]{2,}([/:?#].*)?", value):
        return "https://" + value

    raise ValueError(f"Invalid URL:\n{value}")


def safe_color(value):
    """Validate colors before using them in generated HTML."""
    value = value.strip()

    if re.fullmatch(
        r"#[0-9a-fA-F]{3,4}|#[0-9a-fA-F]{6}|#[0-9a-fA-F]{8}",
        value,
    ):
        return value

    if re.fullmatch(r"[A-Za-z]{1,30}", value):
        return value

    if re.fullmatch(
        r"(?i)(?:rgb|rgba|hsl|hsla)\(\s*[0-9.%+\-\s,]+\)",
        value,
    ):
        return value

    raise ValueError(
        f"Invalid color: {value}\n\n"
        "Examples: red, cyan, #58a6ff, rgb(88, 166, 255)"
    )


def render_markup(raw, allow_links=True):
    """
    Commands:
        /nl                    New line
        Word/link(URL)         Make the previous word clickable
        Word/c(COLOR)          Color the previous word

    Prefix syntax is supported too:
        /c(red)Word
        /link(https://example.com)Word

    When a command has no previous word on the current line,
    it applies to the next word instead.
    """

    raw = str(raw).replace("\r\n", "\n").replace("\r", "\n")

    chars = []
    pending_color = None
    pending_link = None

    def append_plain(chunk):
        nonlocal pending_color, pending_link

        i = 0

        while i < len(chunk):
            ch = chunk[i]

            if ch == "\n":
                chars.append({
                    "ch": "\n",
                    "color": None,
                    "url": None,
                })
                i += 1
                continue

            if ch.isspace():
                chars.append({
                    "ch": ch,
                    "color": None,
                    "url": None,
                })
                i += 1
                continue

            # Read the next word.
            j = i

            while j < len(chunk) and not chunk[j].isspace():
                j += 1

            word = chunk[i:j]

            for letter in word:
                chars.append({
                    "ch": letter,
                    "color": pending_color,
                    "url": pending_link,
                })

            pending_color = None
            pending_link = None
            i = j

    def apply_to_previous_word(attribute, value):
        i = len(chars) - 1

        # Ignore spaces immediately before a command.
        while i >= 0 and chars[i]["ch"] in (
            " ", "\t", "\f", "\v"
        ):
            i -= 1

        # Do not cross a line break.
        if i < 0 or chars[i]["ch"] == "\n":
            return False

        end = i + 1

        while i >= 0 and not chars[i]["ch"].isspace():
            i -= 1

        start = i + 1

        if start >= end:
            return False

        for item in chars[start:end]:
            item[attribute] = value

        return True

    position = 0

    for match in COMMAND_RE.finditer(raw):
        append_plain(raw[position:match.start()])

        command = match.group(0)

        if command.lower() == "/nl":
            chars.append({
                "ch": "\n",
                "color": None,
                "url": None,
            })

        elif command.lower().startswith("/link("):
            url = safe_url(match.group(1))

            if allow_links:
                if not apply_to_previous_word("url", url):
                    pending_link = url

        else:
            color = safe_color(match.group(2))

            if not apply_to_previous_word("color", color):
                pending_color = color

        position = match.end()

    append_plain(raw[position:])

    # Convert the styled text runs into HTML.
    output = []
    run_text = []
    run_color = None
    run_url = None
    has_run = False

    def flush_run():
        nonlocal run_text, run_color, run_url, has_run

        if not has_run:
            return

        content = escape("".join(run_text))

        if run_color:
            content = (
                f'<span style="color: {escape(run_color)}">'
                f'{content}</span>'
            )

        if run_url and allow_links:
            content = (
                f'<a href="{escape(run_url)}" target="_blank" '
                f'rel="noopener noreferrer">{content}</a>'
            )

        output.append(content)

        run_text = []
        run_color = None
        run_url = None
        has_run = False

    for item in chars:
        ch = item["ch"]

        if ch == "\n":
            flush_run()
            output.append("<br>\n")
            continue

        color = item["color"]
        url = item["url"] if allow_links else None

        if has_run and (
            color != run_color or url != run_url
        ):
            flush_run()

        if not has_run:
            run_color = color
            run_url = url
            has_run = True

        run_text.append(ch)

    flush_run()

    return "".join(output)


# =========================================================
# Content parsing
# =========================================================

def parse_skills(raw):
    items = []

    for line_number, line in enumerate(raw.splitlines(), start=1):
        if not line.strip():
            continue

        parts = [part.strip() for part in line.split("|", 2)]

        if len(parts) != 3 or not all(parts):
            raise ValueError(
                f"Skills: line {line_number} is invalid.\n\n"
                "Expected format:\n"
                "emoji | title | description"
            )

        items.append(parts)

    return items


def parse_projects(raw):
    items = []

    for line_number, line in enumerate(raw.splitlines(), start=1):
        if not line.strip():
            continue

        parts = [part.strip() for part in line.split("|", 3)]

        if len(parts) != 4 or not all(parts):
            raise ValueError(
                f"Projects: line {line_number} is invalid.\n\n"
                "Expected format:\n"
                "emoji | title | description | URL"
            )

        emoji, title, description, url = parts

        items.append((
            emoji,
            title,
            description,
            safe_url(url),
        ))

    return items


def parse_custom_sections(raw):
    items = []

    for line_number, line in enumerate(raw.splitlines(), start=1):
        if not line.strip():
            continue

        parts = line.split("|", 1)

        if len(parts) != 2:
            raise ValueError(
                f"Add Sections: line {line_number} is invalid.\n\n"
                "Expected format:\n"
                "Title | Content"
            )

        title = parts[0].strip()
        content = parts[1].strip()

        if not title or not content:
            raise ValueError(
                f"Add Sections: line {line_number} needs "
                "both a title and content."
            )

        items.append((title, content))

    return items


# =========================================================
# HTML generation
# =========================================================

def make_html(about, skills_raw, projects_raw, custom_raw):
    skills = parse_skills(skills_raw)
    projects = parse_projects(projects_raw)
    custom_sections = parse_custom_sections(custom_raw)

    skill_cards = []

    for emoji, title, description in skills:
        skill_cards.append(f"""
            <article class="card">
                <div class="card-icon">{render_markup(emoji)}</div>
                <h3>{render_markup(title)}</h3>
                <p>{render_markup(description)}</p>
            </article>
        """)

    if not skill_cards:
        skill_cards.append(
            '<p class="text-block">No skills added yet.</p>'
        )

    project_cards = []

    for emoji, title, description, url in projects:
        project_cards.append(f"""
            <article class="card project-card">
                <div class="card-icon">{render_markup(emoji)}</div>
                <h3>{render_markup(title)}</h3>
                <p>{render_markup(description)}</p>
                <a class="project-link"
                   href="{escape(url)}"
                   target="_blank"
                   rel="noopener noreferrer">View project ↗</a>
            </article>
        """)

    if not project_cards:
        project_cards.append(
            '<p class="text-block">No projects added yet.</p>'
        )

    extra_nav = []
    extra_content = []

    for number, (title, content) in enumerate(
        custom_sections, start=1
    ):
        section_id = f"extra-section-{number}"

        # No nested links in navigation, but colors still work.
        extra_nav.append(
            f'<a href="#{section_id}">'
            f'{render_markup(title, allow_links=False)}</a>'
        )

        extra_content.append(f"""
            <section class="section extra-section"
                     id="{section_id}">
                <h2>{render_markup(title)}</h2>
                <p class="text-block">{render_markup(content)}</p>
            </section>
        """)

    navigation = "\n".join([
        '<a href="#about">About</a>',
        '<a href="#skills">Skills</a>',
        '<a href="#projects">Projects</a>',
        *extra_nav,
    ])

    template = r'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ali Akbarzade</title>
    <meta name="description" content="Personal website and projects of Ali Akbarzade.">

    <style>
        :root {
            color-scheme: dark;
            --bg: #080b10;
            --panel: #0d1117;
            --border: #1c2633;
            --text: #e6edf3;
            --muted: #9daab8;
            --blue: #58a6ff;
        }

        * { box-sizing: border-box; }

        html {
            scroll-behavior: smooth;
            scroll-padding-top: 90px;
        }

        body {
            margin: 0;
            background: var(--bg);
            color: var(--text);
            font-family: system-ui, -apple-system, BlinkMacSystemFont,
                         "Segoe UI", sans-serif;
            line-height: 1.7;
        }

        a {
            color: var(--blue);
            text-decoration: none;
        }

        a:hover { text-decoration: underline; }

        .navbar {
            position: sticky;
            top: 0;
            z-index: 10;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 24px;
            padding: 16px max(24px, calc((100% - 1100px) / 2));
            border-bottom: 1px solid var(--border);
            background: rgba(8, 11, 16, 0.88);
            backdrop-filter: blur(14px);
        }

        .logo {
            color: var(--text);
            font-size: 22px;
            font-weight: 800;
            white-space: nowrap;
        }

        .logo span, h1 span, h2 span { color: var(--blue); }

        .nav-links {
            display: flex;
            flex-wrap: wrap;
            justify-content: flex-end;
            gap: 20px;
        }

        .nav-links a {
            color: var(--muted);
            font-size: 14px;
        }

        .nav-links a:hover { color: var(--blue); }

        .container {
            width: min(100% - 40px, 1000px);
            margin: 0 auto;
        }

        .hero {
            position: relative;
            isolation: isolate;
            padding: 100px 0 90px;
        }

        .hero::before {
            position: absolute;
            z-index: -1;
            top: 25px;
            left: -100px;
            width: 400px;
            height: 300px;
            border-radius: 50%;
            background: rgba(56, 139, 253, 0.10);
            filter: blur(90px);
            content: "";
            pointer-events: none;
        }

        .terminal {
            display: inline-block;
            margin-bottom: 24px;
            padding: 9px 14px;
            border: 1px solid var(--border);
            border-radius: 7px;
            background: var(--panel);
            color: var(--muted);
            font-family: monospace;
            font-size: 14px;
        }

        .terminal .prompt { color: #7ee787; }
        .terminal .arrow { color: var(--blue); }

        h1 {
            margin: 0 0 18px;
            font-size: clamp(44px, 8vw, 76px);
            line-height: 1.12;
            letter-spacing: -3px;
        }

        .hero-copy {
            max-width: 680px;
            color: var(--muted);
            font-size: 18px;
        }

        .buttons {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            margin-top: 30px;
        }

        .button {
            display: inline-block;
            padding: 10px 17px;
            border: 1px solid var(--border);
            border-radius: 7px;
            color: var(--text);
            font-weight: 650;
            transition: border-color 0.2s, transform 0.2s;
        }

        .button:hover {
            border-color: var(--blue);
            text-decoration: none;
            transform: translateY(-2px);
        }

        .button.primary {
            border-color: var(--blue);
            background: var(--blue);
            color: #08111e;
        }

        .section {
            padding: 48px 0 64px;
            border-top: 1px solid var(--border);
        }

        h2 {
            margin: 0 0 24px;
            font-size: 30px;
            letter-spacing: -0.8px;
        }

        h3 {
            margin: 8px 0;
            font-size: 18px;
        }

        .text-block {
            color: var(--muted);
            white-space: pre-line;
            overflow-wrap: anywhere;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 16px;
        }

        .card {
            min-width: 0;
            padding: 22px;
            border: 1px solid var(--border);
            border-radius: 10px;
            background: linear-gradient(
                145deg,
                rgba(22, 27, 34, 0.70),
                rgba(13, 17, 23, 0.70)
            );
            transition: border-color 0.2s, transform 0.2s;
        }

        .card:hover {
            border-color: #365477;
            transform: translateY(-3px);
        }

        .card-icon { font-size: 27px; }

        .card p {
            margin: 8px 0 0;
            color: var(--muted);
            font-size: 14px;
            overflow-wrap: anywhere;
        }

        .project-link {
            display: inline-block;
            margin-top: 16px;
            font-size: 14px;
            font-weight: 650;
        }

        footer {
            padding: 28px 20px;
            border-top: 1px solid var(--border);
            color: var(--muted);
            text-align: center;
            font-size: 13px;
        }

        @media (max-width: 700px) {
            .navbar {
                align-items: flex-start;
                flex-direction: column;
                gap: 10px;
                padding: 14px 20px;
            }

            .nav-links {
                justify-content: flex-start;
                gap: 14px;
            }

            .hero { padding: 70px 0; }
            h1 { letter-spacing: -1.5px; }

            .grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }

        @media (max-width: 460px) {
            .container { width: min(100% - 28px, 1000px); }
            .grid { grid-template-columns: 1fr; }
        }
    </style>
</head>

<body>
    <header class="navbar">
        <a class="logo" href="#top">Ali<span>.</span></a>
        <nav class="nav-links">%%NAVIGATION%%</nav>
    </header>

    <main class="container">
        <section class="hero" id="top">
            <div class="terminal">
                <span class="prompt">$</span>
                whoami
                <span class="arrow">→</span>
                ali-akbarzade
            </div>

            <h1>Hi, I'm <span>Ali.</span></h1>
            <p class="hero-copy">%%HERO_TEXT%%</p>

            <div class="buttons">
                <a class="button primary"
                   href="%%GITHUB_URL%%"
                   target="_blank"
                   rel="noopener noreferrer">GitHub ↗</a>

                <a class="button" href="#projects">Explore Projects</a>
            </div>
        </section>

        <section class="section" id="about">
            <h2>About <span>Me</span></h2>
            <p class="text-block">%%ABOUT_TEXT%%</p>
        </section>

        <section class="section" id="skills">
            <h2>What I <span>Do</span></h2>
            <div class="grid">%%SKILLS%%</div>
        </section>

        <section class="section" id="projects">
            <h2>Selected <span>Projects</span></h2>
            <div class="grid">%%PROJECTS%%</div>
        </section>

        %%CUSTOM_SECTIONS%%
    </main>

    <footer>© 2026 Ali Akbarzade · Built with HTML &amp; CSS</footer>
</body>
</html>'''

    replacements = {
        "NAVIGATION": navigation,
        "HERO_TEXT": render_markup(HERO_TEXT),
        "GITHUB_URL": escape(GITHUB_URL),
        "ABOUT_TEXT": render_markup(about),
        "SKILLS": "\n".join(skill_cards),
        "PROJECTS": "\n".join(project_cards),
        "CUSTOM_SECTIONS": "\n".join(extra_content),
    }

    # Replace placeholders in one pass.
    # This prevents text entered by the user from changing other placeholders.
    return re.sub(
        r"%%(NAVIGATION|HERO_TEXT|GITHUB_URL|ABOUT_TEXT|SKILLS|PROJECTS|CUSTOM_SECTIONS)%%",
        lambda match: replacements[match.group(1)],
        template,
    )


# =========================================================
# Tkinter editor
# =========================================================

class WebsiteEditor(tk.Tk):

    def __init__(self):
        super().__init__()

        self.title("Ali Akbarzade — Website Editor")
        self.geometry("1100x760")
        self.minsize(760, 520)
        self.configure(bg="#080b10")

        self.setup_styles()
        self.build_ui()

    def setup_styles(self):
        style = ttk.Style(self)

        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        bg = "#080b10"
        panel = "#0d1117"
        border = "#30363d"
        text = "#e6edf3"
        muted = "#9daab8"
        blue = "#58a6ff"

        style.configure(
            ".",
            background=bg,
            foreground=text,
            font=("DejaVu Sans", 10),
        )

        style.configure("TFrame", background=bg)

        style.configure(
            "Title.TLabel",
            font=("DejaVu Sans", 20, "bold"),
            foreground=text,
            background=bg,
        )

        style.configure(
            "Hint.TLabel",
            foreground=muted,
            background=bg,
        )

        style.configure(
            "TNotebook",
            background=bg,
            borderwidth=0,
        )

        style.configure(
            "TNotebook.Tab",
            background=panel,
            foreground=text,
            padding=(16, 10),
        )

        style.map(
            "TNotebook.Tab",
            background=[("selected", "#161b22")],
            foreground=[("selected", blue)],
        )

        style.configure(
            "TButton",
            background=panel,
            foreground=text,
            bordercolor=border,
            padding=(12, 8),
        )

        style.map(
            "TButton",
            background=[("active", "#21262d")],
        )

        style.configure(
            "Primary.TButton",
            background=blue,
            foreground="#08111e",
            bordercolor=blue,
            padding=(14, 9),
            font=("DejaVu Sans", 10, "bold"),
        )

        style.map(
            "Primary.TButton",
            background=[("active", "#79c0ff")],
            foreground=[("active", "#08111e")],
        )

    def build_ui(self):
        header = ttk.Frame(self, padding=(20, 16, 20, 4))
        header.pack(side="top", fill="x")

        ttk.Label(
            header,
            text="Website Editor",
            style="Title.TLabel",
        ).pack(anchor="w")

        ttk.Label(
            header,
            text=(
                "Commands: /nl for a new line, "
                "word/link(URL) for links, word/c(COLOR) for colors."
            ),
            style="Hint.TLabel",
            wraplength=1000,
        ).pack(anchor="w", pady=(6, 10))

        # Footer is packed BEFORE the expanding Notebook so it stays visible.
        footer = ttk.Frame(self, padding=(18, 0, 18, 16))
        footer.pack(side="bottom", fill="x")

        ttk.Button(
            footer,
            text="Reset defaults",
            command=self.reset_defaults,
        ).pack(side="left")

        ttk.Button(
            footer,
            text="Export index.html",
            style="Primary.TButton",
            command=self.export,
        ).pack(side="right")

        ttk.Button(
            footer,
            text="Preview",
            command=self.preview,
        ).pack(side="right", padx=(0, 8))

        self.notebook = ttk.Notebook(self)

        self.add_text_tab(
            "About",
            "About me",
            "Text shown in the About Me section. Commands work here too.",
            "about_text",
            DEFAULT_ABOUT,
        )

        self.add_text_tab(
            "Skills",
            "One skill per line",
            "Format: emoji | title | description. Commands work in each field.",
            "skills_text",
            DEFAULT_SKILLS,
            horizontal_scroll=True,
        )

        self.add_text_tab(
            "Projects",
            "One project per line",
            "Format: emoji | title | description | URL. Commands work in displayed text.",
            "projects_text",
            DEFAULT_PROJECTS,
            horizontal_scroll=True,
        )

        self.add_text_tab(
            "Add Sections",
            "Add your own sections",
            "One per line: Title | Content. Use /nl inside content for line breaks.",
            "custom_text",
            "",
        )

        self.notebook.pack(
            fill="both",
            expand=True,
            padx=18,
            pady=(6, 12),
        )

    def add_text_tab(
        self,
        tab_title,
        heading,
        hint,
        attribute_name,
        default_text,
        horizontal_scroll=False,
    ):
        frame = ttk.Frame(self.notebook, padding=18)
        self.notebook.add(frame, text=tab_title)

        ttk.Label(
            frame,
            text=heading,
            font=("DejaVu Sans", 11, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            frame,
            text=hint,
            style="Hint.TLabel",
            wraplength=1000,
            justify="left",
        ).pack(anchor="w", pady=(8, 10))

        editor_frame = ttk.Frame(frame)
        editor_frame.pack(fill="both", expand=True)

        editor_frame.rowconfigure(0, weight=1)
        editor_frame.columnconfigure(0, weight=1)

        text_widget = tk.Text(
            editor_frame,
            wrap="none" if horizontal_scroll else "word",
            undo=True,
            bg="#0d1117",
            fg="#e6edf3",
            insertbackground="#58a6ff",
            selectbackground="#264f78",
            relief="flat",
            borderwidth=1,
            highlightthickness=1,
            highlightbackground="#263241",
            highlightcolor="#58a6ff",
            font=("DejaVu Sans Mono", 10),
            padx=10,
            pady=10,
            spacing1=2,
            spacing3=2,
        )

        vertical_scrollbar = ttk.Scrollbar(
            editor_frame,
            orient="vertical",
            command=text_widget.yview,
        )

        text_widget.configure(
            yscrollcommand=vertical_scrollbar.set
        )

        text_widget.grid(row=0, column=0, sticky="nsew")
        vertical_scrollbar.grid(row=0, column=1, sticky="ns")

        if horizontal_scroll:
            horizontal_scrollbar = ttk.Scrollbar(
                editor_frame,
                orient="horizontal",
                command=text_widget.xview,
            )

            text_widget.configure(
                xscrollcommand=horizontal_scrollbar.set
            )

            horizontal_scrollbar.grid(
                row=1,
                column=0,
                sticky="ew",
            )

        text_widget.insert("1.0", default_text)
        setattr(self, attribute_name, text_widget)

    @staticmethod
    def get_text(widget):
        return widget.get("1.0", "end-1c")

    @staticmethod
    def set_text(widget, value):
        widget.delete("1.0", "end")
        widget.insert("1.0", value)

    def get_html(self):
        return make_html(
            about=self.get_text(self.about_text),
            skills_raw=self.get_text(self.skills_text),
            projects_raw=self.get_text(self.projects_text),
            custom_raw=self.get_text(self.custom_text),
        )

    def reset_defaults(self):
        answer = messagebox.askyesno(
            "Reset defaults",
            "Reset About, Skills, Projects and custom sections?",
            parent=self,
        )

        if not answer:
            return

        self.set_text(self.about_text, DEFAULT_ABOUT)
        self.set_text(self.skills_text, DEFAULT_SKILLS)
        self.set_text(self.projects_text, DEFAULT_PROJECTS)
        self.set_text(self.custom_text, "")

        messagebox.showinfo(
            "Reset complete",
            "Default content has been restored.",
            parent=self,
        )

    def preview(self):
        try:
            document = self.get_html()

            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                suffix=".html",
                prefix="website-preview-",
                delete=False,
            ) as file:
                file.write(document)
                preview_path = Path(file.name)

            webbrowser.open_new_tab(
                preview_path.resolve().as_uri()
            )

        except (ValueError, OSError) as error:
            messagebox.showerror(
                "Preview failed",
                str(error),
                parent=self,
            )

    def export(self):
        try:
            document = self.get_html()

        except (ValueError, OSError) as error:
            messagebox.showerror(
                "Invalid content",
                str(error),
                parent=self,
            )
            return

        filename = filedialog.asksaveasfilename(
            parent=self,
            title="Export website",
            initialfile="index.html",
            defaultextension=".html",
            filetypes=[
                ("HTML files", "*.html"),
                ("All files", "*"),
            ],
        )

        if not filename:
            return

        try:
            output_path = Path(filename)
            output_path.write_text(
                document,
                encoding="utf-8",
            )

        except OSError as error:
            messagebox.showerror(
                "Export failed",
                str(error),
                parent=self,
            )
            return

        messagebox.showinfo(
            "Export successful",
            "Website exported successfully!\n\n"
            f"File:\n{output_path.resolve()}",
            parent=self,
        )


if __name__ == "__main__":
    app = WebsiteEditor()
    app.mainloop()
