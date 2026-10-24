"""English editorial policy identifiers with support for immutable archived drafts."""

EDITORIAL_VERSION = "ko-300words-v1"
# Historical article bytes and their reviewed delivery hashes must remain unchanged.
LEGACY_EDITORIAL_VERSION = "ko-300eojeol-v1"
SUPPORTED_EDITORIAL_VERSIONS = frozenset((EDITORIAL_VERSION, LEGACY_EDITORIAL_VERSION))
