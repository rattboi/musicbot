""" Service to manage Google Music """
import logging
import string

from gmusicapi import Mobileclient

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def levenshtein(a, b):
    "Calculates the Levenshtein distance between a and b."
    n, m = len(a), len(b)
    if n > m:
        # Make sure n <= m, to use O(min(n,m)) space
        a, b = b, a
        n, m = m, n
    current = range(n+1)
    for i in range(1, m+1):
        previous, current = current, [i]+[0]*n
        for j in range(1, n+1):
            add, delete = previous[j]+1, current[j-1]+1
            change = previous[j-1]
            if a[j-1] != b[i-1]:
                change = change + 1
            current[j] = min(add, delete, change)
    return current[n]


def find_ratio(a, b):
    a_filtered = cleanup(a)
    b_filtered = cleanup(b)
    distance = levenshtein(a_filtered, b_filtered)
    ratio = (distance / max(len(a_filtered), len(b_filtered), 1))
    return ratio

def similarity(artist_a, artist_b, title_a, title_b):
    artist_ratio = find_ratio(artist_a, artist_b)
    title_ratio = find_ratio(title_a, title_b)
    ratio = artist_ratio + title_ratio
    return ratio

def cleanup(s):
    exclude = set(string.punctuation)
    extra_words_filter = ''.join(
             s.lower()
              .replace('the','',-1)
              .replace('deluxe','',-1)
              .replace('expanded','',-1)
              .replace('edition','',-1)
              .replace('remastered','',-1)
              .replace('reissue','',-1)
              .replace('version','',-1)
              .replace('bonus','',-1)
              .replace('tracks','',-1)
              .replace('track','',-1)
              .split())
    punc_filter = ''.join(ch for ch in extra_words_filter if ch not in exclude)
    return punc_filter


class Gmusic(object):
    """Class to handle Google Music-related functionality"""

    def __init__(self, bot):
        """ init """
        self.bot = bot
        self.mob = Mobileclient()

    def login(self, username, password):
        """ login method """
        self.mob.login(username, password, Mobileclient.FROM_MAC_ADDRESS)
        return self.mob.is_authenticated()

    def search(self, searchterms):
        """ search for stuff """
        hits = self.mob.search("{0}".format(searchterms))
        return hits

    def create_playlist(self, name, song_ids, public=True):
        """
        create new playlist named 'name', containing songs with 'song_id'
        """
        playlist_id = self.mob.create_playlist(name,
                                               description="Bot Playlist",
                                               public=public)
        self.mob.add_songs_to_playlist(playlist_id, song_ids)

    def get_best_song_match(self, artist, title):
        hits = self.search("{0} {1}".format(artist, title))
        tracks = self.filter_to_song_minimum_info(self.get_songs(hits))
        similarities = [(similarity(track['artist'], artist,
                                    track['title'], title), track)
                        for track in tracks]

        sorted_tracks = sorted(similarities, key=lambda k: k[0])

        best_track = None
        if len(sorted_tracks) > 0:
            best_track = sorted_tracks[0][1]
        return best_track

    def format_best_match(self, artist, title):
        track = self.get_best_song_match(artist, title)
        share_base_url = 'https://play.google.com/music/m/'

        return "{0} {1} {2} - {3}{4}".format(track['artist'],
                                             track['album'],
                                             track['title'],
                                             share_base_url,
                                             track['storeId'])

    def get_song_ids_from_song_names(self, song_names):
        for name in song_names:
            self.search()

    def get_songs(self, results):
        return [song.get('track', None) for song in results['song_hits']]

    def filter_to_song_minimum_info(self, results):
        return [{'artist':  song.get('artist', None),
                 'album':   song.get('album', None),
                 'title':   song.get('title', None),
                 'storeId': song.get('storeId', None)} for song in results]
