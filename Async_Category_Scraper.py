import requests
import aiohttp
import asyncio
from bs4 import BeautifulSoup
import csv

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}

fieldnames = [
    "Page Attribute","MainCategory","Title","Short description","Description","New","RegularPrice","SalePrice",
    "PublisherDescription","AuthorBio","ImageURL","Mapping","Author","Tags","Attribute 1","Attribute 2",
    "Attribute 3","Attribute 4","Attribute 5","Attribute 6","Attribute 7","Attribute 8","Attribute 9","Attribute 10",
    "Data 1","Data 2","Data 3","Data 4","Data 5","Data 6","Data 7","Data 8","Data 9","Data 10","Data 11","Rating"
]

base_url = "https://www.christianbook.com"

# --- SYNCHRONOUS CATEGORY COLLECTION ---
def find_deepest_uls(ul):
    found = []
    for li in ul.find_all("li", recursive=False):
        sub_ul = li.find("ul", recursive=False)
        if sub_ul:
            found.extend(find_deepest_uls(sub_ul))
        else:
            found.append(li)
    return found

def get_max_page(url):
    if "&page=" not in url:
        url = url + ("&" if "?" in url else "?") + "page=1"
    resp = requests.get(url, headers=headers)
    soup = BeautifulSoup(resp.text, "html.parser")
    max_page = 1
    try:
        span = soup.select_one('#main-content > div.CBD-PagingControls.bottom.active > div.CBD-PagingControlsPages > span')
        if span:
            strongs = span.find_all('strong')
            if len(strongs) >= 2:
                num = int(strongs[1].text)
                max_page = num
    except Exception:
        pass
    return max_page

def get_category_pages(root_url):
    response = requests.get(root_url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    tree = soup.select_one("div.CBD-CategoryTree ul.CBD-TreeCategories")
    category_pages = []
    if not tree:
        return category_pages
    deepest_lis = find_deepest_uls(tree)
    for li in deepest_lis:
        a = li.find("a", href=True)
        if a:
            href = a['href']
            if href.startswith("http"):
                full_url = href
            else:
                full_url = base_url + href
            max_page = get_max_page(full_url)
            category_pages.append((full_url, max_page))
            print(f"{full_url} | pages: {max_page}")
    print(f"Total categories collected: {len(category_pages)}.")
    return category_pages

# --- ASYNCHRONOUS PARSING ---
async def fetch(session, url):
    async with session.get(url, headers=headers) as response:
        return await response.text()

def extract_price(soup):
    sale = soup.select_one(".CBD-ProductDetailActionPrice")
    regular = soup.select_one(".CBD-ProductDetailActionRetail strike")
    return (
        sale.text.replace("Our Price", "").strip() if sale else "",
        regular.text.strip() if regular else ""
    )

def extract_info_dict(soup):
    info = {}
    columns = soup.select("div.CBD-TextContent-Columns td[valign='top']")
    for col in columns:
        for strong in col.find_all("strong"):
            label = strong.get_text(strip=True).rstrip(":")
            value = strong.next_sibling
            if value:
                value = value.strip().strip('" ')
                info[label] = value
    return info

def extract_additional_info(soup):
    # New working selector for the required text
    div = soup.select_one('div.CBD-ProductDetailSubSection div.CBD-Notifications > div:nth-of-type(2)')
    if div:
        return div.get_text(strip=True).lstrip('* ').strip()
    return ''

async def parse_book(session, product_url):
    html = await fetch(session, product_url)
    soup = BeautifulSoup(html, "html.parser")
    tags_tag = soup.select_one('div.CBD-ProductDetailSeries')
    tags_text = tags_tag.text.strip() if tags_tag else ""
    sale_price, regular_price = extract_price(soup)
    title = soup.select_one("h1.CBD-ProductDetailTitle")
    product_description = soup.select_one("div#CBD-PD-Description ~ div.CBD-TextContent")
    if not product_description or 'footer' in product_description.get('class', []) or len(product_description.get_text(strip=True)) > 3000:
        product_description = None
    publisher_block = soup.select_one("div.CBD-PD-Publisher-Description")
    if not publisher_block or 'footer' in publisher_block.get('class', []) or len(publisher_block.get_text(strip=True)) > 3000:
        publisher_block = None
    author_bio = soup.select_one("div#section-heading-Author-Bio ~ div.CBD-TextContent")
    if not author_bio or 'footer' in author_bio.get('class', []) or len(author_bio.get_text(strip=True)) > 3000:
        author_bio = None
    author_tag = soup.select_one("div.CBD-ProductDetailAuthor a")
    publisher_combo = soup.select_one("div.CBD-ProductDetailPublisher")
    author = author_tag.text.strip() if author_tag else ""
    attribute_3 = publisher_combo.text.strip() if publisher_combo else ""
    product_information = extract_info_dict(soup)
    # New block: получаем Data 11
    data_11 = extract_additional_info(soup)
    data = {
        "Description": product_description.get_text(separator="\n", strip=True) if product_description else "",
        "PublisherDescription": publisher_block.get_text(separator="\n", strip=True) if publisher_block else "",
        "AuthorBio": author_bio.get_text(separator="\n", strip=True) if author_bio else "",
        "Author": author,
        "Tags": tags_text,
        "Mapping": attribute_3,
        "Attribute 1": title.text.strip() if title else "",
        "Attribute 2": author,
        "Attribute 3": attribute_3,
        "Attribute 4": product_information.get("Number of Pages", ""),
        "Attribute 5": product_information.get("Vendor", ""),
        "Attribute 6": product_information.get("Publication Date", ""),
        "Attribute 7": product_information.get("Dimensions", ""),
        "Attribute 8": product_information.get("Weight", ""),
        "Attribute 9": "'" + product_information.get("ISBN", ""),
        "Attribute 10": "'" + product_information.get("ISBN-13", ""),
        "RegularPrice": regular_price,
        "SalePrice": sale_price,
        "Data 1": product_information.get("Text Color", ""),
        "Data 2": product_information.get("Text Size", ""),
        "Data 3": product_information.get("Note Size", ""),
        "Data 4": product_information.get("Thumb Index", ""),
        "Data 5": product_information.get("Ribbon Marker", ""),
        "Data 6": product_information.get("Spine", ""),
        "Data 7": product_information.get("Page Gilding", ""),
        "Data 8": product_information.get("Page Edges", ""),
        "Data 9": product_information.get("Stock No", ""),
        "Data 10": product_information.get("Imprintable", ""),
        "Data 11": data_11,
    }
    return data

async def parse_page(session, url):
    html = await fetch(session, url)
    soup = BeautifulSoup(html, "html.parser")
    book_links = []
    for li in soup.select("li.CB-ProductListItem"):
        title_tag = li.select_one("div.CB-ProductListItem-TitleAndAuthor a")
        product_url = "https://www.christianbook.com" + title_tag['href'] if title_tag and title_tag.has_attr('href') else ""
        rating_text_tag = li.select_one("span.CBD-PreviewGroupItemRatingText")
        rating_text = rating_text_tag.text.strip() if rating_text_tag else ""
        img_tag = li.select_one("div.CB-ProductListItem-ImageAndAuthor img")
        img_url = img_tag['src'].strip() if img_tag and img_tag.has_attr('src') else ""
        if img_url.startswith("//"):
            img_url = "https:" + img_url
        title = title_tag.text.strip() if title_tag else ""
        if product_url:
            book_links.append({
                "product_url": product_url,
                "rating_text": rating_text,
                "img_url": img_url,
                "title": title
            })
    return book_links

async def parse_book_with_semaphore(semaphore, session, product_url):
    async with semaphore:
        return await parse_book(session, product_url)

async def main():
    # Enter the link to a large category (e.g., eBooks) in the console when starting
    root_url = input("Paste the link to a large category: ").strip()
    category_pages = get_category_pages(root_url)
    category_pages = category_pages[:1]  # Limit: only the first category
    # REMOVE LIMITS for full mode:
    # category_pages = category_pages[:2]
    results = []
    async with aiohttp.ClientSession() as session:
        all_book_links = []
        for cat_idx, (cat_url, max_page) in enumerate(category_pages):
            print(f"Category {cat_idx+1}/{len(category_pages)}: {cat_url}")
            for page in range(1, max_page + 1):
                page_url = cat_url + ("&" if "?" in cat_url else "?") + f"page={page}"
                book_links = await parse_page(session, page_url)
                all_book_links.extend([(book, cat_url) for book in book_links])
                print(f"  Page {page}/{max_page} — books found: {len(book_links)} (total collected: {len(all_book_links)})")
        print(f"Total books to parse: {len(all_book_links)}")
        # Limit on the number of simultaneous requests
        semaphore = asyncio.Semaphore(15)
        book_tasks = [parse_book_with_semaphore(semaphore, session, book['product_url']) for book, _ in all_book_links]
        books_details = await asyncio.gather(*book_tasks)
        for (book, cat_url), book_detail in zip(all_book_links, books_details):
            result = {
                "Page Attribute": book['product_url'],
                "MainCategory": "Christian-Living",  # You can replace with appropriate category name
                "Title": book['title'],
                "Short description": "",
                "Description": book_detail.get("Description", ""),
                "New": "",
                "RegularPrice": book_detail.get("RegularPrice", ""),
                "SalePrice": book_detail.get("SalePrice", ""),
                "PublisherDescription": book_detail.get("PublisherDescription", ""),
                "AuthorBio": book_detail.get("AuthorBio", ""),
                "ImageURL": book['img_url'],
                "Mapping": book_detail.get("Mapping", ""),
                "Author": book_detail.get("Author", ""),
                "Tags": book_detail.get("Tags", ""),
                "Attribute 1": book_detail.get("Attribute 1", ""),
                "Attribute 2": book_detail.get("Attribute 2", ""),
                "Attribute 3": book_detail.get("Attribute 3", ""),
                "Attribute 4": book_detail.get("Attribute 4", ""),
                "Attribute 5": book_detail.get("Attribute 5", ""),
                "Attribute 6": book_detail.get("Attribute 6", ""),
                "Attribute 7": book_detail.get("Attribute 7", ""),
                "Attribute 8": book_detail.get("Attribute 8", ""),
                "Attribute 9": book_detail.get("Attribute 9", ""),
                "Attribute 10": book_detail.get("Attribute 10", ""),
                "Data 1": book_detail.get("Data 1", ""),
                "Data 2": book_detail.get("Data 2", ""),
                "Data 3": book_detail.get("Data 3", ""),
                "Data 4": book_detail.get("Data 4", ""),
                "Data 5": book_detail.get("Data 5", ""),
                "Data 6": book_detail.get("Data 6", ""),
                "Data 7": book_detail.get("Data 7", ""),
                "Data 8": book_detail.get("Data 8", ""),
                "Data 9": book_detail.get("Data 9", ""),
                "Data 10": book_detail.get("Data 10", ""),
                "Data 11": book_detail.get("Data 11", ""),
                "Rating": book['rating_text']
            }
            results.append(result)
    with open("FFF.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    print(f"✅ Books collected: {len(results)}. Saved to FFF")

if __name__ == "__main__":
    asyncio.run(main())
