#!/usr/bin/env python3
"""
Simple Markdown viewer that uses the Python-Markdown library.
Uses proper HTML/CSS to render Markdown files with correct formatting.
"""
import os
import re
import sys
import http.server
import socketserver
from pathlib import Path
from urllib.parse import unquote, urlparse

# Try to import required libraries, use fallbacks if not available
try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False
    print("Warning: Python-Markdown not installed. Install with 'pip install markdown' for better rendering.")

# Base directory for serving files
BASE_DIR = Path(__file__).parent / "output"

# Simple CSS for Markdown rendering
CSS = """
<style>
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
        line-height: 1.6;
        color: #333;
        max-width: 800px;
        margin: 0 auto;
        padding: 20px;
    }
    h1, h2, h3, h4, h5, h6 {
        margin-top: 24px;
        margin-bottom: 16px;
        font-weight: 600;
        line-height: 1.25;
    }
    h1 { font-size: 2em; border-bottom: 1px solid #eaecef; padding-bottom: .3em; }
    h2 { font-size: 1.5em; border-bottom: 1px solid #eaecef; padding-bottom: .3em; }
    h3 { font-size: 1.25em; }
    h4 { font-size: 1em; }
    p, blockquote, ul, ol, dl, table, pre {
        margin-top: 0;
        margin-bottom: 16px;
    }
    ul, ol {
        padding-left: 2em;
    }
    li+li {
        margin-top: 0.25em;
    }
    blockquote {
        padding: 0 1em;
        color: #6a737d;
        border-left: 0.25em solid #dfe2e5;
    }
    code {
        font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace;
        padding: 0.2em 0.4em;
        margin: 0;
        font-size: 85%;
        background-color: rgba(27,31,35,0.05);
        border-radius: 3px;
    }
    pre {
        word-wrap: normal;
        padding: 16px;
        overflow: auto;
        line-height: 1.45;
        background-color: #f6f8fa;
        border-radius: 3px;
    }
    pre code {
        background-color: transparent;
        padding: 0;
        margin: 0;
        font-size: 100%;
        word-break: normal;
        white-space: pre;
    }
    a {
        color: #0366d6;
        text-decoration: none;
    }
    a:hover {
        text-decoration: underline;
    }
    table {
        border-spacing: 0;
        border-collapse: collapse;
        margin-top: 0;
        margin-bottom: 16px;
    }
    table th {
        font-weight: 600;
        padding: 6px 13px;
        border: 1px solid #dfe2e5;
    }
    table td {
        padding: 6px 13px;
        border: 1px solid #dfe2e5;
    }
    table tr {
        background-color: #fff;
        border-top: 1px solid #c6cbd1;
    }
    table tr:nth-child(2n) {
        background-color: #f6f8fa;
    }
    hr {
        height: 0.25em;
        padding: 0;
        margin: 24px 0;
        background-color: #e1e4e8;
        border: 0;
    }
    .breadcrumb {
        margin-bottom: 20px;
        padding: 8px 15px;
        background-color: #f8f9fa;
        border-radius: 4px;
    }
    .breadcrumb a {
        margin: 0 5px;
    }
    .file-list {
        list-style-type: none;
        padding: 0;
    }
    .file-list li {
        padding: 8px;
        border-bottom: 1px solid #eee;
    }
    .file-list li:last-child {
        border-bottom: none;
    }
    .folder-icon::before {
        content: "📁 ";
    }
    .file-icon::before {
        content: "📄 ";
    }

</style>
"""

def simple_markdown_to_html(markdown_text):
    """
    Convert markdown to HTML using the Python-Markdown library if available,
    or fallback to a simple regex-based method.
    """
    if MARKDOWN_AVAILABLE:
        # Use the Python-Markdown library which properly handles all markdown features
        # Enable the 'extra' extension for tables, footnotes, etc.
        return markdown.markdown(markdown_text, extensions=['extra', 'nl2br'])
    else:
        # Fallback to basic parsing if Python-Markdown is not available
        html = markdown_text
        
        # Headers
        html = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^#### (.*?)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
        html = re.sub(r'^##### (.*?)$', r'<h5>\1</h5>', html, flags=re.MULTILINE)
        html = re.sub(r'^###### (.*?)$', r'<h6>\1</h6>', html, flags=re.MULTILINE)
        
        # Bold and Italic
        html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)
        
        # Links
        html = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', html)
        
        # Code blocks
        html = re.sub(r'```(?:\w+)?\n(.*?)\n```', lambda m: '<pre><code>' + m.group(1).replace('\n', '<br>') + '</code></pre>', html, flags=re.DOTALL)
        
        # Inline code
        html = re.sub(r'`(.*?)`', r'<code>\1</code>', html)
        
        # Paragraphs with proper line break handling
        paragraphs = []
        for para in html.split('\n\n'):
            if not (para.startswith('<h') or para.startswith('<pre')):
                # Replace single newlines with <br> tags to preserve line breaks
                para = para.replace('\n', '<br>\n')
                para = f'<p>{para}</p>'
            paragraphs.append(para)
        
        html = '\n\n'.join(paragraphs)
        
        return html

class MarkdownHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)
    
    def list_directory(self, path):
        """Helper to produce a directory listing (absent index.html).
        
        Return value is either a file object, or None (indicating an
        error).  In either case, the headers are sent, making the
        interface the same as for send_head().
        """
        try:
            list_dir = os.listdir(path)
        except OSError:
            self.send_error(404, "No permission to list directory")
            return None
        
        list_dir.sort(key=lambda a: a.lower())
        
        r = []
        title = f"Directory listing for {self.path}"
        r.append('<!DOCTYPE HTML>')
        r.append('<html>')
        r.append('<head>')
        r.append(f'<title>{title}</title>')
        r.append(CSS)
        r.append('</head>')
        r.append('<body>')
        r.append(f'<h1>{title}</h1>')
        
        # Add breadcrumb navigation
        parts = self.path.split('/')
        breadcrumb = '<div class="breadcrumb">'
        breadcrumb += '<a href="/">Home</a>'
        cumulative_path = ""
        for part in parts:
            if part:
                cumulative_path += f"/{part}"
                breadcrumb += f' / <a href="{cumulative_path}">{part}</a>'
        breadcrumb += '</div>'
        r.append(breadcrumb)
        
        r.append('<ul class="file-list">')
        
        # Add parent directory link
        if self.path != '/':
            parent = os.path.dirname(self.path.rstrip('/'))
            if not parent:
                parent = '/'
            r.append(f'<li><a class="folder-icon" href="{parent}">Parent Directory</a></li>')
        
        # List directories first
        dirs = []
        files = []
        for name in list_dir:
            fullname = os.path.join(path, name)
            if os.path.isdir(fullname):
                dirs.append(name)
            else:
                files.append(name)
        
        # Add directories first
        for name in dirs:
            fullname = os.path.join(path, name)
            displayname = name + "/"
            linkname = name + "/"
            r.append(f'<li><a class="folder-icon" href="{linkname}">{displayname}</a></li>')
        
        # Then list files
        for name in files:
            fullname = os.path.join(path, name)
            displayname = name
            linkname = name
            
            if name.endswith('.md'):
                # For markdown files, show a descriptive name
                try:
                    with open(fullname, 'r', encoding='utf-8') as f:
                        first_line = f.readline().strip()
                        if first_line.startswith('# '):
                            displayname = first_line[2:] + f" ({name})"
                except:
                    pass  # Continue with default display name if error
            
            # Set appropriate icon class based on file type
            icon_class = "file-icon"
            if name.endswith(('.yml', '.yaml')):
                icon_class = "file-icon yaml-file"
                # For YAML files, try to show a descriptive first key if possible
                try:
                    if YAML_AVAILABLE:
                        with open(fullname, 'r', encoding='utf-8') as f:
                            yaml_data = yaml.safe_load(f)
                            if isinstance(yaml_data, dict) and yaml_data:
                                first_key = next(iter(yaml_data.keys()))
                                displayname = f"{first_key} ({name})"
                except:
                    pass  # Continue with default display name if error
            
            r.append(f'<li><a class="{icon_class}" href="{linkname}">{displayname}</a></li>')
        
        r.append('</ul>')
        r.append('</body>')
        r.append('</html>')
        
        encoded = '\n'.join(r).encode('utf-8')
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        # Return a BytesIO object which is file-like instead of raw bytes
        import io
        return io.BytesIO(encoded)
    
    def do_GET(self):
        """Serve a GET request."""
        # Parse the URL
        parsed_url = urlparse(self.path)
        path = unquote(parsed_url.path)
        
        # Convert the URL path to a local filesystem path
        fs_path = os.path.join(self.directory, path[1:])
        
        # Handle Markdown files
        if path.endswith('.md') and os.path.exists(fs_path):
            try:
                with open(fs_path, 'r', encoding='utf-8') as f:
                    markdown_content = f.read()
                
                # Get filename for title
                filename = os.path.basename(fs_path)
                
                # Convert Markdown to HTML
                html_content = simple_markdown_to_html(markdown_content)
                
                # Build the full HTML page with CSS
                full_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{filename}</title>
    {CSS}
</head>
<body>
    <div class="breadcrumb">
        <a href="/">Home</a> / 
        <a href="{os.path.dirname(path) or '/'}">{os.path.dirname(path[1:]) or 'parent'}</a>
    </div>
    {html_content}
</body>
</html>"""
                
                # Serve the HTML
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(full_html.encode('utf-8'))))
                self.end_headers()
                self.wfile.write(full_html.encode('utf-8'))
                return
            except Exception as e:
                self.send_error(500, f"Error rendering Markdown: {str(e)}")
                return
        
        # For other types of files, use the default handler
        return super().do_GET()

def run(port=8000):
    with socketserver.TCPServer(("", port), MarkdownHandler) as httpd:
        print(f"Serving Markdown files at http://localhost:{port}")
        httpd.serve_forever()

if __name__ == "__main__":
    port = 8000
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    
    print(f"Markdown Viewer starting on port {port}...")
    print(f"Base directory: {BASE_DIR}")
    print("Press Ctrl+C to stop the server")
    
    try:
        run(port)
    except KeyboardInterrupt:
        print("\nShutting down server...")
        sys.exit(0)
