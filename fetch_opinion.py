import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

def fetch_opinion():
    today = datetime.now().strftime("%Y-%m-%d")
    base_url = "http://opinion.people.com.cn/GB/159301/"
    
    response = requests.get(base_url)
    response.encoding = "gb18030"
    soup = BeautifulSoup(response.text, "html.parser")
    
    articles = []
    for link in soup.find_all("a", href=True):
        parent = link.parent
        text = parent.get_text()
        if today in text:
            title = link.get_text(strip=True)
            href = urljoin(base_url, link["href"])
            if title:
                articles.append((title, href))

    print(f"找到 {len(articles)} 篇今日评论")

    content = "===== 人民网每日评论 =====\n\n"
    for i, (title, url) in enumerate(articles):
        try:
            print(f"正在下载 {i+1}/{len(articles)}: {title}")
            r = requests.get(url)
            r.encoding = "gb18030"
            s = BeautifulSoup(r.text, "html.parser")
            body = s.find("div", class_="rm_txt_con") or s.find("div", id="rwb_zw")
            if body:
                text = body.get_text(separator="\n", strip=True)
            else:
                text = "（正文获取失败）"
            content += f"【{title}】\n{url}\n\n{text}\n\n{'='*40}\n\n"
        except Exception as e:
            print(f"下载失败: {e}")

    with open("opinion_articles.txt", "w", encoding="utf-8") as f:
        f.write(content)
    print("评论已保存到 opinion_articles.txt")

if __name__ == "__main__":
    fetch_opinion()
