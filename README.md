# christianbook-scraper

A fully asynchronous Python scraper for collecting book data from [Academic category on christianbook.com](https://tinyurl.com/christianbook-academic).


You provide a link to a main category (e.g. “eBooks” or “Christian Living”), and the script will automatically process all subcategories, handle pagination, and visit every product page to extract detailed information.

---

## ✨ Features

- **Async scraping** — Fast, concurrent data collection
- **Auto subcategory detection** — Finds and processes all subcategories of the given main category
- **Smart pagination** — Iterates through every page of each subcategory
- **Deep product parsing** — Collects both main and detailed info from each book’s product page
- **Clean CSV output** — All data saved in a structured, easy-to-analyze CSV file

---

## 📦 Data Collected

- Product URLs
- Main and subcategory names
- Title, full descriptions
- Author, publisher, publication date
- Prices, image URLs, tags, ISBNs, format, availability, and more

---

## ⚙️ How It Works

1. **Loads all subcategories** from the given main category link
2. **Iterates all paginated pages** in every subcategory
3. **Extracts all product URLs**, then scrapes each book’s page for in-depth details
4. **Saves results** to a single, well-formatted CSV file

---

> _This project demonstrates asynchronous scraping, category tree traversal, and structured data extraction from complex e-commerce sites using modern Python tools._
>
> **For demonstration and educational use only.**
