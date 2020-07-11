"""
"""

import aiohttp
import asyncio
import logging
from contextlib import closing


class FileDownloader():

  @staticmethod
  async def _download(url, dest, session, semaphore, chunk_size=1 << 15):
    async with semaphore:
      logging.info("Downloading file '%s' --> '%s'", url, dest)
      try:
        response = await session.get(url)  # , verify_ssl=False
      except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        logging.error("Downloading file '%s': Error occured ('%s')",
            dest, e)
        return -1, url, dest
      else:
        if response.status == 200:
          size = 0
          with closing(response), \
               open(dest, 'wb') as file:
            while True:  # save file
              chunk = await response.content.read(chunk_size)
              if not chunk:
                break
              file.write(chunk)
              size += len(chunk)
          logging.info("Downloading file '%s': Done [%d]", dest, size)
        else:
          logging.error("Downloading file '%s': Error occured (%d)",
              dest, response.status)
        return response.status, url, dest

  @staticmethod
  async def download_files_asynchronously(
      urls, max_connections):
    async with aiohttp.ClientSession() as session:
      semaphore = asyncio.Semaphore(max_connections)
      tasks = [
          FileDownloader._download(url, dest, session, semaphore)
          for url, dest in urls.items()
      ]
      return await asyncio.wait(tasks)


class ContentDownloader():

  @staticmethod
  async def _download(url, session, semaphore, chunk_size=1 << 15):
    content = None
    async with semaphore:
      logging.info("Downloading content of '%s'", url)
      response = await session.get(url)
      if response.status == 200:
        content = await response.read()
        size = len(content)
        content = content.decode('utf-8')
        logging.info("Downloading content of '%s': Done [%d]", url, size)
      else:
        logging.error("Downloading content of '%s': Error occured (%d)",
            url, response.status)
    return response.status, url, content

  @staticmethod
  async def download_content_asynchronously(
      urls, max_connections):
    async with aiohttp.ClientSession() as session:
      semaphore = asyncio.Semaphore(max_connections)
      tasks = [
          ContentDownloader._download(url, session, semaphore)
          for url in urls
      ]
      return await asyncio.wait(tasks)
