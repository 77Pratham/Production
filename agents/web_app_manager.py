import webbrowser
import subprocess
import sys

def search_google(query):
    url = f"https://www.google.com/search?q={query}"
    webbrowser.open(url)
    return f"🌍 Searching Google for: {query}"

def open_website(site):
    if not site.startswith("http"):
        site = "https://" + site
    webbrowser.open(site)
    return f"🌍 Opened website: {site}"

def open_application(app_name):
    try:
        if sys.platform.startswith("win"):
            subprocess.Popen([app_name], shell=True)
        elif sys.platform.startswith("darwin"):
            subprocess.Popen(["open", "-a", app_name])
        else:
            subprocess.Popen([app_name])
        return f"🚀 Opened application: {app_name}"
    except Exception as e:
        return f"❌ Failed to open app: {str(e)}"
