#!/usr/bin/env python3
import sys
import urllib.parse
import requests

def make_http_request(url):
    """Make an HTTP GET request to the specified URL."""
    try:
        response = requests.get(url)
        return response.text
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
        print("  go2web -u <URL>         # Fetches and prints content from the URL")
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