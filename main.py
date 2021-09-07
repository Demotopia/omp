# Done around July 2019. by Aleksandar Radenkovic
# Scraping commands updated 24.7.2020.

from flask import Flask, render_template
from flask import jsonify
from flask import request

#import scrape_module
import requests

from bs4 import BeautifulSoup
from time import sleep

# it appears the server is faster when all scraping code is in here

def cleanStartEnd(text):
  clean_comment = text
  up_limit = 0
  down_limit = 0
  for i in range(len(clean_comment) - 1, 0, -1):
    if not clean_comment[i] == '\t' and not clean_comment[i] == '\n' and not clean_comment[i] == ' ':
      up_limit = i + 1
      break
  for i in range(len(clean_comment)):
    if not clean_comment[i] == '\t' and not clean_comment[i] == '\n' and not clean_comment[i] == ' ':
      down_limit = i
      break
  return clean_comment[down_limit:up_limit]

def generateSoup(url):
  response = requests.get(url)
  soup = BeautifulSoup(response.text, "html.parser")
  if not soup:
    print("Soup is null (URL: " + url + ")")
  return soup


# gets URLs of all songs that match the search
# also should return the author if not specified by user
# ex. https://songmeanings.com/query/?query=in+the+end&type=all
# https://www.youtube.com/results?search_query=in+the+end
def getURLs_Songs(search):
  search = search.strip()
  search = search.lower()
  search = search.replace(" ", "+")
  search = search.replace("'", "%27")
  search = search.replace("$", "%24")  # for things like Ke$ha, but I can't deal with them all
  search = search.replace("(", "%28")
  search_page = 'https://songmeanings.com/query/?query=' + search + '&type=all'

  songs_soup = generateSoup(search_page)
  if not songs_soup:
    print("There was something wrong with the link to song meanings site (link: )" + search_page)
    if 'and' in search_page:
      print("Trying with & instead of 'and'")
      new_one = search_page.replace("and", "%26")
      songs_soup = generateSoup(new_one)
      if not songs_soup:
        return None, None, None, None, None
    else:
      return None, None, None, None, None
  song_choices = None
  songs_meanings_links = []
  songs_names = []
  artists_names = []
  try:
    cur = songs_soup.find('thead').find_next_sibling('tr')
    while cur:
      a_tags = cur.find('td').find_all('a')
      songs_meanings_links.append('https:' + a_tags[0]['href'])
      songs_names.append(a_tags[0].text)
      artists_names.append(a_tags[1].text)
      cur = cur.find_next_sibling('tr')

    print("Song names:\n\n")
    print(songs_names)
    print("Artist names:\n\n")
    print(artists_names)

  except Exception as e:
    print("Error getting song meanings: " + str(e))
    return None, None, None, None, None

  youtube_search_links = []  # using youtube search
  for i in range(len(songs_names)):
    raw_link = 'https://www.youtube.com/results?search_query=' + str(songs_names[i]) + ' ' + str(artists_names[i])
    raw_link = raw_link.replace("'", "%27")
    raw_link = raw_link.replace("$", "%24")
    raw_link = raw_link.replace("(", "%28")
    raw_link = raw_link.replace(")", "%29")
    raw_link = raw_link.lower()
    clean_link = raw_link.replace(" ", "+")
    youtube_search_links.append(clean_link)

  search_art = 'https://www.discogs.com/search/?q='
  art_links = []
  for i in range(len(songs_names)):
    # both the songs and artists names are already capital first letters
    raw_link = search_art + str(songs_names[i]) + ' ' + str(artists_names[i]) + '&type=all'
    raw_link = raw_link.replace(" ", "+")
    raw_link = raw_link.replace("'", "%27")
    raw_link = raw_link.replace("$", '%24')
    raw_link = raw_link.lower()
    art_links.append(raw_link)

  return songs_meanings_links, songs_names, artists_names, youtube_search_links, art_links


def getLyrics(soup):
  try:
    lyrics_raw_arr = soup.find_all('div', 'holder lyric-box')[0].contents
    lyrics_arr = []  # arr of strings - both text and tags
    for el in lyrics_raw_arr:
      lyrics_arr.append(str(el))
    # get lyrics and filter out the tags:
    lyrics = ''
    for el in lyrics_arr:
      if not el[0] == '<':
        lyrics += el
    lyrics = cleanStartEnd(lyrics)
    return lyrics
  except Exception as e:
    print("An error occured trying to get the lyrics.\nError: " + str(e))
    return ''

# returns top two comments/meanings with their ratings,
# one of which has to have "song meaning" title
def getMeaning(soup):
  first_comment = soup.find('ul', 'comments-list').findChild('li')
  votes = []
  comments = []
  i = 0
  prev = first_comment
  foundSongMeaning = False
  # in order to have at least 2 comments and at least one of them is SongMeaning type
  while ((not foundSongMeaning and i < 10) or i < 2) and prev.find_next_sibling('li'):
    li = prev
    prev = prev.find_next_sibling('li')
    raw_comment = li.find('div', 'text')
    if raw_comment.findChild().text == "Song Meaning":
      foundSongMeaning = True
    # top rated comment should be displayed no matter its type
    elif i != 0 and not foundSongMeaning and prev.find_next_sibling('li'):
      i += 1
      continue
    elif not prev.find_next_sibling('li'):  # go back to second comment
      li = first_comment.find_next_sibling('li')
      raw_comment = li.find('div', 'text')
    raw_comment_arr = []  # turning the tag into string array
    for el in raw_comment:
      raw_comment_arr.append(str(el))
    clean_comment = ''
    for el in raw_comment_arr:
      if not el[0] == '<':  # skipping break lines and other tags
        clean_comment += el
    clean_comment = cleanStartEnd(clean_comment)
    # saving the comment:
    comment = {}  # dict, key is the type of comment (ex. General) value is the comment itself
    comment[raw_comment.findChild().text] = clean_comment
    comments.append(comment)
    votes.append(li.findChild('strong', 'numb').text)
    i += 1
  return comments, votes


def getYT_VideoLink(youtube_search_link='', original_search=''):
  cur_soup = None
  if youtube_search_link == '':
    print("Generating an alternative YouTube link..")
    sleep(0.1)
    new_link = 'https://www.youtube.com/results?search_query=' + original_search.strip()
    new_link = new_link.replace(" ", "+")
    new_link = new_link.replace("'", "%27")
    new_link = new_link.replace("$", "s")
    new_link = new_link.replace("(", "%28")
    new_link = new_link.replace(")", "%29")
    new_link = new_link.lower()
    print("Generated an alternative YouTube link: " + new_link)
    cur_soup = generateSoup(new_link)
  else:
    cur_soup = generateSoup(youtube_search_link)
  try:
    #video_link = str(cur_soup.findChildren('div', attrs={"class":'yt-lockup yt-lockup-tile yt-lockup-video vve-check clearfix'})[1]['data-context-item-id'])
    link_wrapper = '"watchEndpoint":{"videoId":"'
    link_is_there = str(cur_soup.find('body', attrs={"dir": "ltr"}))
    video_link_start_idx = link_is_there.find(link_wrapper) + len(link_wrapper)
    video_link = ''
    while link_is_there[video_link_start_idx] != '"':
      video_link += link_is_there[video_link_start_idx]
      video_link_start_idx += 1
    print("Found YT id: " + video_link)
    return video_link
  except Exception as e:
    print(";( There was an error trying to find yt video link.\nError: " + str(e))
    print("Tried on google link: " + youtube_search_link)
    return ''


# get the link for the icon which will be in image src tag of html

def getImageLink(art_search):
  soup = generateSoup(art_search)
  try:
    cover_image_tag = soup.find('div', attrs={"id": "search_results"}).findChild().findChild().find('span', 'thumbnail_center')
    cover_image_link = str(cover_image_tag.findChild('img')['data-src'])
    return cover_image_link
  except:
    print("Couldn't get cover image.")
    return ''


# Part of this function is from repl: https://repl.it/@paulfears/similar-music-api
# which was given as inspiration project for the competition
def getSimiliarArtists(muse):
  search_page = 'https://www.music-map.com/map-search.php?f=' + muse
  soup = generateSoup(search_page)
  try:
    similiar_artists = soup.find_all('a', 'S')
    similiar_artists = map(lambda x: x.get_text(), similiar_artists)
    sleep(0.1)
    return list(similiar_artists)  # first el is the searched one(muse)
  except Exception as e:
    print("An error occurred trying to get similiar artists to " + muse + "\nError: " + str(e))
    return []


# return wiki link to the author
def getWikiArtist(artist):
  if artist == '':
    return ''
  wiki_page = 'https://en.wikipedia.org/wiki/'
  link = wiki_page + artist
  link = link.replace(" ", "_")
  link = link.replace("$", "s")
  link = link.lower()
  return link

# gather all data into object to send through a GET request
def getSongNode(soup, song_name, artist_name, youtube_search_link, art_link):
  # always get the artist defined by user (if defined)
  wiki_page = getWikiArtist(artist_name)
  similiar_artists = getSimiliarArtists(artist_name)
  songMeanings, votes = getMeaning(soup)
  lyrics = getLyrics(soup)
  yt_VideoID = getYT_VideoLink(youtube_search_link=youtube_search_link)
  albumCoverLink = getImageLink(art_link)

  songNode = {"songName": song_name,  # the one found on the website
              "artistName": artist_name,  # the one found on the website
              "wikiAboutArtistURL": wiki_page,  # unsure if value is valid page link, some value always returned (never empty string)
              "similiarArtists": similiar_artists,  # empty list if nothing was found
              "songMeaningsVotes": votes,  # empty list if nothing was found
              "songMeanings": songMeanings,  # empty list if nothing was found
              "songLyrics": lyrics,  # empty string if nothing was found
              "yt_VideoID": yt_VideoID,  # empty string if nothing was found
              "albumCoverLink": albumCoverLink  # emoty string if nothing was found
              }
  return songNode


def getAllSongData(song_search, artist_search):
  songNodesArr = []  # data returned
  search = song_search.strip() + ' ' + artist_search.strip()

  songs_search_found_urls, songs_search_found_names, artists_search_found_names, youtube_search_links, art_links = getURLs_Songs(search)

  if songs_search_found_urls:  # found songmeanings.com's data
    # get separate node for each soup based on each song_url from array above
    for i in range(len(songs_search_found_urls)):
      cur_soup = generateSoup(songs_search_found_urls[i])
      cur_songName = songs_search_found_names[i]
      cur_artistName = artists_search_found_names[i]
      cur_youtube_search_link = youtube_search_links[i]
      cur_art_link = art_links[i]

      songNodesArr.append(getSongNode(cur_soup, cur_songName, cur_artistName, cur_youtube_search_link, cur_art_link))

  # adding an alternative in case other data was not found or incorrect
  wiki_page = getWikiArtist(artist_search)
  similiar_artists = getSimiliarArtists(artist_search)
  yt_VideoID = ''
  try:
    yt_VideoID = getYT_VideoLink(original_search=search)
  except Exception as e:
    print("Did not get yt video ID. Error: " + str(e))
  albumCoverLink = ''
  try:
    raw_link = 'https://www.discogs.com/search/?q=' + search + '&type=all'
    raw_link = raw_link.replace(" ", "+")
    raw_link = raw_link.replace("'", "%27")
    raw_link = raw_link.replace("$", '%24')
    raw_link = raw_link.lower()
    albumCoverLink = getImageLink(raw_link)
  except Exception as e:
    print("Sth fishy here. Error: " + str(e))

  # an alternative is always added
  songNode = {"songName": song_search,  # the one user specified
              "artistName": artist_search,  # the one user specified
              "wikiAboutArtistsURL": wiki_page,  # unsure if value is valid page link, if artist unspecified returns empty string
              "similiarArtists": similiar_artists,  # empty list if nothing was found
              "songMeaningsVotes": [],  # empty list if nothing was found
              "songMeanings": [],  # empty list if nothing was found
              "songLyrics": '',  # empty string if nothing was found
              "yt_VideoID": yt_VideoID,  # empty string if nothing was found
              "albumCoverLink": albumCoverLink  # emoty string if nothing was found
              }
  songNodesArr.append(songNode)
  return songNodesArr


# =========================================================================
# *************************************************************************
# =========================================================================
#                     APP:

"""

app = Flask(__name__, static_folder='.', root_path='/home/runner')


@app.route('/')
def root():
  return app.send_static_file('./index.html')


@app.route('/send_user_search')
def send_user_search():
  try:
    song_searched = str(request.args.get('songSearched')).strip().lower()
    artist_searched = str(request.args.get('artistSearched')).strip().lower()
    print("Got Song Search info: " + song_searched)
    print("Got Artist Search info: " + artist_searched)

    #songNodesList = scrape_module.getAllSongData(song_searched, artist_searched)
    songNodesList = getAllSongData(song_searched, artist_searched)
    return jsonify(song_nodes=songNodesList)
  except Exception as e:
    print("Oops. An error occurred brah: " + str(e))
    return str(e)



if __name__ == '__main__':
  app.run(host='0.0.0.0', port='8080')
"""



@web_site.route('/')
def index():
	return render_template('index.html')

@web_site.route('/send_user_search')
def send_user_search():
  try:
    song_searched = str(request.args.get('songSearched')).strip().lower()
    artist_searched = str(request.args.get('artistSearched')).strip().lower()
    print("Got Song Search info: " + song_searched)
    print("Got Artist Search info: " + artist_searched)

    #songNodesList = scrape_module.getAllSongData(song_searched, artist_searched)
    songNodesList = getAllSongData(song_searched, artist_searched)
    return jsonify(song_nodes=songNodesList)
  except Exception as e:
    print("Oops. An error occurred brah: " + str(e))
    return str(e)


web_site = Flask(__name__)
web_site.run(host='0.0.0.0', port=8080)
# web_site.run(debug=True)
