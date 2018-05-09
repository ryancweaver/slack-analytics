from __future__ import print_function

import requests
import pickle
import csv
import sys
from enchant.checker import SpellChecker
import re
from collections import defaultdict
import unidecode

TOKEN ="Mo0zoKrxRAyj1fGMTopktqd2C5vTAEEuvB6Vl5yt" #replace this with your API token (get from GroupMe Website)
GROUP_ID = "31637994" #replace this with your group ID

def get_messages(group, token):
	"""Gets all messages from a group since it was created. Requires that the token
	belongs to an account that is currently a member of the group. Paged 100 messages
	per request, so might take a while for groups with 1000+ messages."""

	GROUP_URI = 'https://api.groupme.com/v3/groups/' + str(group)
	messages = []
	message_id = get_latest_message(group, token)['id']

	while True:
		request_string = GROUP_URI + '/messages?token=' + token + '&before_id=' + str(message_id) + '&limit=' + '100'
		r = requests.get(request_string)
		try:
			messages += r.json()['response']['messages']
			message_id = messages[-1]['id']
		except ValueError:
			break
		print(len(messages))

	return messages

def get_latest_message(group, token):
	"""Gets the most recent message from a group. Token must be valid for the group."""

	GROUP_URI = 'https://api.groupme.com/v3/groups/' + str(group)
	r = requests.get(GROUP_URI + '/messages?token=' + token + '&limit=1')
	return r.json()['response']['messages'][0]

def save_messages(messages):
	"""Save messages so they don't have to be requested from GroupMe servers every time."""
	with open('messages.pkl', 'w') as save_file:
		pickle.dump(messages, save_file)

def load_messages():
	"""Load saved messages"""
	with open('messages.pkl', 'r') as save_file:
		return pickle.load(save_file)

def print_messages(messages):
	for m in reversed(messages):
		print(m['name'] + ':', end=' '*(26-len(m['name'])))
		print('(', len(m['favorited_by']), ')\t', sep='', end='')
		if len(m['attachments']) > 0:
			print('<image>')
		else:
			print(m['text'])

def latest_user_names(messages):
	"""GroupMe users can change their alias as many times as they want. this
	method returns a mapping of user_id to most recent alias. Useful for creating up-to-date
	statistics for groups with a lot of members who change their names frequently."""

	usermap = {}
	for m in messages:
		uid = m['user_id']
		if uid not in usermap or usermap[uid][1] > int(m['created_at']):
			usermap[uid] = (m['name'].encode('utf-8'), int(m['created_at']))
	return {uid: usermap[uid][0] for uid in usermap}

def user_stats(messages, usermap):
	"""Keys: (posts, likes_recieved, likes_given, wordcount, images, misspellings, kicked, self likes)"""
	#TODO: number of Polls, poll names (extract from string, make set)
	# number of Name Changes
	#Lord giveth and lord taketh away - people added
	stats = {}
	othermap = {}
	checker = SpellChecker('en_US')
	pattern = re.compile("Poll '(.*)'.*")
	polls =  defaultdict(dict)
	for user_id in usermap:
		stats[usermap[user_id]] = {
			'posts': [],
			'likes_recieved': 0,
			'likes_given': 0,
			'wordcount': 0,
			'images': 0,
			'misspellings': [],
			'kicked': 0,
			'been_kicked': 0,
			'self_likes': 0,
			'zero_like_posts' : 0,
			'image_likes': 0}
	current_names = {} # map user id to alias at the time of each message
	name_map =  {}
	original_names = set()
	for m in reversed(messages):
		current_names[m['sender_id']] = m['name']
		if m['user_id'] == 'system':
			# print(m)
			if m['text'] is not None:
				if ' added ' in m['text']:
					if 'added_users' in m['event']['data']:
						for user in m['event']['data']['added_users']:
							original_names.add(user['nickname'])
				elif ' changed name to ' in m['text']:
					s = m['text'].split(' changed name to ')
					name_map[s[0].encode('utf-8')]= s[1].encode('utf-8')
					# name_path.append(s[1])
					for uid in current_names:
						if current_names[uid] == s[0]:
							current_names[uid] = s[1]
				elif ' removed ' in m['text']:
					s = m['text'][:-16].split(' removed ')
					remover = 0
					removed = 0
					for uid in current_names:
						if current_names[uid] == s[0]: remover = uid
						if current_names[uid] == s[1]: removed = uid
					if remover != 0 and removed != 0:
						stats[usermap[remover]]['kicked'] += 1
						stats[usermap[removed]]['been_kicked'] += 1
				elif "Poll '" in m['text'] and 'options' in m['event']['data']:
					question = (m['event']['data']['poll']['subject']).encode('utf-8')
					for option in m['event']['data']['options']:
						polls[question][option['title']] = 0 if 'votes' not in option else option['votes']

		name = usermap[m['sender_id']]
		stats[name]['posts'].append(m)
		stats[name]['likes_recieved'] += len(m['favorited_by'])
		if(len(m['favorited_by']) == 0):
			stats[name]['zero_like_posts'] += 1
		for liker in m['favorited_by']:
			try:
				likername = usermap[liker]
				stats[likername]['likes_given'] += 1
				if likername == name:
					stats[likername]['self_likes'] +=1
			except KeyError:
				pass
		stats[name]['images'] += 1 if len(m['attachments']) > 0 else 0
		if len(m['attachments']) > 0:
			stats[name]['image_likes'] += len(m['favorited_by'])
		if m['text'] is not None:
			stats[name]['wordcount'] += len(m['text'].split(' '))
			checker.set_text(m['text'])
			stats[name]['misspellings'] += [error.word for error in list(checker)]
	othermap['polls'] = polls
	name_path = defaultdict(list)
	visited = set()
	for name in original_names:
		if name in name_map:
			temp = name_map[name]
		else:
			continue
		while True:
			name_path[name].append(temp)
			if temp in name_map and temp not in visited:
				visited.add(temp)
				temp = name_map[temp]
			else:
				break
	othermap['names'] = name_path

	# print (name_map)
	#
	# name_set = set([name for name in name_map])
	# # print(name_set)
	# visited = set()
	# for name in name_set:
	# 	# print ('hi')
	# 	visited.add(name)
	# 	temp = name_map[name]
	# 	visited.add(temp)
	# 	while True:
	# 		# print(temp)
	# 		name_path[name].append(temp)
	# 		if temp in name_map and temp not in visited:
	# 			temp = name_map[temp]
	# 		else:
	# 			break
	# print(name_path)
	# for t,v in name_path:
	# 	print (t, v)


	# print (polls)

	# del stats['GroupMe']
	# del stats['GroupMe Calendar']
	# del stats['Annie Hughey']
	# del stats['Nicole Vergara']
	return (stats, othermap)

def rank_best(*rankings):
	rank_map = defaultdict(lambda: 0)
	for ranking in rankings:
		# print (ranking, "\n--------------------------------------------------------------\n")
		for rank, name in ranking:
			rank_map[name] += rank
	for name in rank_map:
		rank_map[name] = float(rank_map[name])/len(rankings)
	rank_order = list(sorted([(rank_map[u],u) for u in rank_map ]))
	return rank_order

def print_stats(userstats, othermap, num_listed):
	"""Prints stats to console and also compiles them to a csv file."""

	total_posts = sum([len(userstats[u]['posts']) for u in userstats])
	posts = list(reversed(sorted([(len(userstats[u]['posts']), u) for u in userstats])))
	likes_recieved = list(reversed(sorted([(userstats[u]['likes_recieved'], u) for u in userstats])))
	likes_given = list(reversed(sorted([(userstats[u]['likes_given'], u) for u in userstats])))
	average_likes = list(reversed(sorted([(float(userstats[u]['likes_recieved']) / len(userstats[u]['posts']), u) for u in userstats])))
	misspellings = list(reversed(sorted([(float(len(userstats[u]['misspellings'])) / len(userstats[u]['posts']), u) for u in userstats])))
	misspelled_count = {u: {} for u in userstats} #map users to a dict that maps words to times misspelled
	self_likes = list(reversed(sorted([(userstats[u]['self_likes'], u) for u in userstats])))
	zero_like_posts = list(reversed(sorted([(userstats[u]['zero_like_posts'], u) for u in userstats])))
	image_likes = list(reversed(sorted([(userstats[u]['image_likes'], u) for u in userstats])))

	zero_like_posts_map = dict((u, userstats[u]['zero_like_posts']) for u in userstats)
	image_likes_map = dict((u, userstats[u]['image_likes']) for u in userstats)
	likes_given_map = dict((u, userstats[u]['likes_given']) for u in userstats)
	likes_recieved_map = dict((u, userstats[u]['likes_recieved']) for u in userstats)
	posts_map = dict((u, len(userstats[u]['posts'])) for u in userstats)
	image_map = dict((u, userstats[u]['images']) for u in userstats)

	# image_likes_alphabetical
	# print("image_likes", image_likes)
	polls = list(othermap['polls']);
	names = othermap['names']
	for u in userstats:
		all_misspellings = userstats[u]['misspellings']
		for word in all_misspellings:
			if word not in misspelled_count[u]:
				misspelled_count[u][word] = 1
			else:
				misspelled_count[u][word] += 1
	commonly_misspelled = {u: [] for u in userstats} #map users to a list of touples: (times misspelled, word)
	for user in misspelled_count:
		for word in misspelled_count[user]:
			commonly_misspelled[user].append((misspelled_count[user][word], word))
		commonly_misspelled[user] = list(reversed(sorted(commonly_misspelled[user])))
	kicked = list(reversed(sorted([(userstats[u]['kicked'], u) for u in userstats])))
	been_kicked = list(reversed(sorted([(userstats[u]['been_kicked'], u) for u in userstats])))
	images = list(reversed(sorted([(userstats[u]['images'], u) for u in userstats])))

	with open('stats_final.csv', 'wb') as csvfile:
		writer = csv.writer(csvfile, delimiter=',')
		writer.writerow(['Total Posts', total_posts])

		writer.writerow([])
		writer.writerow(['Most Posts', '', '', 'Fewest Posts'])
		for i in range(num_listed):
			writer.writerow([posts[i][1], posts[i][0], '', posts[-i-1][1], posts[-i-1][0]])

		writer.writerow([])
		writer.writerow(['Most Likes Given', '', '', 'Fewest Likes Given'])
		for i in range(num_listed):
			writer.writerow([likes_given[i][1], likes_given[i][0], '', likes_given[-i-1][1], likes_given[-i-1][0]])

		writer.writerow([])
		writer.writerow(['Most Likes Received', '', '', 'Fewest Likes Received'])
		for i in range(num_listed):
			writer.writerow([likes_recieved[i][1], likes_recieved[i][0], '', likes_recieved[-i-1][1], likes_recieved[-i-1][0]])

		writer.writerow([])
		writer.writerow(['Most likes given per like received'])
		# print (self_likes)
		likes_given_per_likes_received = list(reversed(sorted([(float(likes_given_map[u])/likes_recieved_map[u],u) for u in userstats])))
		for i in range(num_listed):
			# writer.writerow([image_likes[i][1], str(image_likes[i][0])])
			writer.writerow([likes_given_per_likes_received[i][1], str(likes_given_per_likes_received[i][0])])

		writer.writerow([])
		writer.writerow(['Most Average Likes', '', '', 'Fewest Average Likes'])
		for i in range(num_listed):
			writer.writerow([average_likes[i][1], str(average_likes[i][0])[:4], '', average_likes[-i-1][1], str(average_likes[-i-1][0])[:4]])

		writer.writerow([])
		writer.writerow(['Misspelled Words Per Post', '', '', 'Most Common Misspellings'])
		for i in range(num_listed):
			m = ', '.join([cm[1] for cm in commonly_misspelled[misspellings[i][1]]][:7])
			try:
				writer.writerow([misspellings[i][1], str(misspellings[i][0])[:4], '', m])
			except UnicodeEncodeError:
				pass
				# sys.stderr.write('Could not encode')

		writer.writerow([])
		writer.writerow(['Images/Gifs'])
		for i in range(num_listed):
			writer.writerow([images[i][1], images[i][0]])

		writer.writerow([])
		writer.writerow(['Most Image Likes', '', '', 'Fewest Image Likes'])
		# print (self_likes)
		for i in range(num_listed):
			writer.writerow([image_likes[i][1], str(image_likes[i][0]), '', image_likes[-i-1][1], str(image_likes[-i-1][0])])

		writer.writerow([])
		writer.writerow(['Most likes received per image'])
		# print (self_likes)
		likes_received_per_image = list(reversed(sorted([(float(image_likes_map[u])/(image_map[u] if image_map[u] != 0 else float("inf")),u) for u in userstats ])))
		for i in range(num_listed):
			# writer.writerow([image_likes[i][1], str(image_likes[i][0])])
			writer.writerow([likes_received_per_image[i][1], str(likes_received_per_image[i][0])])


		writer.writerow([])
		writer.writerow(['Times Kicked From Group', '', '', 'People Kicked'])
		for i in range(num_listed):
			writer.writerow([been_kicked[i][1], been_kicked[i][0], '', kicked[i][1], kicked[i][0]])

		writer.writerow([])
		writer.writerow(['Most Self Likes', '', '', 'Fewest Self Likes'])
		for i in range(num_listed):
			writer.writerow([self_likes[i][1], str(self_likes[i][0]), '', self_likes[-i-1][1], str(self_likes[-i-1][0])])

		writer.writerow([])
		writer.writerow(['Most Zero Like Posts', '', '', 'Fewest Zero Like Posts'])
		for i in range(num_listed):
			writer.writerow([zero_like_posts[i][1], str(zero_like_posts[i][0]), '', zero_like_posts[-i-1][1], str(zero_like_posts[-i-1][0])])

		writer.writerow([])
		writer.writerow(['Fewest Zero like posts per post'])
		zero_like_posts_per_post = list(sorted([(float(zero_like_posts_map[u])/posts_map[u],u) for u in userstats ]))
		for i in range(num_listed):
			# writer.writerow([image_likes[i][1], str(image_likes[i][0])])
			writer.writerow([zero_like_posts_per_post[i][1], str(zero_like_posts_per_post[i][0])])


		#structure of polls dict
		#{question:
		#	{options: votes}}
		writer.writerow([])
		writer.writerow(['Polls'])
		writer.writerow(['Question','Choices/Result'])
		for question in othermap['polls']:
			writer.writerow([question])
			for option in othermap['polls'][question].items():
				writer.writerow(['',unidecode.unidecode(option[0]), option[1]])
		# names: {name: [list of names]}
		writer.writerow([])
		writer.writerow(['Names'])
		for name in names:
			writer.writerow([name])
			writer.writerow(['']+ names[name])

		#TODO:
		#	best groupme-r
		most_posts_order = zip([i for i in xrange(1,40)], [p[1] for p in posts])
		likes_given_per_like_received_order = zip([i for i in xrange(1,40)], [p[1] for p in likes_given_per_likes_received])
		likes_given_order = zip([i for i in xrange(1,40)], [p[1] for p in likes_given])
		likes_received_order = zip([i for i in xrange(1,40)], [p[1] for p in likes_recieved])
		average_likes_order = zip([i for i in xrange(1,40)], [p[1] for p in average_likes])
		num_images_order = zip([i for i in xrange(1,40)], [p[1] for p in images])
		likes_received_per_image_order = zip([i for i in xrange(1,40)], [p[1] for p in likes_received_per_image])
		zero_like_posts_order = zip([i for i in range(36,1,-1)], [p[1] for p in zero_like_posts])
		zero_like_posts_per_post_order = zip([i for i in xrange(1,40)], [p[1] for p in zero_like_posts_per_post])
		best_groupmer= rank_best(most_posts_order,
								likes_given_per_like_received_order,
								likes_given_order,
								likes_received_order,
								average_likes_order,
								num_images_order,
								likes_received_per_image_order,
								zero_like_posts_order,
								zero_like_posts_per_post_order)

		writer.writerow([])
		writer.writerow(['Best GroupMe-r'])
		for i in range(num_listed):
			# writer.writerow([image_likes[i][1], str(image_likes[i][0])])
			writer.writerow([best_groupmer[i][1], str(best_groupmer[i][0])])

		#Most Posts
		#Likes given per like received
		#Most Likes Given
		#Most Likes Received
		#Most Average Likes
		#Images/Gifs
		#zero like posts
		#zero like posts per post or inverse
		#image likes per image



if __name__ == '__main__':
	# comment the following lines after first run
	messages = get_messages(GROUP_ID, TOKEN)
	save_messages(messages)

	# uncomment after first run to use saved messages
	# messages = load_messages()

	usermap = latest_user_names(messages)
	userstats, othermap = user_stats(messages, usermap)

	print_stats(userstats, othermap, 36)
main.py
Displaying main.py.
