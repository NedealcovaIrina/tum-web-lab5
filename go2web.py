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
from bs4 import BeautifulSoup

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
CACHE_DIR = "C:\\Users\\User\\Desktop\\Univer 3\\WEB_UTM\\tum-web-lab-gotoweb\\tum-web-lab5\\cache"
print('TGHGGGTNTTHNH',CACHE_DIR)
CACHE_EXPIRATION = 600  # 10 minutes
MAX_REDIRECTS = 5

os.makedirs(CACHE_DIR, exist_ok=True)


def generate_cache_key(url):
    return hashlib.sha256(url.encode()).hexdigest()


def get_from_cache(url):
    """Retrieve cached response if valid."""
    cache_key = generate_cache_key(url)
    cache_file = os.path.join(CACHE_DIR, cache_key + ".json")

    if os.path.exists(cache_file):
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        if time.time() - cache_data['timestamp'] < CACHE_EXPIRATION:
            print(f"\n[CACHE] Loading data from cache for URL: {url}")
            print(f"[CACHE] Cache file: {cache_file}")
            print("-" * 50)
            return cache_data['content']
    return None


def store_in_cache(url, response):
    """Store response in cache."""
    cache_key = generate_cache_key(url)
    cache_file = os.path.join(CACHE_DIR, cache_key + ".json")
    cache_data = {
        'timestamp': time.time(),
        'url': url,
        'content': response
    }
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, ensure_ascii=False)
    print(f"[CACHE] Saved to cache: {cache_file}")


def extract_text(html):
    """Extracts readable text from HTML."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove unwanted tags (JavaScript, CSS, metadata, iframes, etc.)
    for element in soup(["script", "style", "meta", "noscript", "iframe", "link"]):
        element.decompose()

    # Get visible text
    text = soup.get_text(separator="\n", strip=True)

    # Clean up excessive blank lines
    return "\n".join(line for line in text.splitlines() if line.strip())


def make_http_request(url, redirect_count=0):
    """Make an HTTP/HTTPS request manually using sockets and return extracted text."""
    if redirect_count > MAX_REDIRECTS:
        return "Error: Too many redirects"

    parsed_url = urllib.parse.urlparse(url)
    if not parsed_url.netloc:
        return "Error: Invalid URL"

    host, path = parsed_url.netloc, parsed_url.path or "/"
    is_https = parsed_url.scheme == "https"

    cached_response = get_from_cache(url)
    if cached_response:
        return cached_response

    try:
        port = 443 if is_https else 80
        s = socket.create_connection((host, port))

        if is_https:
            context = ssl.create_default_context()
            s = context.wrap_socket(s, server_hostname=host)

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

        headers, body = response.split(b"\r\n\r\n", 1)
        headers_str = headers.decode(errors="ignore")

        # Handle redirects
        if "HTTP/1.1 301" in headers_str or "HTTP/1.1 302" in headers_str:
            match = re.search(r"Location: ([^\r\n]+)", headers_str)
            if match:
                redirect_url = urllib.parse.urljoin(url, match.group(1).strip())
                print(f"Redirecting to: {redirect_url}")
                return make_http_request(redirect_url, redirect_count + 1)

        response_text = body.decode(errors="ignore")

        # Extract and clean text
        extracted_text = extract_text(response_text)
        store_in_cache(url, extracted_text)

        return extracted_text

    except Exception as e:
        return f"Error: {e}"


def search_duckduckgo(query):
    """Search DuckDuckGo and return first 10 results."""
    encoded_query = urllib.parse.quote(query)
    search_path = f"/html/?q={encoded_query}"

    cached_response = get_from_cache(search_path)
    if cached_response:
        return cached_response

    response = make_http_request("https://html.duckduckgo.com" + search_path)
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
        print("  go2web -u <URL>         # Fetch and display text from a URL")
        print("  go2web -s <search-term> # Search term on DuckDuckGo and show top 10 results")
        print("  go2web -h               # Display this help message")
        print(f"  Cache directory: {CACHE_DIR}")

    elif command == "-u" and len(sys.argv) > 2:
        url = sys.argv[2]
        print(make_http_request(url))

    elif command == "-s" and len(sys.argv) > 2:
        query = " ".join(sys.argv[2:])
        print(search_duckduckgo(query))

    else:
        print("Invalid command. Use -h for help.")


if __name__ == "__main__":
    main()
