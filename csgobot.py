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


def auto_scrape():
    tcount = 0
    pcount = 0
    teamlink = teamlinks()
    for tname in teamlink:
        players_updated = False
        tlink = teamlink[tname]
        players, playerlink = tscrape(teamlink[tname])
        win, draw, loss, mapsplayed, kills, deaths, rounds, kdratio = statscrape(teamlink[tname])
        for player in playerlink:
            plink = playerlink[player]
            pname, age, team, k, hsp, d, rating, p1, p2, p3, p4 = pstats(playerlink[player])
            if not players_updated:
                team_database_update(team, p1, p2, p3, p4, player, win, draw, loss, rounds, tlink)
                players_updated = True
                tcount += 1
                print team + ' has been modified. \n' + str(tcount) + ' teams modified.'
            player_database_update(player, pname, age, team, k, d, hsp, rating, plink)
            pcount += 1
            print player + ' has been modified. \n' + str(pcount) + ' players modified. #' + team
            time.sleep(3)
            # name, age, team, K, HSP, D, Rating
        time.sleep(3)
    print 'UPDATE COMPLETE :)'


def teamlinks():
    namelink = {}
    req = urllib2.Request('http://www.hltv.org/?pageid=182&mapCountOverride=10', headers={
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.111 Safari/537.36"})
    con = urllib2.urlopen(req)
    source = con.read()
    soup = BeautifulSoup(source, 'html.parser')
    for link in soup.find_all('a', href=True):
        if re.findall('pageid=179', link['href']):
            namelink[link.get_text().encode('latin1').strip()] = link.get('href').encode('latin1')
    return namelink


def pstats(plink):
    req = urllib2.Request('http://www.hltv.org/' + str(plink), headers={
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.111 Safari/537.36"})
    con = urllib2.urlopen(req)
    source = con.read()
    soup = BeautifulSoup(source, 'html.parser')
    stats = []
    names = []
    personalstats = []
    for stat in soup.find_all(style="font-weight:normal;width:100px;float:left;text-align:right;color:black"):
        if '%' in stat.get_text():
            stats += [stat.get_text().replace('%', '')]
        else:
            stats += [stat.get_text()]
    for stat in soup.find_all(style="font-weight:normal;width:185px;float:left;text-align:right;color:black;"):
        if '-' == stat.get_text():
            personalstats += [stat.get_text().replace('-', '99')] #fix for no age listed
        else:
            personalstats += [stat.get_text()]
    for stat in soup.find_all(
            style="font-weight:normal;width:100px;float:left;text-align:right;color:black;font-weight:bold"):
        stats += [stat.get_text()]
    for name in soup.find_all('b'):
        if name.get_text()[0] == "'":
            names += [name.get_text().strip("'")]
    if len(names) == 4 and len(personalstats == 4) and len(stats) == 10:
        print '\n', names
        return personalstats[0], personalstats[1], personalstats[3], stats[0], stats[1], stats[2], stats[9], names[0], names[1], names[2], names[3]
    elif len(personalstats) == 4 and len(stats) == 10:
        print 'Incomplete team or overloaded (>5 members)'
        return personalstats[0], personalstats[1], personalstats[3], stats[0], stats[1], stats[2], stats[9], '', '', '', ''
    else:
        return '', '', '', '', '', '', '', '', '', '', ''

def tscrape(teamlink):
    players = []
    req = urllib2.Request('http://www.hltv.org/' + teamlink, headers={
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.111 Safari/537.36"})
    con = urllib2.urlopen(req)
    source = con.read()
    soup = BeautifulSoup(source, 'html.parser')
    playerlink = {}
    for link in soup.find_all('a', href=True):
        if re.findall('pageid=173', link['href']):
            if '(' in link.get_text():
                playerlink[link.get_text().split(' (')[0]] = link.get('href')
                players += [link.get_text().split(' (')[0]]
    return players, playerlink  # every player that has been on a team.


def player_database_update(player, name, age, team, k, d, hsp, rating, link):
    conn = psycopg2.connect(
            database=url.path[1:],
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port
    )
    cur = conn.cursor()
    cur.execute("SELECT LINK FROM CSGO_PLAYERS")
    linklist = cur.fetchall()
    if (link.encode('latin1'),) not in linklist:
        cur.execute(
                "INSERT INTO CSGO_PLAYERS (PLAYER, IRLNAME, AGE, TEAM, KILLS, DEATHS, HSP, RATING, LINK) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (player, name, age, team, k, d, hsp, rating, link))
        print '\nNew Player Added Successfullly'
    else:
        cur.execute("UPDATE CSGO_PLAYERS SET IRLNAME=(%s) WHERE PLAYER=(%s)", (name, player))
        cur.execute("UPDATE CSGO_PLAYERS SET AGE=(%s) WHERE PLAYER=(%s)", (age, player))
        cur.execute("UPDATE CSGO_PLAYERS SET TEAM=(%s) WHERE PLAYER=(%s)", (team, player))
        cur.execute("UPDATE CSGO_PLAYERS SET KILLS=(%s) WHERE PLAYER=(%s)", (k, player))
        cur.execute("UPDATE CSGO_PLAYERS SET DEATHS=(%s) WHERE PLAYER=(%s)", (d, player))
        cur.execute("UPDATE CSGO_PLAYERS SET HSP=(%s) WHERE PLAYER=(%s)", (hsp, player))
        cur.execute("UPDATE CSGO_PLAYERS SET RATING=(%s) WHERE PLAYER=(%s)", (rating, player))
        cur.execute("UPDATE CSGO_PLAYERS SET LINK=(%s) WHERE PLAYER=(%s)", (link, player))
        print '\nExisting Player Updated'
    conn.commit()
    conn.close()


def team_database_update(tname, p1, p2, p3, p4, p5, win, draw, loss, rounds, link):
    conn = psycopg2.connect(
            database=url.path[1:],
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port
    )
    cur = conn.cursor()
    cur.execute("SELECT TEAM_NAME FROM csgo_teams")
    nameslist = cur.fetchall()
    if (tname.encode('latin1'),) not in nameslist:
        cur.execute(
                "INSERT INTO CSGO_TEAMS (TEAM_NAME, PLAYER1, PLAYER2, PLAYER3, PLAYER4, PLAYER5, WINS, DRAWS, LOSSES, ROUNDS, LINK) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (tname, p1, p2, p3, p4, p5, win, draw, loss, rounds, link))
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
    return windrawloss[0], windrawloss[1], windrawloss[2], otherstats[0], otherstats[1], otherstats[2], otherstats[3], \
           otherstats[4]  # win, draw, loss
    # other stats are maps played, total kills, total deaths, rounds played, K/D ratio


def get_team(comment):
    comment = str(comment).split()
    for num in range(len(comment)):
        if comment[num] == '!roster' or comment[num] == '!team':
            return str(comment[num + 1])


def show_table():
    conn = psycopg2.connect(
            database=url.path[1:],
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port
    )
    cur = conn.cursor()
    print 'connected'
    cur.execute("SELECT * FROM CSGO_TEAMS")
    print 'changes completed'
    # cur.execute("ALTER TABLE CSGO_PLAYERS ALTER COLUMN HSP SET DATA TYPE NUMERIC (3,1)")
    # rows = cur.fetchall()
    # print "\nShow me the databases:\n"
    # for row in rows:
    #     print "   ", row
    conn.commit()
    print 'done'
    conn.close()


auto_scrape()
# r = praw.Reddit('An easy way to access team rosters.')
# r.login(os.environ['REDDIT_USER'], os.environ['REDDIT_PASS'])
# rcall = ['!roster', '!team']
# pcall = ['!player', '!rektby']
# talready_done = []
# palready_done = []
# forbidden = '+%\\*";[]{}:'
# while True:
#     conn = psycopg2.connect(
#             database=url.path[1:],
#             user=url.username,
#             password=url.password,
#             host=url.hostname,
#             port=url.port
#     )
#     cur = conn.cursor()
#     subreddit = r.get_subreddit('globaloffensive')
#     comments = subreddit.get_comments()
#     flat_comments = praw.helpers.flatten_tree(comments)
#     for comment in flat_comments:
#         print comment
#         has_team_call = rcall[0] in comment.body or rcall[1] in comment.body
#         has_player_call = rcall[0] in comment.body or rcall[1] in comment.body
#         if comment.id not in already_done and has_team_call:
#             team = get_team(comment.body)
#             statfill = '\n\n**Wins:** %s' + '\n\n**Draws:** %s' + '\n\n**Losses:** %s' + '\n\n**Rounds Played:**  %s'
#             if team != '!roster' and team != '!team' and any((c in forbidden) for c in team) == -1:
#                 try:
#                     if team.upper() == 'VP':
#                         team.replace('VP', 'Virtus.Pro')
#                     cur.execute("SELECT * FROM CSGO_TEAMS WHERE UPPER(TEAM_NAME) LIKE UPPER((%s)) LIMIT 1",
#                                 ('%' + team + '%',))
#                     stats = cur.fetchall()
#                     print stats
#                     tstats = stats[0][6:10]
#                     players = stats[0][1:6]
#                     team = stats[0][0]
#                     link = stats[0][10]
#                     print players
#                 except:
#                     print '~~~~~~ERROR1~~~~~~'
#                     pass
#                 try:
#                     format_text = '\n\nPlayer | Rating ' + '\n:--:|:--:' + (
#                     '\n%s | Rating will be added soon.' * 5) + (
#                                       statfill % (tuple(tstats))) + '\n\n**Win/Loss Ratio:** ' + str(
#                             round((float(tstats[0]) / float(tstats[2])), 2))
#                 except:
#                     print '~~~~~~ERROR2~~~~~~'
#                     pass
#                 try:
#                     comment.reply(
#                             'Information for **' + team.replace('&nbsp;', '').replace('%20', ' ').upper() + '**:' + (
#                                 format_text % (
#                                 tuple(players))) + '\n\n [Powered by HLTV](http://www.hltv.org/' + link + ') \n\n [GitHub Source](https://github.com/Charrod/csgoteambot)')
#                 except:
#                     print '~~~~~~ERROR3~~~~~~'
#                     pass
#                 talready_done.append(comment.id)
#             print "~~~~~~~~~Comment posted.~~~~~~~~~"
#         if comment.id not in already_done and has_team_call:
#             team = get_team(comment.body)
#             statfill = '\n\n**Wins:** %s' + '\n\n**Draws:** %s' + '\n\n**Losses:** %s' + '\n\n**Rounds Played:**  %s'
#             if team != '!roster' and team != '!team' and any((c in forbidden) for c in team) == -1:
#                 try:
#                     if team.upper() == 'VP':
#                         team.replace('VP', 'Virtus.Pro')
#                     cur.execute("SELECT * FROM CSGO_TEAMS WHERE UPPER(TEAM_NAME) LIKE UPPER((%s)) LIMIT 1",
#                                 ('%' + team + '%',))
#                     stats = cur.fetchall()
#                     print stats
#                     tstats = stats[0][6:10]
#                     players = stats[0][1:6]
#                     team = stats[0][0]
#                     link = stats[0][10]
#                     print players
#                 except:
#                     print '~~~~~~ERROR1~~~~~~'
#                     pass
#                 try:
#                     format_text = '\n\nPlayer | Rating ' + '\n:--:|:--:' + (
#                     '\n%s | Rating will be added soon.' * 5) + (
#                                       statfill % (tuple(tstats))) + '\n\n**Win/Loss Ratio:** ' + str(
#                             round((float(tstats[0]) / float(tstats[2])), 2))
#                 except:
#                     print '~~~~~~ERROR2~~~~~~'
#                     pass
#                 try:
#                     comment.reply(
#                             'Information for **' + team.replace('&nbsp;', '').replace('%20', ' ').upper() + '**:' + (
#                                 format_text % (
#                                 tuple(players))) + '\n\n [Powered by HLTV](http://www.hltv.org/' + link + ') \n\n [GitHub Source](https://github.com/Charrod/csgoteambot)')
#                 except:
#                     print '~~~~~~ERROR3~~~~~~'
#                     pass
#                 talready_done.append(comment.id)
#             print "~~~~~~~~~Player Comment posted.~~~~~~~~~"
#     conn.close()
#     time.sleep(20)
