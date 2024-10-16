# Configuration file for the Sphinx documentation builder.
# https://www.sphinx-doc.org/en/master/usage/configuration.html

from __future__ import annotations

import inspect
import os
import re
import sys
import warnings
from pathlib import Path
from typing import Any

import sphinx_autosummary_accessors

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here.

# Add py-polars directory
sys.path.insert(0, str(Path("../..").resolve()))


# -- Project information -----------------------------------------------------

project = "Junction"
author = "Junction Labs"
copyright = f"2024, {author}"


# -- General configuration ---------------------------------------------------

extensions = [
    # Sphinx extensions
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.githubpages",
    "sphinx.ext.intersphinx",
    "sphinx.ext.linkcode",
    "sphinx.ext.mathjax",
    # Third-party extensions
    "autodocsumm",
    "sphinx_autosummary_accessors",
    "sphinx_copybutton",
    "sphinx_design",
    "sphinx_favicon",
    "sphinx_reredirects",
    "sphinx_toolbox.more_autodoc.overloads",
]

# Render docstring text in `single backticks` as code.
default_role = "code"

maximum_signature_line_length = 88

# Below setting is used by
# sphinx-autosummary-accessors - build docs for namespace accessors like `Series.str`
# https://sphinx-autosummary-accessors.readthedocs.io/en/stable/
templates_path = ["_templates", sphinx_autosummary_accessors.templates_path]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["Thumbs.db", ".DS_Store"]

# Hide overload type signatures
# sphinx_toolbox - Box of handy tools for Sphinx
# https://sphinx-toolbox.readthedocs.io/en/latest/
overloads_location = ["bottom"]

# -- Extension settings ------------------------------------------------------

# sphinx.ext.intersphinx - link to other projects' documentation
# https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

# Sphinx-copybutton - add copy button to code blocks
# https://sphinx-copybutton.readthedocs.io/en/latest/index.html
# strip the '>>>' and '...' prompt/continuation prefixes.
copybutton_prompt_text = r">>> |\.\.\. "
copybutton_prompt_is_regexp = True

# redirect empty root to the actual landing page
redirects = {"index": "reference/index.html"}


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.
html_theme = "pydata_sphinx_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]
html_css_files = ["css/custom.css"]  # relative to html_static_path
html_show_sourcelink = False

# key site root paths
static_assets_root = (
    "https://raw.githubusercontent.com/junction-labs/junction-static/master"
)
github_root = "https://github.com/junction-labs/junction-client"
web_root = "https://docs.junctionlabs.io"

# Specify version for version switcher dropdown menu
git_ref = os.environ.get("JUNCTION_VERSION", "main")
version_match = re.fullmatch(r"py-(\d+)\.\d+\.\d+.*", git_ref)
switcher_version = version_match.group(1) if version_match is not None else "dev"

html_js_files = [
    (
        "https://plausible.io/js/script.js",
        {"data-domain": "docs.junction-labs,combined.junction-labs", "defer": "defer"},
    ),
]

html_theme_options = {
    "external_links": [
        {
            "name": "User guide",
            "url": f"{web_root}/",
        },
    ],
    "icon_links": [
        {
            "name": "GitHub",
            "url": github_root,
            "icon": "fa-brands fa-github",
        },
        {
            "name": "Discord",
            "url": "https://discord.gg/9Uq9FwnW3y",
            "icon": "fa-brands fa-discord",
        },
        # {
        #     "name": "Twitter",
        #     "url": "https://twitter.com/DataPolars",
        #     "icon": "fa-brands fa-twitter",
        # },
    ],
    "logo": {
        "image_light": f"{static_assets_root}/logos/junction-labs-logo-dark-medium.png",
        "image_dark": f"{static_assets_root}/logos/junction-labs-logo-dimmed-medium.png",
    },
    "switcher": {
        "json_url": f"{web_root}/api/python/dev/_static/version_switcher.json",
        "version_match": switcher_version,
    },
    "show_version_warning_banner": False,
    "navbar_end": ["theme-switcher", "version-switcher", "navbar-icon-links"],
    "check_switcher": False,
}

# sphinx-favicon - Add support for custom favicons
# https://github.com/tcmetzger/sphinx-favicon
favicons = [
    {
        "rel": "icon",
        "sizes": "32x32",
        "href": f"{static_assets_root}/icons/favicon-32x32.png",
    },
    {
        "rel": "apple-touch-icon",
        "sizes": "180x180",
        "href": f"{static_assets_root}/icons/touchicon-180x180.png",
    },
]


# sphinx-ext-linkcode - Add external links to source code
# https://www.sphinx-doc.org/en/master/usage/extensions/linkcode.html
def linkcode_resolve(domain: str, info: dict[str, Any]) -> str | None:
    """
    Determine the URL corresponding to Python object.

    Based on pandas equivalent:
    https://github.com/pandas-dev/pandas/blob/main/doc/source/conf.py#L629-L686
    """
    if domain != "py":
        return None

    modname = info["module"]
    fullname = info["fullname"]

    submod = sys.modules.get(modname)
    if submod is None:
        return None

    obj = submod
    for part in fullname.split("."):
        try:
            with warnings.catch_warnings():
                # Accessing deprecated objects will generate noisy warnings
                warnings.simplefilter("ignore", FutureWarning)
                obj = getattr(obj, part)
        except AttributeError:  # noqa: PERF203
            return None

    try:
        fn = inspect.getsourcefile(inspect.unwrap(obj))
    except TypeError:
        try:  # property
            fn = inspect.getsourcefile(inspect.unwrap(obj.fget))
        except (AttributeError, TypeError):
            fn = None
    if not fn:
        return None

    try:
        source, lineno = inspect.getsourcelines(obj)
    except TypeError:
        try:  # property
            source, lineno = inspect.getsourcelines(obj.fget)
        except (AttributeError, TypeError):
            lineno = None
    except OSError:
        lineno = None

    linespec = f"#L{lineno}-L{lineno + len(source) - 1}" if lineno else ""

    conf_dir_path = Path(__file__).absolute().parent
    junction_client_root = (conf_dir_path.parent.parent / "junction").absolute()

    fn = os.path.relpath(fn, start=junction_client_root)
    return f"{github_root}/blob/{git_ref}/junction-python/junction/{fn}{linespec}"


def process_signature(  # noqa: D103
    app: object,
    what: object,
    name: object,
    obj: object,
    opts: object,
    sig: str,
    ret: str,
) -> tuple[str, str]:
    return (sig, ret)


def setup(app: Any) -> None:  # noqa: D103
    # TODO: a handful of methods do not seem to trigger the event for
    #  some reason (possibly @overloads?) - investigate further...
    app.connect("autodoc-process-signature", process_signature)