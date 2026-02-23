# src/tasks/news.py
"""News scraping and context building."""

import aiohttp
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import re


class NewsScraper:
    """Scrape local news for context embedding."""

    def __init__(self):
        self.sources = {
            "San Francisco": [
                {"name": "SF Chronicle", "url": "https://www.sfchronicle.com"},
                {"name": "SF Examiner", "url": "https://www.sfexaminer.com"},
                {"name": "Mission Local", "url": "https://missionlocal.org"},
                {"name": "SF Gate", "url": "https://www.sfgate.com"},
            ],
            "Miami-Dade": [
                {"name": "Miami Herald", "url": "https://www.miamiherald.com"},
                {"name": "Miami New Times", "url": "https://www.miaminewtimes.com"},
                {"name": "Miami Today", "url": "https://www.miamitodaynews.com"},
            ]
        }

    async def scrape_local_news(
        self,
        county: str,
        hours_back: int = 48,
        articles_per_source: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Scrape recent news articles for a county.

        Note: In production, you'd want to use news APIs like:
        - NewsAPI.org
        - GDELT (free, global news database)
        - Bing News API
        """
        articles = []

        sources = self.sources.get(county, [])
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)

        for source in sources:
            source_articles = await self._scrape_source(
                source,
                cutoff_time,
                articles_per_source
            )
            articles.extend(source_articles)

        # Sort by recency
        articles.sort(key=lambda x: x.get("published_at", ""), reverse=True)

        return articles

    async def _scrape_source(
        self,
        source: Dict[str, str],
        cutoff_time: datetime,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Scrape a single news source."""
        articles = []

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(source["url"], timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status != 200:
                        return articles

                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")

                    # Find article links - this is source-specific
                    # For a real implementation, you'd customize per source
                    article_links = self._extract_article_links(soup, source["url"])

                    for link in article_links[:limit]:
                        article = await self._scrape_article(session, link, source["name"])
                        if article:
                            articles.append(article)

        except Exception as e:
            print(f"Error scraping {source['name']}: {e}")

        return articles

    def _extract_article_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract article links from a page."""
        links = []

        # This is a simplified implementation
        # Real implementation would be source-specific
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if self._looks_like_article(href):
                if href.startswith("/"):
                    href = base_url.rstrip("/") + href
                links.append(href)

        return links

    def _looks_like_article(self, url: str) -> bool:
        """Check if URL looks like an article (not homepage, category, etc.)."""
        # Exclude common non-article patterns
        exclusions = ["/category/", "/tag/", "/author/", "/about", "/contact"]
        return not any(excl in url.lower() for excl in exclusions)

    async def _scrape_article(
        self,
        session: aiohttp.ClientSession,
        url: str,
        source_name: str
    ) -> Optional[Dict[str, Any]]:
        """Scrape a single article."""
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    return None

                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")

                # Extract title
                title = self._extract_title(soup)
                if not title:
                    return None

                # Extract summary/first paragraph
                summary = self._extract_summary(soup)

                return {
                    "title": title,
                    "url": url,
                    "summary": summary,
                    "source": source_name,
                    "published_at": datetime.utcnow().isoformat(),  # Would parse from page
                }

        except Exception as e:
            print(f"Error scraping article {url}: {e}")
            return None

    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract article title."""
        # Try common patterns
        for tag in ["h1", "title", "h2"]:
            for el in soup.find_all(tag):
                text = el.get_text().strip()
                if text and len(text) > 10 and len(text) < 200:
                    return text
        return None

    def _extract_summary(self, soup: BeautifulSoup) -> str:
        """Extract article summary."""
        # Try to find first paragraph
        for p in soup.find_all("p"):
            text = p.get_text().strip()
            if text and len(text) > 50:
                return text[:500]  # Truncate
        return ""

    async def get_local_news_summary(self, county: str, hours_back: int = 24) -> str:
        """Get a formatted summary of local news."""
        articles = await self.scrape_local_news(county, hours_back)

        if not articles:
            return f"No recent news available for {county}."

        summary = f"Recent news from {county}:\n\n"
        for article in articles[:10]:
            summary += f"- {article['title']}\n"
            if article.get('summary'):
                summary += f"  {article['summary'][:200]}...\n"
            summary += "\n"

        return summary


async def get_combined_news_context(counties: List[str]) -> str:
    """Get news context for multiple counties."""
    scraper = NewsScraper()
    contexts = []

    for county in counties:
        context = await scraper.get_local_news_summary(county)
        contexts.append(context)

    return "\n\n".join(contexts)


# ============================================================================
# SOCIAL MEDIA / REDDIT (Optional)
# ============================================================================

class RedditScraper:
    """Scrape local discussions from Reddit (using JSON API, no auth needed)."""

    async def get_local_posts(
        self,
        subreddit: str,
        limit: int = 20,
        hours_back: int = 24
    ) -> List[Dict[str, Any]]:
        """Get recent posts from a subreddit."""
        posts = []

        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://www.reddit.com/r/{subreddit}/new.json?limit={limit}"
                async with session.get(url, headers={"User-Agent": "JeffersonAI/1.0"}) as response:
                    if response.status == 200:
                        data = await response.json()

                        for child in data["data"]["children"]:
                            post = child["data"]
                            created_utc = post.get("created_utc", 0)
                            created_time = datetime.fromtimestamp(created_utc)

                            if (datetime.utcnow() - created_time).total_seconds() > hours_back * 3600:
                                continue

                            posts.append({
                                "title": post.get("title"),
                                "selftext": post.get("selftext", "")[:500],
                                "url": f"https://reddit.com{post.get('permalink')}",
                                "score": post.get("score"),
                                "num_comments": post.get("num_comments"),
                                "created_at": created_time.isoformat()
                            })

        except Exception as e:
            print(f"Error scraping r/{subreddit}: {e}")

        return posts

    async def get_local_discussions_summary(self, county: str) -> str:
        """Get summary of local Reddit discussions."""
        subreddits = {
            "San Francisco": ["sanfrancisco", "AskSF"],
            "Miami-Dade": ["Miami", "MiamiUniversity"]
        }

        subs = subreddits.get(county, [])
        all_posts = []

        for sub in subs:
            posts = await self.get_local_posts(sub)
            all_posts.extend(posts)

        if not all_posts:
            return ""

        # Sort by engagement
        all_posts.sort(key=lambda x: x.get("score", 0), reverse=True)

        summary = f"Trending discussions on Reddit for {county}:\n\n"
        for post in all_posts[:5]:
            summary += f"- {post['title']} ({post['score']} upvotes)\n"
            summary += f"  {post.get('selftext', '')[:100]}...\n\n"

        return summary
