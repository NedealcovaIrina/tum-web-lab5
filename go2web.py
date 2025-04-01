#!/usr/bin/env python3
import sys
import urllib.parse
import re

def clean_html(text):
    """Removes HTML tags and unnecessary whitespace."""
    text = re.sub(r'<script[^>]*>.*?</script>', ' ', text, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', ' ', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', '', text)  # Remove all HTML tags
    text = re.sub(r'\s+', ' ', text).strip()  # Normalize whitespace
    return text

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

    elif command == "-u" and len(sys.argv) > 2:
        url = sys.argv[2]
        print(f"Fetching content from: {url}")
        # Placeholder for actual request function
        response = "<html><body><h1>Example</h1><p>This is a test.</p></body></html>"  # Example response
        print("Cleaned Content:", clean_html(response))

    elif command == "-s" and len(sys.argv) > 2:
        query = " ".join(sys.argv[2:])
        encoded_query = urllib.parse.quote(query)
        print(f"Searching for: {query}")
        # Placeholder for actual search function
    
    else:
        print("Invalid command. Use -h for help.")

if __name__ == "__main__":
    main()
