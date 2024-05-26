# -*- coding: utf-8 -*-

"""
This script accepts 2 arguments:
  - page_addr - a link to some post page of the livejournal which is supposed
                to be downloaded.
  - year - a year for which all post links will be fetched.

It downloads a calendar page of a given year, looks for a proper year calendar
parser, then downloads all calendar pages of days with posts published
(one by one), looks for a proper day calendar parser, then obtains all post
links and prints them to STDOUT in the following format:

<post_date1> <post_link1>
<post_date1> <post_link2>
<post_date2> <post_link3>
<post_date3> <post_link4>
...

Debug logging is printed to STDERR, so can be easily filtered.

For now the script supports only Minimalism style, so if you need other styles,
you can extend this script with new parsers and add their support to the functions
`get_year_calendar_parser` and `and get_day_calendar_parser`.
"""

import sys
import urllib.request
import re
from html.parser import HTMLParser


"""
Common functions
"""
def eprint(*args, **kwargs):
  print(*args, file=sys.stderr, **kwargs)


verbose = True
def vprint(*args, **kwargs):
  if not verbose: return
  print(*args, file=sys.stderr, **kwargs)


def is_post_day_link(link):
  if not link or not len(link.strip()):
    return False

  link = link.strip()
  m = re.search("(?:/*)([\w\-]+)\.livejournal.com/(\d{4})/(\d{2})/(\d{2})/", link)
  return m is not None


def retrieve_date_from_post_day_link(link):
  if not link or not len(link.strip()):
    return False

  link = link.strip()
  m = re.search("([\w\-]+)\.livejournal.com/(\d{4})/(\d{2})/(\d{2})/", link)
  dt = None
  if m is not None:
    dt = f"{m.group(2)}-{m.group(3)}-{m.group(4)}"
  return dt


def get_webpage_content(addr):
  err = None
  out = None
  try:
    response = urllib.request.urlopen(addr)
    out = response.read().decode('UTF-8')
    length = response.info()['Content-Length']
    if length == None: length = 'unknown size'
    vprint("Downloading content of '%s'... [%s]" % (addr, length))
  except urllib.error.URLError as e:
    vprint("Error: Downloading content of web page '%s' failed (%s)" % (addr, e.reason))
    err = e.reason
  return (out, err)


class YearCalendarMinimalismParser(HTMLParser):
  def __init__(self, day_links):
    HTMLParser.__init__(self)
    self.day_links = day_links
    self.state = 0
    self.div_count = 0

  def handle_starttag(self, tag, attrs):
    if tag == "div":
      if self.state == 0:
        for (k, v) in attrs:
          if k == "class" and v == "content-inner":
            self.state = 1
            self.div_count = 1
      elif self.state == 1:
        self.div_count += 1
      return

    if self.state == 1:
      if tag == "a":
        for (k, v) in attrs:
          if k == "href":
            if is_post_day_link(v):
              day_links.append(v)

  def handle_endtag(self, tag):
    if tag == "div":
      if self.state == 1:
        self.div_count -= 1
        if self.div_count == 0:
          self.state = 2


class DayCalendarMinimalismParser(HTMLParser):
  def __init__(self, post_links):
    HTMLParser.__init__(self)
    self.post_links = post_links
    self.state = 0
    self.div_count = 0
    self.post_date = None

  def set_post_date(self, post_date):
      self.post_date = post_date

  def handle_starttag(self, tag, attrs):
    if tag == "a":
      attrs_dict = {}
      for (k, v) in attrs:
        attrs_dict[k] = v
      if 'href' in attrs_dict.keys() and 'rel' in attrs_dict.keys():
        if attrs_dict['rel'] == 'bookmark':
          self.post_links.append((self.post_date, attrs_dict['href']))


def get_year_calendar_parser(page_content):
  """
  Searches for patterns in the given page content and returns proper
  year calendar parser if succeeds, otherwise returns None.
  """
  m = re.search('"journalStyleLayout":"Minimalism"', page_content)
  if m is not None:
    return YearCalendarMinimalismParser

  return None


def get_day_calendar_parser(page_content):
  """
  Searches for patterns in the given page content and returns proper
  day calendar parser if succeeds, otherwise returns None.
  """
  m = re.search('"journalStyleLayout":"Minimalism"', page_content)
  if m is not None:
    return DayCalendarMinimalismParser

  return None


def scan_year_calendar(ljuser, year, day_links):
  """
  Scans a page of the calendar for a given year and saves links to day pages
  which contains posts.
  """
  if not ljuser or not year:
    raise ValueError

  page_addr = ("https://%s.livejournal.com/%d/" % (ljuser, year))
  (page_content, err) = get_webpage_content(page_addr)
  if err: exit(2)

  parser_class = get_year_calendar_parser(page_content)
  if not parser_class:
    eprint("Error: No Year Calendar parser found!")
    exit(3)

  page_parser = parser_class(day_links)
  vprint("Parsing the page '%s'..." % page_addr)
  page_parser.feed(page_content)


def scan_day_calendar(day_links, post_links):
  """
  Scans a page of the calendar for a given day and saves links to post pages
  which were published on that day.
  """
  for day_link in day_links:
      (page_content, err) = get_webpage_content(day_link)
      if err: exit(2)

      parser_class = get_day_calendar_parser(page_content)
      if not parser_class:
        eprint("Error: No Day Calendar parser found!")
        exit(3)

      parser = parser_class(post_links)
      parser.set_post_date(retrieve_date_from_post_day_link(day_link))
      parser.feed(page_content)


if __name__ == '__main__':
  if len(sys.argv) < 3:
    print("Error: Too few params")
    exit(1)

  page_addr = sys.argv[1]
  year = sys.argv[2]

  m = re.search("(?:/*)([\w\-]+)\.livejournal.com\w*", page_addr)
  if m is None:
    eprint("Error: Parsing '%s' failed" % (page_addr))
    exit(2)

  ljuser = m.group(1)
  vprint("ljuser: '%s'" % ljuser)

  year = int(year)
  if year < 2000 or year > 2030:
    eprint("Error: The year %d seems to be in invalid range (allowed range is 2000 < year < 2030)" % (year))
    exit(3)

  day_links = []
  scan_year_calendar(ljuser, year, day_links)

  post_links = []
  scan_day_calendar(day_links, post_links)
  for post_link in post_links:
    print(post_link[0], post_link[1])
