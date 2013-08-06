#!/usr/bin/env python2

import sys, os, hashlib, webbrowser, mimetypes, threading, ConfigParser
import markdown
from flask import (Flask, render_template, request, redirect, abort, Response, send_file)
from urllib import unquote, quote

script_path, script_name = os.path.split(os.path.realpath(__file__))

home_dir = os.path.expanduser('~')
index_file = None


config = ConfigParser.SafeConfigParser()
config.add_section("general")
config.add_section("browser")
config.add_section("httpd")
config.set("general", "home", "~")
config.set("general", "show_hidden", "false")
config.set("browser", "autostart", "true")
config.set("browser", "executable", "")
config.set("httpd", "host", '127.0.0.1')
config.set("httpd", "port", '5212')
config.read([script_path + '/mimir.cfg', os.path.expanduser('~/.mimir.cfg'), os.path.expanduser('~/.config/mimir.cfg')])

home_dir = os.path.expanduser(config.get("general", "home"))

mimetypes.add_type("text/markdown", ".md")
mimetypes.add_type("text/markdown", ".markddown")
mimetypes.add_type("text/tasklist", ".task")
mimetypes.add_type("text/tasklist", ".tasks")
mimetypes.add_type("text/html", ".html")
mimetypes.add_type("text/html", ".htm")


def openFile(filename):
    filepath = unicode(os.path.join(home_dir, filename))
    print "Trying to open %s " % (filepath)
    if not filepath.startswith(home_dir):
        print "File not in scope"
        return None
    if not os.path.exists(filepath):
        print "File does not exists"
        return None
    if not os.path.isfile(filepath):
        print "File is no file"
        return None

    f = open(filepath, "r")
    return f


def compileBreadcrumbs(title):
    title = title.split("/")
    href = ""
    breadcrumbs = []
    for part in title:
        href += "/" + part
        breadcrumbs.append({"href": href, "part": part})
    return breadcrumbs

app = Flask(__name__)


@app.route("/", methods=['GET', 'POST'])
@app.route("/<path:filename>", methods=['GET', 'POST'])
def appOpen(filename=""):
    if index_file and not filename:
        filename = index_file
    filename = unicode(unquote(filename))
    filepath = unicode(os.path.join(home_dir, filename))
    print "Opening %s " % (filepath)
    if not os.path.exists(filepath):
        abort(404)
    if os.path.isdir(filepath):
        return appBrowse(filename)
    else:
        mime = mimetypes.guess_type(filename)
        if mime[0] == "text/tasklist":
            return appShowTasks(filename)
        if mime[0] == "text/markdown":
            print "Markdown file"
            return appShowMarkdown(filename)
        if mime[0] == "text/html":
            return appShowHTML(filename)
        return appShow(filename)


def appBrowse(filename=""):
    filepath = unicode(os.path.join(home_dir, filename))
    print "Using %s " % (filepath)
    if not filepath.startswith(home_dir):
        filepath = home_dir
    if not os.path.exists(filepath):
        abort(404)
    _files = os.listdir(filepath)
    _files.sort()
    files = []
    for f in _files:
        if not f.startswith(".") or config.getboolean("general", "show_hidden"):
            fn = f
            if os.path.isdir(os.path.join(filepath, f)):
                fn = "[%s]" % f
            files.append({
                "filename": fn,
                "filepath": quote(os.path.join(filename, f).encode('utf-8'))
            })
    title = filename
    if not title:
        title = ""
    if request.method == 'GET':
        return render_template("browse.html", title=title, breadcrumbs=compileBreadcrumbs(title), files=files)
    if request.method == 'POST':
        if not request.form['filename']:
            return render_template("browse.html", title=title, breadcrumbs=compileBreadcrumbs(title), files=files, error="Please enter a filename")
        filepath = os.path.abspath(os.path.join(filepath, request.form['filename']))
        if not filepath.startswith(home_dir):
            return render_template("browse.html", title=title, breadcrumbs=compileBreadcrumbs(title), files=files, error="File outside of directory")
        if os.path.exists(filepath):
            return render_template("browse.html", title=title, breadcrumbs=compileBreadcrumbs(title), files=files, error="File already exists")
        dirs, _filename = os.path.split(filepath)
        if dirs and not os.path.exists(dirs):
            print "Creating directories %s " % (dirs)
            os.makedirs(dirs)
        if _filename:
            print "Creating file %s " % (filepath)
            f = open(filepath, 'w')
            f.write('')
            f.close()
        return redirect("/" + quote(filename.encode('utf-8')))


def appShow(filename=""):
    f = openFile(filename)
    if not f:
        abort(404)
    mime = mimetypes.guess_type(filename)
    if mime[0] is None or mime[0][:4] == "text":
        content = f.read().decode('utf-8')
        if request.method == 'GET':
            return render_template("show.html",
                                   content=content,
                                   title=filename,
                                   breadcrumbs=compileBreadcrumbs(filename),
                                   menu={
                                   "/edit/"+quote(filename.encode('utf-8')): "Edit",
                                   "/get/"+quote(filename.encode('utf-8')): "Raw",
                                   "/delete/"+quote(filename.encode('utf-8')): "Delete"
                                   },
                                   filename=quote(filename.encode('utf-8')))
    else:
        return send_file(os.path.join(home_dir, filename), mimetype=mime[0])


def appShowHTML(filename=""):
    f = openFile(filename)
    if not f:
        abort(404)
    content = f.read().decode('utf-8')
    if request.method == 'GET':
        return render_template("show_html.html",
            content=content,
            title=filename,
            breadcrumbs=compileBreadcrumbs(filename),
            menu={
                "/edit/"+quote(filename.encode('utf-8')) : "Edit",
                "/get/"+quote(filename.encode('utf-8')) : "Raw",
                "/delete/"+quote(filename.encode('utf-8')): "Delete"
            },
            filename=quote(filename.encode('utf-8')))

def appShowMarkdown(filename = ""):
    f = openFile(filename)
    if not f:
        abort(404)
    content = markdown.markdown(f.read().decode('utf-8'))
    if request.method == 'GET':
        return render_template("show_html.html",
            content=content,
            title=filename,
            breadcrumbs=compileBreadcrumbs(filename),
            menu={
                "/edit/"+quote(filename.encode('utf-8')) : "Edit",
                "/get/"+quote(filename.encode('utf-8')) : "Raw",
                "/delete/"+quote(filename.encode('utf-8')): "Delete"
            },
            filename=quote(filename.encode('utf-8')))

def appShowTasks(filename = ""):
    f = openFile(filename)
    if not f:
        abort(404)
    try:
        l = f.readlines()
    except:
        abort(404)
    l.sort()
    tasks = []
    for s in l:
        if len(s) > 1:
            tasks.append( {
                "task":s.decode("utf-8"),
                "id":hashlib.md5(s).hexdigest(),
                "done": (s[:2] == "x ")
            } )
    if request.method == 'GET':
        return render_template("tasklist.html",
            tasks=tasks,
            title=filename,
            breadcrumbs=compileBreadcrumbs(filename),
            menu={
                "/edit/"+quote(filename.encode('utf-8')) : "Edit",
                "/get/"+quote(filename.encode('utf-8')) : "Raw",
                "/delete/"+quote(filename.encode('utf-8')): "Delete"
            },
            filename=quote(filename.encode('utf-8')))
    if request.method == 'POST':
        if not request.form['tasks']:
            return render_template("tasklist.html",
                error="Please enter new tasks",
                tasks=tasks,
                title=filename,
                breadcrumbs=compileBreadcrumbs(filename),
                menu={
                    "/edit/"+quote(filename.encode('utf-8')) : "Edit",
                    "/get/"+quote(filename.encode('utf-8')) : "Raw",
                    "/delete/"+quote(filename.encode('utf-8')): "Delete"
                },
                filename=quote(filename.encode('utf-8')))
        tasks = "\n" + request.form['tasks']
        with open(os.path.join(home_dir, filename), "a") as f:
            f.write(tasks.encode('utf-8'))
        return redirect("/" + quote(filename.encode('utf-8')))


@app.route("/tasks/<path:filename>/<id>/complete")
def appTaskComplete(filename, id):
    filename = unicode(unquote(filename))
    f = openFile(filename)
    if not f:
        abort(404)
    l = f.readlines()
    for i, s in enumerate(l):
        if id == hashlib.md5(s).hexdigest():
            l[i] = "x " + s
    with open(os.path.join(home_dir, filename), 'w') as f:
        f.writelines(l)
    return redirect("/" + quote(filename.encode('utf-8')))


@app.route("/get/<path:filename>")
def appGet(filename):
    filename = unicode(unquote(filename))
    f = openFile(filename)
    if not f:
        abort(404)
    return Response(f.read(), status=200, mimetype='text/plain')


@app.route("/edit/<path:filename>", methods=['GET', 'POST'])
def appEdit(filename):
    filename = unicode(unquote(filename))
    f = openFile(filename)
    if not f:
        abort(404)
    if request.method == 'GET':
        return render_template("edit.html",
            text=f.read().decode('utf-8'),
            title=filename,
            breadcrumbs=compileBreadcrumbs(filename),
            filename=quote(filename.encode('utf-8')))
    if request.method == 'POST':
        text = request.form['text']
        with open(os.path.join(home_dir, filename), "w") as f:
            f.write(text.encode('utf-8'))
        return redirect("/" + quote(filename.encode('utf-8')))


@app.route("/favicon.ico")
def favIcon():
    return redirect("/static/img/favicon.ico")

if __name__ == "__main__":

    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        home_dir = unicode(sys.argv[1])

    home_dir = os.path.abspath(home_dir)

    if os.path.isfile(home_dir):
        home_dir, index_file = os.path.split(home_dir)

    url = "http://localhost:%s" % config.get("httpd", "port")
    print "\nMimir is running at \n\n%s\n" % url
    if config.getboolean("browser", "autostart"):
        print "Trying to open new tab in browser"
        if "" is not config.get("browser", "executable"):
            threading.Timer(1.25, lambda: webbrowser.get(config.get("browser", "executable") + " %s").open(url, 2, True) ).start()
        else:
            threading.Timer(1.25, lambda: webbrowser.open(url, 2, True) ).start()
    app.run(
        host=config.get("httpd", "host"),
        port=config.getint("httpd", "port"),
        debug=True
    )
