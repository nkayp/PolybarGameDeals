#!/usr/bin/python3

'''
  This script contains all the methods pertaining to database interactions.
  ps.py and pc.py both fetch and return the data that this file processes and
  adds to the database.
'''

from datetime import datetime, timedelta

from .db_enums import DB_Indices, DB_Columns
from ..platforms.pc import PC
from ..platforms.ps import PS

class DB_Calls:
  #####################
  '''   VARIABLES   '''
  #####################
  ''' The default delay before updating the top deals '''
  _UPDATE_DELAY = timedelta(seconds=0, minutes=0, hours=12, days=0)



  ############################
  '''   "PUBLIC" METHODS   '''
  ############################
  ''' A simple function to fetch all the data from the given table. If the table
      doesn't exist then it will be created. '''
  @staticmethod
  def get_data(cur, table):
    try:
      cur.execute(f"""SELECT SALE_PRICE FROM {table}""")
    except Exception:
      cur.execute(f"""CREATE TABLE {table}(title TEXT NOT NULL UNIQUE, full_price REAL, sale_price REAL, cover_image TEXT, url TEXT NOT NULL UNIQUE, gid INTEGER UNIQUE, update_time TEXT, title_length INTEGER)""")
    return cur.execute(f"""SELECT * FROM {table} ORDER BY sale_price ASC""").fetchall()

  ''' Add top deals to the database. Since top deals will time out and not exist
      anymore, we need to check if games in the database need to updated or
      removed. '''
  @staticmethod
  def add_top_deals(cur, table, existing_games, new_games):
    ''' When adding top deals, we need to remove the games that are no longer a "top deal" '''
    unmatched_titles = []
    for existing_game in existing_games:
      matched = False
      for new_game in new_games:
        if(existing_game[DB_Indices.TITLE.value] == new_game[DB_Columns.TITLE.value]):
          matched = True
          break
      if(not matched):
        ''' append it to the list of titles that we will delete '''
        unmatched_titles.append(existing_game[DB_Indices.TITLE.value])
    
    ''' Delete the games that aren't found in the api response anymore '''
    for title in unmatched_titles:
      DB_Calls.delete_game_with_title(cur, table, title)
   
    ''' Update the remainder of the games that are already present, add the
        games that are new entries to the database. '''
    for game in new_games: 
      if(cur.execute(f"SELECT * FROM {table} WHERE TITLE=?", (game[DB_Columns.TITLE.value], )).fetchone()):
        cur.execute(f"""UPDATE {table} SET sale_price=?, url=?, update_time=? WHERE TITLE=?""", (game[DB_Columns.SALE_PRICE.value], game[DB_Columns.URL.value], datetime.now(), game[DB_Columns.TITLE.value]))
      else:
        cur.execute(f"""INSERT INTO {table} VALUES(?, ?, ?, ?, ?, ?, ?, ?)""", (game[DB_Columns.TITLE.value], game[DB_Columns.FULL_PRICE.value], game[DB_Columns.SALE_PRICE.value], game[DB_Columns.COVER_IMAGE.value], game[DB_Columns.URL.value], game[DB_Columns.GID.value], datetime.now(), len(game[DB_Columns.TITLE.value])))

  @staticmethod
  def game_exists(cur, table, cls, id):
    if(cls.is_valid(id)):
      if(cur.execute(f"""SELECT * FROM {table} WHERE gid=? OR url=?""", (id, id)).fetchone()): return True
    return False

  ''' Delete game with given title from the database '''
  @staticmethod
  def delete_game_with_title(cur, table, title):
    cur.execute(f"""DELETE FROM {table} WHERE TITLE=?""", (title, ))

  @staticmethod
  def delete_game_with_id(cur, table, id):
    cur.execute(f"""DELETE FROM {table} WHERE gid=?""", (id, ))

  ''' Delete game with given title from the database and the list of games
      This function is used exclusively to delete games through the rofi prompt '''
  @staticmethod
  def delete_game_now(cur, table, title, games):
    for index, game in enumerate(games[table]):
      if(game[DB_Indices.TITLE.value] == title):
        del games[table][index]
        cur.execute(f"""DELETE FROM {table} WHERE TITLE=?""", (title, ))
        return games

  ''' Called when wanting to add new wishlist PC games '''
  @staticmethod
  def add_pc_games(cur, table, ids):
    time = datetime.now()
    id_string = ""
    update_ids = []
    for index, id in enumerate(ids):
      if(PC.is_valid(id)):
        ''' Form the valid string of ids for fetching data from api with one request '''
        if(not index == len(ids)-1): id_string += f"{id},"
        else: id_string += f"{id}"
        ''' If it is in the database then we will update, not insert '''
        if(cur.execute(f"""SELECT update_time FROM {table} WHERE gid=?""", (id, )).fetchone()):
          update_ids.append(id)
    games = PC.get_wishlist_games(id_string)
    if(games):
      for game in games:
        ''' If it is a game that we needed to update '''
        if(game[DB_Columns.GID.value] in update_ids):
          cur.execute(f"""UPDATE {table} SET full_price=?, sale_price=?, url=?, update_time=? WHERE gid=?""", (game[DB_Columns.FULL_PRICE.value], game[DB_Columns.SALE_PRICE.value], game[DB_Columns.URL.value], time, game[DB_Columns.GID.value]))
        else:
          cur.execute(f"""INSERT INTO {table} VALUES(?, ?, ?, ?, ?, ?, ?, ?)""", (game[DB_Columns.TITLE.value], game[DB_Columns.FULL_PRICE.value], game[DB_Columns.SALE_PRICE.value], game[DB_Columns.COVER_IMAGE.value], game[DB_Columns.URL.value], game[DB_Columns.GID.value], time, len(game[DB_Columns.TITLE.value])))

  ''' Called when wanting to add new wishlist Playstation games '''
  @staticmethod
  def add_ps_games(cur, table, urls):
    time = datetime.now()
    games = []
    existing_games = []
    for index, url in enumerate(urls):
      gid = PS.get_gid(url)
      if(PS.is_valid(url)):
        ''' If the game already exists in the database then we need only update '''
        if(cur.execute(f"""SELECT url, update_time FROM {table} WHERE URL=? OR GID=?""", (url, gid)).fetchone()):
          existing_games.append(gid)
        ''' We must fetch the data for every game, because every game provided needs updating '''
        if(index == len(urls)-1): sleep = False
        else: sleep = True
        game = PS.get_your_deals(url, sleep)
        if(game): games.append(game)
    if(games):
      for game in games:
        ''' If it is a game that we needed to update '''
        if(game[DB_Columns.GID.value] in existing_games):
          cur.execute(f"""UPDATE {table} SET full_price=?, sale_price=?, update_time=? WHERE GID=?""", (game[DB_Columns.FULL_PRICE.value], game[DB_Columns.SALE_PRICE.value], time, game[DB_Columns.GID.value]))
        else:
          cur.execute(f"""INSERT INTO {table} VALUES(?, ?, ?, ?, ?, ?, ?, ?)""", (game[DB_Columns.TITLE.value], game[DB_Columns.FULL_PRICE.value], game[DB_Columns.SALE_PRICE.value], game[DB_Columns.COVER_IMAGE.value], game[DB_Columns.URL.value], game[DB_Columns.GID.value], time, len(game[DB_Columns.TITLE.value])))
    return games
      
  ''' Fetch a game's url given the title and table of the game '''
  @staticmethod
  def get_game_url(cur, table, title):
    url = cur.execute(f"""SELECT url FROM {table} WHERE TITLE=?""", (title, )).fetchone()
    if(url): return url[0]
    else: return None

  ''' Simple function to get the longest title from the given table '''
  @staticmethod
  def get_longest_title(cur, table):
    length = cur.execute(f"""SELECT title_length FROM {table} ORDER BY title_length DESC""").fetchone()
    ''' if we have a title length, then return it otherwise return some arbitrary value... like 10! ''' 
    if(length): return length[0]
    else: return 10

  ''' Determine if the top deals need to be updated based on update_delay. The 
      function first checks to see if an entry even exists, if one does then it
      will check the elapsed time. '''
  @staticmethod
  def needs_updating(cur, table, update_delay=None):
    try: past_time = DB_Calls.__str_to_dt(cur.execute(f"""SELECT update_time FROM {table}""").fetchone()[0])
    except: return True
    if(not update_delay):
      update_delay = DB_Calls._UPDATE_DELAY
    return ((datetime.now() - past_time) > update_delay)

  ''' Checks and finds all PC wishlist games that need updating '''
  @staticmethod
  def pc_wishlist_needs_updating(cur, table, update_delay=None):
    if(not update_delay):
      update_delay = DB_Calls._UPDATE_DELAY
    try:
      ids_to_update = []
      games = cur.execute(f"""SELECT gid, update_time FROM {table}""").fetchall()
      for game in games:
        if((datetime.now() - DB_Calls.__str_to_dt(game[1])) > update_delay):
          ids_to_update.append(game[0])
      return ids_to_update
    except Exception:
      return []

  ''' Checks and finds all Playstation wishlist games that need updating '''
  @staticmethod
  def ps_wishlist_needs_updating(cur, table, update_delay=None):
    if(not update_delay):
      update_delay = DB_Calls._UPDATE_DELAY
    try:
      games_to_update = []
      games = cur.execute(f"""SELECT url, update_time FROM {table}""").fetchall()
      for game in games:
        if((datetime.now() - DB_Calls.__str_to_dt(game[1])) > update_delay):
          games_to_update.append(game[0])
      return games_to_update
    except Exception:
      return []



  #############################
  '''   "PRIVATE" METHODS   '''
  #############################
  ''' Convert a date string into a valid datetime object '''
  @staticmethod
  def __str_to_dt(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S.%f")
