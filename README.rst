37.6 - A Strategic Game of Dice Placement
=========================================

An electronic version of Artem Borovkov's 37.6 

.. image:: screenshots/37.6.png
   :align: center
   :scale: 50 %
   
Rules
=====

For two to five players (the official version of the game is for two players)

1. Each player has 12 dice that are placed in a stack
   to the side of the board
2. Players take turns to select and place a single die
3. Select: player may selects one of their die
   from the stack or from the hex board
4. The selected die is rolled.
5. Place: The player then selects an empty spot on the board
   to place his or her die.
6. A player scores a point for each die on the board
   that has neighboring dice equal in number to the
   value in the face of the die (e.g. if the die face
   is a 2 you will score a point for that die if it has
   exactly 2 neighboring die).
7. The player with the most points the first time any
   player reaches 6 points is the winner (the scoreboard
   is displayed at the top right of the screen)

For more information: http://boardgamegeek.com/thread/1167751/376-game-under-open-license-here/page/1

How to Play
===========

Android
-------

1. Download the source package to your device from https://github.com/spillz/37.6/archive/master.zip
2. Goto the play store and install kivy
3. Using a file manager application (I recommend ES File Explorer), extract the sources package to sdcard/kivy/37.6
4. Start kivy launcher and select 37.6 from the list of games

Ubuntu Linux
------------

Open a terminal and type the following commands:

.. code:: bash

    sudo apt-get install python python-kivy
    git clone https://github.com/spillz/37.6
    cd 37.6
    python main.py

Windows
-------

1. Download the source package to your computer from https://github.com/spillz/37.6/archive/master.zip
2. Install kivy and following the instructions for running the package: http://kivy.org/docs/installation/installation-windows.html

TODOs
=====

1. AI players (choosing this option will probably crash the game)
2. Network players (choosing this option will probably crash the game)
3. Placement Animations
4. Game Persistence
5. Sound effects
6. UI tidy up (menus, graphics)
7. Player customiztion (names, colors, profiles)
8. Binary Packages
   
See the LICENSE file for copyright information
