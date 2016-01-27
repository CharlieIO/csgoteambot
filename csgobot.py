import praw
import time
import os
import urllib2
import re
import psycopg2
import urlparse
from bs4 import BeautifulSoup

urlparse.uses_netloc.append("postgres")
url = urlparse.urlparse(os.environ["DATABASE_URL"])


def teamlinks():
    namelink = {}
    req = urllib2.Request('http://www.hltv.org/?pageid=182&mapCountOverride=10', headers={
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.111 Safari/537.36"})
    con = urllib2.urlopen(req)
    source = con.read()
    soup = BeautifulSoup(source, 'html.parser')
    print soup.prettify()
    for link in soup.find_all('a', href=True):
        if re.findall('pageid=179', link['href']):
            namelink[link.get_text().strip()] = link.get('href')
    return namelink


def show_table():
    conn = psycopg2.connect(
            database=url.path[1:],
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port
    )
    cur = conn.cursor()
    cur.execute("select team_name from csgo_teams")
    # cur.execute("DELETE FROM csgo_teams WHERE ROUNDS IS NULL")
    rows = cur.fetchall()
    print "\nShow me the databases:\n"
    for row in rows:
        print "   ", row
    conn.commit()
    conn.close()


def auto_scrape():
    time.sleep(86400)
    count = 0
    teamlink = teamlinks()
    for name in teamlink:
        link = teamlink[name]
        p1, p2, p3, p4, p5 = tscrape(teamlink[name])
        win, draw, loss, mapsplayed, kills, deaths, rounds, kdratio = statscrape(teamlink[name])
        database_update(name, p1, p2, p3, p4, p5, win, draw, loss, rounds, link)
        count += 1
        print name + ' has been modified. \n' + str(count) + ' teams modified.'
        time.sleep(3)
    print 'UPDATE COMPLETE :)'


def database_update(tname, p1, p2, p3, p4, p5, win, draw, loss, rounds, link):
    conn = psycopg2.connect(
            database=url.path[1:],
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port
    )
    cur = conn.cursor()
    cur.execute("SELECT TEAM_NAME FROM CSGO_TEAMS")
    nameslist = cur.fetchall()
    if (tname,) not in nameslist:
        cur.execute("INSERT INTO CSGO_TEAMS (TEAM_NAME, PLAYER1, PLAYER2, PLAYER3, PLAYER4, PLAYER5, WINS, DRAWS, LOSSES, ROUNDS, LINK) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (tname, p1, p2, p3, p4, p5, win, draw, loss, rounds, link))
        print '\nNew Team Added Successfullly'
    else:
        cur.execute("UPDATE CSGO_TEAMS SET TEAM_NAME=(%s) WHERE TEAM_NAME= (%s)", (tname, tname))
        cur.execute("UPDATE CSGO_TEAMS SET PLAYER1=(%s) WHERE TEAM_NAME= (%s)", (p1, tname))
        cur.execute("UPDATE CSGO_TEAMS SET PLAYER2=(%s) WHERE TEAM_NAME= (%s)", (p2, tname))
        cur.execute("UPDATE CSGO_TEAMS SET PLAYER3=(%s) WHERE TEAM_NAME= (%s)", (p3, tname))
        cur.execute("UPDATE CSGO_TEAMS SET PLAYER4=(%s) WHERE TEAM_NAME= (%s)", (p4, tname))
        cur.execute("UPDATE CSGO_TEAMS SET PLAYER5=(%s) WHERE TEAM_NAME= (%s)", (p5, tname))
        cur.execute("UPDATE CSGO_TEAMS SET WINS=(%s) WHERE TEAM_NAME= (%s)", (win, tname))
        cur.execute("UPDATE CSGO_TEAMS SET DRAWS=(%s) WHERE TEAM_NAME= (%s)", (draw, tname))
        cur.execute("UPDATE CSGO_TEAMS SET LOSSES=(%s) WHERE TEAM_NAME= (%s)", (loss, tname))
        cur.execute("UPDATE CSGO_TEAMS SET ROUNDS=(%s) WHERE TEAM_NAME= (%s)", (rounds, tname))
        cur.execute("UPDATE CSGO_TEAMS SET LINK=(%s) WHERE TEAM_NAME= (%s)", (link, tname))

        print '\nExisting Team Updated'
    conn.commit()
    conn.close()


def tscrape(teamlink):
    players = []
    req = urllib2.Request('http://www.hltv.org/' + teamlink, headers={
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.111 Safari/537.36"})
    con = urllib2.urlopen(req)
    source = con.read()
    soup = BeautifulSoup(source, 'html.parser')
    for link in soup.find_all('a', href=True):
        if re.findall('pageid=173', link['href']):
            if '(' in link.get_text():
                players += [link.get_text().split(' (')[0]]
    return players[0], players[1], players[2], players[3], players[4] #top 5 players by rounds played


def statscrape(teamlink):
    req = urllib2.Request('http://www.hltv.org/' + teamlink, headers={
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.111 Safari/537.36"})
    con = urllib2.urlopen(req)
    source = con.read()
    soup = BeautifulSoup(source, 'html.parser')
    otherstats = []
    for stat in soup.find_all(style="font-weight:normal;width:140px;float:left;color:black;text-align:right;"):
        windrawloss = stat.get_text().split(' / ')
    for stat in soup.find_all(style="font-weight:normal;width:180px;float:left;color:black;text-align:right;"):
        otherstats += [stat.get_text()]
    return windrawloss[0],windrawloss[1],windrawloss[2], otherstats[0], otherstats[1], otherstats[2], otherstats[3], otherstats[4] #win, draw, loss
    #other stats are maps played, total kills, total deaths, rounds played, K/D ratio

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
    conn = psycopg2.connect(
            database=url.path[1:],
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port
    )
    cur = conn.cursor()
    subreddit = r.get_subreddit('globaloffensive')
    comments = subreddit.get_comments()
    flat_comments = praw.helpers.flatten_tree(comments)
    for comment in flat_comments:
        print comment
        has_call = rcall[0] in comment.body or rcall[1] in comment.body
        if comment.id not in already_done and has_call:
            team = get_team(comment.body)
            statfill = '\n\n**Wins:** %s' + '\n\n**Draws:** %s' + '\n\n**Losses:** %s' + '\n\n**Rounds Played:**  %s'
            if team != '!roster' and team != '!team' and '%' not in team and '\\' not in team:
                try:
                    cur.execute("SELECT * FROM CSGO_TEAMS WHERE UPPER(TEAM_NAME) LIKE UPPER((%s)) LIMIT 1", ('%' + team + '%',))
                    stats = cur.fetchall()
                    print stats
                    tstats = stats[0][6:10]
                    players = stats[0][1:6]
                    team = stats[0][0]
                    link = stats[0][10]
                    print players
                except:
                    print '~~~~~~ERROR1~~~~~~'
                    pass
                try:
                    format_text = '\n\nPlayer | Rating ' + '\n:--:|:--:' + ('\n%s | Rating is under maintnance.' * 5) + (
                        statfill % (tuple(tstats))) + '\n\n**Win/Loss Percentage:** ' + str(
                            round((float(tstats[0]) / float(tstats[2])), 2))
                except:
                    print '~~~~~~ERROR2~~~~~~'
                    pass
                try:
                    comment.reply(
                            'Information for **' + team.replace('&nbsp;', '').replace('%20', ' ').upper() + '**:' + (
                                format_text % (tuple(players))) + '\n\n [Powered by HLTV](http://www.hltv.org/' + link + ')')
                except:
                    print '~~~~~~ERROR3~~~~~~'
                    pass
                    already_done.append(comment.id)
            print "~~~~~~~~~Comment posted.~~~~~~~~~"
    conn.close()
    time.sleep(20)
