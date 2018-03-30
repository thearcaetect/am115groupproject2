import numpy as np
from numpy import random as rand


# game state class
	# global dice, and which player has what
	# players turn
	# current bid



class GameState:
	def __init__(self, num_players):
		self.num_players = num_players
		self.num_dice = 5 * self.num_players
		self.player_hands = []
		# the current bid is a tuple of quantity and face value
		# i.E. initial bid is that there is at least one dice with 
		# face value 2
		self.current_bid = (1,2)


	def get_current_bid(self):
		return self.current_bid

	def get_player_hands(self):
		return self.player_hands


# utilities for running the actual rounds of the game
class RunGame:
	# initial distribution (roll the dies)
	def __init__(self):


	def initial_roll():

	# simulates another round, says whether or not the game is won
	def next_round(self):
	calculate probabili

# rungame class
	# simulates each person's turn, given game state



class Player:
	# want to know which player it is, ids are just ints
	def __init__(self, player_id):
		self.player_id = player_id


	def get_my_hand(self, ):


	def get_total_dice_left(self):


	def get_current_bet(self):


	def calculate_prob(self):



# player turn --> calculate probabilities for that player's bid
	# total number of dice 
	# their current dice


