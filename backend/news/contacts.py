"""Derive a conservative dial target without changing stored contact text."""

import re

from django.core.exceptions import ValidationError

_GROUPS = re.compile(r"\+?[0-9]+(?:[ .-][0-9]+)*")
_PARENS = re.compile(r"\([0-9]{2,4}\)")
_DOMESTIC = re.compile(
    r"(?:02[0-9]{7,8}|"
    r"0(?:31|32|33|41|42|43|44|51|52|53|54|55|61|62|63|64)[0-9]{7,8}|"
    r"010[0-9]{8}|01[16789][0-9]{7,8})"
)
_KAKAO_CHAT = re.compile(r"https://pf\.kakao\.com/_[A-Za-z0-9]{1,128}/chat")


def kakao_chat_href(value):
    """Return only an exact supported chat URL; never repair stored input."""
    if isinstance(value, str) and len(value) <= 500 and _KAKAO_CHAT.fullmatch(value):
        return value
    return ""


def validate_kakao_chat_url(value):
    if value != "" and not kakao_chat_href(value):
        raise ValidationError(
            "https://pf.kakao.com/_공개ID/chat 형식의 1:1 채팅 URL을 입력해 주세요. 채널 홈 주소는 자동 변환하지 않습니다.",
            code="invalid_kakao_chat_url",
        )


def telephone_href(value):
    """Support selected Korean national forms and +digits, not arbitrary URIs.

    Only visual separators in a wholly accepted input are removed. Extensions,
    instructions, prose, control characters and ambiguous extra numbers stay text.
    This is a presentation subset, not a number-allocation or reachability check.
    """
    if not isinstance(value, str) or len(value) > 80:
        return ""
    text = value.strip(" ")
    if not text or not re.fullmatch(r"[+0-9 .()\-]+", text):
        return ""
    if "(" in text or ")" in text:
        if text.count("(") != 1 or text.count(")") != 1:
            return ""
        match = _PARENS.search(text)
        if match is None:
            return ""
        text = text[: match.start()] + match[0][1:-1] + text[match.end() :]
    if not _GROUPS.fullmatch(text):
        return ""
    number = text.translate(str.maketrans("", "", " .-"))
    if number.startswith("+"):
        if not re.fullmatch(r"\+[1-9][0-9]{7,14}", number):
            return ""
        # Do not guess away a Korean trunk marker supplied after a country code.
        return "tel:" + number if not number.startswith("+820") else ""
    if _DOMESTIC.fullmatch(number):
        return "tel:+82" + number[1:]
    return ""
