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
    if len(players) >= 1:
        return str(players)
    else:
        return 'I could not find a team on HLTV with the name ' + team


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
            comment.reply(scrape(get_team(comment)))
            already_done.append(comment.id)
            print "Comment posted"
    print 'sleeping'
    time.sleep(5)
