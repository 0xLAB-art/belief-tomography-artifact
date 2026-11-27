"""Hash-pinned prompt/cwd patch for Cowrie's LLM shell backend.

The pinned Cowrie image hardcodes the LLM shell's working directory to ``/``
(``llm/protocol.py``: ``self.cwd = "/"``) and renders that value verbatim in the
prompt. The native shell instead starts in ``avatar.home`` and renders ``~``
(and ``~/sub``) relative to it (``shell/honeypot.py``). One declared persona
therefore shows two different prompts depending on which backend serves the
session, which a matched ablation cannot carry.

This module is the whole patch. It is deliberately small and deterministic:

* the upstream bytes are hash-pinned (:data:`BASE_PROTOCOL_SHA256`);
* every anchor must appear exactly once, so a changed image fails loudly
  instead of silently producing an unpatched or half-patched file;
* the result is mounted read-only over the single image path, so no other
  Cowrie behaviour changes and no image is rebuilt or pulled.

Only the RAGIN (LLM-backend) arm is patched. The native arm stays byte-identical
to the pinned image so the comparison remains a comparison.
"""

from __future__ import annotations

#: SHA-256 of the unmodified ``llm/protocol.py`` inside the pinned image.
BASE_PROTOCOL_SHA256 = "4cbc4408647a4add6cc338fb5f8eed0e11cf1293d67013ae6572dd4fa063d527"

#: Path of the file inside the pinned image that is replaced by a bind mount.
PROTOCOL_PATH_IN_IMAGE = "/cowrie/cowrie-git/src/cowrie/llm/protocol.py"

_CWD_ANCHOR = '        self.cwd = "/"\n'

# ``getProtoTransport`` appears in two classes, so the helpers are inserted
# after the last attribute of the base protocol's __init__, which is unique.
_HELPERS_ANCHOR = "        self.password_input = False\n"

_HELPERS_BLOCK = '''    def _home_dir(self) -> str:
        """Home directory for this session, or '' when none is declared.

        The LLM avatar carries no passwd entry (shell/avatar.py has one), so
        the persona home is supplied through [llm] home / COWRIE_LLM_HOME. An
        avatar that does carry a home wins over configuration.
        """
        home = getattr(self.user, "home", "")
        if not (isinstance(home, str) and home.startswith("/")):
            home = CowrieConfig.get("llm", "home", fallback="")
        if isinstance(home, str) and home.startswith("/"):
            return home
        return ""

    def _initial_cwd(self) -> str:
        """Mirror the native shell: start in the account home when declared."""
        return self._home_dir() or "/"
'''

_PROMPT_ANCHOR = '''        # Build a realistic prompt
        if self.user.username == "root":
            prompt = f"{self.user.username}@{self.hostname}:{self.cwd}# "
        else:
            prompt = f"{self.user.username}@{self.hostname}:{self.cwd}$ "
'''

_PROMPT_BLOCK = '''        # Build a realistic prompt. The native shell relativises the cwd
        # against the account home (shell/honeypot.py); the LLM backend must do
        # the same or one persona shows two prompts.
        cwd = self.cwd
        home = self._home_dir()
        if home and cwd == home:
            cwd = "~"
        elif home and cwd.startswith(home + "/"):
            cwd = "~" + cwd[len(home) :]
        if self.user.username == "root":
            prompt = f"{self.user.username}@{self.hostname}:{cwd}# "
        else:
            prompt = f"{self.user.username}@{self.hostname}:{cwd}$ "
'''


class PatchError(RuntimeError):
    """Raised when the pinned upstream text does not match the anchors."""


def _replace_once(source: str, anchor: str, replacement: str, label: str) -> str:
    found = source.count(anchor)
    if found != 1:
        raise PatchError(f"anchor {label!r} appeared {found} times, expected exactly 1")
    return source.replace(anchor, replacement, 1)


def patch_protocol_source(source: str) -> str:
    """Return ``protocol.py`` with the home-relative cwd and prompt applied."""
    patched = _replace_once(source, _CWD_ANCHOR, "        self.cwd = self._initial_cwd()\n", "cwd")
    patched = _replace_once(patched, _HELPERS_ANCHOR, _HELPERS_ANCHOR + "\n" + _HELPERS_BLOCK, "helpers")
    patched = _replace_once(patched, _PROMPT_ANCHOR, _PROMPT_BLOCK, "prompt")
    # The patch must be syntactically valid before it is ever mounted.
    compile(patched, "<patched llm/protocol.py>", "exec")
    return patched
