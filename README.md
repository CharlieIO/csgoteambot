# CSGOTeamBot

A Python bot for [/r/globaloffensive](http://www.reddit.com/r/globaloffensive), powered by [HLTV](http://www.hltv.org)'s statistics. Easily access specific team and player stats, instantly.

## Usage

Call the bot using `!player`, `!rektby`, `!team`, or `!roster`, followed by a player or team name, respectively.
If the team or player's name is two words, just surround the name with quotes. The bot will always check for a case-sensitive match first, and then check for any applicable matches.
CSGOTeamBot supports multiple calls in one comment, so `!team nip !player get_right` would produce:
>Information for **[NIP](http://hltv.org/?pageid=179&teamid=4411)**:
>
>Player | Rating 
>:--:|:--:
>GeT_RiGhT | 1.21 
>f0rest | 1.18 
>Xizt | 1.07 
>friberg | 1.04 
>pyth | 1.07 
>
>**Wins:** 581 
>
>**Draws:** 4 
>
>**Losses:** 252 
>
>**Rounds Played:**  20974 
>
>**Win/Loss Ratio:** 2.31
>
>[Powered by HLTV](http://www.hltv.org/)
>
>[GitHub Source](https://github.com/Charrod/csgoteambot) // [Developer's Steam](https://steamcommunity.com/id/CHARKbite/)
>
>Information for **[GeT_RiGhT](http://www.hltv.org/?pageid=173&playerid=39)**:
>
>Stats | Values
>:--|:--:
>Real Name: | **Christopher Alesund**
>Age: | **25**
>Primary Team: | **NiP**
>Kills: | **17711**
>Deaths: | **13235**
>Kill/Death Ratio: | **1.34**
>HSP: | **49.1%**
>HLTV Rating: | **1.21**
>
>[Powered by HLTV](http://www.hltv.org/)
>
>[GitHub Source](https://github.com/Charrod/csgoteambot) // [Developer's Steam](https://steamcommunity.com/id/CHARKbite/)


## Contributing

1. Fork it!
2. Create your feature branch: `git checkout -b my-new-feature`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin my-new-feature`
5. Submit a pull request!


## Credits

[Charrod](https://github.com/Charrod) - Primary developer

[The-Nutty](https://github.com/The-Nutty) - Implemented multiple calls per comment

[Fatbird3](https://github.com/Fatbird3) - Help with testing and code-cleanup

## Contact

[Developer's Steam](https://steamcommunity.com/id/CHARKbite/)

[Email](mailto:charrod796@gmail.com)
