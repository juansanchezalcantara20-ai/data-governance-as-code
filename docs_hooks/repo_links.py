"""MkDocs hook: links from docs/ to repository files outside docs/ become GitHub links on the published site."""

from __future__ import annotations

import posixpath
import re

REPO = "https://github.com/juansanchezalcantara20-ai/data-governance-as-code/blob/main/"
LINK = re.compile(r"(\]\()([^)\s#]+)(#[^)\s]*)?(\))")


def on_page_markdown(markdown, page, config, files):
    page_dir = posixpath.dirname(page.file.src_uri)

    def fix(m):
        target = m.group(2)
        if re.match(r"^[a-z]+:", target) or target.startswith("/"):
            return m.group(0)
        resolved = posixpath.normpath(posixpath.join("docs", page_dir, target))
        if resolved.startswith("docs/"):
            rel = posixpath.relpath(resolved, posixpath.join("docs", page_dir) if page_dir else "docs")
            return f"{m.group(1)}{rel}{m.group(3) or ''}{m.group(4)}"
        return f"{m.group(1)}{REPO}{resolved}{m.group(3) or ''}{m.group(4)}"

    return LINK.sub(fix, markdown)
