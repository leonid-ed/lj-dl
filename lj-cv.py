# -*- coding: utf-8 -*-

import sys
import subprocess
import re
import os.path
import json

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

def make_post_html_page(main_dir, postid):
  fdata = "%s/%s.data" % (main_dir, postid)
  if not os.path.isfile(fdata):
    print("Error: file '%s' doesn't exist" % fdata)
    return 1

  with open(fdata, "r") as f:
    jdata = json.load(f)

    out = "<!DOCTYPE HTML>\n"
    out += "<html><head>\n"
    out += "<meta charset=\"utf-8\">\n"
    out += "<title>%s</title>\n" % jdata[POST_HEADER]
    out += """<style type=\"text/css\">
  .post-head {
    background: #BFEFFF;
    border: solid 0px black;
    padding: 2px;
  }
  .post-head-date {
    font:  12pt sans-serif;
    color: #8B8989
  }
  .post-head-title {
    font:  16pt sans-serif;
    background: #BFEFFF;
  }
  .post-text {
    background: #FFFFFF;
    border: solid 0px black;
    padding: 4px;
    font:  12pt Helvetica;
  }
  .post-tags {
    font:  12pt sans-serif;
    color: #8B8989
  }
  .post-comments {
    background: #FFFFFF;
    border: solid 0px black;
    padding: 15px;
    font:  bold 14pt Sans-serif;
  }
  .comment-text {
    background: #FFFFFF;
    border: solid 0px black;
    padding: 1px;
    font:  11pt Sans-serif;
  }
  .comment-head-ljuser {
    background: #87CEFA;
    border: solid 0px black;
    padding: 1px;
  }
  .comment-head {
    background: #DCDCDC;
    border: solid 0px black;
    padding: 1px;
  }
  .comment-head-user {
    font:  bold 10pt sans-serif;
  }
  .comment-head-date {
    font:  10pt sans-serif;
  }
</style>\n"""

  out += "</head>\n"
  out += "<body>\n"

  post_tags = ""
  if jdata.get(POST_TAGS):
    post_tags = "Tags: " + ", ".join(jdata[POST_TAGS].keys())

  out += ( """
<div class=\"post-head\" ">
  <table>
  <tr><td>
    <div class=\"post-head-title\" >
      %s
    </div>
  </td></tr>
  <tr><td>
    <div class=\"post-head-date\" >
      %s
    </div>
  </td></tr>
  <tr><td>
    <a href=\"%s\">(link)</a>
  </td></tr>
  <tr><td>
    <div class=\"post-text\" >
      %s
    </div>
  </td></tr>
    <tr><td>
    <div class=\"post-tags\" >
      %s
    </div>
  </td></tr>
  </table>
</div>
""") % ( jdata[POST_HEADER], jdata[POST_DATE],
         jdata[POST_LINK], jdata[POST_TEXT], post_tags )

  out += ( """
<div class=\"post-comments\" >
  %d Comments
</div>
""") % (len(jdata[POST_COMMENTS]))

  for comm in jdata[POST_COMMENTS]:
    comment_user_style = "comment-head"
    if comm[COM_USER] == jdata[POST_AUTHOR]:
      comment_user_style = "comment-head-ljuser"

    if comm[COM_USERPIC] is None:
      print("Warning: user '%s' does not have userpic!" % comm[COM_USER])

    offset = int(comm[COM_LEVEL]) * 20
    out += ( """
<div style=\"border: solid 0px black; padding: 2px; padding-left: %dpx; \">
  <table>
  <tr><td>
    <div class=\"%s\" >
      <table>
      <tr><td class=\"comment-head-user\" rowspan=3>
        <img src=\"%s\"></img>
      </td>
      <td>
        %s
      </td></tr>
      <tr><td class=\"comment-head-date\">
        %s
      </td></tr>
      <tr><td class=\"comment-head-date\">
        <a href=\"%s\">(link)</a>
      </td></tr>
      </table>
    </div>
  </td></tr>
  <tr><td>
    <div class=\"comment-text\" >%s
    </div>
  </td></tr>
  </table>
</div>
""" ) % (offset, comment_user_style, "../" + comm[COM_USERPIC],
         comm[COM_USER], comm[COM_DATE], comm[COM_THREADURL], comm[COM_TEXT])

  out += "</body>"
  out += "</html>"

  filename = "%s/html/%s.html" % (main_dir, postid)
  with open(filename, 'w+') as f:
    f.write(out)

  print("HTML file '%s' has been generated successfully" % filename)
  return 0

# MAIN
if __name__=='__main__':
  if len(sys.argv) < 2:
    print("Error: Too few params")
    exit(1)

  ljuser = sys.argv[1]
  fdata = ljuser + "/index.data"
  if not os.path.isfile(fdata):
    print("Error: file '%s' doesn't exist" % fdata)
    exit(1)

  html_dir = "%s/html/" % ljuser
  if not os.path.exists(html_dir):
    os.makedirs("./" + html_dir)

  with open(fdata, "r") as f:
    jdata = json.load(f)

  for p in jdata[INDEX_POSTS].values():
    make_post_html_page(ljuser, p[INDEX_POST_ID])
