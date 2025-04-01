#!/usr/bin/env python3
import socket
import ssl
import sys
import re
import time
import urllib.parse
import os
import json
import hashlib
import json

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

CACHE_DIR = os.path.join(os.path.expanduser("~"), ".go2web_cache")
CACHE_EXPIRATION = 600  # 10 minutes (600 seconds)
MAX_REDIRECTS = 5

# Ensure cache directory exists
os.makedirs(CACHE_DIR, exist_ok=True)


def generate_cache_key(url):
    """Generate a unique, filesystem-safe cache key for a given URL."""
    return hashlib.sha256(url.encode()).hexdigest()


def get_from_cache(url):
    """Retrieve cached response from file if it is still valid."""
    cache_key = generate_cache_key(url)
    cache_file = os.path.join(CACHE_DIR, cache_key + ".json")

    try:
        if os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

            # Check if cache has expired
            if time.time() - cache_data['timestamp'] < CACHE_EXPIRATION:
                print(f"[CACHE HIT] Returning cached response for {url}")
                return cache_data['content']

    except (json.JSONDecodeError, IOError) as e:
        print(f"Cache read error: {e}")

    return None


def store_in_cache(url, response):
    """Store the response in a file cache with a timestamp."""
    cache_key = generate_cache_key(url)
    cache_file = os.path.join(CACHE_DIR, cache_key + ".json")

    try:
        cache_data = {
            'timestamp': time.time(),
            'url': url,
            'content': response
        }

        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False)
    except IOError as e:
        print(f"Cache write error: {e}")


def parse_content(headers, body, content_type):
    """
    Parse content based on content type.

    Args:
        headers (str): HTTP headers
        body (bytes): Response body
        content_type (str): Content-Type header value

    Returns:
        str: Parsed and cleaned content
    """
    body_text = body.decode(errors="ignore")

    if 'application/json' in content_type.lower():
        # JSON parsing
        try:
            # Try to pretty print JSON
            parsed_json = json.loads(body_text)
            return json.dumps(parsed_json, indent=2)
        except json.JSONDecodeError:
            return body_text

    elif 'text/html' in content_type.lower():
        # HTML cleaning (existing method)
        return clean_html(body_text)

    elif 'text/plain' in content_type.lower():
        # Plain text, return as-is
        return body_text

    # Default fallback
    return body_text


def make_http_request(host, path, is_https=False, redirect_count=0):
    """Manually performs an HTTP GET request using sockets, handling HTTPS and relative/absolute redirections."""

    if redirect_count > MAX_REDIRECTS:
        return "Error: Too many redirects"

    # Normalize path
    path = path if path.startswith("/") else "/" + path
    url = f"{'https' if is_https else 'http'}://{host}{path}"

    try:
        port = 443 if is_https else 80
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        if is_https:
            context = ssl.create_default_context()
            s = context.wrap_socket(s, server_hostname=host)

        s.connect((host, port))

        # HTTP request
        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}\r\n"
            f"User-Agent: {USER_AGENT}\r\n"
            f"Accept: text/html, application/json, text/plain\r\n"
            "Connection: close\r\n\r\n"
        )
        s.sendall(request.encode())

        response = b""
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            response += chunk
        s.close()

        response_text = response.decode(errors="ignore")

        # Handle redirection (301, 302)
        if 'HTTP/1.1 301' in response_text or 'HTTP/1.1 302' in response_text:
            match = re.search(r"Location: ([^\r\n]+)", response_text)
            if match:
                redirect_url = match.group(1).strip()
                print(f"Redirecting to: {redirect_url}")

                # Resolve relative paths
                redirect_url = urllib.parse.urljoin(url, redirect_url)
                parsed_url = urllib.parse.urlparse(redirect_url)

                return make_http_request(parsed_url.netloc, parsed_url.path or "/",
                                         is_https=(parsed_url.scheme == "https"),
                                         redirect_count=redirect_count + 1)

        # Extract headers and body
        headers, body = response.split(b"\r\n\r\n", 1)
        headers_str = headers.decode(errors="ignore")

        # Extract content type (default to text/html if not specified)
        content_type_match = re.search(r"Content-Type:\s*([^\r\n]+)", headers_str, re.IGNORECASE)
        content_type = content_type_match.group(1) if content_type_match else "text/html"

        return body.decode(errors="ignore")  # Returning content

    except Exception as e:
        return f"Error: {e}"


def clean_html(text):
    """Removes HTML tags and cleans up the text for better readability with trimmed output."""
    # Remove scripts and style sections completely
    text = re.sub(r'<script[^>]*>.*?</script>', ' ', text, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', ' ', text, flags=re.DOTALL)

    # Replace common HTML entities
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&quot;', '"', text)

    # Remove special Unicode and hex entities (like &#xE5CF;)
    text = re.sub(r'&#x[0-9A-Fa-f]+;', '', text)
    text = re.sub(r'&#[0-9]+;', '', text)

    # Replace block elements with newlines
    text = re.sub(r'<br[^>]*>', '\n', text)
    text = re.sub(r'</p>', '\n\n', text)
    text = re.sub(r'</div>', '\n', text)
    text = re.sub(r'</h[1-6]>', '\n\n', text)
    text = re.sub(r'</tr>', '\n', text)
    text = re.sub(r'</li>', '\n', text)

    # Add newlines for common block elements
    text = re.sub(r'<(div|p|h[1-6]|tr|td|li|ul|ol)[^>]*>', '\n', text)

    # Remove all remaining HTML tags
    text = re.sub(r'<[^>]*>', '', text)

    # Clean up excessive whitespace
    text = re.sub(r' +', ' ', text)  # Multiple spaces to single space
    text = re.sub(r'\t+', ' ', text)  # Tabs to space

    # Process line by line
    lines = []
    for line in text.split('\n'):
        line = line.strip()
        # Skip empty lines and lines with just special characters
        if line and not re.match(r'^[\s\*\=\-\_\+\.\,\;\:]*$', line):
            lines.append(line)

    # Join non-empty lines
    text = '\n'.join(lines)

    # Remove redundant newlines
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Remove common junk text patterns (customize as needed)
    text = re.sub(r'[0-9]+\s*\>', '', text)  # Remove patterns like "767>"
    text = re.sub(r'minProd\)\s*&&\s*\(\$index', '', text)  # Remove code fragments

    return text.strip()


def search_duckduckgo(query):
    """Search DuckDuckGo and return the first 10 results."""
    encoded_query = urllib.parse.quote(query)
    search_path = f"/html/?q={encoded_query}"

    cached_response = get_from_cache(search_path)
    if cached_response:
        return cached_response

    response = make_http_request("html.duckduckgo.com", search_path)
    links = re.findall(r'<a rel="nofollow" href="(https?://[^"]+)"', response)

    if not links:
        return "No results found."

    result = "\n".join(links[:10])
    store_in_cache(search_path, result)
    return result


def main():
    """Command-line argument handling."""
    if len(sys.argv) < 2:
        print("Usage: go2web -u <URL> | -s <search-term> | -h")
        sys.exit(1)

    command = sys.argv[1]

    if command == "-h":
        print("Usage:")
        print("  go2web -u <URL>         # Fetches and prints content from the URL")
        print("  go2web -s <search-term> # Searches the term on DuckDuckGo and shows top 10 results")
        print("  go2web -h               # Displays this help message")
        print(f"  Cache directory: {CACHE_DIR}")

    elif command == "-u" and len(sys.argv) > 2:
        url = sys.argv[2]
        # Remove any protocol prefix if present
        if "://" in url:
            url = url.split("://")[1]
        
        # Split into host and path, defaulting to root path if no path given
        parts = url.split("/", 1)
        host = parts[0]
        path = "/" + parts[1] if len(parts) > 1 else "/"
        
        # Determine if HTTPS should be used (you might want to try HTTPS first)
        is_https = False  # Default to HTTP
        
        print(make_http_request(host, path, is_https))

    elif command == "-s" and len(sys.argv) > 2:
        query = " ".join(sys.argv[2:])
        print(search_duckduckgo(query))

    else:
        print("Invalid command. Use -h for help.")


if __name__ == "__main__":
    main()