"""
HTML formatter for dry-run log preview
"""
import markdown


def format_log_html(log_markdown: str) -> str:
    """
    Convert log markdown to HTML with proper rendering.
    
    Args:
        log_markdown: Markdown content to render
        
    Returns:
        str: Complete HTML document with rendered markdown
    """
    # Convert markdown to HTML
    md = markdown.Markdown(extensions=['extra', 'codehilite', 'tables'])
    html_content = md.convert(log_markdown)
    
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Dry-Run Log Preview</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f6f8fa;
            line-height: 1.6;
            color: #24292e;
        }}
        h1 {{
            color: #24292e;
            border-bottom: 1px solid #e1e4e8;
            padding-bottom: 0.3em;
            margin-top: 24px;
            margin-bottom: 16px;
            font-size: 2em;
            font-weight: 600;
        }}
        h2 {{
            color: #24292e;
            border-bottom: 1px solid #e1e4e8;
            padding-bottom: 0.3em;
            margin-top: 24px;
            margin-bottom: 16px;
            font-size: 1.5em;
            font-weight: 600;
        }}
        table {{
            border-collapse: collapse;
            border-spacing: 0;
            width: 100%;
            margin: 16px 0;
            background: white;
            border: 1px solid #d0d7de;
            border-radius: 6px;
        }}
        th, td {{
            padding: 6px 13px;
            border: 1px solid #d0d7de;
            text-align: left;
        }}
        th {{
            background: #f6f8fa;
            font-weight: 600;
        }}
        tr:nth-child(even) {{
            background: #f6f8fa;
        }}
        pre {{
            background: #f6f8fa;
            border: 1px solid #d0d7de;
            border-radius: 6px;
            padding: 16px;
            overflow: auto;
            font-size: 85%;
            line-height: 1.45;
            margin: 16px 0;
        }}
        code {{
            background: #f6f8fa;
            padding: 0.2em 0.4em;
            margin: 0;
            font-size: 85%;
            border-radius: 6px;
            font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
        }}
        pre code {{
            background: transparent;
            padding: 0;
            font-size: 100%;
            border-radius: 0;
        }}
        .codehilite {{
            background: #f6f8fa;
            border-radius: 6px;
        }}
    </style>
</head>
<body>
{html_content}
</body>
</html>"""
