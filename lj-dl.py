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
      self.post[ENUM_POST.TEXT] += ("<%s " % tag)
      for (k, v) in attrs:
        # images
        if tag == "img" and k == "src":
          filename = get_file(
            addr=v,
            directory=self.post[ENUM_POST.MAIN_DIR],
            postid=self.post[ENUM_POST.ID],
            files=self.post[ENUM_POST.FILES]
          )
          if filename:
            v = filename
          else:
            pass

        self.post[ENUM_POST.TEXT] += ("%s = \"%s\" " % (k, v))
      self.post[ENUM_POST.TEXT] += ">"
      return

    # handle tags
    if tag == "h1":
      (k, v) = attrs[0]
      if k == "class" and re.search("b-singlepost-title entry-title p-name", v):
        self.state.append(PS_HEADER)
    elif tag == "ul":
      if attrs and len(attrs) > 0:
        (k, v) = attrs[0]
        if k == "class" and re.search("b-pager-pages", v):
          self.state.append(PS_COMPAGES)
          self.post[ENUM_POST.COMPAGES] = []
    elif tag == "a":
      if attrs and len(attrs) > 1:
        (k, v) = attrs[1]
        if k == "class" and re.search("i-ljuser-username", v):
          self.state.append(PS_AUTHOR)
          self.post[ENUM_POST.AUTHOR] = ""
      elif attrs and len(attrs) == 1 and len(self.state) > 0 and self.state[-1] == PS_COMPAGES:
        (k, v) = attrs[0]
        if k == "href":
          self.post[ENUM_POST.COMPAGES].append(v)
    elif tag == "time":
      if attrs and len(attrs) > 0:
        (k, v) = attrs[0]
        if k == "class" and re.search("b-singlepost-author-date published dt-published", v):
          self.state.append(PS_DATE)
          self.post[ENUM_POST.DATE] = ""
    elif tag == "article":
      if attrs and len(attrs) > 0:
        (k, v) = attrs[0]
        if k == "class" and re.search("b-singlepost-body entry-content e-content", v):
          self.state.append(PS_TEXT)
          self.post[ENUM_POST.TEXT] = ""
    elif tag == "meta":
      if attrs and len(attrs) > 1:
        (k0, v0) = attrs[0]
        (k1, v1) = attrs[1]
        if k0 == "property" and v0 == "article:tag" and k1 == "content":
          if self.post.get(ENUM_POST.TAGS, None) is None:
            self.post[ENUM_POST.TAGS] = {}
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
      self.post[ENUM_POST.HEADER] = data.strip()
    elif self.state[-1] == PS_TEXT:
      self.post[ENUM_POST.TEXT] += data
    elif self.state[-1] == PS_DATE:
      self.post[ENUM_POST.DATE] += data
    elif self.state[-1] == PS_AUTHOR:
      self.post[ENUM_POST.AUTHOR] += data


class LJCommentParser(HTMLParser):
  def __init__(self, post, comment):
    HTMLParser.__init__(self)
    self.comment = comment
    self.post    = post

  def handle_starttag(self, tag, attrs):
    # include given tag
    self.comment[ENUM_COM.TEXT] += ("<%s " % tag)
    for (k, v) in attrs:
      # images
      if tag == "img" and k == "src":
        filename = get_file(
          addr=v,
          directory=self.post[ENUM_POST.MAIN_DIR],
          postid=self.post[ENUM_POST.ID],
          files=self.post[ENUM_POST.FILES]
        )
        if filename: v = filename

      self.comment[ENUM_COM.TEXT] += ("%s = \"%s\" " % (k, v))
    self.comment[ENUM_COM.TEXT] += ">"

  def handle_endtag(self, tag):
    if tag == "br":
      return
    self.comment[ENUM_COM.TEXT] += (" </%s> " % tag)

  def handle_data(self, data):
    self.comment[ENUM_COM.TEXT] += data


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
    if length == None: length = 'unknown size'
    print("Downloading content of web page '%s'... [%s]" % (addr, length))
  except urllib.error.URLError as e:
    print("Error: Downloading content of web page '%s' failed (%s)" % (addr, e.reason))
    err = e.reason
  return (out, err)


def extract_comments(page_content, post):
  m = re.search('^.*Site.page = (.+);', page_content, re.MULTILINE)
  if m is None:
    print("Error: Parsing failed")
    return

  comments = post[ENUM_POST.COMMENTS]
  comment_json = json.loads(m.group(1))['comments']
  # exit(0)
  for jc in comment_json:
    if 'thread' in jc.keys():
      if not jc['thread'] in comments[0].keys():
        if 'collapsed' in jc.keys():
          if jc['collapsed'] == 0:
            com = {}
            com[ENUM_COM.ABOVE]     = jc['above']
            com[ENUM_COM.BELOW]     = jc['below']
            com[ENUM_COM.USER]      = jc['uname']
            com[ENUM_COM.USERPIC]   = jc['userpic']
            com[ENUM_COM.THREAD]    = jc['thread']
            com[ENUM_COM.THREADURL] = jc['thread_url']
            com[ENUM_COM.DATE]      = jc['ctime']
            com[ENUM_COM.DATETS]    = jc['ctime_ts']
            com[ENUM_COM.LEVEL]     = jc['level']

            com[ENUM_COM.TEXT] = ""
            comment_parser = LJCommentParser(post, com)
            comment_parser.feed(jc['article'])

            comments.append(com)
            comments[0][com[ENUM_COM.THREAD]] = 1
          else:
            if jc['deleted'] == 1:
              com = {}
              com[ENUM_COM.ABOVE]     = jc['above']
              com[ENUM_COM.BELOW]     = jc['below']
              com[ENUM_COM.USER]      = None
              com[ENUM_COM.USERPIC]   = None
              com[ENUM_COM.DELETED]   = jc['deleted']
              com[ENUM_COM.THREAD]    = jc['thread']
              com[ENUM_COM.THREADURL] = jc['thread_url']
              com[ENUM_COM.DATE]      = jc['ctime']
              com[ENUM_COM.DATETS]    = jc['ctime_ts']
              com[ENUM_COM.LEVEL]     = jc['level']

              com[ENUM_COM.TEXT] = "deleted"
              comments.append(com)
              comments[0][com[ENUM_COM.THREAD]] = 1
            else:
              if 'thread_url' in jc.keys():
                # import pdb; pdb.set_trace()
                (page, err) = get_webpage_content(jc['thread_url'])
                if err:
                  print("Error: %s" % err)
                else:
                  extract_comments(page, post)

    elif 'more' in jc.keys() and jc['more'] > 1:
      if 'actions' in jc.keys():
        if 'href' in jc['actions'][0]:
          href = jc['actions'][0]['href']
          print("Expanding thread '%s' (%s comments):" % (href, jc['more']))
          (page, err) = get_webpage_content(href)
          if err:
            print("Error: %s" % err)
          else:
            extract_comments(page, post)

def save_json_to_file(js, filename):
  with open(filename, 'w+') as out:
    json.dump(js, out, ensure_ascii=False, indent=2)

def add_post_to_index(postid, index):
  if postid in index[ENUM_INDEX.POSTS]:
    print("Post %s is already saved. Passed" % postid)
    return

  (page_content, err) = get_webpage_content(page_addr)
  if err: exit(2)

  post = {}
  post[ENUM_POST.ID]       = postid
  post[ENUM_POST.MAIN_DIR] = index[ENUM_INDEX.LJUSER]
  post[ENUM_POST.FILES]    = index[ENUM_INDEX.FILES]
  post[ENUM_POST.COMMENTS] = []

  post_parser = LJPostParser(post)
  print("Parsing the post...")
  post_parser.feed(page_content)
  post[ENUM_POST.LINK] = page_addr
  # print(post)
  # exit(0)

  if post.get(ENUM_POST.COMPAGES) is None:
    post[ENUM_POST.COMPAGES] = []
    post[ENUM_POST.COMPAGES].append("/%s.html" % postid)

  print("Parsing the comments (%d page(s) found)..." % len(post[ENUM_POST.COMPAGES]))
  threads = {}
  post[ENUM_POST.COMMENTS].append(threads)

  for p in post[ENUM_POST.COMPAGES]:
    link = "http://%s.livejournal.com%s" % (index[ENUM_INDEX.LJUSER], p)
    (page_content, err) = get_webpage_content(link)
    if err:
      print("Error: %s" % err)
      continue
    extract_comments(page_content, post)

  post[ENUM_POST.COMMENTS] = post[ENUM_POST.COMMENTS][1:]
  pics = {}
  pic = None
  directory = "./%s" % index[ENUM_INDEX.LJUSER]
  for com in post[ENUM_POST.COMMENTS]:
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

  index_post = {}
  index_post[ENUM_INDEX.POST_ID]     = postid
  index_post[ENUM_INDEX.POST_HEADER] = post[ENUM_POST.HEADER]
  index_post[ENUM_INDEX.POST_DATE]   = post[ENUM_POST.DATE]
  index_post[ENUM_INDEX.POST_TAGS]   = post[ENUM_POST.TAGS]

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
    index[ENUM_INDEX.FILES] = {}
    index[ENUM_INDEX.LJUSER] = ljuser
  else:
    with open(findex, "r") as f:
      index = json.load(f)
      print("Found index file '%s' (%d posts, %d files)"
        % (findex, len(index[ENUM_INDEX.POSTS]), (len(index[ENUM_INDEX.FILES])))
      )

  index[ENUM_INDEX.DATE] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

  add_post_to_index(index=index, postid=postid)
