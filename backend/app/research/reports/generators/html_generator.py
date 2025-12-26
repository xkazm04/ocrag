"""HTML report generator using OpenRouter Gemini."""

import httpx
from typing import Optional

from ..schemas import ReportData
from .style_guides import get_style_guide, format_style_guide_for_prompt, BASE_CSS


class HTMLGenerator:
    """
    Generates styled HTML reports from markdown using OpenRouter Gemini.

    Uses LLM to create professionally styled HTML with template-aware design.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
        model: str = "google/gemini-3-flash-preview"
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    async def generate(
        self,
        markdown_content: str,
        template_type: str,
        title: str,
        style_overrides: Optional[dict] = None
    ) -> str:
        """
        Generate styled HTML from markdown content.

        Args:
            markdown_content: The markdown report content
            template_type: Research template type for styling
            title: Report title
            style_overrides: Optional custom style settings

        Returns:
            Complete HTML document string
        """
        # Get style guide for template
        style_guide = get_style_guide(template_type)

        # Apply any overrides
        if style_overrides:
            style_guide = {**style_guide, **style_overrides}

        # Build the prompt
        prompt = self._build_prompt(markdown_content, template_type, title, style_guide)

        # Call OpenRouter API
        html_content = await self._call_llm(prompt)

        # Validate and clean response
        html_content = self._clean_html_response(html_content)

        return html_content

    def _build_prompt(
        self,
        markdown_content: str,
        template_type: str,
        title: str,
        style_guide: dict
    ) -> str:
        """Build the prompt for HTML generation."""
        style_text = format_style_guide_for_prompt(style_guide)

        return f"""You are a professional report designer. Generate beautifully styled HTML from the provided markdown content.

## MARKDOWN CONTENT
```markdown
{markdown_content}
```

## REPORT TITLE
{title}

## TEMPLATE TYPE
{template_type.replace('_', ' ').title()} Research

## STYLE GUIDANCE
{style_text}

## REQUIREMENTS
1. Use semantic HTML5 elements (header, main, section, article, footer, nav)
2. Embed ALL CSS in a <style> tag - no external dependencies
3. Follow the style guidance but use your professional judgment for optimal presentation
4. Ensure excellent contrast and readability (WCAG AA minimum)
5. Include @media print styles for PDF generation
6. Preserve ALL data, citations, and source links exactly as provided
7. Make tables responsive and well-formatted
8. Use appropriate spacing and visual hierarchy
9. Add subtle visual enhancements that match the template type

## BASE CSS (include and extend this)
```css
{BASE_CSS}
```

## OUTPUT FORMAT
Return ONLY valid HTML starting with <!DOCTYPE html>.
Do not include any explanation or markdown code blocks in your response.
The response should be the complete HTML document ready to render.

Generate the HTML now:"""

    async def _call_llm(self, prompt: str) -> str:
        """Call OpenRouter API to generate HTML."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://research-platform.local",
                    "X-Title": "Research Report Generator"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.3,
                    "max_tokens": 16000
                }
            )

            response.raise_for_status()
            data = response.json()

            # Extract content from response
            content = data["choices"][0]["message"]["content"]
            return content

    def _clean_html_response(self, html: str) -> str:
        """Clean and validate the HTML response."""
        # Remove any markdown code block wrappers
        html = html.strip()

        if html.startswith("```html"):
            html = html[7:]
        elif html.startswith("```"):
            html = html[3:]

        if html.endswith("```"):
            html = html[:-3]

        html = html.strip()

        # Ensure it starts with doctype
        if not html.lower().startswith("<!doctype"):
            # Try to find where HTML actually starts
            doctype_pos = html.lower().find("<!doctype")
            if doctype_pos > 0:
                html = html[doctype_pos:]
            elif html.lower().startswith("<html"):
                html = "<!DOCTYPE html>\n" + html

        return html

    def generate_fallback_html(
        self,
        markdown_content: str,
        title: str,
        template_type: str
    ) -> str:
        """
        Generate basic HTML without LLM (fallback for errors).

        Uses simple markdown-to-HTML conversion with base styles.
        """
        import re

        # Simple markdown to HTML conversion
        html_body = markdown_content

        # Headers
        html_body = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html_body, flags=re.MULTILINE)
        html_body = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html_body, flags=re.MULTILINE)
        html_body = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html_body, flags=re.MULTILINE)

        # Bold and italic
        html_body = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html_body)
        html_body = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html_body)

        # Links
        html_body = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', html_body)

        # Lists
        lines = html_body.split('\n')
        in_list = False
        processed = []

        for line in lines:
            if line.strip().startswith('- '):
                if not in_list:
                    processed.append('<ul>')
                    in_list = True
                processed.append(f'<li>{line.strip()[2:]}</li>')
            elif line.strip().startswith(('1. ', '2. ', '3. ', '4. ', '5. ', '6. ', '7. ', '8. ', '9. ')):
                if not in_list:
                    processed.append('<ol>')
                    in_list = True
                processed.append(f'<li>{line.strip()[3:]}</li>')
            else:
                if in_list:
                    processed.append('</ul>' if processed[-2].startswith('<li>') else '</ol>')
                    in_list = False
                if line.strip() == '---':
                    processed.append('<hr>')
                elif line.strip().startswith('|'):
                    # Simple table handling
                    processed.append(line)
                elif line.strip():
                    processed.append(f'<p>{line}</p>')
                else:
                    processed.append('<br>')

        if in_list:
            processed.append('</ul>')

        html_body = '\n'.join(processed)

        # Horizontal rules
        html_body = html_body.replace('---', '<hr>')

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
{BASE_CSS}
    </style>
</head>
<body>
    <main>
        {html_body}
    </main>
    <footer>
        <p><em>Generated by Research Intelligence Platform</em></p>
    </footer>
</body>
</html>"""


def create_html_generator() -> HTMLGenerator:
    """Factory function to create HTML generator with config."""
    from ...ocr.config import get_ocr_settings

    settings = get_ocr_settings()

    return HTMLGenerator(
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
        model=settings.gemini_model
    )
