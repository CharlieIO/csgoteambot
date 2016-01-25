import praw
import time
import os
import urllib2
import re


def tscrape(team):
    req = urllib2.Request('http://www.hltv.org/?pageid=152&query=' + team, headers={'User-Agent': "Magic Browser"})
    con = urllib2.urlopen(req)
    source = con.read()
    players = re.findall(r'">(.*?)</a></td>', source)
    return players

def statscrape(team):
    req = urllib2.Request('http://www.hltv.org/?pageid=152&query=' + team, headers={'User-Agent': "Magic Browser"})
    con = urllib2.urlopen(req)
    source = con.read()
    stats = re.findall(r'<td style="text-align: right;">(.*?)</td>', source)
    return stats


def get_team(comment):
    comment = str(comment).split()
    for num in range(len(comment)):
        if comment[num] == '!roster' or comment[num] == '!team':
            return str(comment[num + 1])


r = praw.Reddit('An easy way to access team rosters.')
r.login(os.environ['REDDIT_USER'], os.environ['REDDIT_PASS'])
rcall = ['!roster', '!team']
already_done = []
while True:
    subreddit = r.get_subreddit('globaloffensive')
    comments = subreddit.get_comments()
    flat_comments = praw.helpers.flatten_tree(comments)
    for comment in flat_comments:
        print comment
        has_call = rcall[0] in comment.body or rcall[1] in comment.body
        if comment.id not in already_done and has_call:
            team = get_team(comment)
            members = tscrape(team)
            stats = statscrape(team)
            if len(members) >= 1:
                statfill = '\n\n**Wins:**%r' + '\n**Draws:**%r' + '\n**Losses:**%r' + '\n**Rounds Played:**%r'
                format_text = '\n\nPlayer | Rating ' + '\n:--:|:--:' + ('\n%s | %r'*len(members)) + statfill
                comment.reply('Information for **'+team.upper()+'**' + (format_text % (tuple(members),tuple(stats))))
                already_done.append(comment.id)
            else:
                comment.reply('I cannot find a team on HLTV by the name of ' + team + '.')
                already_done.append(comment.id)
            print "Comment posted."
    print 'sleeping'
    time.sleep(5)
