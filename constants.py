def constant(f):
  def fset(self, value):
    raise TypeError
  def fget(self):
    return f()
  return property(fget, fset)

class _EnumIndex(object):
  @constant
  def LJUSER():
    return "index-ljuser"
  @constant
  def DATE():
    return "index-date"
  @constant
  def POSTS():
    return "index-posts"
  @constant
  def POST_DATE():
    return "index-post-date"
  @constant
  def POST_HEADER():
    return "index-post-header"
  @constant
  def POST_TAGS():
    return "index-post-tags"
  @constant
  def POST_ID():
    return "index-post-id"
  @constant
  def FILES():
    return "index-files"

ENUM_INDEX = _EnumIndex()

class _EnumPost(object):
  @constant
  def HEADER():
    return "post-header"
  @constant
  def AUTHOR():
    return "post-author"
  @constant
  def DATE():
    return "post-date"
  @constant
  def TEXT():
    return "post-text"
  @constant
  def COMPAGES():
    return "post-comment-pages"
  @constant
  def COMMENTS():
    return "post-comments"
  @constant
  def LINK():
    return "post-link"
  @constant
  def TAGS():
    return "post-tags"
  @constant
  def ID():
    return "post-id"
  @constant
  def FILES():
    return "post-files"
  @constant
  def MAIN_DIR():
    return "post-main-dir"

ENUM_POST = _EnumPost()


class _EnumCom(object):
  @constant
  def TEXT():
    return 'text'
  @constant
  def USER():
    return 'user'
  @constant
  def USERPIC():
    return 'userpic'
  @constant
  def DATE():
    return 'date'
  @constant
  def DATETS():
    return 'ts'
  @constant
  def ABOVE():
    return 'above'
  @constant
  def BELOW():
    return 'below'
  @constant
  def LEVEL():
    return 'level'
  @constant
  def THREAD():
    return 'thread'
  @constant
  def THREADURL():
    return 'thread-url'

ENUM_COM = _EnumCom()

