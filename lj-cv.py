# -*- coding: utf-8 -*-

from constants import (ENUM_INDEX, ENUM_POST, ENUM_COM)
import sys
import subprocess
import re
import os.path
import json
import shutil

def make_index_html_page(main_dir, posts):

  out = "<!DOCTYPE HTML>\n"
  out += "<html><head>\n"
  out += "<meta charset=\"utf-8\">\n"
  out += "<title>%s</title>\n" % main_dir

  out += "</head>\n"
  out += "<body>\n"

  out += """
<div class=\"post-head\" ">
  <table>
"""
  for p in posts.values():
    link = "<a href=\"./%s.html\">%s</a>" % (p[ENUM_INDEX.POST_ID], "%s")
    out += """
  <tr>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
  </tr>
""" % (
    (link % p[ENUM_INDEX.POST_DATE]),
    (link % p[ENUM_INDEX.POST_HEADER]),
    (", ".join(p[ENUM_INDEX.POST_TAGS].keys())),
  )
    # import pdb; pdb.set_trace()

  out += """
  </table>
</div>
"""
  out += "</body>"
  out += "</html>"

  filename = "%s/html/index.html" % (main_dir)
  with open(filename, 'w+') as f:
    f.write(out)

  print("Index HTML file '%s' has been generated successfully" % filename)
  return 0


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
    out += "<title>%s</title>\n" % jdata[ENUM_POST.HEADER]
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
  if jdata.get(ENUM_POST.TAGS):
    post_tags = "Tags: " + ", ".join(jdata[ENUM_POST.TAGS].keys())

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
""") % ( jdata[ENUM_POST.HEADER], jdata[ENUM_POST.DATE],
         jdata[ENUM_POST.LINK], jdata[ENUM_POST.TEXT], post_tags )

  out += ( """
<div class=\"post-comments\" >
  %d Comments
</div>
""") % (len(jdata[ENUM_POST.COMMENTS]))

  thread_levels = []           # [  (thread_id, thread_level)  ]
  for comm in jdata[ENUM_POST.COMMENTS]:

    thread_above = comm[ENUM_COM.ABOVE]
    thread_level = int(comm[ENUM_COM.LEVEL])
    thread_parent = comm[ENUM_COM.PARENT]

    if not thread_parent:
      thread_levels = [ (comm[ENUM_COM.THREAD], thread_level) ]
    else:
      (prev_tread_id, prev_tread_level) = thread_levels[-1]
      if thread_parent == prev_tread_id:
        thread_level = prev_tread_level + 1
        thread_levels.append( (comm[ENUM_COM.THREAD], thread_level) )
      else:
        while True:
          thread_levels.pop()
          # if len(thread_levels) == 0:
          #   import pdb; pdb.set_trace()
          (prev_tread_id, prev_tread_level) = thread_levels[-1]
          if thread_parent == prev_tread_id:
            thread_level = prev_tread_level + 1
            thread_levels.append( (comm[ENUM_COM.THREAD], thread_level) )
            break

    comment_user_style = "comment-head"
    if comm[ENUM_COM.USER] == jdata[ENUM_POST.AUTHOR]:
      comment_user_style = "comment-head-ljuser"

    if comm[ENUM_COM.USERPIC] is None:
      print("Warning: user '%s' does not have userpic!" % comm[ENUM_COM.USER])

    offset = thread_level * 20
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
""" ) % (offset, comment_user_style, "../" + comm[ENUM_COM.USERPIC],
         comm[ENUM_COM.USER], comm[ENUM_COM.DATE], comm[ENUM_COM.THREADURL],
         comm[ENUM_COM.TEXT])

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

  # copying no-picture.svg to html directory
  nopicture_filename = "no-picture.svg"
  if not os.path.isfile("./%s/%s" % (html_dir, nopicture_filename)):
    if os.path.isfile("./%s" % nopicture_filename):
      shutil.copyfile(
        "./%s" % nopicture_filename,
        "./%s/%s" % (html_dir, nopicture_filename)
      )
    else:
      print("Error: file './%s' doesn't exist" % nopicture_filename)

  with open(fdata, "r") as f:
    jdata = json.load(f)

  # sort posts by creation time
  jdata[ENUM_INDEX.POSTS] = {
    p : jdata[ENUM_INDEX.POSTS][p] for p in sorted(jdata[ENUM_INDEX.POSTS])
  }

  make_index_html_page(ljuser, jdata[ENUM_INDEX.POSTS])

  for p in jdata[ENUM_INDEX.POSTS].values():
    make_post_html_page(ljuser, p[ENUM_INDEX.POST_ID])
