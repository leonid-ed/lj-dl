# -*- coding: utf-8 -*-

import asyncio
import datetime

import json
import logging
import os
import re
import sys
import subprocess
import urllib.request
from collections import OrderedDict
from html.parser import HTMLParser

import helpers
from constants import (ENUM_INDEX, ENUM_POST, ENUM_COM, ENUM_ASYNC_TASK_STATUS)
from download_helpers import (FileDownloader, ContentDownloader)


ANSW_NO  = 0
ANSW_YES = 1
ANSW_ASK = 2

OPT_REWRITE_POSTS_EXISTING = ANSW_ASK


class AbstractFileDownloader():

  MAX_CONNECTIONS_DEFAULT = 5

  def __init__(self, main_dir):
    self.downloader = FileDownloader()
    self.files = {}
    self.files_to_download = {}
    self.urls_to_download = {}
    self.main_dir = main_dir

  def generate_next_file_id(self):
    return '##%d##' % len(self.files_to_download)

  def compose_filename(self, url):
    raise NotImplementedError

  def plan_to_download(self, url):
    if url in self.urls_to_download:
      return self.urls_to_download[url]

    filename, existing = self.compose_filename(url)
    if existing:
      return filename

    file_id = self.generate_next_file_id()
    self.files_to_download[file_id] = (url, filename)
    self.urls_to_download[url] = file_id
    return file_id

  def get_filename_by_id(self, file_id):
    return self.files[file_id]

  def get_fallback_filename(self):
    raise NotImplementedError

  def download_files(self):
    urls = {}
    for file_id, (url, filename) in self.files_to_download.items():
      urls[url] = '%s/%s' % (self.main_dir, filename)
      self.files[file_id] = '%s' % (filename)

    if not urls:
      return

    if sys.version_info >= (3, 7):
      done, pending = asyncio.run(
          self.downloader.download_files_asynchronously(
              urls, max_connections=self.MAX_CONNECTIONS_DEFAULT))
    elif sys.version_info >= (3, 5):
      loop = asyncio.get_event_loop()
      done, pending = loop.run_until_complete(
          self.downloader.download_files_asynchronously(
              urls, max_connections=self.MAX_CONNECTIONS_DEFAULT))
    else:
      assert False, "Your Python version is not support"

    for task in done:
      code, url, dest = task.result()
      if code != 200:
        file_id = self.urls_to_download[url]
        self.files[file_id] = self.get_fallback_filename()

  @staticmethod
  def get_file_id_mark_regex():
    return '##(\d+)##'

  def compose_link_to_file(self, filename):
    raise NotImplementedError

  @staticmethod
  def make_file_id_mark_by_id(file_id):
    return '##{}##'.format(file_id)

  def decode_filenames_in_text(self, text):
    if not text:
      return text

    file_ids = []
    m_list = re.findall(AbstractFileDownloader.get_file_id_mark_regex(),
                        text, re.MULTILINE)
    if not m_list:
      return text

    for m in m_list:
      file_id = AbstractFileDownloader.make_file_id_mark_by_id(m)
      filename = self.compose_link_to_file(self.get_filename_by_id(file_id))
      text = text.replace(file_id, filename)

    return text


class ImageDownloader(AbstractFileDownloader):

  NO_PICTURE = '../../no-picture.svg" width="50" height="50'

  def __init__(self, main_dir, sub_dir):
    AbstractFileDownloader.__init__(self, main_dir)
    self.num_files = -1
    self.sub_dir = sub_dir
    self.file_dir = "./{main_dir}/{sub_dir}".format(
        main_dir=main_dir, sub_dir=sub_dir)
    if not os.path.exists(self.file_dir):
      os.makedirs(self.file_dir)

  def compose_link_to_file(self, filename):
    return '../{}'.format(filename)

  def get_fallback_filename(self):
    return self.NO_PICTURE

  def compose_filename(self, url):
    fileext = ''
    m = re.search(".+\.(.+)$", url, re.MULTILINE)
    if m is None:
      logging.error("Error: Parsing '%s' failed", url)
    else:
      fileext = "." + m.group(1)

    if len(fileext) > 5 or '/' in fileext or '.' in fileext[1:]:
      fileext = '.xxx'

    self.num_files += 1
    return '%s/file%d%s' % (self.sub_dir, self.num_files, fileext), False


class UserpicDownloader(AbstractFileDownloader):

  NO_USERPIC = 'userpic-user.png'
  USERPIC_DIR = 'userpics'

  def __init__(self, main_dir):
    AbstractFileDownloader.__init__(self, main_dir)
    self.file_dir = "./{main_dir}".format(main_dir=main_dir)
    if not os.path.exists(self.file_dir):
      os.makedirs(self.file_dir)

  def get_fallback_filename(self):
    return '%s/%s' % (self.USERPIC_DIR, self.NO_USERPIC)

  def compose_link_to_file(self, filename):
    return filename

  def compose_filename(self, url):
    user_dir = user_pic = None

    if (not url or
        url == 'http://l-stat.livejournal.net/img/userpics/userpic-user.png'):
      user_dir = '/'
      user_pic = self.NO_USERPIC
    else:
      m = re.search('(?:/*)l-userpic.livejournal.com/(\d+)/(\d+)', url)
      if m is None:
        logging.error("Error: Parsing '%s' failed", url)
        return None

      user_dir = m.group(1)
      user_pic = m.group(2)

    subdir = '%s/%s/%s' % (self.file_dir, self.USERPIC_DIR, user_dir)
    if not os.path.exists(subdir):
      os.makedirs(subdir)

    filename = '%s/%s/%s/%s' % (
        self.file_dir, self.USERPIC_DIR, user_dir, user_pic)
    rel_filename = '%s/%s/%s' % (self.USERPIC_DIR, user_dir, user_pic)
    return rel_filename, os.path.isfile(filename)


class LJPostParser(HTMLParser):

  PS_TEXT     = 'ps-text'
  PS_DATE     = 'ps-date'
  PS_COMPAGES = 'ps-comment-pages'

  def __init__(self, downloader, post):
    HTMLParser.__init__(self)
    self.state = []
    self.post = post
    self.downloader = downloader

  def handle_starttag(self, tag, attrs):
    if len(self.state) > 0 and self.state[-1] == self.PS_TEXT:
      # stop condition
      if tag == 'a':
        if attrs and len(attrs) > 0:
          k, v = attrs[0]
          if k == 'name' and re.search('cutid1-end', v):
            self.state.pop()
            return
      # include given tag
      self.post[ENUM_POST.TEXT] += ('<%s ' % tag)
      for k, v in attrs:
        # images
        if tag == 'img' and k == 'src':
          v = self.downloader.plan_to_download(v)

        self.post[ENUM_POST.TEXT] += '%s = "%s" ' % (k, v)
      self.post[ENUM_POST.TEXT] += '>'
      return

    # handle tags
    if tag == 'ul':
      if attrs and len(attrs) > 0:
        k, v = attrs[0]
        if k == 'class' and re.search('b-pager-pages', v):
          self.state.append(self.PS_COMPAGES)
          self.post[ENUM_POST.COMPAGES] = []
    elif tag == 'a':
      if (attrs and len(attrs) == 1 and len(self.state) > 0 and
          self.state[-1] == self.PS_COMPAGES):
        k, v = attrs[0]
        if k == 'href':
          self.post[ENUM_POST.COMPAGES].append(v)
    elif tag == 'time':
      if attrs and len(attrs) > 0:
        k, v = attrs[0]
        if (k == 'class' and
            re.search('b-singlepost-author-date published dt-published', v)):
          self.state.append(self.PS_DATE)
          self.post[ENUM_POST.DATE] = ''
    elif tag == 'article':
      if attrs and len(attrs) > 0:
        k, v = attrs[0]
        if (k == 'class' and
            re.search('b-singlepost-body entry-content e-content', v)):
          self.state.append(self.PS_TEXT)
          self.post[ENUM_POST.TEXT] = ''
    elif tag == 'meta':
      if attrs and len(attrs) > 1:
        k0, v0 = attrs[0]
        k1, v1 = attrs[1]
        if k0 == 'property' and v0 == 'article:tag' and k1 == 'content':
          self.post[ENUM_POST.TAGS][v1] = 1

  def handle_endtag(self, tag):
    if len(self.state) == 0: return

    if self.state[-1] == self.PS_TEXT:
      if tag == 'article':
        self.state.pop()
      elif tag == 'br':
        pass
      else:
        self.post[ENUM_POST.TEXT] += (' </%s> ' % tag)
      return

    # handle tags
    if tag == 'ul' and self.state[-1] == self.PS_COMPAGES:
      self.state.pop()
    elif tag == 'time':
      assert self.state[-1] == self.PS_DATE
      self.state.pop()

  def handle_data(self, data):
    if len(self.state) == 0: return

    if self.state[-1] == self.PS_TEXT:
      self.post[ENUM_POST.TEXT] += data
    elif self.state[-1] == self.PS_DATE:
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
      if tag == 'img' and k == 'src':
        v = self.downloader.plan_to_download(v)

      self.comment[ENUM_COM.TEXT] += '%s ="%s" ' % (k, v)
    self.comment[ENUM_COM.TEXT] += '>'

  def handle_endtag(self, tag):
    if tag == 'br':
      return
    self.comment[ENUM_COM.TEXT] += ' </%s> ' % tag

  def handle_data(self, data):
    self.comment[ENUM_COM.TEXT] += data


class AsyncTaskNode():

  def __init__(self, data):
    self.status = ENUM_ASYNC_TASK_STATUS.PLANNED
    self.children = []
    self.result = None
    self.data = data

  def get_state(self):
    raise NotImplementedError

  def get_result(self):
    raise NotImplementedError

  def set_result(self, result):
    self.result = result

  def get_async_task_data(self):
    raise NotImplementedError


class AsyncTaskProcessor():

  def __init__(self):
    self.task_queue = OrderedDict()
    self.root_task = AsyncTaskNode(None)

  async def run_tasks_asynchronously(self, async_tasks_data):
    raise NotImplementedError

  def handle_task_result(self, task):
    raise NotImplementedError

  def run(self):
    round_needed = True
    while round_needed:
      round_needed = self.run_round()

  def run_round(self):
    async_tasks_data = {}
    for task_id in self.task_queue.keys():
      task = self.task_queue[task_id]
      task.status = ENUM_ASYNC_TASK_STATUS.PROCESSING
      async_tasks_data[task_id] = None

    if sys.version_info >= (3, 7):
      done, pending = asyncio.run(
          self.run_tasks_asynchronously(async_tasks_data.keys()))
    elif sys.version_info >= (3, 5):
      loop = asyncio.get_event_loop()
      done, pending = loop.run_until_complete(
          self.run_tasks_asynchronously(async_tasks_data.keys()))
    else:
      assert False, "Your Python version is not support"

    for task_result in done:
      result = task_result.result()
      if len(result) == 1:
        logging.error('Error: Coroutine failed: %s', task_result)
      else:
        code, task_id, result = result
        task = self.task_queue[task_id]
        task.status = ENUM_ASYNC_TASK_STATUS.FINISHED
        task.set_result(result)

    tasks = self.task_queue
    self.task_queue = OrderedDict()
    for task in tasks.values():
      self.handle_task_result(task)
    return len(self.task_queue) > 0

  @staticmethod
  def create_task(task_data):
    return AsyncTaskNode(task_data)

  def add_task(self, parent_task, task_data):
    if task_data in self.task_queue:
      assert False, ("'%s' is already existing in the task queue"
                     "(parent is '%s')"
                     % (task_data, parent_task.url if parent_task else 'None'))

    task = self.create_task(task_data)
    self.task_queue[task_data] = task
    logging.info("Planned '%s' thread" % (task_data))

    if not parent_task:
      self.root_task.children.append(task)
    else:
      parent_task.children.append(task)

  def get_results(self):
    raise NotImplementedError


class CommentTaskNode(AsyncTaskNode):

  def __init__(self, data):
    AsyncTaskNode.__init__(self, data)
    self.url = data
    self.comments = []

  def get_async_task_data(self):
    return self.url


class CommentTaskProcessor(AsyncTaskProcessor):

  MAX_CONNECTIONS_DEFAULT = 4

  def __init__(self, image_downloader, userpic_downloader):
    AsyncTaskProcessor.__init__(self)
    self.content_downloader = ContentDownloader()
    self.image_downloader = image_downloader
    self.userpic_downloader = userpic_downloader
    self.comment_ids = {}

  async def run_tasks_asynchronously(self, comment_thread_urls):
    return await self.content_downloader.download_content_asynchronously(
        comment_thread_urls, max_connections=self.MAX_CONNECTIONS_DEFAULT)

  @staticmethod
  def create_task(task_data):
    return CommentTaskNode(task_data)

  def handle_task_result(self, task):
    if task.status != ENUM_ASYNC_TASK_STATUS.FINISHED:
      raise ValueError(
          "Error: Incorrect task status ('{}')".format(task.status))

    self.extract_comments(task)
    task.status = ENUM_ASYNC_TASK_STATUS.HANDLED

  def _get_task_result(self, task):
    comments = []
    for com in task.comments:
      child_commment_num = com.get(ENUM_COM.CHILD_COMMENT)
      if child_commment_num:
        comments += self._get_task_result(task.children[child_commment_num-1])
      else:
        comments.append(com)
    return comments

  def get_results(self):
    comments = []
    for task in self.root_task.children:
      comments += self._get_task_result(task)
    return comments

  def extract_comments(self, task):
    json_content = extract_json_content(task.result)
    comment_json = json_content.get('comments')
    if comment_json is None:
      logging.error('Error: Did not manage to obtain the comment section :('
                    '(url: %s)', task.url)
      exit(1)

    i = 0
    while i < len(comment_json):
      jc = comment_json[i]
      if 'thread' in jc.keys():
        if jc['thread'] not in self.comment_ids:
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
                  ENUM_COM.TEXT:      '',
              }
              if com[ENUM_COM.USERPIC]:
                com[ENUM_COM.USERPIC] = (
                    self.userpic_downloader.plan_to_download(
                      com[ENUM_COM.USERPIC]))
              comment_parser = LJCommentParser(self.image_downloader, com)
              if jc['article']:
                comment_parser.feed(jc['article'])
              task.comments.append(com)
              self.comment_ids[com[ENUM_COM.THREAD]] = task
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
                    ENUM_COM.TEXT:      'deleted',
                }
                if com[ENUM_COM.USERPIC]:
                  com[ENUM_COM.USERPIC] = (
                      self.userpic_downloader.plan_to_download(
                          com[ENUM_COM.USERPIC]))
                task.comments.append(com)
                self.comment_ids[com[ENUM_COM.THREAD]] = task
              else:
                # Create a task to download the collapsed thread
                #   in the next round
                self.add_task(task, jc['thread_url'])
                com = {
                    ENUM_COM.CHILD_COMMENT: len(task.children),
                }
                task.comments.append(com)

                # Skip all the comments in the collapsed thread because
                #   they will be obtained in the next rounds
                above_thread_id = jc['above']
                while True:
                  i += 1
                  if not i < len(comment_json):
                    break

                  jc = comment_json[i]
                  parent = jc.get('parent')
                  above = jc.get('above')

                  # Skip also 'more' sections if we're going to fetch them later
                  if ('more' in jc and jc['more'] and
                      jc['parent'] not in self.comment_ids):
                    continue

                  if any((
                     not ('collapsed' in jc and jc['collapsed'] == 1),
                     not (above and above != above_thread_id),
                     not (parent and parent not in self.comment_ids),
                  )):
                    i -= 1
                    break
      elif 'more' in jc.keys() and jc['parent'] in self.comment_ids:
        # Sometimes thread are collapsed in the 'more' section and their ids are
        #    actually stored in the 'data' item. We request such 'more' threads
        #    only if their parent thread is handled, otherwise it means that
        #    the 'more' threads will be requested via their parent thread which
        #    is not handled so far
        hrefs = []
        for action in jc['actions']:
          if action['name'] == 'expand':
            href_pref = action['href'].split('=')[0]
            for target_thread_id in jc['data'].split(':'):
              hrefs.append(href_pref + '={0}#t{0}'.format(target_thread_id))
            break

        for href in hrefs:
          self.add_task(task, href)
          com = {
              ENUM_COM.CHILD_COMMENT: len(task.children),
          }
          task.comments.append(com)
        logging.info("Planned to expand threads %s", jc['data'])
      i += 1
    logging.info("Thread '%s': %d comments found, %d tasks planned",
                 task.url, len(task.comments), len(task.children))


def get_webpage_content(addr):
  err = out = None
  try:
    headers = {
        'Cookie': 'adult_explicit=1'
    }
    request = urllib.request.Request(addr, headers=headers)
    response = urllib.request.urlopen(request)
    out = response.read().decode('UTF-8')
    length = response.info()['Content-Length']
    if length == None: length = 'unknown size'
    logging.info("Downloading content of '%s'... [%s]", addr, length)
  except urllib.error.URLError as e:
    logging.error("Error: Downloading content of web page '%s' failed (%s)",
        addr, e.reason)
    err = e.reason
  return out, err


def extract_json_content(page_content):
  m = re.search('^.*Site.page = (.+);', page_content, re.MULTILINE)
  if m is None:
    logging.error('Error: Parsing failed (no json content)')
    return None
  return json.loads(m.group(1))


def extract_author(json_content, post):
  entry_json = json_content.get('entry')
  if entry_json:
    post[ENUM_POST.AUTHOR] = entry_json['poster'].strip()
  else:
    logging.error('Error: Parsing failed (no author in json content)')


def extract_header(json_content, post):
  entry_json = json_content.get('entry')
  if entry_json:
    post[ENUM_POST.HEADER] = entry_json['title'].strip()
  else:
    logging.error('Error: Parsing failed (no title in json content)')

  replycount = json_content.get('replycount')
  post[ENUM_POST.REPLYCOUNT] = replycount
  if replycount is None:
    logging.error('Error: Parsing failed (no replycount in json content)')


def save_json_to_file(js, filename):
  with open(filename, 'w+') as out:
    json.dump(js, out, ensure_ascii=False, indent=2)


def add_post_to_index(postid, index):
  if postid in index[ENUM_INDEX.POSTS]:
    if  OPT_REWRITE_POSTS_EXISTING == ANSW_ASK:
      if not helpers.confirm(
          'Post %s is already saved. Do you want to update it?' % postid):
        return
    elif OPT_REWRITE_POSTS_EXISTING == ANSW_NO:
      return

  page_content, err = get_webpage_content(page_addr)
  if err: exit(2)

  post = {
      ENUM_POST.ID:       postid,
      ENUM_POST.HEADER:   '',
      ENUM_POST.MAIN_DIR: index[ENUM_INDEX.LJUSER],
      ENUM_POST.FILES:    {},
      ENUM_POST.TAGS:     {},
      ENUM_POST.COMMENTS: [],
  }

  image_downloader = ImageDownloader(main_dir=post[ENUM_POST.MAIN_DIR],
                                     sub_dir=postid)
  userpic_downloader = UserpicDownloader(main_dir=post[ENUM_POST.MAIN_DIR])
  post_parser = LJPostParser(image_downloader, post)
  logging.info('Parsing the post...')
  post_parser.feed(page_content)
  post[ENUM_POST.LINK] = page_addr
  json_content = extract_json_content(page_content)
  extract_author(json_content, post)
  extract_header(json_content, post)

  if post.get(ENUM_POST.COMPAGES) is None:
    post[ENUM_POST.COMPAGES] = []
    post[ENUM_POST.COMPAGES].append('/%s.html' % postid)

  logging.info('Parsing the comments (%d page(s) found)...',
      len(post[ENUM_POST.COMPAGES]))
  comment_processor = CommentTaskProcessor(
      image_downloader, userpic_downloader)
  for p in post[ENUM_POST.COMPAGES]:
    link = 'http://%s.livejournal.com%s' % (index[ENUM_INDEX.LJUSER], p)
    comment_processor.add_task(None, link)

  comment_processor.run()
  post[ENUM_POST.COMMENTS] = comment_processor.get_results()
  image_downloader.download_files()
  userpic_downloader.download_files()

  post[ENUM_POST.TEXT] = image_downloader.decode_filenames_in_text(
      post[ENUM_POST.TEXT])
  for com in post[ENUM_POST.COMMENTS]:
    com[ENUM_COM.TEXT] = image_downloader.decode_filenames_in_text(
        com[ENUM_COM.TEXT])
    com[ENUM_COM.USERPIC] = userpic_downloader.decode_filenames_in_text(
        com[ENUM_COM.USERPIC])

  # pop redundant fields
  post.pop(ENUM_POST.FILES)

  outfilename = '%s/%s.data' % (index[ENUM_INDEX.LJUSER], postid)
  save_json_to_file(post, outfilename)

  if (post[ENUM_POST.REPLYCOUNT] is not None and
      len(post[ENUM_POST.COMMENTS]) != post[ENUM_POST.REPLYCOUNT]):
    logging.warning(
        'WARNING: The number of obtained comments (%d) is different than '
        'in the post (%d)!' % (
            len(post[ENUM_POST.COMMENTS]), post[ENUM_POST.REPLYCOUNT]))

  logging.info("Summary: %d comments have been saved to file '%s'",
      len(post[ENUM_POST.COMMENTS]), outfilename)

  index_post = {
      ENUM_INDEX.POST_ID:     postid,
      ENUM_INDEX.POST_HEADER: post[ENUM_POST.HEADER],
      ENUM_INDEX.POST_DATE:   post[ENUM_POST.DATE],
      ENUM_INDEX.POST_TAGS:   post[ENUM_POST.TAGS],
  }
  index[ENUM_INDEX.POSTS][postid] = index_post

  outfilename = '%s/index.data' % (index[ENUM_INDEX.LJUSER])
  save_json_to_file(index, outfilename)


# MAIN
if __name__=='__main__':
  if len(sys.argv) < 2:
    print('Error: Too few params')
    exit(1)

  logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

  page_addr = sys.argv[1]

  m = re.search('(?:/*)([\w\-]+)\.livejournal.com/(\d+)\.\w*', page_addr)
  if m is None:
    logging.crtical("Error: Parsing '%s' failed", page_addr)
    exit(2)

  ljuser = m.group(1)
  postid = m.group(2)
  logging.info("ljuser: '%s', postid: '%s'", ljuser, postid)

  main_dir = './%s' % ljuser
  if not os.path.exists(main_dir):
    os.makedirs(main_dir)

  index = None
  findex = '%s/index.data' % main_dir
  if not os.path.isfile(findex):
    index = {}
    index[ENUM_INDEX.POSTS] = {}
    index[ENUM_INDEX.LJUSER] = ljuser
  else:
    with open(findex, 'r') as f:
      index = json.load(f)
      logging.info("Found index file '%s' (%d posts)",
          findex, len(index[ENUM_INDEX.POSTS]))

  index[ENUM_INDEX.DATE] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

  add_post_to_index(index=index, postid=postid)
