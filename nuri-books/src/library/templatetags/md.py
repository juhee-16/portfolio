import markdown
from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name="md")
def md(text: str) -> str:
    """AI 답변(마크다운)을 HTML로 변환한다."""
    if not text:
        return ""
    html = markdown.markdown(escape(text), extensions=["nl2br", "sane_lists"])
    return mark_safe(html)
