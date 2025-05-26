import json
import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

output_path = "data/test_data.json"
base_url = "https://www.newsbreak.com"

# Setup headless browser
options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
wait = WebDriverWait(driver, 15)

def get_all_states():
    driver.get(f"{base_url}/locations")
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/locations/']")))
    links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/locations/']")
    return {link.text.strip(): link.get_attribute("href") for link in links if link.text.strip()}

def get_cities(state_url):
    driver.get(state_url)
    time.sleep(2)
    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/']")))
        links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/']")
        return {
            link.text.strip(): link.get_attribute("href")
            for link in links
            if link.text.strip() and "/locations/" not in link.get_attribute("href")
        }
    except Exception as e:
        print(f"[!] City load failed: {e}")
        return {}

def scroll_page():
    last_height = driver.execute_script("return document.body.scrollHeight")
    for _ in range(3):  # scroll 3 times to load content
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

def scrape_news_cards(city_url):
    driver.get(city_url)
    scroll_page()
    time.sleep(2)
    cards = driver.find_elements(By.CSS_SELECTOR, "a[href*='/news/']")
    articles = []
    seen = set()
    for card in cards[:5]:  # limit to 5 articles
        try:
            href = card.get_attribute("href")
            title = card.text.strip()
            full_url = base_url + href if href and href.startswith("/") else href
            if full_url and full_url not in seen and title and "Open in NewsBreak" not in title:

                content = extract_full_article(full_url)
                articles.append({
                    "title": title,
                    "url": full_url,
                    "content": content
                })
                seen.add(full_url)
        except Exception as e:
            print(f"[!] Failed to process article: {e}")
    return articles

def extract_full_article(article_url):
    try:
        res = requests.get(article_url, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        paragraphs = soup.select("p")
        text = " ".join(p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 40)
        return text[:2000] if text else "No content found"
    except Exception as e:
        return f"Error loading article: {e}"

def fallback_rss(city_url):
    try:
        res = requests.get(city_url.rstrip("/") + "/rss.xml", timeout=10)
        if res.status_code != 200:
            return []
        soup = BeautifulSoup(res.content, "xml")
        return [
            {
                "title": item.title.text,
                "url": item.link.text,
                "content": extract_full_article(item.link.text)
            }
            for item in soup.find_all("item")[:5]
        ]
    except Exception as e:
        return [{"title": "RSS failed", "url": "", "content": str(e)}]

def main():
    states = get_all_states()
    all_data = {}

    for state_name, state_url in states.items():
        print(f"\n🟦 State: {state_name}")
        cities = get_cities(state_url)
        state_data = {}

        for city_name, city_url in cities.items():
            print(f"   → City: {city_name}")
            news = scrape_news_cards(city_url)
            if not news:
                print(f"     ⚠ No HTML news, trying RSS...")
                news = fallback_rss(city_url)
            state_data[city_name] = news
            for item in news:
                print(f"     • {item['title']}")

        all_data[state_name] = state_data

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Saved all news to {output_path}")
    driver.quit()
if __name__ == "__main__":
    main()
