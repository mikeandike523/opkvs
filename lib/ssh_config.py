"""
Utilities for parsing and idempotently editing OpenSSH config files (~/.ssh/config).
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class HostBlock:
    """A single Host block in an SSH config file."""
    host_alias: str     # bare alias, e.g. 'alice@myserver' (no surrounding quotes)
    lines: List[str]    # raw lines, no trailing newline characters per line


@dataclass
class ParsedSshConfig:
    """Parsed representation of an ~/.ssh/config file."""
    preamble: List[str]      # lines before the first Host block
    blocks: List[HostBlock]  # Host blocks in file order
    line_ending: str         # '\r\n' or '\n' — detected from the original file


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _detect_line_ending(text: str) -> str:
    """Return '\\r\\n' if CRLF is present anywhere in the text, else '\\n'."""
    return "\r\n" if "\r\n" in text else "\n"


def _extract_host_alias(header_line: str) -> str:
    """
    Extract the bare alias from a Host directive line.

      Host "alice@myserver"  ->  alice@myserver
      Host alice@myserver    ->  alice@myserver
    """
    parts = header_line.strip().split(None, 1)
    if len(parts) < 2:
        return ""
    rest = parts[1].strip()
    if rest.startswith('"') and rest.endswith('"') and len(rest) >= 2:
        rest = rest[1:-1]
    return rest


def _is_host_line(line: str) -> bool:
    lower = line.strip().lower()
    return lower.startswith("host ") or lower == "host"


def parse_ssh_config(text: str) -> ParsedSshConfig:
    """Parse SSH config text into a structured form."""
    line_ending = _detect_line_ending(text)

    # Normalise to LF internally for processing
    normalised = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalised.split("\n")

    # A trailing newline produces a spurious empty final element — drop it
    if lines and lines[-1] == "":
        lines = lines[:-1]

    preamble: List[str] = []
    blocks: List[HostBlock] = []
    current_lines: Optional[List[str]] = None
    current_alias: str = ""

    for line in lines:
        if _is_host_line(line):
            if current_lines is not None:
                blocks.append(HostBlock(host_alias=current_alias, lines=current_lines))
            current_alias = _extract_host_alias(line)
            current_lines = [line]
        else:
            if current_lines is not None:
                current_lines.append(line)
            else:
                preamble.append(line)

    if current_lines is not None:
        blocks.append(HostBlock(host_alias=current_alias, lines=current_lines))

    return ParsedSshConfig(preamble=preamble, blocks=blocks, line_ending=line_ending)


# ---------------------------------------------------------------------------
# Editing
# ---------------------------------------------------------------------------

def _block_from_text(entry_text: str) -> HostBlock:
    """Build a HostBlock from a formatted entry string (output of format_entry)."""
    normalised = entry_text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalised.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    alias = _extract_host_alias(lines[0]) if lines else ""
    return HostBlock(host_alias=alias, lines=lines)


def _blocks_equivalent(a: HostBlock, b: HostBlock) -> bool:
    """Compare two blocks ignoring trailing whitespace and blank lines."""
    def norm(lines):
        return [l.rstrip() for l in lines if l.strip()]
    return norm(a.lines) == norm(b.lines)


def apply_entries(
    config: ParsedSshConfig,
    formatted_blocks: List[str],
    host_aliases: List[str],
) -> Tuple[ParsedSshConfig, List[Tuple[str, str]]]:
    """
    Idempotently upsert a list of SSH config blocks into a parsed config.

    Parameters
    ----------
    config          : the parsed existing config to update
    formatted_blocks: raw entry text per block (output of format_entry())
    host_aliases    : bare Host alias per entry, parallel to formatted_blocks

    Returns
    -------
    (updated_config, actions)
        updated_config : new ParsedSshConfig with changes applied
        actions        : list of (alias, action) where action is one of
                         'added', 'updated', or 'unchanged'
    """
    new_blocks = list(config.blocks)
    actions: List[Tuple[str, str]] = []

    for alias, entry_text in zip(host_aliases, formatted_blocks):
        new_block = _block_from_text(entry_text)

        # Resolve index against the growing list so earlier appends are visible
        idx = next(
            (i for i, b in enumerate(new_blocks) if b.host_alias == alias),
            None,
        )

        if idx is not None:
            if _blocks_equivalent(new_blocks[idx], new_block):
                actions.append((alias, "unchanged"))
            else:
                new_blocks[idx] = new_block
                actions.append((alias, "updated"))
        else:
            new_blocks.append(new_block)
            actions.append((alias, "added"))

    return ParsedSshConfig(
        preamble=config.preamble,
        blocks=new_blocks,
        line_ending=config.line_ending,
    ), actions


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

def serialize_config(config: ParsedSshConfig) -> str:
    """
    Serialize a ParsedSshConfig back to text using the file's original line ending.

    Trailing blank lines are stripped from each block so that the double-newline
    separator between blocks gives exactly one blank line.  The result always ends
    with a single (appropriately styled) newline.
    """
    le = config.line_ending
    parts: List[str] = []

    preamble = list(config.preamble)
    while preamble and not preamble[-1].strip():
        preamble.pop()
    if preamble:
        parts.append(le.join(preamble))

    for block in config.blocks:
        block_lines = list(block.lines)
        while block_lines and not block_lines[-1].strip():
            block_lines.pop()
        parts.append(le.join(block_lines))

    result = (le + le).join(p for p in parts if p)
    if result and not result.endswith(le):
        result += le
    return result
