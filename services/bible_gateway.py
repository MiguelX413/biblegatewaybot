import logging
from urllib.parse import quote

from bs4 import BeautifulSoup

try:
    import httpx
except (
    ImportError
):  # pragma: no cover - exercised only in dependency-missing environments
    httpx = None

from parsing import ensure_text
from state import (
    DEFAULT_VERSION,
    EMPTY,
    InlinePassageResult,
    MAX_SEARCH_RESULTS,
    REQUEST_TIMEOUT_SECONDS,
)


def to_sup(text: str) -> str:
    sups = {
        "0": "\u2070",
        "1": "\xb9",
        "2": "\xb2",
        "3": "\xb3",
        "4": "\u2074",
        "5": "\u2075",
        "6": "\u2076",
        "7": "\u2077",
        "8": "\u2078",
        "9": "\u2079",
        "-": "\u207b",
    }
    return "".join(sups.get(char, char) for char in text)


def parse_passage_html(
    html: str, version: str = DEFAULT_VERSION, inline_details: bool = False
) -> str | InlinePassageResult:
    start = html.find('<div class="passage-col')
    if start == -1:
        return EMPTY

    end = html.find("<!-- passage-box -->", start)
    passage_html = html[start:end]
    soup = BeautifulSoup(passage_html, "lxml")

    title_node = soup.select_one(".bcv")
    passage_soup = soup.select_one(".passage-text")
    if title_node is None or passage_soup is None:
        return EMPTY

    title = title_node.text.strip()
    header = f"{title} ({version})"

    for tag in passage_soup.select(
        ".passage-other-trans, .footnote, .footnotes, .crossreference, .crossrefs"
    ):
        tag.decompose()

    for tag in passage_soup.select("h1, h2, h3, h4, h5, h6"):
        tag["class"] = "bg-bot-passage-text"
        tag.string = tag.text.strip()

    for tag in passage_soup.select("p"):
        tag["class"] = "bg-bot-passage-text"

    for tag in passage_soup.select("br"):
        tag.replace_with("\n")

    for tag in passage_soup.select(".chapternum"):
        tag.string = f"{tag.text.strip()} "

    for tag in passage_soup.select(".versenum"):
        tag.string = to_sup(tag.text.strip())

    for tag in passage_soup.select(".text"):
        tag.string = tag.text.rstrip()

    blocks = [header]
    for tag in passage_soup(class_="bg-bot-passage-text"):
        text = " ".join(tag.text.split())
        if text:
            blocks.append(text)

    final_text = "\n\n".join(blocks).strip()
    if not final_text:
        return EMPTY

    if not inline_details:
        return final_text

    osis_start = html.find('data-osis="')
    result_id = f"{title}/{version}"
    if osis_start != -1:
        osis_start += len('data-osis="')
        osis_end = html.find('"', osis_start)
        if osis_end != -1:
            result_id = f"{html[osis_start:osis_end]}/{version}"

    content = " ".join(final_text.split())
    description = f"{content[:150]}..." if len(content) > 153 else content
    return InlinePassageResult(
        passage=final_text,
        result_id=result_id,
        title=header,
        description=description,
    )


def parse_search_results_html(text: str, start: int = 0) -> str:
    soup = BeautifulSoup(text, "lxml")
    headers = soup.select(".l")
    bodies = soup.select(".s")
    num_results = min(len(headers), len(bodies))

    if num_results == 0 or start >= num_results:
        return EMPTY

    lines = []
    end = min(num_results, start + MAX_SEARCH_RESULTS)
    for i in range(start, end):
        header = headers[i].text
        idx = header.find(":")
        idx += header[idx:].find(" ")
        title = header[:idx].strip()

        body_text = " ".join(bodies[i].text.split())
        cutoff = body_text.rfind("//biblehub.com")
        if cutoff != -1:
            body_text = body_text[:cutoff].strip()

        link = "/" + "".join(title.split()).lower().replace(":", "V")
        lines.append(f"🔹{title}\n{body_text}\n{link}")

    header_text = "Search results"
    if num_results > MAX_SEARCH_RESULTS:
        header_text += f" ({start + 1}-{end} of {num_results})"

    result = f"{header_text}\n\n" + "\n\n".join(lines)
    if start + MAX_SEARCH_RESULTS < num_results:
        result += "\n\nGet /more results"
    return result


class BibleGatewayClient:
    def __init__(self, client=None):
        if httpx is None:
            raise RuntimeError("httpx is required to use BibleGatewayClient.")
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT_SECONDS,
            follow_redirects=True,
            headers={"User-Agent": "biblegatewaybot/1.0"},
        )

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def fetch_text(self, url: str) -> str | None:
        try:
            response = await self._client.get(url)
            response.raise_for_status()
            return response.text
        except httpx.HTTPError as exc:
            logging.warning("Error fetching %s: %s", url, exc)
            return None

    async def get_passage(
        self, passage: str, version: str = DEFAULT_VERSION, inline_details: bool = False
    ) -> str | InlinePassageResult | None:
        search = quote(ensure_text(passage).lower().strip())
        url = "https://www.biblegateway.com/passage/?search={}&version={}&interface=print".format(
            search, version
        )
        html = await self.fetch_text(url)
        if html is None:
            return None
        return parse_passage_html(html, version=version, inline_details=inline_details)

    async def get_search_results(self, text: str, start: int = 0) -> str | None:
        query = quote(ensure_text(text).lower().strip())
        url = f"http://biblehub.net/search.php?q={query}"
        html = await self.fetch_text(url)
        if html is None:
            return None
        return parse_search_results_html(html, start=start)
