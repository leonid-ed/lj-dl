# -*- coding: utf-8 -*-

import sys
import subprocess
import re
import os.path
import json

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
    out += "<title>%s</title>\n" % jdata["post-header"]
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
  if jdata.get('post-tags'):
    post_tags = "Tags: " + ", ".join(jdata['post-tags'].keys())

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
""") % ( jdata['post-header'], jdata['post-date'],
         jdata['post-link'], jdata['post-text'], post_tags )

  out += ( """
<div class=\"post-comments\" >
  %d Comments
</div>
""") % (len(jdata["comments"]))

  for comm in jdata["comments"]:
    comment_user_style = "comment-head"
    if comm['user'] == jdata['post-author']:
      comment_user_style = "comment-head-ljuser"

    if comm['userpic'] is None:
      print("Warning: user '%s' does not have userpic!" % comm['user'])

    offset = int(comm["level"]) * 20
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
""" ) % (offset, comment_user_style, "../" + comm['userpic'],
         comm['user'], comm['date'], comm['thread-url'], comm['text'])

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
    for p in jdata['index-posts']:
      make_post_html_page(ljuser, p['index-post-id'])
