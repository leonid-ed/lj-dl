"""
"""

def confirm(question):
  answer = ""
  while answer not in ['y', 'n']:
    answer = str(input("%s (y/n): " % question)).lower().strip()
  return answer == 'y'
