37.6 - A Strategic Game of Dice Placement
=========================================

An electronic version of Artem Borovkov's 37.6 

.. image:: screenshots/37.6.png
   :align: center
   :scale: 50 %

Youtube: http://youtu.be/z4mxD9EQsJs
      
Rules
=====

For two to five players (the original version of the game is for two players)

1. **Setup**: Each player has 12 dice that are placed in a stack
   to the side of an empty hex board.

2. **Action**: Players take turns to **select** and then **place** a die.
    
    - **Select**: player selects and rolls one of their dice
      from the stack or from the hex board.

    - **Place**: The player then places the selected die on an 
      empty spot on the board.

3. **Lock Dice**: A die is locked if the face value of the die equals
   the number of dice in neighboring hexes (e.g. if the die face
   is a 2 that die is locked if exactly 2 neighboring dice). 
   If a neighboring die to a locked die is removed, that die is no longer locked.

4. **Win with 6 Locked Dice**: The player with the most locked dice the first time any
   player reaches 6 locked dice is the winner (each player's locked dice
   count is displayed at the top right of the screen). The game is a draw
   if two or more players have the same number of locked dice (but at least 6).

For more information: http://boardgamegeek.com/thread/1167751/376-game-under-open-license-here/page/1

How to Install and Play the Game
================================

Windows
-------

Download the all-in-one binary release here: https://github.com/spillz/37.6/releases 

or run the sources:

1. Download the source package to your computer from https://github.com/spillz/37.6/archive/master.zip
2. Install kivy and following the instructions for running the package: http://kivy.org/docs/installation/installation-windows.html

Android
-------

1. Download the source package to your device from https://github.com/spillz/37.6/archive/master.zip
2. Goto the play store, find and install kivy
3. Using a file manager application to open the source package (I recommend ES File Explorer),
   then extract the source package to /sdcard/kivy/ 
   (i.e. you need to put the folder called 37.6-master in 
   /sdcard/kivy, creating the kivy folder if necessary)
4. Start kivy launcher and select 37.6 from the list of games

Ubuntu Linux
------------

Open a terminal and type the following commands:

.. code:: bash

    sudo apt-get install git python python-kivy
    git clone https://github.com/spillz/37.6
    cd 37.6
    python main.py

TODOs
=====

1. Varying levels of AI players
2. Standalone server for internet play
3. Game Persistence
4. Sound effects
5. UI tidy up (menus, graphics)
6. Player customiztion (names, colors, profiles)
7. Binary Packages (Android, Linux, Mac)
   
See the LICENSE file for copyright information
