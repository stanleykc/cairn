import hashlib

import pytest
import yaml

from cairn.textutil import read_front_matter, sha256_bytes, slugify, yaml_str


def test_slugify_accents_and_punctuation():
    assert (
        slugify("Société Générale") + "-" + slugify("Q4: Fulfillment Review!")
        == "societe-generale-q4-fulfillment-review"
    )


def test_slugify_all_punctuation_is_empty():
    assert slugify("!!! ---  ???") == ""


def test_slugify_collapses_runs():
    assert slugify("  Acme   --  Fulfillment__Review ") == "acme-fulfillment-review"


@pytest.mark.parametrize(
    "value",
    ["Acme: Phase 2", "Review #3", 'The "Big" One', "Société Générale", "it's", ""],
)
def test_yaml_str_round_trips(value):
    assert yaml.safe_load(f"name: {yaml_str(value)}") == {"name": value}


def test_read_front_matter_quoted_unquoted_and_comments():
    text = (
        "---\n"
        'id: "acme-review"\n'
        "type: engagement\n"
        'framework_version: "0.1.0"  # updated only by cairn refresh\n'
        "model_use: unconfirmed  # allowed | restricted | unconfirmed\n"
        "name: 'it''s'\n"
        "team: []\n"
        "---\n"
        "body: not front matter\n"
    )
    assert read_front_matter(text) == {
        "id": "acme-review",
        "type": "engagement",
        "framework_version": "0.1.0",
        "model_use": "unconfirmed",
        "name": "it's",
        "team": "[]",
    }


def test_read_front_matter_missing_or_unclosed():
    assert read_front_matter("# Title\n\ntext\n") == {}
    assert read_front_matter("---\ntype: engagement\n") == {}
    assert read_front_matter("") == {}


def test_sha256_bytes():
    assert sha256_bytes(b"abc") == "sha256:" + hashlib.sha256(b"abc").hexdigest()
    assert sha256_bytes(b"").startswith("sha256:e3b0c442")
