"""Explicit outbound demo allowlist; an empty configuration sends nothing."""
import os
import re


def normalize_phone(value: str) -> str:
    phone = re.sub(r'[\s+()-]', '', value)
    if phone.startswith('0'): phone = '62' + phone[1:]
    if not re.fullmatch(r'[1-9]\d{7,14}', phone): raise ValueError('invalid phone')
    return phone


def require_allowed_recipient(phone: str) -> str:
    normalized = normalize_phone(phone)
    allowed = {normalize_phone(v.strip()) for v in os.environ.get('PARTPILOT_WA_ALLOWED_RECIPIENTS','').split(',') if v.strip()}
    if normalized not in allowed: raise ValueError('recipient_not_allowlisted')
    return normalized
