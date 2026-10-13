"""
Format checks for Indian tax IDs (shape only: they don't confirm with the
government; real verification is a later phase).
"""
import re

from rest_framework import serializers

PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")


def clean_id(value):
    return (value or "").strip().upper().replace(" ", "")


def validate_pan(value):
    value = clean_id(value)
    if not PAN_RE.match(value):
        raise serializers.ValidationError("Enter a valid PAN, like ABCDE1234F.")
    return value


def validate_gstin(value):
    value = clean_id(value)
    if not GSTIN_RE.match(value):
        raise serializers.ValidationError("Enter a valid 15-character GSTIN, like 27ABCDE1234F1Z5.")
    return value
