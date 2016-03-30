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
        if comment[num] == '!roster' or comment[num] == '!team' or comment[
                num] == '!player' or comment[num] == '!rektby':
            if instance_count == which_instance:  # ensures correct return
                # for multi-word teams, players.
                if comment[num + 1][0] == '"':
                    if comment[num + 1][-1] == '"':
                        if len(str(comment[num + 1][1:-1])
                               ) < 50:  # can't be too long
                            return str(comment[num + 1][1:-1])
                    # if it is 2 words
                    elif comment[num + 2][-1] == '"' and comment[num + 1][-1] != '"':
                        if len(str(comment[num + 1][1:] +
                                   ' ' + comment[num + 2][:-1])) < 50:
                            return str(comment[num + 1][1:] +
                                       ' ' + comment[num + 2][:-1])
                    # if it is 3 words
                    elif '"' not in comment[num + 2] and comment[num + 3][-1] != '"':
                        if len(str(comment[num][
                               1:] + ' ' + comment[num + 2][:] + ' ' + comment[num + 3][:-1])) < 50:
                            return str(
                                comment[num][1:] + ' ' + comment[num + 2][:] + ' ' + comment[num + 3][:-1])
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
        if comment[num] == '!roster' or comment[num] == '!team' or comment[
                num] == '!player' or comment[num] == '!rektby':
            tcount += 1
            pcount += 1
    return tcount, pcount


# def show_table():
#     '''
#     utility so I can lookup in the DB. Doesn't do anything necessary
#     @return:
#     '''
#     conn = psycopg2.connect(
#         database=url.path[1:],
#         user=url.username,
#         password=url.password,
#         host=url.hostname,
#         port=url.port
#     )
#     cur = conn.cursor()
#     print 'connected'
#     # cur.execute("DELETE FROM CSGO_PLAYERS")
#     # cur.execute("DELETE FROM CSGO_TEAMS")
#     cur.execute("SELECT TEAM_NAME FROM CSGO_TEAMS*")
#     stats = cur.fetchall()
#     print len(stats)
#     print stats
#     # cur.execute("ALTER TABLE CSGO_PLAYERS ALTER COLUMN HSP SET DATA TYPE NUMERIC (3,1)")
#     # rows = cur.fetchall()
#     # print "\nShow me the databases:\n"
#     # for row in rows:
#     #     print "   ", row
#     # conn.commit()
#     print 'done'
#     conn.close()


def main():
    r = praw.Reddit('An easy way to access team rosters and stats.')
    r.login(os.environ['REDDIT_USER'], os.environ['REDDIT_PASS'])
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
                    statfill = '\n\n**Wins:** %s' + ' \n\n**Draws:** %s' + ' \n\n**Losses:** %s' + \
                        ' \n\n**Rounds Played:**  %s '  # layout for commenting
                    if team != '!roster' and team != '!team' and any(
                            (c in forbidden) for c in team) == False and forbidden2 not in team.upper():
                        stats = []
                        try:
                            stats = []
                            if team.upper() == 'VP':
                                # single common case exception
                                team.replace('VP', 'Virtus.Pro')
                            cur.execute(
                                "SELECT * FROM CSGO_TEAMS WHERE TEAM_NAME=(%s) LIMIT 1", (team,))  #
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
                                tstats = stats[6:10]
                                players = stats[1:6]
                                team = stats[0]  # assigns statistics
                                link = stats[10]
                                player_ratings = []
                                for player in players:
                                    cur.execute(
                                        "SELECT RATING FROM CSGO_PLAYERS WHERE PLAYER=(%s)", (player,))
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
                                    cur.execute(
                                        "SELECT RATING FROM CSGO_PLAYERS WHERE PLAYER=(%s)", (player,))
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
                                format_text = ('\n\nPlayer | Rating ' +
                                               '\n:--:|:--:' +
                                               (('\n %s | %s ' *
                                                 5)) +
                                               (statfill %
                                                   (tuple(tstats))) +
                                               '\n\n**Win/Loss Ratio:** ' +
                                               str(round((float(tstats[0]) /
                                                          float(tstats[2])), 2)))
                            if len(stats) == 6:
                                format_text = ('\n\nPlayer | Rating ' + '\n:--:|:--:' + ((
                                    '\n %s | %s ' * 5)))

                        except:
                            print '~~~~~~ERROR2~~~~~~'
                            pass
                        try:
                            if len(stats) > 6:
                                if link:
                                    comment_reply = comment_reply + '###Information for **[' + team.replace('&nbsp;', '').replace('%20', ' ').upper() + '](http://hltv.org/' + str(link) + ')**:' + ((format_text) % (tuple(
                                        unite))) + '\n\n [Powered by HLTV](http://www.hltv.org/)\n\n [GitHub Source](https://github.com/CharlieIO/csgoteambot) // [Developer\'s Steam](https://steamcommunity.com/id/CharlieIO/)\n\n'
                                    print "~~~~~~~~~Team Comment posted.~~~~~~~~~"
                                else:
                                    comment_reply = comment_reply + '###Information for **' + team.replace('&nbsp;', '').replace('%20', ' ').upper() + '**:' + ((format_text) % (tuple(
                                        unite))) + '\n\n [Powered by HLTV](http://www.hltv.org/)\n\n [GitHub Source](https://github.com/CharlieIO/csgoteambot) // [Developer\'s Steam](https://steamcommunity.com/id/CharlieIO/) \n\n'
                            if len(stats) == 6:
                                comment_reply = comment_reply + '###Limited information (<10 maps played) for **' + team.replace('&nbsp;', '').replace('%20', ' ').upper() + '**:' + ((format_text) % (tuple(
                                    unite))) + '\n\n [Powered by HLTV](http://www.hltv.org/)\n\n [GitHub Source](https://github.com/CharlieIO/csgoteambot) // [Developer\'s Steam](https://steamcommunity.com/id/CharlieIO/) \n\n'

                        except:
                            print '~~~~~~~~ERROR3~~~~~~~~~'
                    unite = []
                    tstats = []
                    players = []
                    team = []
                    link = []
                    player_ratings = []
                talready_done.append(comment.id)

                # ---------------------------------------------Player called---

            if comment.id not in palready_done:
                for instance in range(pcall_count):
                    p = get_team(comment.body, instance)
                    if p != '!roster' and p != '!team' and any(
                            (c in forbidden) for c in p) == False and forbidden2 not in p.upper():
                        stats = []
                        try:
                            if p != "CSGOTeamBot":
                                stats = []
                                cur.execute(
                                    "SELECT * FROM CSGO_PLAYERS WHERE PLAYER=(%s) LIMIT 1", (p,))
                                stats = cur.fetchall()
                                if len(stats) == 0:
                                    cur.execute(
                                        "SELECT * FROM CSGO_PLAYERS WHERE UPPER(PLAYER)=UPPER(%s) LIMIT 1", (p,))
                                    stats = cur.fetchall()
                            elif p == "CSGOTeamBot":
                                stats = [
                                    ("n/a",
                                     "you now me on reddit nice",
                                     "Gabe Newell",
                                     "12",
                                     "6969",
                                     "101",
                                     "100",
                                     "9.99",
                                     "?pageid=179&teamid=6060",
                                     "U-Bot")]
                            if len(stats) > 0:
                                personal = stats[0][1:4] + (stats[0][9],)
                                if str(personal[2]) == '99':
                                    personal = personal[
                                        0:2] + ('Age data not available.',) + personal[3:]
                                print personal  # Player, Name, Age, team
                                KD = stats[0][4:6]
                                print KD  # Kills, Deaths
                                HSRating = stats[0][6:8]
                                print HSRating
                                link = stats[0][8]
                                print link
                            if p != "CSGOTeamBot" and len(stats) > 0:
                                cur.execute(
                                    "SELECT LINK FROM CSGO_TEAMS WHERE UPPER(TEAM_NAME)=UPPER(%s) LIMIT 1", (personal[-1],))
                                tlink = cur.fetchall()
                                tlink = tlink[0][0]
                                print tlink
                        except:
                            print '~~~~~~ERROR1~~~~~~'
                            pass
                        try:
                            if len(stats) > 0:
                                format_text = 'Stats | Values' + '\n:--|:--:' + '\nReal Name: | **' + personal[1] + '**\nAge: | **' + personal[2] + '**\nPrimary Team: | **' + personal[3] + '**\nKills: | **' + str(
                                    KD[0]) + '**\nDeaths: | **' + str(KD[1]) + '**\nKill/Death Ratio: | **' + str(round((float(KD[0]) / float(KD[1])), 2)) + '**\nHSP: | **' + str(HSRating[0]) + '%**\nHLTV Rating: | **' + str(HSRating[1]) + '**'
                        except:
                            print '~~~~~~ERROR2~~~~~~'
                            pass
                        if len(stats) > 0:
                            comment_reply = comment_reply + '###Information for **[' + personal[0] + '](http://www.hltv.org/' + str(
                                link) + ')**:\n\n' + format_text + '\n\n [Powered by HLTV](http://www.hltv.org/)\n\n [GitHub Source](https://github.com/CharlieIO/csgoteambot) // [Developer\'s Steam](https://steamcommunity.com/id/CharlieIO/)\n\n'
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


if __name__ == '__main__':
    main()
