import json
import os
import re
import csv

filePath = "../slack-export/"
usersFile = "users.json"

#Create a user dictionary
uDict = {}

#Create a reaction dictionary
reactions = {}

#Load json data from users file
userData = json.load(open(filePath + usersFile))

#Load all of the users into this user dictionary
for user in userData:
    if user['id'] not in uDict:
        uDict[user['id']] = {}

        #Get the user's real name
        if user['real_name']:
            uDict[user['id']]['realName'] = user['real_name']
        else:
            uDict[user['id']]['realName'] = ''

        #Get the user's display name
        if user['profile']['display_name']:
            uDict[user['id']]['displayName'] = user['profile']['display_name']
        else:
            uDict[user['id']]['displayName'] = ''

        #Initialize all of the user's statistics
        uDict[user['id']]['fileShareCount'] = 0
        uDict[user['id']]['msgCount'] = 0
        uDict[user['id']]['msgWordCount'] = 0
        uDict[user['id']]['mentions'] = 0
        uDict[user['id']]['editCount'] = 0
        uDict[user['id']]['reactionCount'] = 0
        uDict[user['id']]['reactedCount'] = 0
        uDict[user['id']]['wordsPerMsg'] = 0.0
        uDict[user['id']]['reactedPerReactions'] = 0.0
        uDict[user['id']]['reactionsPerMsg'] = 0.0
        uDict[user['id']]['rating'] = 0.0

#Remove inactive users
del uDict['U8TTQBS7J']
del uDict['U8NV86D7C']
del uDict['U98CRFKL5']
del uDict['U8URRD4Q6']
del uDict['U8TRB6BH9']

#Go through all of the files that were exported from slack
for dirName, subdirList, fileList in os.walk(filePath):
    for fname in fileList:
        #Ignore the users, channels, and integration_logs files
        if fname != 'users.json' and fname != 'channels.json' and fname != 'integration_logs.json':
            fileData = json.load(open(dirName + '/' + fname))

            for msg in fileData:
                #Go through all of the subtype messages
                if 'subtype' in msg:
                    #Go through all of the subtype messages that are file shares
                    if msg['subtype'] == 'file_share':
                        uDict[msg['user']]['fileShareCount'] += 1
                else:
                    #The messages that don't have a subtype
                    #Count the number of messages the user sent
                    uDict[msg['user']]['msgCount'] += 1

                    #Count the number of words sent in all of the user's messages
                    uDict[msg['user']]['msgWordCount'] = uDict[msg['user']]['msgWordCount'] + len(msg['text'].split())

                    #Count the number of times a user was mentioned in a message
                    for mention in re.findall(r"<@[^@^>^<]*>", msg['text']):
                        mention = mention.replace('<', '')
                        mention = mention.replace('>', '')
                        mention = mention.replace('@', '')

                        uDict[mention]['mentions'] += 1

                    #Count the number of messages a user has edited
                    if 'edited' in msg:
                        uDict[msg['user']]['editCount'] += 1

                    #Count the number of times a reaction was used to react to a message
                    if 'reactions' in msg:
                        for reaction in msg['reactions']:
                            if reaction['name'] not in reactions:
                                reactions[reaction['name']] = {}
                            if 'count' not in reactions[reaction['name']]:
                                reactions[reaction['name']]['count'] = 0
                            reactions[reaction['name']]['count'] = reactions[reaction['name']]['count'] + reaction['count']

                            #Count the number of times a user's message was reacted to
                            uDict[msg['user']]['reactionCount'] = uDict[msg['user']]['reactionCount'] + reaction['count']

                            #Count the number of time a user reacted to a message
                            for u in reaction['users']:
                                uDict[u]['reactedCount'] += 1
for u in uDict:
    if uDict[u]['msgCount'] > 0:
        #Calculate the words per message stat
        uDict[u]['wordsPerMsg'] = float(uDict[u]['msgWordCount']) / float(uDict[u]['msgCount'])
        #Calculate reactions received per message sent
        uDict[u]['reactionsPerMsg'] = float(uDict[u]['reactionCount']) / float(uDict[u]['msgCount'])

    if uDict[u]['reactionCount'] > 0:
        #Calculate reactions given per reactions received
        uDict[u]['reactedPerReactions'] = float(uDict[u]['reactedCount']) / float(uDict[u]['reactionCount'])

#Rank users in all of their stats
messageCount = list(reversed(sorted([(uDict[u]['msgCount'], u) for u in uDict])))
fileShareCount = list(reversed(sorted([(uDict[u]['fileShareCount'], u) for u in uDict])))
messageWordCount = list(reversed(sorted([(uDict[u]['msgWordCount'], u) for u in uDict])))
mentionsCount = list(reversed(sorted([(uDict[u]['mentions'], u) for u in uDict])))
reactionCount = list(reversed(sorted([(uDict[u]['reactionCount'], u) for u in uDict])))
reactedCount = list(reversed(sorted([(uDict[u]['reactedCount'], u) for u in uDict])))
wordsPerMessage = list(reversed(sorted([(uDict[u]['wordsPerMsg'], u) for u in uDict])))
reactedPerReactions = list(reversed(sorted([(uDict[u]['reactedPerReactions'], u) for u in uDict])))
reactionsPerMsg = list(reversed(sorted([(uDict[u]['reactionsPerMsg'], u) for u in uDict])))

#Find the position of where each user is ranked in each stat and caluclate the
#overall rating for that user (add 1 to the index because the indecies start at 0)
for u in uDict:
    for m in messageCount:
        if u in m:
            uDict[u]['rating'] += (messageCount.index(m) + 1)
    for fs in fileShareCount:
        if u in fs:
            uDict[u]['rating'] += (fileShareCount.index(fs) + 1)
    for mw in messageWordCount:
        if u in mw:
            uDict[u]['rating'] += (messageWordCount.index(mw) + 1)
    for men in mentionsCount:
        if u in men:
            uDict[u]['rating'] += (mentionsCount.index(men) + 1)
    for rn in reactionCount:
        if u in rn:
            uDict[u]['rating'] += (reactionCount.index(rn) + 1)
    for rd in reactedCount:
        if u in rd:
            uDict[u]['rating'] += (reactedCount.index(rd) + 1)
    for wpm in wordsPerMessage:
        if u in wpm:
            uDict[u]['rating'] += (wordsPerMessage.index(wpm) + 1)
    for rpr in reactedPerReactions:
        if u in rpr:
            uDict[u]['rating'] += (reactedPerReactions.index(rpr) + 1)
    for rpm in reactionsPerMsg:
        if u in rpm:
            uDict[u]['rating'] += (reactionsPerMsg.index(rpm) + 1)

    #Calculate the average rating among all of the stats
    uDict[u]['rating'] /= 9

#Create csv file for user stats
with open('user_stats.csv', 'wb') as user_stats:
    writer = csv.writer(user_stats, delimiter=',')

    #Write users statistics to the csv file
    writer.writerow(['User Real Name', 'User Display Name', 'Messages Sent',
    'Files Shared', 'Total Words Sent', 'Words Per Message',
    'Mentions', 'Number of Messages Edited', 'Reactions Received',
    'Number of Times User Reacted', 'Reactions Received Per Message', 'Reactions Given Per Reactions Received', 'Overall Rating'])

    #Initialize totals
    totalUsers = len(uDict)
    totalMsgCount = 0
    totalFileShareCount = 0
    totalMsgWordCount = 0
    totalMentions = 0
    totalEditCount = 0
    totalReactionCount = 0
    totalReactedPerReactions = 0.0

    for u in uDict:
        #Keep a running total of most of the stats to show in the csv file
        totalMsgCount += uDict[u]['msgCount']
        totalFileShareCount += uDict[u]['fileShareCount']
        totalMsgWordCount += uDict[u]['msgWordCount']
        totalMentions += uDict[u]['mentions']
        totalEditCount += uDict[u]['editCount']
        totalReactionCount +=  uDict[u]['reactionCount']
        totalReactedPerReactions += uDict[u]['reactedPerReactions']

        writer.writerow([uDict[u]['realName'], uDict[u]['displayName'], uDict[u]['msgCount'],
        uDict[u]['fileShareCount'], uDict[u]['msgWordCount'], uDict[u]['wordsPerMsg'],
        uDict[u]['mentions'], uDict[u]['editCount'],  uDict[u]['reactionCount'],
        uDict[u]['reactedCount'], uDict[u]['reactionsPerMsg'], uDict[u]['reactedPerReactions'], uDict[u]['rating']])

    #Write Total row
    writer.writerow(['Total', '', totalMsgCount,
    totalFileShareCount, totalMsgWordCount, float(totalMsgWordCount) / float(totalMsgCount),
    totalMentions, totalEditCount, totalReactionCount,
    '', float(totalReactionCount) / float(totalMsgCount), float(totalReactedPerReactions) / float(totalUsers)])

#Create csv file for reacion statistics
with open('reaction_stats.csv', 'wb') as reaction_stats:
    writer = csv.writer(reaction_stats, delimiter=',')

    writer.writerow(['Reaction', 'Count'])

    #Initialize totals
    totalCount = 0

    for r in reactions:
        count = 0

        if 'count' in reactions[r]:
            count = reactions[r]['count']

        #Keep a running total of most of the stats to show in the csv file
        totalCount += count
        writer.writerow([r, count])
    writer.writerow(['Total', totalCount])
