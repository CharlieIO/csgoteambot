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
    '''
    Used to update the database automagically
    '''
    tcount = 0  # team count
    pcount = 0  # player count
    teamlink = teamLinks()  # gets dict with teams as keys and links as values
    for tname in teamlink:  # go through each team on top 400 list
        tlink = teamlink[tname]  # sets a variable for the team's HLTV link
        players, playerlink = tScrape(
            tlink)  # obtains a list of players, and a dictionary containing player names and links
        # (anyone who has been on a top 400 team)
        win, draw, loss, mapsplayed, kills, deaths, rounds, kdratio = statScrape(tlink)
        for player in playerlink:  # look at each player in the playerlink list
            try:
                plink = playerlink[player]  # set a variable for their link
                p1, p2, p3, p4 = otherPlayers(plink)  # set variables for their teammates
                tcount += 1  # increment teams added
                pname, age, team, k, hsp, d, rating, u1, u2, u3, u4 = pStats(
                    plink)  # get player stats and teammates (u is unused variables)
                if tname == team:  # if the players are on the correct team, update DB
                    team_database_update(tname, p1, p2, p3, p4, player, win, draw, loss, rounds, tlink)
                    print tname + ' has been modified. \n' + str(tcount) + ' teams modified.'
                else:
                    team_database_update_nolink(team, p1, p2, p3, p4,
                                                player)  # if the team is missing a link, update DB
                    print team + ' has been modified. \n' + str(tcount) + ' teams modified.'
                player_database_update(player, pname, age, team, k, d, hsp, rating,
                                       plink)  # regardless, update the player DB
                pcount += 1  # increment players added
                print player + ' has been modified. \n' + str(pcount) + ' players modified. #' + team
                time.sleep(3)  # reduce load on HLTV servers
            except:
                print 'error'
                pass
                # name, age, team, K, HSP, D, Rating
        time.sleep(3)
    print 'UPDATE COMPLETE :)'


def teamLinks():
    '''
    extracts names of teams, and their links
    @return: dictionary with name as key and link as value
    '''
    namelink = {}
    req = urllib2.Request('http://www.hltv.org/?pageid=182&mapCountOverride=10', headers={
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.111 Safari/537.36"})
    con = urllib2.urlopen(req)
    source = con.read()  # get source code
    soup = BeautifulSoup(source, 'html.parser')
    for link in soup.find_all('a', href=True):  # finds all links in the HTML
        if re.findall('pageid=179', link['href']):  # pageid=179 is a player's page
            namelink[link.get_text().encode('latin1').strip()] = link.get('href').encode('latin1').replace('/', '')
            # strips spaces from links, and removes the beginning / (preference, could function with the /)
    return namelink  # returns dictionary with name as key and link as value


def otherPlayers(plink):
    '''
    @param plink: player's link
    @return: all the team values we care about
    '''
    u1, u2, u3, u4, u5, u6, u7, p1, p2, p3, p4 = pStats(plink)  # again, u is variables we recieve but don't need
    return p1, p2, p3, p4


def pStats(plink):
    '''
    Extracts player's stats given a link to their page
    @param plink: a link to the player's page
    @return: depending on how much information is found, can return variable amount
    '''
    req = urllib2.Request('http://www.hltv.org/' + str(plink), headers={
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.111 Safari/537.36"})
    con = urllib2.urlopen(req)
    source = con.read()
    soup = BeautifulSoup(source, 'html.parser')
    stats = []
    names = []
    personalstats = []  # stats such as name and age
    for stat in soup.find_all(style="font-weight:normal;width:100px;float:left;text-align:right;color:black"):
        if '%' in stat.get_text():  # HS percentage has a percent sign that must be removed
            stats += [stat.get_text().replace('%', '')]
        else:
            stats += [stat.get_text()]
    for stat in soup.find_all(style="font-weight:normal;width:185px;float:left;text-align:right;color:black;"):
        if '-' == stat.get_text():
            personalstats += [stat.get_text().replace('-', '99')]  # fix for no age listed
        else:
            personalstats += [stat.get_text()]
    for stat in soup.find_all(
            style="font-weight:normal;width:100px;float:left;text-align:right;color:black;font-weight:bold"):
        stats += [stat.get_text()]
    for name in soup.find_all('b'):
        if name.get_text()[0] == "'":  # obtains the names of teammates
            names += [name.get_text().strip("'")]
    if len(names) == 4 and len(personalstats) == 4 and len(stats) == 10:  # full set of stats
        print '\n', names
        return personalstats[0], personalstats[1], personalstats[3], stats[0], stats[1], stats[2], stats[9], names[0], \
               names[1], names[2], names[3]  # in order: name, age, team, kills, HSP, deaths, rating, 4 teammates
    elif len(personalstats) == 4 and len(stats) == 10:  # team doesn't have 5 members
        print '\nIncomplete team or overloaded (>5 members)'
        return personalstats[0], personalstats[1], personalstats[3], stats[0], stats[1], stats[2], stats[
            9], '', '', '', ''  # all but the teammates
    else:
        return '', '', '', '', '', '', '', '', '', '', ''  # if missing anything else, just return empty strings.


def tScrape(teamlink):
    '''
    Gets all players that have been on a team + their links
    @param teamlink: takes dictionary with teams  and links
    @return: returns a list of players as well as a dictionary with players names and links
    '''
    players = []
    req = urllib2.Request('http://www.hltv.org/' + teamlink, headers={
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.111 Safari/537.36"})
    con = urllib2.urlopen(req)
    source = con.read()
    soup = BeautifulSoup(source, 'html.parser')
    playerlink = {}
    for link in soup.find_all('a', href=True):
        if re.findall('pageid=173', link['href']):  # pageid=173 is the id for a player's page
            if '(' in link.get_text():  # if it is a relevant plink it will have '('
                playerlink[link.get_text().split(' (')[0]] = link.get('href').replace('/', '')  # removes / from link
                players += [link.get_text().split(' (')[0]]
    return players, playerlink  # every player that has been on a team.


def player_database_update(player, name, age, team, k, d, hsp, rating, link):
    '''
    using psycopg2 updates the player DB
    @param player: player's in-game-name
    @param name: player's IRL names
    @param age: age of the player
    @param team: player's listed primary team
    @param k: kills
    @param d: deaths
    @param hsp: headshot percentage
    @param rating: HLTV rating for that player
    @param link: link to their HLTV page
    @return: none
    '''
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
    try:
        if (link,) not in linklist:  # if not already in the DB, add them
            cur.execute(
                "INSERT INTO CSGO_PLAYERS (PLAYER, IRLNAME, AGE, TEAM, KILLS, DEATHS, HSP, RATING, LINK) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (player, name, age, team, k, d, hsp, rating, link))
            print '\nNew Player Added Successfully'
        else:  # if already in the DB, just update each field
            cur.execute("UPDATE CSGO_PLAYERS SET IRLNAME=(%s) WHERE LINK=(%s)", (name, link))
            cur.execute("UPDATE CSGO_PLAYERS SET AGE=(%s) WHERE LINK=(%s)", (age, link))
            cur.execute("UPDATE CSGO_PLAYERS SET TEAM=(%s) WHERE LINK=(%s)", (team, link))
            cur.execute("UPDATE CSGO_PLAYERS SET KILLS=(%s) WHERE LINK=(%s)", (k, link))
            cur.execute("UPDATE CSGO_PLAYERS SET DEATHS=(%s) WHERE LINK=(%s)", (d, link))
            cur.execute("UPDATE CSGO_PLAYERS SET HSP=(%s) WHERE LINK=(%s)", (hsp, link))
            cur.execute("UPDATE CSGO_PLAYERS SET RATING=(%s) WHERE LINK=(%s)", (rating, link))
            # cur.execute("UPDATE CSGO_PLAYERS SET LINK=(%s) WHERE LINK=(%s)", (link, link))
            print '\nExisting Player Updated'
        conn.commit()
        conn.close()
    except:
        conn.close()
        pass


def team_database_update(tname, p1, p2, p3, p4, p5, win, draw, loss, rounds, link):
    '''
    Same as player DB update but for the team info
    @param tname: name of the team
    @param p1: roster of the team
    @param p2: "
    @param p3: "
    @param p4: "
    @param p5: "
    @param win: wins the team has
    @param draw: draws " " "
    @param loss: losses " " "
    @param rounds: rounds the team has played
    @param link: link to the team page
    @return: none
    '''
    conn = psycopg2.connect(
        database=url.path[1:],
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port
    )
    cur = conn.cursor()
    cur.execute("SELECT LINK FROM csgo_teams")
    linklist = cur.fetchall()
    if (link,) not in linklist:
        cur.execute(
            "INSERT INTO CSGO_TEAMS (TEAM_NAME, PLAYER1, PLAYER2, PLAYER3, PLAYER4, PLAYER5, WINS, DRAWS, LOSSES, ROUNDS, LINK) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (tname, p1, p2, p3, p4, p5, win, draw, loss, rounds, link))  # if not already in the DB, add them
        print '\nNew Team Added Successfully'
    else:  # if else, update their info
        cur.execute("UPDATE CSGO_TEAMS SET TEAM_NAME=(%s) WHERE LINK= (%s)", (tname, link))
        cur.execute("UPDATE CSGO_TEAMS SET PLAYER1=(%s) WHERE LINK= (%s)", (p1, link))
        cur.execute("UPDATE CSGO_TEAMS SET PLAYER2=(%s) WHERE LINK= (%s)", (p2, link))
        cur.execute("UPDATE CSGO_TEAMS SET PLAYER3=(%s) WHERE LINK= (%s)", (p3, link))
        cur.execute("UPDATE CSGO_TEAMS SET PLAYER4=(%s) WHERE LINK= (%s)", (p4, link))
        cur.execute("UPDATE CSGO_TEAMS SET PLAYER5=(%s) WHERE LINK= (%s)", (p5, link))
        cur.execute("UPDATE CSGO_TEAMS SET WINS=(%s) WHERE LINK= (%s)", (win, link))
        cur.execute("UPDATE CSGO_TEAMS SET DRAWS=(%s) WHERE LINK= (%s)", (draw, link))
        cur.execute("UPDATE CSGO_TEAMS SET LOSSES=(%s) WHERE LINK= (%s)", (loss, link))
        cur.execute("UPDATE CSGO_TEAMS SET ROUNDS=(%s) WHERE LINK= (%s)", (rounds, link))
        print '\nExisting Team Updated'
    conn.commit()
    conn.close()


def team_database_update_nolink(tname, p1, p2, p3, p4, p5):
    '''
    If the team is missing the team link (not in top 400) update this way
    @param tname: team name
    @param p1: roster
    @param p2: "
    @param p3: "
    @param p4: "
    @param p5: "
    @return: none
    '''
    conn = psycopg2.connect(
        database=url.path[1:],
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port
    )
    cur = conn.cursor()
    cur.execute("SELECT TEAM_NAME FROM csgo_teams")
    teamnames = cur.fetchall()
    tname = tname.encode('latin1')
    if (tname,) not in teamnames:
        cur.execute(
            "INSERT INTO CSGO_TEAMS (TEAM_NAME, PLAYER1, PLAYER2, PLAYER3, PLAYER4, PLAYER5) VALUES (%s, %s, %s, %s, %s, %s)",
            (tname, p1, p2, p3, p4, p5))
        print '\nNew Team Added Successfully'
    else:
        cur.execute("UPDATE CSGO_TEAMS SET PLAYER1=(%s) WHERE TEAM_NAME= (%s)", (p1, tname))
        cur.execute("UPDATE CSGO_TEAMS SET PLAYER2=(%s) WHERE TEAM_NAME= (%s)", (p2, tname))
        cur.execute("UPDATE CSGO_TEAMS SET PLAYER3=(%s) WHERE TEAM_NAME= (%s)",
                    (p3, tname))  # functions identically to other update funcs
        cur.execute("UPDATE CSGO_TEAMS SET PLAYER4=(%s) WHERE TEAM_NAME= (%s)", (p4, tname))
        cur.execute("UPDATE CSGO_TEAMS SET PLAYER5=(%s) WHERE TEAM_NAME= (%s)", (p5, tname))
        print '\nExisting Team Updated'
    conn.commit()
    conn.close()


def statScrape(teamlink):
    '''
    obtains the team stats
    @param teamlink: link to the team page
    @return: win, draw, loss, maps played, kills, deaths, rounds played, K/D ratio
    '''
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


def get_team(comment, which_instance):
    '''
    Given a comment, returns the team/player called
    @param comment: content of a comment
    @param which_instance: how many times is CSGOTeamBot called in this function?
    @return: team/player name
    '''
    instance_count = 0
    comment = str(comment).split()
    for num in range(len(comment)):
        if comment[num] == '!roster' or comment[num] == '!team' or comment[num] == '!player' or comment[
            num] == '!rektby':
            if instance_count == which_instance:  # ensures correct return
                if comment[num + 1][0] == '"':  # for multi-word teams, players.
                    if comment[num + 1][-1] == '"':
                        if len(str(comment[num + 1][1:-1])) < 50:  # can't be too long
                            return str(comment[num + 1][1:-1])
                    elif comment[num + 2][-1] == '"' and comment[num + 1][-1] != '"':  # if it is 2 words
                        if len(str(comment[num + 1][1:] + ' ' + comment[num + 2][:-1])) < 50:
                            return str(comment[num + 1][1:] + ' ' + comment[num + 2][:-1])
                    elif '"' not in comment[num + 2] and comment[num + 3][-1] != '"':  # if it is 3 words
                        if len(str(comment[num][1:] + ' ' + comment[num + 2][:] + ' ' + comment[num + 3][:-1])) < 50:
                            return str(comment[num][1:] + ' ' + comment[num + 2][:] + ' ' + comment[num + 3][:-1])
                    else:
                        return 'DROP'  # banned keyword, just an easy way to say "don't make a post"
                else:
                    if len(comment[num + 1]) < 50:
                        return comment[num + 1]
            instance_count += 1


def get_count(comment):
    '''
    Gets count of calls in the comment
    @param comment: text of the comment
    @return: number of team calls, and number of player calls
    '''
    tcount = 0
    pcount = 0
    comment = str(comment).split()
    for num in range(len(comment)):
        if comment[num] == '!roster' or comment[num] == '!team' or comment[num] == '!player' or comment[
            num] == '!rektby':
            tcount += 1
            pcount += 1
    return tcount, pcount


def show_table():
    '''
    utility so I can lookup in the DB. Doesn't do anything necessary
    @return:
    '''
    conn = psycopg2.connect(
        database=url.path[1:],
        user=url.username,
        password=url.password,
        host=url.hostname,
        port=url.port
    )
    cur = conn.cursor()
    print 'connected'
    # cur.execute("DELETE FROM CSGO_PLAYERS")
    # cur.execute("DELETE FROM CSGO_TEAMS")
    cur.execute("SELECT TEAM_NAME FROM CSGO_TEAMS*")
    stats = cur.fetchall()
    print len(stats)
    print stats
    # cur.execute("ALTER TABLE CSGO_PLAYERS ALTER COLUMN HSP SET DATA TYPE NUMERIC (3,1)")
    # rows = cur.fetchall()
    # print "\nShow me the databases:\n"
    # for row in rows:
    #     print "   ", row
    # conn.commit()
    print 'done'
    conn.close()


r = praw.Reddit('An easy way to access team rosters and stats.')
r.login(os.environ['REDDIT_USER'], os.environ['REDDIT_PASS'])
rcall = ['!roster', '!team']  # words to call by
pcall = ['!player', '!rektby']
talready_done = []
palready_done = []
forbidden = '+%\\*;[]{}:"'  # forbidden characters
forbidden2 = 'DROP'  # forbidden keyword
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
    for comment in flat_comments:  # all the comments posted in the subreddit
        comment_reply = ""  # will append to this later
        print comment
        tcall_count, pcall_count = get_count(comment)
        if comment.id not in talready_done:  # talready_done is a list of comment id's where I have already
            for instance in range(tcall_count):
                team = get_team(comment.body, instance)
                statfill = '\n\n**Wins:** %s' + ' \n\n**Draws:** %s' + ' \n\n**Losses:** %s' + ' \n\n**Rounds Played:**  %s '  # layout for commenting
                if team != '!roster' and team != '!team' and any(
                        (c in forbidden) for c in team) == False and forbidden2 not in team.upper():
                    stats = []
                    try:
                        stats = []
                        if team.upper() == 'VP':
                            team.replace('VP', 'Virtus.Pro')  # single common case exception
                        cur.execute("SELECT * FROM CSGO_TEAMS WHERE TEAM_NAME=(%s) LIMIT 1", (team,))  #
                        stats = cur.fetchall()
                        if len(stats) == 0:
                            cur.execute(
                                "SELECT * FROM CSGO_TEAMS WHERE UPPER(TEAM_NAME)=UPPER(%s) AND PLAYER5 IS NOT NULL LIMIT 1",
                                (team,))
                            stats = cur.fetchall()
                        stats = [x for x in stats[0] if x is not None]
                        print len(stats)
                        if len(stats) > 6:
                            unite = []
                            tstats = stats[0][6:10]
                            players = stats[0][1:6]
                            team = stats[0][0]  # assigns statistics
                            link = stats[0][10]
                            player_ratings = []
                            for player in players:
                                cur.execute("SELECT RATING FROM CSGO_PLAYERS WHERE PLAYER=(%s)",
                                            (player,))
                                playerrating = cur.fetchall()
                                if len(playerrating) > 0:
                                    player_ratings += playerrating[0]
                                else:
                                    player_ratings += ['Rating not found.']
                            fixed_rating = []
                            for rate in player_ratings:
                                fixed_rating += [str(rate)]
                            for num in range(5):
                                unite.append(players[num])
                                unite.append(fixed_rating[num])
                        if len(stats) == 6:
                            player_ratings = []
                            unite = []
                            print stats[1:6]
                            players = stats[1:6]
                            for player in players:
                                cur.execute("SELECT RATING FROM CSGO_PLAYERS WHERE PLAYER=(%s)",
                                            (player,))
                                playerrating = cur.fetchall()
                                if len(playerrating) > 0:
                                    player_ratings += playerrating[0]
                                else:
                                    player_ratings += ['Rating not found.']
                            fixed_rating = []
                            for rate in player_ratings:
                                fixed_rating += [str(rate)]
                            for num in range(5):
                                unite.append(players[num])
                                unite.append(fixed_rating[num])
                    except:
                        print '~~~~~~ERROR1~~~~~~'
                        pass
                    try:
                        if len(stats) > 6:
                            format_text = ('\n\nPlayer | Rating ' + '\n:--:|:--:' + ((
                                '\n %s | %s ' * 5)) + (statfill % (tuple(tstats))) + '\n\n**Win/Loss Ratio:** ' + str(
                                round((float(tstats[0]) / float(tstats[2])), 2)))
                        if len(stats) == 6:
                            format_text = ('\n\nPlayer | Rating ' + '\n:--:|:--:' + ((
                                '\n %s | %s ' * 5)))

                    except:
                        print '~~~~~~ERROR2~~~~~~'
                        pass
                    try:
                        if len(stats) > 6:
                            if link:
                                comment_reply = comment_reply + '###Information for **[' + team.replace('&nbsp;',
                                                                                                        '').replace(
                                    '%20',
                                    ' ').upper() + '](http://hltv.org/' + str(link) + ')**:' + (
                                                    (
                                                        format_text) % (
                                                        tuple(
                                                            unite))) + '\n\n [Powered by HLTV](http://www.hltv.org/)\n\n [GitHub Source](https://github.com/Charrod/csgoteambot) // [Developer\'s Steam](https://steamcommunity.com/id/CHARKbite/)\n\n'
                                print "~~~~~~~~~Team Comment posted.~~~~~~~~~"
                            else:
                                comment_reply = comment_reply + '###Information for **' + team.replace('&nbsp;',
                                                                                                       '').replace(
                                    '%20',
                                    ' ').upper() + '**:' + (
                                                    (
                                                        format_text) % (
                                                        tuple(
                                                            unite))) + '\n\n [Powered by HLTV](http://www.hltv.org/)\n\n [GitHub Source](https://github.com/Charrod/csgoteambot) // [Developer\'s Steam](https://steamcommunity.com/id/CHARKbite/) \n\n'
                        if len(stats) == 6:
                            comment_reply = comment_reply + '###Limited information (<10 maps played) for **' + team.replace('&nbsp;',
                                                                                                   '').replace(
                                '%20',
                                ' ').upper() + '**:' + (
                                                (
                                                    format_text) % (
                                                    tuple(
                                                        unite))) + '\n\n [Powered by HLTV](http://www.hltv.org/)\n\n [GitHub Source](https://github.com/Charrod/csgoteambot) // [Developer\'s Steam](https://steamcommunity.com/id/CHARKbite/) \n\n'

                    except:
                        print '~~~~~~~~ERROR3~~~~~~~~~'
                unite = []
                tstats = []
                players = []
                team = []
                link = []
                player_ratings = []
            talready_done.append(comment.id)


            # ---------------------------------------------Player called-----------------------------------------------------

        if comment.id not in palready_done:
            for instance in range(pcall_count):
                p = get_team(comment.body, instance)
                if p != '!roster' and p != '!team' and any(
                        (c in forbidden) for c in p) == False and forbidden2 not in p.upper():
                    stats = []
                    try:
                        if p != "CSGOTeamBot":
                            stats = []
                            cur.execute("SELECT * FROM CSGO_PLAYERS WHERE PLAYER=(%s) LIMIT 1", (p,))
                            stats = cur.fetchall()
                            if len(stats) == 0:
                                cur.execute("SELECT * FROM CSGO_PLAYERS WHERE UPPER(PLAYER)=UPPER(%s) LIMIT 1", (p,))
                                stats = cur.fetchall()
                        elif p == "CSGOTeamBot":
                            stats = [("n/a", "you now me on reddit nice", "Gabe Newell", "12", "6969", "101", "100",
                                      "9.99", "?pageid=179&teamid=6060", "U-Bot")]
                        if len(stats) > 0:
                            personal = stats[0][1:4] + (stats[0][9],)
                            if str(personal[2]) == '99':
                                personal = personal[0:2] + ('Age data not available.',) + personal[3:]
                            print personal  # Player, Name, Age, team
                            KD = stats[0][4:6]
                            print KD  # Kills, Deaths

                            HSRating = stats[0][6:8]
                            print HSRating
                            link = stats[0][8]
                            print link
                        if p != "CSGOTeamBot" and len(stats) > 0:
                            cur.execute("SELECT LINK FROM CSGO_TEAMS WHERE UPPER(TEAM_NAME)=UPPER(%s) LIMIT 1",
                                        (personal[-1],))
                            tlink = cur.fetchall()
                            tlink = tlink[0][0]
                            print tlink
                    except:
                        print '~~~~~~ERROR1~~~~~~'
                        pass
                    try:
                        if len(stats) > 0:
                            format_text = 'Stats | Values' + '\n:--|:--:' + '\nReal Name: | **' + personal[
                                1] + '**\nAge: | **' + \
                                          personal[2] + '**\nPrimary Team: | **' + personal[
                                              3] + '**\nKills: | **' + str(
                                KD[0]) + '**\nDeaths: | **' + str(KD[1]) + '**\nKill/Death Ratio: | **' + str(
                                round((float(KD[0]) / float(KD[1])), 2)) + '**\nHSP: | **' + str(
                                HSRating[0]) + '%**\nHLTV Rating: | **' + str(HSRating[1]) + '**'
                    except:
                        print '~~~~~~ERROR2~~~~~~'
                        pass
                    if len(stats) > 0:
                        comment_reply = comment_reply + '###Information for **[' + personal[
                            0] + '](http://www.hltv.org/' + str(
                            link) + ')**:\n\n' + format_text + '\n\n [Powered by HLTV](http://www.hltv.org/)\n\n [GitHub Source](https://github.com/Charrod/csgoteambot) // [Developer\'s Steam](https://steamcommunity.com/id/CHARKbite/)\n\n'
                    stats = []
                    KD = []
                    HSRating = []
                    link = []
                    palready_done.append(comment.id)
        if not comment_reply == "":
            try:
                comment.reply(comment_reply)
                print "~~~~~~~~~Comment posted.~~~~~~~~~"
            except:
                print '~~~~~~ERROR3~~~~~~'
                pass
    conn.close()
    time.sleep(10)
