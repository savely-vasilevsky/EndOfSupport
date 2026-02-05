"""HTML User Guide Generator.

Converts USERGUIDE_VISUAL.md to a styled HTML document.
"""

import re
from pathlib import Path


class HTMLUserGuideGenerator:
    """Generates HTML user guide from markdown."""
    
    def __init__(self, markdown_path: str = "USERGUIDE_VISUAL.md", 
                 output_path: str = "docs/USERGUIDE.html"):
        self.markdown_path = Path(markdown_path)
        self.output_path = Path(output_path)
        self.sections = []
    
    def read_markdown(self) -> str:
        """Read the markdown source file."""
        with open(self.markdown_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def slugify(self, text: str) -> str:
        """Convert text to URL-friendly slug."""
        slug = text.lower().strip()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[\s_]+', '-', slug)
        return slug
    
    def convert_markdown_to_html(self, markdown: str) -> str:
        """Convert markdown to HTML with basic formatting."""
        html = markdown
        
        # Track sections for TOC
        self.sections = []
        
        # Headers with IDs for linking
        def replace_h2(match):
            title = match.group(1)
            slug = self.slugify(title)
            self.sections.append((title, slug, 2))
            return f'<h2 id="{slug}">{title}</h2>'
        
        def replace_h3(match):
            title = match.group(1)
            slug = self.slugify(title)
            self.sections.append((title, slug, 3))
            return f'<h3 id="{slug}">{title}</h3>'
        
        def replace_h4(match):
            title = match.group(1)
            slug = self.slugify(title)
            return f'<h4 id="{slug}">{title}</h4>'
        
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', replace_h2, html, flags=re.MULTILINE)
        html = re.sub(r'^### (.+)$', replace_h3, html, flags=re.MULTILINE)
        html = re.sub(r'^#### (.+)$', replace_h4, html, flags=re.MULTILINE)
        
        # Bold and italic
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
        
        # Code blocks with language support
        def format_code_block(match):
            lang = match.group(1) or ''
            code = match.group(2)
            lang_class = f' class="language-{lang}"' if lang else ''
            shell_indicator = '<span class="shell-prompt">$</span> ' if lang in ('bash', 'shell', 'sh') else ''
            if lang in ('bash', 'shell', 'sh'):
                # Add prompt to each line
                lines = code.strip().split('\n')
                formatted_lines = [f'<span class="shell-prompt">$</span> {line}' for line in lines if line.strip()]
                code = '\n'.join(formatted_lines)
                return f'<pre class="shell-block"><code{lang_class}>{code}</code></pre>'
            return f'<pre><code{lang_class}>{code}</code></pre>'
        
        html = re.sub(r'```(\w+)?\n(.*?)```', format_code_block, html, flags=re.DOTALL)
        
        # Inline code
        html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)
        
        # Links
        html = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<a href="\2">\1</a>', html)
        
        # Horizontal rules
        html = re.sub(r'^---+$', '<hr>', html, flags=re.MULTILINE)
        
        # Lists
        html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        
        # Numbered lists
        html = re.sub(r'^(\d+)\. (.+)$', r'<li>\2</li>', html, flags=re.MULTILINE)
        
        # Tables
        html = self._convert_tables(html)
        
        # Paragraphs
        lines = html.split('\n')
        processed_lines = []
        in_list = False
        in_pre = False
        
        for line in lines:
            stripped = line.strip()
            
            if '<pre>' in line:
                in_pre = True
            if '</pre>' in line:
                in_pre = False
                
            if in_pre:
                processed_lines.append(line)
                continue
                
            if stripped.startswith('<li>'):
                if not in_list:
                    processed_lines.append('<ul>')
                    in_list = True
                processed_lines.append(line)
            else:
                if in_list:
                    processed_lines.append('</ul>')
                    in_list = False
                    
                if not stripped:
                    processed_lines.append('')
                elif stripped.startswith('<'):
                    processed_lines.append(line)
                else:
                    processed_lines.append(f'<p>{line}</p>')
        
        if in_list:
            processed_lines.append('</ul>')
        
        return '\n'.join(processed_lines)
    
    def _convert_tables(self, html: str) -> str:
        """Convert markdown tables to HTML tables."""
        table_pattern = r'\|(.+)\|\n\|[-:\| ]+\|\n((?:\|.+\|\n?)+)'
        
        def replace_table(match):
            header_row = match.group(1)
            body_rows = match.group(2)
            
            headers = [h.strip() for h in header_row.split('|') if h.strip()]
            header_html = '<tr>' + ''.join(f'<th>{h}</th>' for h in headers) + '</tr>'
            
            rows_html = []
            for row in body_rows.strip().split('\n'):
                cells = [c.strip() for c in row.split('|') if c.strip()]
                if cells:
                    row_html = '<tr>' + ''.join(f'<td>{c}</td>' for c in cells) + '</tr>'
                    rows_html.append(row_html)
            
            return f'<table class="doc-table"><thead>{header_html}</thead><tbody>{"".join(rows_html)}</tbody></table>'
        
        return re.sub(table_pattern, replace_table, html, flags=re.MULTILINE)
    
    def generate_toc_html(self) -> str:
        """Generate table of contents HTML."""
        toc_items = []
        for title, slug, level in self.sections:
            if level == 2:
                icon = self._get_section_icon(title)
                toc_items.append(f'<a href="#{slug}" class="toc-item"><span class="toc-icon">{icon}</span>{title}</a>')
        return '\n'.join(toc_items)
    
    def _get_section_icon(self, title: str) -> str:
        """Get an icon for a section based on its title."""
        icons = {
            'introduction': '📋',
            'getting started': '🚀',
            'using the gui': '🖥️',
            'using the cli': '⌨️',
            'understanding support status': '📊',
            'output formats': '📄',
            'excel': '📗',
            'html': '🌐',
            'filtering': '🔍',
            'troubleshooting': '🔧',
            'faq': '❓',
            'keyboard': '⌨️',
        }
        title_lower = title.lower()
        for key, icon in icons.items():
            if key in title_lower:
                return icon
        return '📌'
    
    def get_css(self) -> str:
        """Get CSS styles for the HTML document."""
        return """
        :root {
            --aws-orange: #ff9900;
            --aws-dark: #232f3e;
            --aws-light: #f5f5f5;
            --success-green: #2e7d32;
            --warning-yellow: #f9a825;
            --info-blue: #1565c0;
            --danger-red: #c62828;
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Arial, sans-serif;
            line-height: 1.7;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        
        .header {
            background: var(--aws-dark);
            color: white;
            padding: 30px 40px;
            text-align: center;
            position: relative;
            overflow: hidden;
        }
        
        .header::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, var(--aws-orange), #ffcc00, var(--aws-orange));
        }
        
        .header h1 {
            font-size: 2.5em;
            font-weight: 600;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .header .subtitle {
            font-size: 1.1em;
            opacity: 0.9;
            font-weight: 300;
        }
        
        .container {
            max-width: 1100px;
            margin: 0 auto;
            background: white;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
        
        .toc-section {
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            padding: 30px 40px;
            border-bottom: 3px solid var(--aws-orange);
        }
        
        .toc-title {
            font-size: 1.4em;
            color: var(--aws-dark);
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .toc-title::before {
            content: '📑';
            font-size: 1.2em;
        }
        
        .toc-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 12px;
        }
        
        .toc-item {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 12px 16px;
            background: white;
            border-radius: 8px;
            text-decoration: none;
            color: var(--aws-dark);
            font-weight: 500;
            transition: all 0.2s ease;
            border: 1px solid #dee2e6;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        
        .toc-item:hover {
            background: var(--aws-dark);
            color: white;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        
        .toc-icon {
            font-size: 1.3em;
        }
        
        .content {
            padding: 40px;
        }
        
        h1 { display: none; }
        
        h2 {
            color: var(--aws-dark);
            font-size: 1.8em;
            margin: 50px 0 25px 0;
            padding: 15px 20px;
            background: linear-gradient(90deg, var(--aws-dark) 0%, #37475a 100%);
            color: white;
            border-radius: 8px;
            position: relative;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        
        h2::after {
            content: '';
            position: absolute;
            bottom: -8px;
            left: 20px;
            width: 60px;
            height: 4px;
            background: var(--aws-orange);
            border-radius: 2px;
        }
        
        h2:first-of-type {
            margin-top: 0;
        }
        
        h3 {
            color: var(--aws-dark);
            font-size: 1.4em;
            margin: 35px 0 15px 0;
            padding-bottom: 10px;
            border-bottom: 2px solid #e9ecef;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        h3::before {
            content: '▸';
            color: var(--aws-orange);
            font-weight: bold;
        }
        
        h4 {
            color: #495057;
            font-size: 1.15em;
            margin: 25px 0 12px 0;
            padding-left: 15px;
            border-left: 4px solid var(--aws-orange);
        }
        
        p {
            margin-bottom: 16px;
            line-height: 1.8;
            color: #444;
        }
        
        ul {
            margin: 15px 0 20px 0;
            padding-left: 0;
            list-style: none;
        }
        
        li {
            margin-bottom: 10px;
            padding: 8px 12px 8px 35px;
            position: relative;
            background: #f8f9fa;
            border-radius: 6px;
            border-left: 3px solid var(--aws-orange);
        }
        
        li::before {
            content: '✓';
            position: absolute;
            left: 12px;
            color: var(--success-green);
            font-weight: bold;
        }
        
        code {
            background: #fff3e0;
            padding: 3px 8px;
            border-radius: 4px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 0.9em;
            color: #e65100;
            border: 1px solid #ffe0b2;
        }
        
        pre {
            background: linear-gradient(135deg, #1e1e1e 0%, #2d2d2d 100%);
            color: #d4d4d4;
            padding: 25px;
            border-radius: 10px;
            overflow-x: auto;
            margin: 20px 0;
            box-shadow: inset 0 2px 10px rgba(0,0,0,0.3), 0 4px 15px rgba(0,0,0,0.1);
            border: 1px solid #444;
        }
        
        pre.shell-block {
            background: linear-gradient(135deg, #0d1117 0%, #161b22 100%);
            border: 1px solid #30363d;
            position: relative;
        }
        
        pre.shell-block::before {
            content: 'Terminal';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            background: linear-gradient(90deg, #238636, #2ea043);
            color: white;
            padding: 6px 15px;
            font-size: 0.75em;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            border-radius: 9px 9px 0 0;
        }
        
        pre.shell-block code {
            display: block;
            margin-top: 25px;
        }
        
        .shell-prompt {
            color: #58a6ff;
            font-weight: bold;
            user-select: none;
        }
        
        pre code {
            background: none;
            color: #9cdcfe;
            padding: 0;
            border: none;
            font-size: 0.95em;
        }
        
        pre.shell-block code {
            color: #c9d1d9;
        }
        
        a {
            color: var(--info-blue);
            text-decoration: none;
            border-bottom: 1px dotted var(--info-blue);
            transition: all 0.2s;
        }
        
        a:hover {
            color: var(--aws-orange);
            border-bottom-color: var(--aws-orange);
        }
        
        hr {
            border: none;
            height: 2px;
            background: linear-gradient(90deg, transparent, #dee2e6, transparent);
            margin: 40px 0;
        }
        
        .doc-table {
            width: 100%;
            border-collapse: collapse;
            margin: 25px 0;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        
        .doc-table th {
            background: linear-gradient(135deg, var(--aws-dark) 0%, #37475a 100%);
            color: white;
            padding: 15px 20px;
            text-align: left;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.85em;
            letter-spacing: 0.5px;
        }
        
        .doc-table td {
            padding: 14px 20px;
            border-bottom: 1px solid #e9ecef;
        }
        
        .doc-table tr:nth-child(even) {
            background: #f8f9fa;
        }
        
        .doc-table tr:hover {
            background: #fff3e0;
        }
        
        /* Status badges */
        .status-supported { color: var(--success-green); }
        .status-approaching { color: var(--warning-yellow); }
        .status-extended { color: var(--info-blue); }
        .status-out { color: var(--danger-red); }
        
        /* Info boxes */
        .info-box {
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            border-left: 5px solid;
        }
        
        .info-box.tip {
            background: #e8f5e9;
            border-color: var(--success-green);
        }
        
        .info-box.warning {
            background: #fff8e1;
            border-color: var(--warning-yellow);
        }
        
        .info-box.info {
            background: #e3f2fd;
            border-color: var(--info-blue);
        }
        
        /* Footer */
        .footer {
            background: var(--aws-dark);
            color: #adb5bd;
            text-align: center;
            padding: 20px;
            font-size: 0.9em;
        }
        
        /* Back to top button */
        .back-to-top {
            position: fixed;
            bottom: 30px;
            right: 30px;
            background: var(--aws-orange);
            color: white;
            width: 50px;
            height: 50px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            text-decoration: none;
            font-size: 1.5em;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            transition: all 0.3s;
            border: none;
        }
        
        .back-to-top:hover {
            background: var(--aws-dark);
            transform: translateY(-3px);
        }
        
        /* Smooth scrolling */
        html {
            scroll-behavior: smooth;
        }
        
        /* Print styles */
        @media print {
            body { background: white; }
            .container { box-shadow: none; }
            .back-to-top { display: none; }
            .header { background: white; color: black; }
            h2 { background: none; color: black; border: 2px solid #333; }
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .header { padding: 20px; }
            .header h1 { font-size: 1.8em; }
            .content { padding: 20px; }
            .toc-grid { grid-template-columns: 1fr; }
            h2 { font-size: 1.4em; }
        }
        """
    
    def generate(self) -> str:
        """Generate the complete HTML document."""
        markdown_content = self.read_markdown()
        body_html = self.convert_markdown_to_html(markdown_content)
        toc_html = self.generate_toc_html()
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AWS End-of-Support Tool - User Guide</title>
    <style>{self.get_css()}</style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>AWS End-of-Support Tool</h1>
            <div class="subtitle">📖 User Guide &amp; Documentation</div>
        </div>
        
        <div class="toc-section">
            <div class="toc-title">Quick Navigation</div>
            <div class="toc-grid">
                {toc_html}
            </div>
        </div>
        
        <div class="content">
            {body_html}
        </div>
        
        <div class="footer">
            AWS End-of-Support Tool &bull; Last updated: February 2026
        </div>
    </div>
    
    <a href="#" class="back-to-top" title="Back to top">↑</a>
</body>
</html>"""
    
    def save(self):
        """Generate and save the HTML document."""
        html_content = self.generate()
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"HTML user guide generated: {self.output_path.absolute()}")
        return self.output_path


def main():
    generator = HTMLUserGuideGenerator()
    output_path = generator.save()
    print(f"Open in browser: file:///{output_path.absolute()}")


if __name__ == "__main__":
    main()
