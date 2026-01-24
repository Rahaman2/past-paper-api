# Scraping South Africa's Exam Papers: A Weekend Project That Taught Me More Than Expected

*How a simple API turned into a lesson about HTML parsing edge cases*

---

Every year, millions of South African students prepare for their National Senior Certificate exams. The Department of Basic Education publishes past papers on their website—a goldmine for students wanting to practice. But navigating government websites isn't exactly a joy. So I thought: why not build an API?

What started as a "quick weekend project" became an unexpectedly deep dive into the quirks of web scraping.

## The Idea

The concept was simple: scrape the DBE website, extract all the exam paper links, and serve them through a clean REST API. Students or developers could then filter by year, exam session (November, May/June), and subject.

```
GET /papers/2025/MayJune?subject=math
```

Returns nicely structured JSON with download links. Clean. Simple. What could go wrong?

## The First Surprise: Link Wrappers

Government websites love their link tracking. Instead of direct URLs to PDFs, every link on the DBE site goes through `LinkClick.aspx` with encoded parameters. A "simple" href looked like this:

```
/LinkClick.aspx?link=5475&tabid=593&portalid=0&mid=1741
```

Some links had an embedded `link=` parameter pointing to another URL. Others were relative paths. Some were already absolute HTTPS URLs. I ended up writing a small URL extraction utility just to handle the variations:

```python
def extract_embedded_url(href: str) -> str | None:
    if href.startswith("https://"):
        return href
    if "link=" in href:
        link_param = href.split("link=")[1].split("&")[0]
        return unquote(link_param)
    return None
```

Not glamorous, but necessary.

## The Second Surprise: Two Different HTML Structures

Here's where things got interesting. The DBE site organizes subjects into two categories: **Languages** and **Non-Languages**. Sounds straightforward, but they're structured completely differently in the HTML.

**Non-language subjects** (Mathematics, Physics, etc.) follow a predictable pattern:
- An `<h2>` header with the subject name
- Links underneath like "Paper 1 (English)", "Paper 2 (Afrikaans)"
- Memos labeled as "Memo 1 (English)"

**Language subjects** (English, Afrikaans, IsiZulu, etc.) embed the subject *in the link text itself*:
- "English FAL P1"
- "Afrikaans HL P2 memo"
- "IsiZulu FAL P3"

My parser initially only looked at `<h2>` headers for subject names. Language papers were getting dropped because their parent header was just "LANGUAGES"—which I was deliberately skipping.

The fix? Extract subject names from the link text when the header is generic:

```python
subject_part = text[:paper_match.start()].strip()
if subject_part and not subject_part.lower().startswith("paper"):
    subject = subject_part  # "English FAL" from "English FAL P1"
else:
    subject = current_subject  # from <h2> header
```

## The Bug That Took Longest to Find

With the scraper working, I deployed and started testing. Mathematics worked. Physical Sciences worked. But searching for "english" returned a 500 error.

The stack trace pointed to Pydantic validation failing because a dictionary key was `None`. But how? I had guards everywhere.

After adding debug logging, I found the culprit. Language subjects don't specify a language variant in parentheses—because the language *is* the subject. So "English HL P1" has no "(English)" at the end.

My code was doing this:

```python
language = p.get("language", "default")
```

But when `p["language"]` existed and was explicitly `None`, `.get()` returned `None`—not the default. The fix was embarrassingly simple:

```python
language = p.get("language") or "default"
```

One missing `or` caused hours of debugging.

## The Memo Mystery

Users reported that memos were always empty in the API response. Papers had download links, but `"memo": {}` every time.

I checked my memo detection logic—it looked for "memo" in the link text. That worked fine. So why empty?

Turns out, while papers were labeled "Paper 1 (English)", memos were labeled "Memo 1 (English)"—not "Paper 1 memo". My regex only matched "P1", "P2", "P3" or "Paper 1", "Paper 2", "Paper 3". The pattern "Memo 1" never matched, so those links were silently dropped.

```python
# Added this pattern
paper_match = re.search(r"\bMemo\s*([1-3])\b", text, re.IGNORECASE)
```

After that, memos populated correctly.

## Lessons Learned

1. **Government websites are inconsistent.** The same site can have completely different HTML structures for similar content. Defensive parsing is essential.

2. **Test with diverse inputs early.** My tests focused on "Mathematics" and "Physical Sciences"—both non-language subjects with the same structure. Testing with "English" earlier would have caught the language subject bug.

3. **Pydantic validation errors are your friend.** That 500 error with `None.[key]` told me exactly where the problem was—a dict key was None when it should be a string.

4. **Regex can fail silently.** When a pattern doesn't match, you get `None` back. If you're not explicitly handling that case, data just disappears.

## The Result

The API now serves 60+ subjects across multiple years and exam sessions. Language filtering works with partial matches—search "hl" to get all Home Language papers, or "fal" for First Additional Language.

```json
{
  "year": "2025",
  "session": "MayJune",
  "subjects": {
    "Mathematics": {
      "P1": {
        "paper": {"English": "https://...", "Afrikaans": "https://..."},
        "memo": {"Afrikaans": "https://..."}
      }
    }
  }
}
```

Is it the most complex API I've built? No. But it reminded me that "simple" scraping projects rarely stay simple—and that's where the real learning happens.

---

*The full source code is available on GitHub. If you're a South African student or teacher, I hope this helps with exam prep. If you're a developer, may your regex always match on the first try.*
