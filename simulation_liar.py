#!/usr/local/bin/python

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
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

        # flag that determines when to reroll dice
        self.roll_flag = 0
        self.round_lengths = []
        self.round_counter = 0

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
        self.naive_threshold = 0.5

        # probability that a bluffing player commits the
        # opposite of the rational action
        self.bluff_threshold = 0.2

        # player ranking, tracks who loses the game first
        # for example [3,1,2] means that player 3 is in last place
        # and player 2 in second to last place (the only player left is
        # the winner)
        self.player_ranking = []


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
    def calc_rational_bid(self, return_val=0):
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
        # print bids_dict
        suggested_bid = max(bids_dict.iteritems(), key=operator.itemgetter(1))[0]
        suggest_bid_prob = bids_dict[suggested_bid]

        if return_val == 0:
            return suggested_bid

        if return_val == 1:
            return suggest_bid_prob

    # chooses a new bid uniformly at random from potential new bids
    def calc_naive_bid(self):
        possible_bids = self.get_possible_bids()
        return random.choice(possible_bids)


    # decies which action to do based on player personality and
    # executes it
    def decide_action(self, player_pers):
        # must make a bid if there currently is no bid
        # corner case if you reach the highest bid possible
        if self.previous_player is None or self.current_bid is None:
            # naive player makes a naive bid
            if player_pers == 1:
                self.make_new_bid(self.calc_naive_bid())
            # bluffer and rational player make a rational bid
            else:
                self.make_new_bid(self.calc_rational_bid())
            return

        # has the option to call and will decide based on personality
        else:
            (quantity, face_value) = self.current_bid
            if face_value == 6 and quantity == self.total_dice:
                self.call_on_bid()
                return

            # rational player
            if player_pers == 0:
                make_new_bid_prob = self.calc_rational_bid(return_val=1)
                # prob of current bid being true is below threshold, so call
                if self.check_bid_prob() < make_new_bid_prob:
                    self.call_on_bid()
                # rational decision is to make a new bid
                else:
                    self.make_new_bid(self.calc_rational_bid())
                return

            # naive player
            elif player_pers == 1:
                # calls with probability self.naive_threshold
                if random.uniform(0,1) < self.naive_threshold:
                    self.call_on_bid()
                # otherwise makes a naive bid
                else:
                    self.make_new_bid(self.calc_naive_bid())
                return

            # bluffing player
            else:
                make_new_bid_prob = self.calc_rational_bid(return_val=1)
                # prob of current bid being true is below threshold, so should call
                # rational move is to call but with some prob you raise the bid
                if self.check_bid_prob() < make_new_bid_prob:
                    # with prob bluff_threshold will go opposite and bid
                    if random.uniform(0,1) < self.bluff_threshold:
                        self.make_new_bid(self.calc_rational_bid())
                    else:
                        self.call_on_bid()
                # rational decision is to make a new bid, 
                # but with some prob you call
                else:
                    # with prob bluff_threshold calls instead of making the bid
                    if random.uniform(0,1) < self.bluff_threshold:
                        self.call_on_bid()
                    else:
                        self.make_new_bid(self.calc_rational_bid())
                return

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
            if self.player_dice[self.current_player] == 0:
                self.player_ranking.append(self.current_player)

            self.current_bid = None
            # player is out of game and cannot initiate bidding next round
            if self.player_dice[self.current_player] == 0:
                # will edit the global variable for current player
                self.next_player_id()
                self.check_if_game_won()

        # previous bid was false, previous player loses a die
        else:
            self.player_dice[self.previous_player] -= 1
            if self.player_dice[self.previous_player] == 0:
                self.player_ranking.append(self.previous_player)

            self.current_bid = None
            # player who loses the round begins bidding in next round
            # player is out of game and cannot initiate bidding next round
            if self.player_dice[self.previous_player] > 0:
                self.current_player = self.previous_player
            else:
                self.next_player_id()
                self.check_if_game_won()

            self.previous_player = None

        # indicate that the dice need to be rerolled
        self.roll_flag = 1

        return


    # method to execute the making of a new bid
    def make_new_bid(self,bid):
        self.current_bid = bid
        self.previous_player = self.current_player
        self.next_player_id()
        return


    # method to return the id of the player who holds the next turn
    def next_player_id(self):
        next_id = (self.current_player + 1) % self.num_players
        while self.player_dice[next_id] < 1:
            next_id = (next_id + 1) % self.num_players

        self.current_player = next_id
        return


    # simulates another round, returns 1 for game being won, 0 otherwise
    def simulate_one_turn(self):
        # check for game being won which occurs when current_player is None
        if self.game_over == 1:
            # self.print_state()
            return 1
        else:
            # execute the mechanics of a turn
            y = self.player_types[self.current_player]
            self.decide_action(y)
            # turn has been decided, add one to counter
            self.cumul_turns += 1
            self.round_counter += 1
            # only roll once a player loses a die
            if self.roll_flag == 1:
                self.roll_dice()
                self.round_lengths.append(self.round_counter)
                self.round_counter = 0
                # set flag back to 0 after rolling
                self.roll_flag = 0
            # self.print_state()
            # time.sleep(0.65)
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

    def print_rounds(self):
        print(self.round_lengths)
        final_ranking = list(reversed([x + 1 for x in self.player_ranking]))
        print final_ranking
        print('Ranking:')
        for i in range(len(final_ranking)):
            print('%dth place: %d' % (i + 1, final_ranking[i]))
        return


#### Utilities for Running Statistics ####
def average(lst):
    return float(sum(lst)) / float(len(lst))


def simulate_game(n, num_players, dice_per_player, personalities):
    total_turns_list = []
    avg_turns_list = []
    winners_list = []

    for i in range(n):
        # instantiate the RunGame class
        liars = RunGame(num_players, dice_per_player, personalities)

        while True:
            # liars.print_state()
            turn = liars.simulate_one_turn()
            if turn == 1:
                winners_list.append(liars.current_player + 1)
                liars.player_ranking.append(liars.current_player)
                break

        avg_round_length = average(liars.round_lengths)
        avg_turns_list.append(avg_round_length)
        total_turns_list.append(liars.cumul_turns)


    print('Average Total Turn Length: %f' % average(total_turns_list))
    print('Average Turns Per Round: %f ' % average(avg_turns_list))

    win_count_dict = {}
    for player in set(winners_list):
        win_count_dict[player] = winners_list.count(player)
    print('Frequency of Winners:')
    print win_count_dict



# format of personalities here is one player of a type and five of another
# type, such that player 0 is the player whose ranking distribution we want
def simulate_one_vs_many(n, num_players, dice_per_player, personalities):
    winners_list = []
    # in each game, track the place that the player comes in, and store it
    one_player_rankings = []
    ranking_count_dict = {}

    for i in range(n):
        print i
        # instantiate the RunGame class
        liars = RunGame(num_players, dice_per_player, personalities)

        while True:
            # liars.print_state()
            turn = liars.simulate_one_turn()
            if turn == 1:
                winners_list.append(liars.current_player + 1)
                liars.player_ranking.append(liars.current_player)
                break

        player_id = 0
        ranking = liars.player_ranking
        # get the ranking in descending order from first to last
        ranking.reverse()
        one_player_rankings.append(ranking.index(player_id))

    # build the probability distribution
    for i in range(num_players):
        count = one_player_rankings.count(i)
        ranking_count_dict[i] = count

    win_count_dict = {}
    for player in set(winners_list):
        win_count_dict[player] = winners_list.count(player)
    print('Frequency of Winners:')
    print win_count_dict
    print '\n'
    return ranking_count_dict

# format of personalities here will be [0,1,2]
# so one rational, one naive, and one bluffing player
def simulate_mixed(n, num_players, dice_per_player, personalities):
    total_turns_list = []
    avg_turns_list = []
    winners_list = []

    # in each game, track the place that each player comes in, and store it
    naive_rankings = []
    naive_ranking_count_dict = {}

    rational_rankings = []
    rational_ranking_count_dict = {}

    bluffing_rankings = []
    bluffing_ranking_count_dict = {}


    for i in range(n):
        print i
        # instantiate the RunGame class
        liars = RunGame(num_players, dice_per_player, personalities)

        while True:
            # liars.print_state()
            turn = liars.simulate_one_turn()
            if turn == 1:
                winners_list.append(liars.current_player + 1)
                liars.player_ranking.append(liars.current_player)
                break

        ranking = liars.player_ranking
        # get the ranking in descending order from first to last
        rational_rankings.append(ranking.index(0))
        naive_rankings.append(ranking.index(1))
        bluffing_rankings.append(ranking.index(2))

    # build the probability distributions for each player
    for i in range(num_players):
        rational_count = rational_rankings.count(i)
        rational_ranking_count_dict[i] = rational_count

        naive_count = naive_rankings.count(i)
        naive_ranking_count_dict[i] = naive_count

        bluffing_count = bluffing_rankings.count(i)
        bluffing_ranking_count_dict[i] = bluffing_count

    print rational_ranking_count_dict
    print naive_ranking_count_dict
    print bluffing_ranking_count_dict
    return [rational_ranking_count_dict, naive_ranking_count_dict, bluffing_ranking_count_dict]




# code that we actually want to run
if __name__ == "__main__":
    num_players = 6
    dice_per_player = 5
    # 0 is rational, 1 is naive, 2 is bluffer
    personalities = [2,0,0,0,0,0]
    number_of_trials = 1000
    # simulate_game(number_of_trials, num_players, dice_per_player, personalities)
    rank_distr = simulate_one_vs_many(number_of_trials, num_players, dice_per_player, personalities)
    places = [i + 1 for i in rank_distr.keys()]
    place_freq = rank_distr.values()
    place_percents = [k / float(number_of_trials) for k in place_freq]
    # print('Possible ranks')
    # print places
    print('Place Count Frequencies')
    print place_freq
    print('Place Probabilities')
    print place_percents
    fig, ax = plt.subplots()
    plt.bar(places, place_percents, width=1, color='purple')
    plt.xlabel('Ranking Position', fontsize=20)
    plt.ylabel('Probability', fontsize=20)
    plt.title('Probability Distr. 1 Bluffing vs. 5 Rational Players', y=1.03, fontsize=20)
    purple_patch = mpatches.Patch(color='purple', label='n = 1000')
    plt.legend(handles=[purple_patch])
    plt.savefig('1bluffing5naive.png')


#### SUMMARY STATISTICS ####
# liars.print_summary_statistics()
# print('The game is over! The winner is Player ' + str(liars.current_player + 1))
# print liars.cumul_turns
# liars.print_rounds()


#### GRAPHING ####
# x = [0,1,2,3,4,5]
# y = [0,2,4,6,7,13]
# plt.plot(x, y, color='green', marker='o', linewidth=2, markersize=12)
# plt.xlabel('Time')
# plt.ylabel('Result')
# plt.title('Graph of Something Cool')
# plt.show()


