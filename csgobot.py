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
    return stats[:5], stats[5:]


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
            pstats, tstats = statscrape(team)
            statfill = '\n\n**Wins:** %s' + '\n\n**Draws:** %s' + '\n\n**Losses:** %s' + '\n\n**Rounds Played:**  %s'
            if len(members) >= 1 and team != '!roster' and team != '!team':
                unite = []
                try:
                    for num in range(len(members)):
                        unite.append(members[num])
                        unite.append(pstats[num])
                except:
                    pass
                try:
                    format_text = '\n\nPlayer | Rating ' + '\n:--:|:--:' + ('\n%s | %s' * len(members)) + (
                        statfill % (tuple(tstats)))
                except:
                    pass
                try:
                    comment.reply(
                            'Information for **' + team.strip().upper() + '**:' + (format_text % (tuple(unite))))
                except:
                    pass
                already_done.append(comment.id)
            print "~~~~~~~~~Comment posted.~~~~~~~~~"
    print 'sleeping'
    time.sleep(20)
