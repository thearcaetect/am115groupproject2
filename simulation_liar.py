#!/usr/local/bin/python

import numpy as np
import scipy.stats as prob
import time
import os


# utilities for running the actual rounds of the game
# inherits the gamestate class, as that is what it manipulates
class RunGame:
    # initial distribution (roll the dies)
    def __init__(self, num_players, dice_per_player, personalities):
        self.num_players = num_players
        self.total_dice = dice_per_player * self.num_players

        self.player_hands = []
        self.player_dice = []
        self.player_types = personalities

        # no need to shuffle as already random, one array per player
        for i in xrange(1,self.num_players+1):
            roll = np.random.randint(1,7,dice_per_player)
            self.player_hands.append(roll)
            self.player_dice.append(dice_per_player)

        # total number of turns in game so far
        self.cumul_turns = 0

        # who holds the current turn
        self.current_player = 0
        self.previous_player = None
        self.game_over = 0

        # the current bid is a tuple of quantity and face value
        # i.E. initial bid is that there is at least one dice with
        # face value 2
        self.current_bid = (1,2)


    # method for rerolling the dice and taking into account
    def roll_dice(self):
        new_total = 0
        # initiate each player as a tuple and add to the players list
        for i in xrange(0,self.num_players):
            cur_dice = self.player_dice[i]
            # implies the player has dice which to roll
            if cur_dice > 0:
                new_total += cur_dice
                new_hand = np.random.randint(1,7,cur_dice)
                self.player_hands[i] = new_hand

        self.total_dice = new_total
        return


    # calculate the probability that the current bid is true
    def check_bid_prob(self):
        return


    # calculate probabilities of potential new bids being true,
    # return the most likely one 
    def calc_rational_bid(self):
        return


    # chooses a new bid uniformly at random from potential new bids
    def calc_naive_bid(self):
        return


    # decies which action to do based on player personality and
    # executes it
    def decide_action(self, player_type):
        # once prob has been determined
        if self.previous_player is None:
            self.make_new_bid((3,4))

        else:
            self.call_on_bid()

        return


    # method that checks if only one player remains, if so updates global flag
    def check_if_game_won(self):
        x = [i for i in self.player_dice if i > 0]
        if len(x) == 1:
            self.game_over = 1
        return


    # method to execute the calling of a bid, handles changing of all
    # global variables
    def call_on_bid(self):

        (count,face_value) = self.current_bid
        # cnt is number of actual occurences of the face value plus wild cards
        cnt = 0

        for i in xrange(0,self.num_players):
            # implies the player is active
            if self.player_dice[i] > 0:
                x = self.player_hands[i]
                for j in xrange(0,x.size):
                    if (x[j] == 1) or (x[j] == face_value):
                        cnt += 1

        # previous bid was true, current player loses a die
        if cnt >= count:
            self.previous_player = None
            self.player_dice[self.current_player] -= 1

            # player is out of game and cannot initiate bidding next round
            if self.player_dice[self.current_player] == 0:
                # will edit the global variable for current player
                self.next_player_id()
                self.check_if_game_won()


        # previous bid was false, previous player loses a die
        else:
            self.player_dice[self.previous_player] -= 1
            # player who loses the round begins bidding in next round
            # player is out of game and cannot initiate bidding next round
            if self.player_dice[self.previous_player] > 0:
                self.current_player = self.previous_player
            else:
                self.next_player_id()
                self.check_if_game_won()

            self.previous_player = None

        return


    # method to execute the making of a new bid
    def make_new_bid(self,bid):
        self.current_bid = bid
        self.previous_player = self.current_player
        self.next_player_id()
        return


    # method to return the id of the player who holds the next turn
    def next_player_id(self):
        next_id = self.current_player
        while self.player_dice[next_id] < 1:
            next_id = (next_id + 1) % self.num_players

        self.current_player = next_id
        return


    # simulates another round, returns 1 for game being won, 0 otherwise
    def simulate_one_turn(self):
        # check for game being won which occurs when current_player is None
        if self.game_over == 1:
            return 1
        else:
            # execute the mechanics of a turn

            # determine which function to call based on personality
            y = self.player_types[self.current_player]
            if y == 0:
                self.calculate_prob_rational()
            elif y == 1:
                self.calculate_prob_naive()
            else:
                self.calculate_prob_bluffer()
            self.roll_dice()
            self.cumul_turns += 1
            return 0


    # method to print general information for debugging
    def print_state(self):
        print('Current state of game')
        print('Current Player: ' + str(self.current_player+1))
        print('Current Dice: ' + str(self.player_dice))
        print('Total Dice: ' + str(self.total_dice))
        print('\n')

        return


# code that we actually want to run
if __name__ == "__main__":
    num_players = 3
    dice_per_player = 5
    # 0 is rational, 1 is naive, 2 is bluffer
    personalities = [0,0,0]
    # instantiate the RunGame class
    liars = RunGame(num_players, dice_per_player, personalities)

    while liars.simulate_one_turn() == 0:
        os.system('clear')
        print('Next turn')
        time.sleep(0.5)
        liars.print_state()
        time.sleep(1)

    print('The game is over! The winner is Player ' + str(liars.current_player + 1))



