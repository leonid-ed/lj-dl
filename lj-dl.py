# -*- coding: utf-8 -*-

import sys
import os
import subprocess
import urllib.request
import datetime
import re
import json
from html.parser import HTMLParser


INDEX_DATE        = "index-date"
INDEX_POSTS       = "index-posts"
INDEX_POST_DATE   = "index-post-date"
INDEX_POST_HEADER = "index-post-header"
INDEX_POST_TAGS   = "index-post-tags"
INDEX_POST_ID     = "index-post-id"
INDEX_FILES       = "index-files"

POST_HEADER   = "post-header"
POST_AUTHOR   = "post-author"
POST_DATE     = "post-date"
POST_TEXT     = "post-text"
POST_COMPAGES = "post-comment-pages"
POST_COMMENTS = "post-comments"
POST_LINK     = "post-link"
POST_TAGS     = "post-tags"
POST_ID       = "post-id"
POST_FILES    = "post-files"
POST_MAIN_DIR = "post-main-dir"

PS_HEADER   = 'ps-header'
PS_TEXT     = 'ps-text'
PS_DATE     = 'ps-date'
PS_AUTHOR   = 'ps-author'
PS_TAG      = 'ps-tag'
PS_COMPAGES = 'ps-comment-pages'

class LJPostParser(HTMLParser):
  def __init__(self, post):
    HTMLParser.__init__(self)
    self.state = []
    self.post = post

  def handle_starttag(self, tag, attrs):
    if len(self.state) > 0 and self.state[-1] == PS_TEXT:
      # stop condition
      if tag == "a":
        if attrs and len(attrs) > 0:
          (k, v) = attrs[0]
          if k == "name" and re.search("cutid1-end", v):
            self.state.pop()
            return
      # include given tag
      self.post[POST_TEXT] += ("<%s " % tag)
      for (k, v) in attrs:
        # images
        if tag == "img" and k == "src":
          filename = get_file(
            addr=v,
            directory=self.post[POST_MAIN_DIR],
            postid=self.post[POST_ID],
            files=self.post[POST_FILES]
          )
          if filename:
            v = filename
          else:
            pass

        self.post[POST_TEXT] += ("%s = \"%s\" " % (k, v))
      self.post[POST_TEXT] += ">"
      return

    # handle tags
    if tag == "h1":
      self.state.append(PS_HEADER)
    elif tag == "ul":
      if attrs and len(attrs) > 0:
        (k, v) = attrs[0]
        if k == "class" and re.search("b-pager-pages", v):
          self.state.append(PS_COMPAGES)
          self.post[POST_COMPAGES] = []
    elif tag == "a":
      if attrs and len(attrs) > 1:
        (k, v) = attrs[1]
        if k == "class" and re.search("i-ljuser-username", v):
          self.state.append(PS_AUTHOR)
          self.post[POST_AUTHOR] = ""
      elif attrs and len(attrs) == 1 and len(self.state) > 0 and self.state[-1] == PS_COMPAGES:
        (k, v) = attrs[0]
        if k == "href":
          self.post[POST_COMPAGES].append(v)
    elif tag == "time":
      if attrs and len(attrs) > 0:
        (k, v) = attrs[0]
        if k == "class" and re.search("b-singlepost-author-date published dt-published", v):
          self.state.append(PS_DATE)
          self.post[POST_DATE] = ""
    elif tag == "article":
      if attrs and len(attrs) > 0:
        (k, v) = attrs[0]
        if k == "class" and re.search("b-singlepost-body entry-content e-content", v):
          self.state.append(PS_TEXT)
          self.post[POST_TEXT] = ""
    elif tag == "meta":
      if attrs and len(attrs) > 1:
        (k0, v0) = attrs[0]
        (k1, v1) = attrs[1]
        if k0 == "property" and v0 == "article:tag" and k1 == "content":
          if self.post.get(POST_TAGS, None) is None:
            self.post[POST_TAGS] = {}
          self.post[POST_TAGS][v1] = 1


  def handle_endtag(self, tag):
    if len(self.state) == 0: return

    if self.state[-1] == PS_TEXT:
      if tag == "article":
        s = self.state.pop()
      elif tag == "br":
        pass
      else:
        self.post[POST_TEXT] += (" </%s> " % tag)
      return

    # handle tags
    if tag == "h1":
      assert self.state[-1] == PS_HEADER
      self.state.pop()
    elif tag == "ul" and self.state[-1] == PS_COMPAGES:
      self.state.pop()
    elif tag == "a" and self.state[-1] == PS_AUTHOR:
      self.state.pop()
    elif tag == "time":
      assert self.state[-1] == PS_DATE
      self.state.pop()

  def handle_data(self, data):
    if len(self.state) == 0: return

    if self.state[-1] == PS_HEADER:
      self.post[POST_HEADER] = data.strip()
    elif self.state[-1] == PS_TEXT:
      self.post[POST_TEXT] += data
    elif self.state[-1] == PS_DATE:
      self.post[POST_DATE] += data
    elif self.state[-1] == PS_AUTHOR:
      self.post[POST_AUTHOR] += data


class LJCommentParser(HTMLParser):
  def __init__(self, post, comment):
    HTMLParser.__init__(self)
    self.comment = comment
    self.post    = post

  def handle_starttag(self, tag, attrs):
    # include given tag
    self.comment[COM_TEXT] += ("<%s " % tag)
    for (k, v) in attrs:
      # images
      if tag == "img" and k == "src":
        filename = get_file(
          addr=v,
          directory=self.post[POST_MAIN_DIR],
          postid=self.post[POST_ID],
          files=self.post[POST_FILES]
        )
        if filename: v = filename

      self.comment[COM_TEXT] += ("%s = \"%s\" " % (k, v))
    self.comment[COM_TEXT] += ">"

  def handle_endtag(self, tag):
    if tag == "br":
      return
    self.comment[COM_TEXT] += (" </%s> " % tag)

  def handle_data(self, data):
    self.comment[COM_TEXT] += data


def execSubprocess(cmd):
  proc = subprocess.Popen([ cmd ], stdout=subprocess.PIPE, shell=True)
  return proc.communicate()


def get_file(addr, directory, postid, files):
  file_dir = "./%s/%s" % (directory, postid)
  if not os.path.exists("./" + file_dir):
    os.makedirs("./" + file_dir)

  fileext = ""
  m = re.search(".+\.(.+)$", addr, re.MULTILINE)
  if m is None:
    print("Error: Parsing '%s' failed" % addr)
  else:
    fileext = "." + m.group(1)

  if addr in files:
    return files[addr]

  filename = "%s/file%d%s" % (file_dir, len(files), fileext)

  try:
    local_filename, headers = urllib.request.urlretrieve(addr, filename)
    length = headers['Content-Length']
    print("Downloading file '%s' --> '%s' [%s]" % (addr, filename, length))
  except urllib.error.URLError as e:
    print("Error: Downloading file '%s' failed (%s)" % (addr, e.reason))
    return None

  filename = "../%s/file%d%s" % (postid, len(files), fileext)
  files[addr] = filename
  return filename


PIC_NOUSERPIC = "http://l-stat.livejournal.net/img/userpics/userpic-user.png"

def get_userpic(addr, directory, pics):
  if not os.path.exists("./" + directory):
    os.makedirs("./" + directory)

  user_dir = None
  user_pic = None

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
  err = None
  out = None
  try:
    response = urllib.request.urlopen(addr)
    out = response.read().decode('UTF-8')
    length = response.info()['Content-Length']
    print("Downloading content of web page '%s'... [%s]" % (addr, length))
  except urllib.error.URLError as e:
    print("Error: Downloading content of web page '%s' failed (%s)" % (addr, e.reason))
    err = e.reason
  return (out, err)


COM_TEXT      = 'text'
COM_USER      = 'user'
COM_USERPIC   = 'userpic'
COM_DATE      = 'date'
COM_DATETS    = 'ts'
COM_ABOVE     = 'above'
COM_BELOW     = 'below'
COM_LEVEL     = 'level'
COM_THREAD    = 'thread'
COM_THREADURL = 'thread-url'

def extract_comments(page_content, post):
  m = re.search('^.*Site.page = (.+);', page_content, re.MULTILINE)
  if m is None:
    print("Error: Parsing failed")
    return

  comments = post[POST_COMMENTS]
  comment_json = json.loads(m.group(1))['comments']
  # pprint.pprint(comment_json)
  # exit(0)
  for jc in comment_json:
    if 'thread' in jc.keys():
      if not jc['thread'] in comments[0].keys():
        if 'collapsed' in jc.keys():
          if jc['collapsed'] == 0:
            com = {}
            com[COM_ABOVE] = jc['above']
            com[COM_BELOW] = jc['below']
            com[COM_USER] = jc['uname']
            com[COM_USERPIC] = jc['userpic']
            com[COM_THREAD] = jc['thread']
            com[COM_THREADURL] = jc['thread_url']
            com[COM_DATE] = jc['ctime']
            com[COM_DATETS] = jc['ctime_ts']
            com[COM_LEVEL] = jc['level']

            com[COM_TEXT] = ""
            comment_parser = LJCommentParser(post, com)
            comment_parser.feed(jc['article'])

            comments.append(com)
            comments[0][com[COM_THREAD]] = 1
          else:
            if 'thread_url' in jc.keys():
              (page, err) = get_webpage_content(jc['thread_url'])
              extract_comments(page, post)

    elif 'more' in jc.keys() and jc['more'] > 1:
      if 'actions' in jc.keys():
        if 'href' in jc['actions'][0]:
          href = jc['actions'][0]['href']
          print("Expanding thread '%s' (%s comments):" % (href, jc['more']))
          (page, err) = get_webpage_content(href)
          extract_comments(page, post)

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
    index[INDEX_POSTS] = {}
    index[INDEX_FILES] = {}
  else:
    with open(findex, "r") as f:
      index = json.load(f)
      print("Found index file '%s' (%d posts, %d files)"
        % (findex, len(index[INDEX_POSTS]), (len(index[INDEX_FILES])))
      )

  index[INDEX_DATE] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

  if postid in index[INDEX_POSTS]:
    print("Post %s is already saved. Passed" % postid)
    exit(0)

  (page_content, err) = get_webpage_content(page_addr)
  if err: exit(2)

  post = {}
  post[POST_MAIN_DIR] = ljuser
  post[POST_ID]       = postid
  post[POST_FILES]    = index[INDEX_FILES]
  post[POST_COMMENTS] = []

  post_parser = LJPostParser(post)
  print("Parsing the post...")
  post_parser.feed(page_content)
  post[POST_LINK] = page_addr
  # print(post)
  # exit(0)

  if post.get(POST_COMPAGES) is None:
    post[POST_COMPAGES] = []
    post[POST_COMPAGES].append("/%s.html" % postid)

  print("Parsing the comments (%d page(s) found)..." % len(post[POST_COMPAGES]))
  threads = {}
  post[POST_COMMENTS].append(threads)

  for p in post[POST_COMPAGES]:
    link = "http://%s.livejournal.com%s" % (ljuser, p)
    (page_content, err) = get_webpage_content(link)
    if err: continue
    extract_comments(page_content, post)

  post[POST_COMMENTS] = post[POST_COMMENTS][1:]
  pics = {}
  pic = None
  directory = "./%s" % ljuser
  for com in post[POST_COMMENTS]:
    if com[COM_USERPIC]:
      pic = get_userpic(com[COM_USERPIC], directory, pics)
    else:
      pic = get_userpic(PIC_NOUSERPIC, directory, pics)

    if pic:
      com[COM_USERPIC] = pic

  outfilename = "%s/%s.data" % (ljuser, postid)
  with open(outfilename, 'w+') as out:
    # pop redundant fields
    post.pop(POST_FILES)
    # pprint.pprint(post, out)
    json.dump(post, out, ensure_ascii=False, indent=2)

  print("Summary: %d comments have been saved to file '%s'" %
    (len(post[POST_COMMENTS]), outfilename))

  index_post = {}
  index_post[INDEX_POST_ID]     = postid
  index_post[INDEX_POST_HEADER] = post[POST_HEADER]
  index_post[INDEX_POST_DATE]   = post[POST_DATE]
  index_post[INDEX_POST_TAGS]   = post[POST_TAGS]

  index[INDEX_POSTS][postid] = index_post

  outfilename = "%s/index.data" % (ljuser)
  with open(outfilename, 'w+') as out:
    json.dump(index, out, ensure_ascii=False, indent=2)

