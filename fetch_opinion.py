import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import date
import os
import re

BASE_URL = "http://opinion.people.com.cn/GB/159301/"
DATE_PATTERN = re.compile(r"(20\d{2})-(\d{2})-(\d{2})")

def parse_date(text):
    match = DATE_PATTERN.search(text)
    if not match:
        return None
    year, month, day = map(int, match.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None

def fetch_soup(url):
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    response.encoding = "utf-8"
    return BeautifulSoup(response.text, "html.parser")

def get_latest_articles(soup):
    articles = []
    today = date.today()

    for link in soup.find_all("a", href=True):
        title = link.get_text(strip=True)
        href = link["href"]
        if not title or "/n1/" not in href or not href.endswith(".html"):
            continue

        parent_text = link.parent.get_text(" ", strip=True) if link.parent else ""
        published_at = parse_date(parent_text)
        if not published_at or published_at > today:
            continue

        articles.append((published_at, title, urljoin(BASE_URL, href)))

    if not articles:
        return None, []

    latest_date = max(published_at for published_at, _, _ in articles)
    latest_articles = []
    seen_urls = set()
    for published_at, title, url in articles:
        if published_at != latest_date or url in seen_urls:
            continue
        seen_urls.add(url)
        latest_articles.append((title, url))

    return latest_date, latest_articles

def get_article_text(url):
    soup = fetch_soup(url)
    body = soup.find("div", class_="rm_txt_con") or soup.find("div", id="rwb_zw")
    if not body:
        return "（正文获取失败）"

    for node in body.select("script, style"):
        node.decompose()

    lines = []
    for line in body.get_text(separator="\n", strip=True).splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("分享让更多人看到"):
            continue
        lines.append(line)

    return "\n".join(lines) if lines else "（正文获取失败）"

def fetch_opinion():
    soup = fetch_soup(BASE_URL)
    latest_date, articles = get_latest_articles(soup)

    if not articles:
        if os.path.exists("opinion_articles.txt"):
            os.remove("opinion_articles.txt")
        print("未找到可推送的人民网每日评论")
        return

    latest_date_text = latest_date.strftime("%Y-%m-%d")
    print(f"找到 {len(articles)} 篇 {latest_date_text} 评论")

    content = f"===== 人民网每日评论（{latest_date_text}） =====\n\n"
    for i, (title, url) in enumerate(articles):
        try:
            print(f"正在下载 {i+1}/{len(articles)}: {title}")
            text = get_article_text(url)
            content += f"【{title}】\n{url}\n\n{text}\n\n{'='*40}\n\n"
        except Exception as e:
            print(f"下载失败: {e}")

    with open("opinion_articles.txt", "w", encoding="utf-8") as f:
        f.write(content)
    print("评论已保存到 opinion_articles.txt")

if __name__ == "__main__":
    fetch_opinion()
