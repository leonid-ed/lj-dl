# lj-dl

LiveJournal Downloader

These tools download pages of livejournal in HTML format including images and
userpics in order to create one HTML page for each post with all the comments unrolled on the disk.

## lj-get-post-links-for-year.py

This tool accepts 2 arguments:
- `page_addr` - a link to some post page of the livejournal which is supposed to be downloaded.
- `year` - a year for which all post links will be fetched.

It downloads a calendar page of a given year, looks for a proper year calendar
parser, then downloads all calendar pages of days with posts published
(one by one), looks for a proper day calendar parser, then obtains all post
links and prints them to `STDOUT` in the following format:
```
<post_date1> <post_link1>
<post_date1> <post_link2>
<post_date2> <post_link3>
<post_date3> <post_link4>
...
```
Debug logging is printed to `STDERR`, so can be easily filtered.

For now the script supports only `Minimalism` style, so if you need other styles,
you can extend this script with new parsers and add their support to the functions
`get_year_calendar_parser` and `and get_day_calendar_parser`.

Example of usage:
```bash
$ python lj-get-post-links-for-year.py https://danwalsh.livejournal.com/81756.html 2019 | tee danwalsh_2019.txt
ljuser: 'danwalsh'
Downloading content of 'https://danwalsh.livejournal.com/2019/'... [626980]
Parsing the page 'https://danwalsh.livejournal.com/2019/'...
Downloading content of 'https://danwalsh.livejournal.com/2019/02/20/'... [628650]
Downloading content of 'https://danwalsh.livejournal.com/2019/05/21/'... [627968]
2019-02-20 https://danwalsh.livejournal.com/81480.html
2019-05-21 https://danwalsh.livejournal.com/81756.html
```

## lj-dl.py

The tool downloads livejournal posts and comments in HTML format (including images and
userpics) and creates json files to keep their structure on the disk.

Requirements: `aiohttp`, `asyncio`

**For now it supports only livejournal posts that have `is_version2` version
(you can it find in the source of the page.**
Otherwise you will get an error:
```
Error: Parsing failed (no author in json content)
```

Example of usage:
```bash
$ python lj-dl.py https://<user_name>.livejournal.com/1234567.html

# or

$ cat danwalsh_2019.txt | awk '{print $2}' | xargs -n 1 python lj-dl.py 2>&1 | tee danwalsh_2019.log
```

After the tool finishes you will have a directory with `<user_name>` name
containing the downloaded files.

## lj-cv.py

The tool is to create HTML pages based on downloaded files.

Example of usage:
```bash
python3 lj-cv.py <user_name>
```

After the tool finishes you will have a subdirectory `html` in `<user_name>`
containing the generated HTML-files.


## Install requirements

```
$ python3 -m venv venv
$ source ./venv/bin/activate
$ pip install -r requirements.txt
```