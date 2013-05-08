# Mímir

> »The rememberer, the wise one«
*- Norse mythology*

Mímir is a flat-file note-taking and task managing application.

## Screenshots

![Browse](http://saibotd.com/mimir/browse.png)

![Tasks](http://saibotd.com/mimir/tasks.png)

![Editor](http://saibotd.com/mimir/edit.png)

![HTML](http://saibotd.com/mimir/html.png)

## Installation

1. `pip install flask markdown`
2. [Download Mímir](https://github.com/saibotd/mimir/archive/master.zip)
3. Put Mímir into a directory (e.g. ~/mimir)

## Usage

Setup a directory where you would like to store your notes.
Storing your files inside your Dropbox folder is highly recommended.

Launch Mímir `python2 mimir.py ~/Dropbox/my-notes`

Your default browser should start automatically and open Mímir. If not, point your browser to `http://localhost:5212`.

Inside of Mímir you may now start to create or edit your files. The following filetypes are supported:

- Plain text files
- Markdown (.md)
- HTML (.html)
- Tasklist (.task, losely based on Todo.txt)
- All other files will be forwarded to your browser (e.g. images, PDF) so you may use these in your documents as links or image tags.

There is also a mimir.cfg file, which you my customize and move at ~/.mimir.cfg.
