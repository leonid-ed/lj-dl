# lj-dl

LiveJournal Downloader

These tools download pages of livejournal in HTML format including images and
userpics in order to create one HTML page for each post with all the comments unrolled on the disk.


## lj-dl.py

The tool downloads livejournal posts and comments in HTML format (including images and
userpics) and creates json files to keep their structure on the disk.

Requirements: `aiohttp`, `asyncio`

**For now it supports only jivejournal pages that have json section with comments.**
Otherwise you will get an error:
```
Error: Parsing failed (no author in json content)
```

Example of usage:
```bash
python3 lj-dl.py https://<user_name>.livejournal.com/1234567.html
```

After the tool finishes you will have a directory with `<user_name>` name
containing the downloaded files.

## lj-cv.py

The tool is to create HTML pages based on downloaded files.

Example of usage:
```bash
python3 lj-cv.py <user_name>
```

After the tool finishes you will have a subdirectory `html` in `<user_name>` name
containing the generated HTML-files.
