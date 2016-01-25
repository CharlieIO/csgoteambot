import praw
import time
import os
import urllib2
import re


def scrape(team):
    req = urllib2.Request('http://www.hltv.org/?pageid=152&query=' + team, headers={'User-Agent': "Magic Browser"})
    con = urllib2.urlopen(req)
    source = con.read()
    players = re.findall(r'">(.*?)</a></td>', source)
    return players


def get_team(comment):
    comment = comment.split()
    for num in range(len(comment)):
        if list[num] == '!roster' or '!team':
            return list[num + 1]


r = praw.Reddit('An easy way to access team rosters.')
r.login(os.environ['REDDIT_USER'], os.environ['REDDIT_PASS'])
rcall = ['!roster', '!team']
already_done = []
while True:
    subreddit = r.get_subreddit('globaloffensive')
    print subreddit
    comments = subreddit.get_comments()

    print comments
    flat_comments = praw.helpers.flatten_tree(comments)
    for comment in flat_comments:
        print comments
        print comment
        has_call = any(string in comment.body for string in rcall)
        if comment.id not in already_done and has_call:
            comment.reply(scrape(get_team(comment)))
            already_done.append(comment.id)
            print "Comment posted"
    print 'found'
    time.sleep(15)
