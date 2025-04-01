#!/usr/bin/env python3
import sys
import urllib.parse
import requests
import re

def clean_html(text):
    """Remove HTML tags and clean up the text for better readability."""
    # Remove script and style sections
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    # Replace HTML entities
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&quot;', '"', text)
    # Remove remaining HTML tags
    text = re.sub(r'<[^>]*>', '', text)
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return text

def make_http_request(url):
    """Make an HTTP GET request to the specified URL and clean the HTML response."""
    max_redirects = 5  # Maximum number of redirects to follow
    current_redirects = 0
    
    while True:
        try:
            # Make request with redirect tracking
            response = requests.get(url, allow_redirects=False)
            
            # Check if this is a redirect
            if response.is_redirect or response.is_permanent_redirect:
                current_redirects += 1
                
                # Check for redirect limit
                if current_redirects > max_redirects:
                    return f"Error: Too many redirects (limit: {max_redirects})"
                
                # Get the redirect URL
                redirect_url = response.headers.get('Location')
                if not redirect_url:
                    return "Error: Redirect location not specified"
                
                # Handle relative URLs
                if not redirect_url.startswith(('http://', 'https://')):
                    redirect_url = urllib.parse.urljoin(url, redirect_url)
                
                print(f"Redirecting to: {redirect_url}")
                url = redirect_url
                continue
            
            # Handle successful response
            if response.status_code == 200:
                # Clean HTML if content is text/html
                if 'text/html' in response.headers.get('content-type', ''):
                    return clean_html(response.text)
                return response.text
            
            # Handle other status codes
            return f"Error: Status code {response.status_code}"
            
        except Exception as e:
            return f"Error: {e}"

def search_duckduckgo(query):
    """Search DuckDuckGo and return the first 10 results."""
    encoded_query = urllib.parse.quote(query)
    search_url = f"https://html.duckduckgo.com/html?q={encoded_query}"
    try:
        response = requests.get(search_url)
        links = []
        for line in response.text.split('\n'):
            if 'href="' in line:
                link_start = line.find('href="') + 6
                link_end = line.find('"', link_start)
                if link_start != -1 and link_end != -1:
                    links.append(line[link_start:link_end])
        return "\n".join(links[:10])
    except Exception as e:
        return f"Error: {e}"

def main():
    """Command-line argument handling."""
    if len(sys.argv) < 2:
        print("Usage: go2web -u <URL> | -s <search-term> | -h")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "-h":
        print("Usage:")
        print("  go2web -u <URL>         # Fetches and prints cleaned content from the URL")
        print("  go2web -s <search-term> # Searches the term on DuckDuckGo and shows top 10 results")
        print("  go2web -h               # Displays this help message")
        
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