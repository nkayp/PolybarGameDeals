#!/usr/bin/python3 

'''
  This script is for fetching and parsing the PC deals, deals from cheapshark.com
'''

import requests
import re
from enum import Enum

from ..utils.db_enums import DB_Columns
from .shared import create_game_dictionary

class API_Indices(Enum):
  TITLE = "title"
  NORMAL_PRICE = "normalPrice"
  SALE_PRICE = "salePrice"
  COVER_IMAGE = "thumb"
  DEAL_ID = "dealID"
  GAME_ID = "gameID"

class PC:
  #####################
  '''   VARIABLES   '''
  #####################
  _UPPER_PRICE = 10
  _YOUR_DEALS_URL = "https://www.cheapshark.com/api/1.0/games?ids="
  _TOP_DEALS_URL = "https://www.cheapshark.com/api/1.0/deals?upperPrice="
  _DEAL_URL = "https://www.cheapshark.com/redirect?dealID="
  _GAME_LOOKUP_URL = "https://www.cheapshark.com/api/1.0/games?title="



  ############################
  '''   "PUBLIC" METHODS   '''
  ############################
  ''' Makes a request to get the top deals, parses them, and returns that data. 
      If an upper_price is provided no deals greater than that amount will be
      discovered. 
  '''
  @staticmethod
  def get_top_deals(upper_price=None):
    if(upper_price == None): upper_price = PC._UPPER_PRICE

    data = PC._make_request(f"{PC._TOP_DEALS_URL}{upper_price}")
    if(data):
      data = PC._parse_data(data)
      return data
    return None

  @staticmethod
  def get_wishlist_games(id_string):
    data = PC._make_request(f"{PC._YOUR_DEALS_URL}{id_string}")
    if(data):
      data = PC._parse_wishlist_deals(data)
      return data
    return None

  @staticmethod
  def is_valid(id):
    return re.search(fr"^\d+$", str(id))
    


  #############################
  '''   "PRIVATE" METHODS   '''
  #############################
  ''' Makes a request for the provided url (the api) ''' 
  @staticmethod
  def _make_request(url):
    r = requests.get(url)
    if(r.status_code == 200):
      return r.json()
    return None

  ''' Parse the deals '''
  @staticmethod
  def _parse_data(data):
    parsed_data = []
    titles = []
    for game in data:
      title = game[API_Indices.TITLE.value]
      full_price = float(game[API_Indices.NORMAL_PRICE.value])
      sale_price = float(game[API_Indices.SALE_PRICE.value])
      cover_image = game[API_Indices.COVER_IMAGE.value]
      url = f"{PC._DEAL_URL}{game[API_Indices.DEAL_ID.value]}"
      gid = game[API_Indices.GAME_ID.value]

      ''' 
      Unfortunately, or fortunately?, the api can have lots of duplicates, some with different prices, so I must do some checking to remove dupes.
      '''
      if(not title in titles):  # If this title hasn't been added then add it
        titles.append(title)
        parsed_data.append(create_game_dictionary(title, full_price, sale_price, cover_image, gid, url))
      else:   # if this title has been added, check if this one is cheaper
        for existing_game in parsed_data:
          if((title == existing_game[API_Indices.TITLE.value]) and (sale_price < existing_game[DB_Columns.SALE_PRICE.value])):
            existing_game.update({DB_Columns.SALE_PRICE.value: sale_price, DB_Columns.URL.value: url})
    return parsed_data

  @staticmethod
  def _parse_wishlist_deals(data):
    games = []
    for game in data:
      gid = int(game)

      game = data[game]
      info = game['info']
      title = info[API_Indices.TITLE.value]
      cover_image = info[API_Indices.COVER_IMAGE.value]

      deals = game['deals'][0]
      full_price = float(deals['price'])
      try: sale_price = deals['salePrice']
      except Exception: sale_price = full_price
      url = f"{PC._DEAL_URL}{deals[API_Indices.DEAL_ID.value]}"

      games.append(create_game_dictionary(title, full_price, sale_price, cover_image, gid, url))
    return games
