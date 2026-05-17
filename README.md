# tunefind
tunefind parser for TV shows and movies tracklist

just find show in tunefind and get name from url, eg for Breaking Bad we get https://www.tunefind.com/show/breaking-bad that means we use breaking-bad as "showname" argument

```python3 tunefind.py breaking-bad```

```python3 tunefind.py https://www.tunefind.com/show/breaking-bad```

```python3 tunefind.py movie/el-camino-a-breaking-bad-movie-2019```

after process we get breaking-bad.md in result folder

use ```--no-cache``` option to force downloading data again instead using cached data
```-v``` for debug logging
```-s``` for search (or don't use arguments)
