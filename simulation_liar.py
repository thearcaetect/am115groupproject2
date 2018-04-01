#!/usr/local/bin/python

import numpy as np
import operator
import os
import random
from scipy.stats import binom
import time


# utilities for running the actual rounds of the game
# inherits the gamestate class, as that is what it manipulates
class RunGame:
    # initial distribution (roll the dies)
    def __init__(self, num_players, dice_per_player, personalities):

        # note: here we are rounding 1/3 to the float 0.333
        self.rolling_prob = 0.333
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
        self.current_bid = None

        # parameters for players:
        # naive_threshold is the probability with which a naive
        # player chooses to call
        self.naive_threshhold = 0.5

        # probability with which a rational player chooses
        # to call the previous player's bluff
        self.rational_threshold = 0.6

        # probability that a bluffing player commits the
        # opposite of the rational action
        self.bluff_threshold = 0.2


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
    # from the current player's perspective
    def check_bid_prob(self):
        # DOUBLE CHECK IF THIS IS RIGHT
        # if there is no current bid, prob should be 1
        if self.current_bid is None:
            return 1.0
        else:
            # get current player's dice
            player_hand = self.player_hands[self.current_player]

            # subtract the current player's matching dice from the
            # bid count
            face_value = self.current_bid[1]

            # occurrences of the face value in the current player's hand

            frequency = list(player_hand.flatten()).count(face_value)

            # the number of occurrences of the current bids face value
            # for required in other player's hands for the bid to be true
            other_freq = self.current_bid[0] - frequency

            if other_freq == 0:
                return 1.0
            else:
                # total number of dice of other players
                num_other_dice = self.total_dice - len(player_hand)

                # calculate probability based on binomial distr.
                trials, p = num_other_dice, self.rolling_prob
                # the prob is converse of the cdf, as we want
                # to know probability of at least that many successes
                prob = 1.0 - binom.cdf(other_freq, trials, p)
                return prob

    def get_possible_bids(self):
        # list of all the possible new bids
        possible_bids = []
        if self.current_bid is None:
            frequency = 0
            face_value = 1

        else:
            frequency = self.current_bid[0]
            face_value = self.current_bid[1]

        # bids keeping face value the same and raising frequency
        for i in range(frequency + 1, self.total_dice + 1):
            possible_bids.append((i, face_value))

        # bids raising the face value
        for j in range(face_value + 1, 7):
            for k in range(1, self.total_dice + 1):
                possible_bids.append((k, j))
        return possible_bids

    # calculate probabilities of potential new bids being true
    # from the current player's perspective, 
    # return the most likely one
    def calc_rational_bid(self):
        possible_bids = self.get_possible_bids()
        # dictionary which stores the bids as keys and has
        # the probability of the bid being true as values
        bids_dict = {}

        # get current player's dice
        player_hand = self.player_hands[self.current_player]

        # dict which tells you how much of each die a player has
        hand_count = {}
        hand_list = list(player_hand.flatten())
        for i in range(1,7):
            hand_count[i] = hand_list.count(i)

        num_other_dice = self.total_dice - len(player_hand)
        p = self.rolling_prob
        for tup in possible_bids:
            freq = tup[0]
            val = tup[1]
            required_successes = freq - hand_count[val]
            if required_successes == 0:
                bids_dict[tup] = 1.0
            else:
                prob = 1.0 - binom.cdf(freq - hand_count[val], num_other_dice, p)
                bids_dict[tup] = prob

        # return key with max value
        return max(bids_dict.iteritems(), key=operator.itemgetter(1))[0]

    # chooses a new bid uniformly at random from potential new bids
    def calc_naive_bid(self):
        possible_bids = self.get_possible_bids()
        return random.choice(possible_bids)


    # decies which action to do based on player personality and
    # executes it
    def decide_action(self, player_pers):
        # must make a bid if there currently is no bid
        # DOUBLE CHECK --> greater than or less than the threshholds?
        if self.previous_player is None:
            # naive player makes a naive bid
            if player_pers == 1:
                self.make_new_bid(self.calc_naive_bid())
            # bluffer and rational player make a rational bid
            else:
                self.make_new_bid(self.calc_rational_bid())

        # has the option to call and will decide based on personality
        else:
            # rational player
            if player_pers == 0:
                # prob of current bid being true is below threshold, so call
                if self.check_bid_prob() < self.rational_threshold:
                    self.call_on_bid()
                # rational decision is to make a new bid
                else:
                    self.make_new_bid(self.calc_rational_bid())

            # naive player
            elif player_pers == 1:
                # calls with probability self.naive_threshold
                if random.uniform(0,1) < self.naive_threshold:
                    self.call_on_bid()
                # otherwise makes a naive bid
                else:
                    self.make_new_bid(self.calc_naive_bid())

            # bluffing player
            else:
                # prob of current bid being true is below threshold, so should call
                if self.check_bid_prob() < self.rational_threshold:
                    # with prob bluff_threshold will go opposite and bid
                    if random.uniform(0,1) < self.bluff_threshold:
                        self.make_new_bid(self.calc_rational_bid())
                    else:
                        self.call_on_bid()
                # rational decision is to make a new bid
                else:
                    # with prob bluff_threshold calls instead of making the bid
                    if random.uniform(0,1) < self.bluff_threshold:
                        self.call_on_bid()
                    else:
                        self.make_new_bid(self.calc_rational_bid())

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
            y = self.player_types[self.current_player]
            self.decide_action(y)
            self.roll_dice()
            self.cumul_turns += 1
            return 0


    # method to print general information for debugging
    def print_state(self):
        print('Current state of game')
        print('Current Player: ' + str(self.current_player + 1))
        print('Current Number of Dice: ' + str(self.player_dice))
        print('Current Player Hand: ') + str(self.player_hands[self.current_player])
        print('Total Dice: ' + str(self.total_dice))
        print('Current Bid: ') + str(self.current_bid)
        print('\n')
        return

    def print_summary_statistics(self):
        print('SUMMARY STATISTICS:\n')
        return


# code that we actually want to run
if __name__ == "__main__":
    num_players = 2
    dice_per_player = 5
    # 0 is rational, 1 is naive, 2 is bluffer
    personalities = [0,0]
    # instantiate the RunGame class
    liars = RunGame(num_players, dice_per_player, personalities)

    while liars.simulate_one_turn() == 0:
        # os.system('clear')
        print('Next turn')
        time.sleep(0.5)
        liars.print_state()
        time.sleep(1)


    print('The game is over! The winner is Player ' + str(liars.current_player + 1))
    liars.print_summary_statistics()
