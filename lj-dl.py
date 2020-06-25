# -*- coding: utf-8 -*-

from constants import (ENUM_INDEX, ENUM_POST, ENUM_COM)
import sys
import os
import subprocess
import urllib.request
import datetime
import re
import json
from html.parser import HTMLParser

import helpers


ANSW_NO  = 0
ANSW_YES = 1
ANSW_ASK = 2

OPT_REWRITE_POSTS_EXISTING = ANSW_ASK

PS_HEADER   = 'ps-header'
PS_TEXT     = 'ps-text'
PS_DATE     = 'ps-date'
PS_AUTHOR   = 'ps-author'
PS_TAG      = 'ps-tag'
PS_COMPAGES = 'ps-comment-pages'


class FileDownloader():

  NO_PICTURE = '../../no-picture.svg" width="50" height="50'

  def __init__(self, main_dir, sub_dir):
    self.files = {}
    self.files_to_download = {}
    self.main_dir = main_dir
    self.sub_dir = sub_dir
    self.file_dir = "./{main_dir}/{sub_dir}".format(
        main_dir=main_dir, sub_dir=sub_dir)
    if not os.path.exists(self.file_dir):
      os.makedirs(self.file_dir)

  def plan_to_download(self, url):
    file_id = '##%d##' % len(self.files_to_download)
    self.files_to_download[file_id] = url
    return file_id

  def get_filename_by_id(self, file_id):
    if file_id not in self.files:
      raise LookupError

    return self.files[file_id]

  def compose_filename(self, url):
    fileext = ""
    m = re.search(".+\.(.+)$", url, re.MULTILINE)
    if m is None:
      print("Error: Parsing '%s' failed" % url)
    else:
      fileext = "." + m.group(1)

    if len(fileext) > 5 or '/' in fileext or '.' in fileext[1:]:
      fileext = '.xxx'

    return "file%d%s" % (len(self.files), fileext)

  def download_files(self):
    for file_id, url in self.files_to_download.items():
      self.files[file_id] = self.download_file(
          url, self.compose_filename(url))

  def decode_filenames_in_text(self, text):
    if not text:
      return text

    file_ids = []
    m_list = re.findall('##(\d+)##', text, re.MULTILINE)
    if not m_list:
      return text

    for m in m_list:
      find_id = '##%s##' % m
      filename = self.get_filename_by_id(find_id)
      text = text.replace(find_id, filename)

    return text

  def download_file(self, url, filename):
    dest = '%s/%s' % (self.file_dir, filename)
    try:
      local_filename, headers = urllib.request.urlretrieve(url, dest)
      length = headers['Content-Length']
      print("Downloading file '%s' --> '%s' [%s]" % (url, dest, length))
    except urllib.error.URLError as e:
      print("Error: Downloading file '%s' failed (%s)" % (url, e.reason))
      return self.NO_PICTURE
    except FileNotFoundError as e:
      import pdb; pdb.set_trace()
    except ValueError as e:
      print("Error: Invalid address '%s'" % (url))
      return self.NO_PICTURE
    except http.client.IncompleteRead as e:
      print("Error: http.client.IncompleteRead exception occured")
      return self.NO_PICTURE

    return "../%s/%s" % (self.sub_dir, filename)


class LJPostParser(HTMLParser):
  def __init__(self, downloader, post):
    HTMLParser.__init__(self)
    self.state = []
    self.post = post
    self.downloader = downloader

  def handle_starttag(self, tag, attrs):
    if len(self.state) > 0 and self.state[-1] == PS_TEXT:
      # stop condition
      if tag == "a":
        if attrs and len(attrs) > 0:
          k, v = attrs[0]
          if k == "name" and re.search("cutid1-end", v):
            self.state.pop()
            return
      # include given tag
      self.post[ENUM_POST.TEXT] += ("<%s " % tag)
      for k, v in attrs:
        # images
        if tag == "img" and k == "src":
          v = self.downloader.plan_to_download(v)

        self.post[ENUM_POST.TEXT] += "%s = \"%s\" " % (k, v)
      self.post[ENUM_POST.TEXT] += ">"
      return

    # handle tags
    if tag == "ul":
      if attrs and len(attrs) > 0:
        k, v = attrs[0]
        if k == "class" and re.search("b-pager-pages", v):
          self.state.append(PS_COMPAGES)
          self.post[ENUM_POST.COMPAGES] = []
    elif tag == "a":
      if (attrs and len(attrs) == 1 and len(self.state) > 0 and
          self.state[-1] == PS_COMPAGES):
        k, v = attrs[0]
        if k == "href":
          self.post[ENUM_POST.COMPAGES].append(v)
    elif tag == "time":
      if attrs and len(attrs) > 0:
        k, v = attrs[0]
        if (k == "class" and
            re.search("b-singlepost-author-date published dt-published", v)):
          self.state.append(PS_DATE)
          self.post[ENUM_POST.DATE] = ""
    elif tag == "article":
      if attrs and len(attrs) > 0:
        k, v = attrs[0]
        if (k == "class" and
            re.search("b-singlepost-body entry-content e-content", v)):
          self.state.append(PS_TEXT)
          self.post[ENUM_POST.TEXT] = ""
    elif tag == "meta":
      if attrs and len(attrs) > 1:
        k0, v0 = attrs[0]
        k1, v1 = attrs[1]
        if k0 == "property" and v0 == "article:tag" and k1 == "content":
          self.post[ENUM_POST.TAGS][v1] = 1


  def handle_endtag(self, tag):
    if len(self.state) == 0: return

    if self.state[-1] == PS_TEXT:
      if tag == "article":
        self.state.pop()
      elif tag == "br":
        pass
      else:
        self.post[ENUM_POST.TEXT] += (" </%s> " % tag)
      return

    # handle tags
    if tag == "ul" and self.state[-1] == PS_COMPAGES:
      self.state.pop()
    elif tag == "time":
      assert self.state[-1] == PS_DATE
      self.state.pop()

  def handle_data(self, data):
    if len(self.state) == 0: return

    if self.state[-1] == PS_TEXT:
      self.post[ENUM_POST.TEXT] += data
    elif self.state[-1] == PS_DATE:
      self.post[ENUM_POST.DATE] += data


class LJCommentParser(HTMLParser):
  def __init__(self, downloader, comment):
    HTMLParser.__init__(self)
    self.comment    = comment
    self.downloader = downloader

  def handle_starttag(self, tag, attrs):
    # include given tag
    self.comment[ENUM_COM.TEXT] += "<%s " % tag
    for k, v in attrs:
      # images
      if tag == "img" and k == "src":
        v = self.downloader.plan_to_download(v)

      self.comment[ENUM_COM.TEXT] += "%s = \"%s\" " % (k, v)
    self.comment[ENUM_COM.TEXT] += ">"

  def handle_endtag(self, tag):
    if tag == "br":
      return
    self.comment[ENUM_COM.TEXT] += " </%s> " % tag

  def handle_data(self, data):
    self.comment[ENUM_COM.TEXT] += data


PIC_NOUSERPIC = "http://l-stat.livejournal.net/img/userpics/userpic-user.png"

def get_userpic(addr, directory, pics):
  if not os.path.exists("./" + directory):
    os.makedirs("./" + directory)

  user_dir = user_pic = None

  if addr == PIC_NOUSERPIC:
    user_dir = "/"
    user_pic = "userpic-user.png"
  else:
    m = re.search("(?:/*)l-userpic.livejournal.com/(\d+)/(\d+)", addr)
    if m is None:
      print("Error: Parsing '%s' failed" % addr)
      return None

    user_dir = m.group(1)
    user_pic = m.group(2)

  subdir = "%s/userpics/%s" % (directory,  user_dir)
  if not os.path.exists(subdir):
    os.makedirs(subdir)

  filename = "%s/%s" % (subdir, user_pic)
  if os.path.isfile(filename):
    # print("File of userpic '%s' has already existed ('%s')" % (addr, filename))
    filename = "userpics/%s/%s" % (user_dir, user_pic)
    return filename

  try:
    local_filename, headers = urllib.request.urlretrieve(addr, filename)
    length = headers['Content-Length']
    print("Downloading userpic '%s' --> '%s' [%s]" % (addr, filename, length))
  except urllib.error.URLError as e:
    print("Error: Downloading userpic '%s' failed (%s)" % (addr, e.reason))
    return None

  pics[addr] = 1
  filename = "userpics/%s/%s" % (user_dir, user_pic)
  return filename


def get_webpage_content(addr):
  err = out = None
  try:
    headers = {
        'Cookie': "adult_explicit=1"
    }
    request = urllib.request.Request(addr, headers=headers)
    response = urllib.request.urlopen(request)
    out = response.read().decode('UTF-8')
    length = response.info()['Content-Length']
    if length == None: length = 'unknown size'
    print("Downloading content of '%s'... [%s]" % (addr, length))
  except urllib.error.URLError as e:
    print("Error: Downloading content of web page '%s' failed (%s)" %
        (addr, e.reason))
    err = e.reason
  return out, err


def extract_json_content(page_content):
  m = re.search('^.*Site.page = (.+);', page_content, re.MULTILINE)
  if m is None:
    print("Error: Parsing failed (no json content)")
    return None
  return json.loads(m.group(1))


def extract_author(json_content, post):
  entry_json = json_content.get('entry')
  if entry_json:
    post[ENUM_POST.AUTHOR] = entry_json['poster'].strip()
  else:
    print("Error: Parsing failed (no author in json content)")


def extract_header(json_content, post):
  entry_json = json_content.get('entry')
  if entry_json:
    post[ENUM_POST.HEADER] = entry_json['title'].strip()
  else:
    print("Error: Parsing failed (no title in json content)")


def extract_comments(json_content, post, downloader):
  comments = post[ENUM_POST.COMMENTS]
  comment_json = json_content.get('comments')
  if comment_json is None:
    print("Error: Did not manage to obtain the comment section :( (postid: %s)"
        % post[ENUM_POST.ID])
    import pdb; pdb.set_trace()
    exit(1)
  # exit(0)
  for jc in comment_json:
    if 'thread' in jc.keys():
      if not jc['thread'] in comments[0].keys():
        if 'collapsed' in jc.keys():
          if jc['collapsed'] == 0:
            com = {
                ENUM_COM.ABOVE:     jc['above'],
                ENUM_COM.BELOW:     jc['below'],
                ENUM_COM.USER:      jc['uname'],
                ENUM_COM.USERPIC:   jc['userpic'],
                ENUM_COM.THREAD:    jc['thread'],
                ENUM_COM.THREADURL: jc['thread_url'],
                ENUM_COM.DATE:      jc['ctime'],
                ENUM_COM.DATETS:    jc['ctime_ts'],
                ENUM_COM.LEVEL:     jc['level'],
                ENUM_COM.PARENT:    jc['parent'],
                ENUM_COM.TEXT:      "",
            }
            comment_parser = LJCommentParser(downloader, com)
            comment_parser.feed(jc['article'])

            comments.append(com)
            comments[0][com[ENUM_COM.THREAD]] = 1
          else:
            if jc['deleted'] == 1 or jc['actions'] is None:
              com = {
                  ENUM_COM.ABOVE:     jc['above'],
                  ENUM_COM.BELOW:     jc['below'],
                  ENUM_COM.USER:      None,
                  ENUM_COM.USERPIC:   None,
                  ENUM_COM.DELETED:   jc['deleted'],
                  ENUM_COM.THREAD:    jc['thread'],
                  ENUM_COM.THREADURL: jc['thread_url'],
                  ENUM_COM.DATE:      jc['ctime'],
                  ENUM_COM.DATETS:    jc['ctime_ts'],
                  ENUM_COM.LEVEL:     jc['level'],
                  ENUM_COM.PARENT:    jc['parent'],
                  ENUM_COM.TEXT:      "deleted",
              }
              comments.append(com)
              comments[0][com[ENUM_COM.THREAD]] = 1
            else:
              if 'thread_url' in jc.keys():
                # if jc['thread_url'] == ...
                  # import pdb; pdb.set_trace()
                page, err = get_webpage_content(jc['thread_url'])
                if err:
                  print("Error: %s" % err)
                else:
                  extract_comments(extract_json_content(page), post, downloader)

    elif 'more' in jc.keys() and jc['more'] > 1:
      if 'actions' in jc.keys():
        if 'href' in jc['actions'][0]:
          href = jc['actions'][0]['href']
          print("Expanding thread '%s' (%s comments):" % (href, jc['more']))
          page, err = get_webpage_content(href)
          if err:
            print("Error: %s" % err)
          else:
            extract_comments(extract_json_content(page), post, downloader)

def save_json_to_file(js, filename):
  with open(filename, 'w+') as out:
    json.dump(js, out, ensure_ascii=False, indent=2)


def add_post_to_index(postid, index):
  if postid in index[ENUM_INDEX.POSTS]:
    if  OPT_REWRITE_POSTS_EXISTING == ANSW_ASK:
      if not helpers.confirm(
          "Post %s is already saved. Do you want to update it?" % postid):
        return
    elif OPT_REWRITE_POSTS_EXISTING == ANSW_NO:
      return

  page_content, err = get_webpage_content(page_addr)
  if err: exit(2)

  post = {
      ENUM_POST.ID:       postid,
      ENUM_POST.HEADER:   "",
      ENUM_POST.MAIN_DIR: index[ENUM_INDEX.LJUSER],
      ENUM_POST.FILES:    {},
      ENUM_POST.TAGS:     {},
      ENUM_POST.COMMENTS: [],
  }

  downloader = FileDownloader(main_dir=post[ENUM_POST.MAIN_DIR],
                              sub_dir=postid)
  post_parser = LJPostParser(downloader, post)
  print("Parsing the post...")
  post_parser.feed(page_content)
  post[ENUM_POST.LINK] = page_addr
  json_content = extract_json_content(page_content)
  extract_author(json_content, post)
  extract_header(json_content, post)

  if post.get(ENUM_POST.COMPAGES) is None:
    post[ENUM_POST.COMPAGES] = []
    post[ENUM_POST.COMPAGES].append("/%s.html" % postid)

  print("Parsing the comments (%d page(s) found)..." %
      len(post[ENUM_POST.COMPAGES]))
  threads = {}
  post[ENUM_POST.COMMENTS].append(threads)

  for p in post[ENUM_POST.COMPAGES]:
    link = "http://%s.livejournal.com%s" % (index[ENUM_INDEX.LJUSER], p)
    page_content, err = get_webpage_content(link)
    if err:
      print("Error: %s" % err)
      continue
    json_content = extract_json_content(page_content)
    extract_comments(json_content, post, downloader)

  post[ENUM_POST.COMMENTS] = post[ENUM_POST.COMMENTS][1:]
  downloader.download_files()

  pics = {}
  pic = None
  directory = "./%s" % index[ENUM_INDEX.LJUSER]

  post[ENUM_POST.TEXT] = downloader.decode_filenames_in_text(
      post[ENUM_POST.TEXT])
  for com in post[ENUM_POST.COMMENTS]:
    com[ENUM_COM.TEXT] = downloader.decode_filenames_in_text(com[ENUM_COM.TEXT])

    if com.get(ENUM_COM.USERPIC):
      pic = get_userpic(com[ENUM_COM.USERPIC], directory, pics)
    else:
      pic = get_userpic(PIC_NOUSERPIC, directory, pics)
    if pic:
      com[ENUM_COM.USERPIC] = pic

  # pop redundant fields
  post.pop(ENUM_POST.FILES)

  outfilename = "%s/%s.data" % (index[ENUM_INDEX.LJUSER], postid)
  save_json_to_file(post, outfilename)

  print("Summary: %d comments have been saved to file '%s'" %
      (len(post[ENUM_POST.COMMENTS]), outfilename))

  index_post = {
      ENUM_INDEX.POST_ID:     postid,
      ENUM_INDEX.POST_HEADER: post[ENUM_POST.HEADER],
      ENUM_INDEX.POST_DATE:   post[ENUM_POST.DATE],
      ENUM_INDEX.POST_TAGS:   post[ENUM_POST.TAGS],
  }
  index[ENUM_INDEX.POSTS][postid] = index_post

  outfilename = "%s/index.data" % (index[ENUM_INDEX.LJUSER])
  save_json_to_file(index, outfilename)


# MAIN
if __name__=='__main__':
  if len(sys.argv) < 2:
    print("Error: Too few params")
    exit(1)

  page_addr = sys.argv[1]

  m = re.search("(?:/*)([\w\-]+)\.livejournal.com/(\d+)\.\w*", page_addr)
  if m is None:
    print("Error: Parsing '%s' failed" % (page_addr))
    exit(2)

  ljuser = m.group(1)
  postid = m.group(2)
  print("ljuser: '%s', postid: '%s'" % (ljuser, postid))

  main_dir = "./%s" % ljuser
  if not os.path.exists(main_dir):
    os.makedirs(main_dir)

  index = None
  findex = "%s/index.data" % main_dir
  if not os.path.isfile(findex):
    index = {}
    index[ENUM_INDEX.POSTS] = {}
    index[ENUM_INDEX.LJUSER] = ljuser
  else:
    with open(findex, "r") as f:
      index = json.load(f)
      print("Found index file '%s' (%d posts)"
          % (findex, len(index[ENUM_INDEX.POSTS])))

  index[ENUM_INDEX.DATE] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

  add_post_to_index(index=index, postid=postid)
