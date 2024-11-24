import requests
from bs4 import BeautifulSoup
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Scraping BBC News
def scrape_bbc():
    print("Scraping BBC News...")
    url = "https://www.bbc.com/news/world/asia/india"
    
    # Setup Selenium WebDriver
    options = Options()
    options.add_argument("--headless")  # Run in headless mode
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(url)
    
    # Parse page with BeautifulSoup
    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()
    
    articles = []
    for item in soup.find_all('div', class_='gs-c-promo'):
        title = item.find('h3')
        link = item.find('a', href=True)
        summary = item.find('p')
        date = item.find('time')
        if title and link:
            articles.append({
                "Title": title.text.strip(),
                "Summary": summary.text.strip() if summary else "No summary available",
                "Publication Date": date['datetime'] if date else "Unknown",
                "Source": "BBC",
                "URL": f"https://www.bbc.com{link['href']}"
            })
    print(f"BBC: {len(articles)} articles scraped.")
    return articles

# Scraping CNN News
def scrape_cnn():
    print("Scraping CNN News...")
    url = "https://edition.cnn.com/world"
    
    # Send GET request
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to fetch CNN page. Status code: {response.status_code}")
        return []
    
    # Parse page with BeautifulSoup
    soup = BeautifulSoup(response.text, "html.parser")
    articles = []
    for item in soup.find_all('div', class_='card'):
        title = item.find('h3')
        link = item.find('a', href=True)
        summary = item.find('div', class_='content')
        if title and link:
            articles.append({
                "Title": title.text.strip(),
                "Summary": summary.text.strip() if summary else "No summary available",
                "Publication Date": "Unknown",
                "Source": "CNN",
                "URL": f"https://edition.cnn.com{link['href']}"
            })
    print(f"CNN: {len(articles)} articles scraped.")
    return articles

# Main Scraping Function
def scrape_news():
    bbc_articles = scrape_bbc()
    cnn_articles = scrape_cnn()
    all_articles = bbc_articles + cnn_articles

    # Save to CSV
    if all_articles:
        df = pd.DataFrame(all_articles)
        df.to_csv("news_articles.csv", index=False)
        print("Scraping completed. Data saved to news_articles.csv")
    else:
        print("No articles found. CSV file not created.")

# Run the scraper
if __name__ == "__main__":
    scrape_news()

import pandas as pd
from textblob import TextBlob

# Load data
df = pd.read_csv("news_articles.csv")

# Categorize articles using simple NLP (based on keywords)
def categorize_article(summary):
    if "politics" in summary.lower():
        return "Politics"
    elif "technology" in summary.lower() or "tech" in summary.lower():
        return "Technology"
    elif "sports" in summary.lower():
        return "Sports"
    else:
        return "General"

df["Category"] = df["Summary"].apply(categorize_article)

# Save updated data
df.to_csv("news_articles.csv", index=False)
print("Categorization completed. Updated data saved to news_articles.csv")
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
import pandas as pd
from typing import Optional

# Load the data
def load_data():
    try:
        df = pd.read_csv("news_articles.csv")
        df.fillna("Unknown", inplace=True)
        df["id"] = range(1, len(df) + 1)  # Add an ID column
        return df
    except FileNotFoundError:
        raise RuntimeError("news_articles.csv not found.")

articles_df = load_data()

# Initialize FastAPI app
app = FastAPI()

@app.get("/")
def root():
    return {"message": "Welcome to the News API!"}

@app.get("/articles")
def get_articles(
    category: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    filtered_df = articles_df

    if category:
        filtered_df = filtered_df[filtered_df["Category"].str.lower() == category.lower()]
    if start_date:
        filtered_df = filtered_df[filtered_df["Publication Date"] >= start_date]
    if end_date:
        filtered_df = filtered_df[filtered_df["Publication Date"] <= end_date]

    return JSONResponse(content=filtered_df.to_dict(orient="records"))

@app.get("/articles/{id}")
def get_article_by_id(id: int):
    article = articles_df[articles_df["id"] == id]
    if article.empty:
        raise HTTPException(status_code=404, detail="Article not found")
    return JSONResponse(content=article.iloc[0].to_dict())

@app.get("/search")
def search_articles(keyword: str):
    filtered_df = articles_df[
        articles_df["Title"].str.contains(keyword, case=False, na=False) |
        articles_df["Summary"].str.contains(keyword, case=False, na=False)
    ]
    if filtered_df.empty:
        raise HTTPException(status_code=404, detail="No articles found")
    return JSONResponse(content=filtered_df.to_dict(orient="records"))

# Run the app (for local testing)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
