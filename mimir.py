#!/usr/bin/env python2
# -*- coding: utf8 -*-

import sys, os, hashlib, webbrowser, mimetypes, threading, ConfigParser
import markdown
from flask import (Flask, render_template, request, redirect, abort, Response, send_file, jsonify, session)
from flask.ext.basicauth import BasicAuth
from urllib import unquote, quote, urlencode
from urllib2 import Request, urlopen
from dateutil import parser
from datetime import datetime

script_path, script_name = os.path.split(os.path.realpath(__file__))

home_dir = os.path.expanduser('~')
index_file = None


config = ConfigParser.SafeConfigParser()
config.add_section("general")
config.add_section("security")
config.add_section("browser")
config.add_section("httpd")
config.set("general", "home", "~")
config.set("general", "show_hidden", "false")
config.set("security", "username", "admin")
config.set("security", "password", "")
config.set("browser", "autostart", "true")
config.set("browser", "executable", "")
config.set("httpd", "host", '127.0.0.1')
config.set("httpd", "port", '5212')
config.read([
    script_path + '/mimir.cfg',
    os.path.expanduser('~/.mimir.cfg'),
    os.path.expanduser('~/.config/mimir.cfg'),
    script_path + '/mimir.conf',
    os.path.expanduser('~/.mimir.conf'),
    os.path.expanduser('~/.config/mimir.conf'),
    ])

home_dir = os.path.expanduser(config.get("general", "home"))

mimetypes.add_type("text/markdown", ".md")
mimetypes.add_type("text/markdown", ".markddown")
mimetypes.add_type("text/tasklist", ".task")
mimetypes.add_type("text/tasklist", ".tasks")
mimetypes.add_type("text/timesheet", ".time")
mimetypes.add_type("text/timesheet", ".times")
mimetypes.add_type("text/timesheet", ".tsheet")
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
app.config['SECRET_KEY'] = "MimirIsNotSecure"

if config.get("security", "password") != "":
    app.config['BASIC_AUTH_USERNAME'] = config.get("security", "username")
    app.config['BASIC_AUTH_PASSWORD'] = config.get("security", "password")
    app.config['BASIC_AUTH_REALM'] = "Mímir is password protected"
    app.config['BASIC_AUTH_FORCE'] = True
    BasicAuth(app)

@app.route("/app")
def onePageApp():
    return render_template("app.html", title="Mímir")

@app.route("/", methods=['GET', 'POST'])
@app.route("/+<format>", methods=['GET', 'POST'])
@app.route("/<path:filename>", methods=['GET', 'POST'])
@app.route("/<path:filename>+<format>", methods=['GET', 'POST'])
def appOpen(filename="", format="html"):
    print "APP OPEN"
    if index_file and not filename:
        filename = index_file
    filename = unicode(unquote(filename))
    filepath = unicode(os.path.join(home_dir, filename))
    print "Opening %s " % (filepath)
    if not os.path.exists(filepath):
        abort(404)
    if os.path.isdir(filepath):
        return appBrowse(filename, format)
    else:
        mime = mimetypes.guess_type(filename)
        if mime[0] == "text/tasklist":
            return appShowTasks(filename, format)
        if mime[0] == "text/timesheet":
            return appShowTimesheet(filename, format)
        if mime[0] == "text/markdown":
            print "Markdown file"
            return appShowMarkdown(filename, format)
        if mime[0] == "text/html":
            return appShowHTML(filename, format)
        return appShow(filename, format)


def appBrowse(filename, format):
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
        if format == "json": return jsonify(title=title, breadcrumbs=compileBreadcrumbs(title), files=files, mimetype="directory")
        if format == "html": return render_template("browse.html", title=title, breadcrumbs=compileBreadcrumbs(title), files=files, mimetype="directory")
    if request.method == 'POST':
        if not request.form['filename']:
            if format == "json": return jsonify(error="Please enter a filename")
            if format == "html": return render_template("browse.html", title=title, breadcrumbs=compileBreadcrumbs(title), files=files, error="Please enter a filename")
        filepath = os.path.abspath(os.path.join(filepath, request.form['filename']))
        if not filepath.startswith(home_dir):
            if format == "json": return jsonify(error="File outside of directory")
            if format == "html": return render_template("browse.html", title=title, breadcrumbs=compileBreadcrumbs(title), files=files, error="File outside of directory")
        if os.path.exists(filepath):
            if format == "json": return jsonify(error="File already exists")
            if format == "html": return render_template("browse.html", title=title, breadcrumbs=compileBreadcrumbs(title), files=files, error="File already exists")
        dirs, _filename = os.path.split(filepath)
        if dirs and not os.path.exists(dirs):
            print "Creating directories %s " % (dirs)
            os.makedirs(dirs)
        if _filename:
            print "Creating file %s " % (filepath)
            f = open(filepath, 'w')
            f.write('')
            f.close()
        if format == "json": return jsonify(error=False)
        else: return redirect("/" + quote(filename.encode('utf-8')))


def appShow(filename, format):
    print "SHOW FILE"
    mime = mimetypes.guess_type(filename)
    if mime[0] is None or mime[0][:4] == "text":
        f = openFile(filename)
        if not f:
            abort(404)
        content = f.read().decode('utf-8')
        if request.method == 'GET':
            if format == "json": return jsonify(
                                   content=content,
                                   title=os.path.basename(filename),
                                   breadcrumbs=compileBreadcrumbs(filename),
                                   mimetype=mime[0],
                                   menu={
                                   "/edit/"+quote(filename.encode('utf-8')): "Edit",
                                   "/get/"+quote(filename.encode('utf-8')): "Raw",
                                   "/topdf/"+quote(filename.encode('utf-8'))+".pdf" : "PDF",
                                   "/delete/"+quote(filename.encode('utf-8')): "Delete"
                                   },
                                   filename=quote(filename.encode('utf-8')))
            if format == "html": return render_template("show.html",
                                   content=content,
                                   title=os.path.basename(filename),
                                   breadcrumbs=compileBreadcrumbs(filename),
                                   mimetype=mime[0],
                                   menu={
                                   "/edit/"+quote(filename.encode('utf-8')): "Edit",
                                   "/get/"+quote(filename.encode('utf-8')): "Raw",
                                   "/topdf/"+quote(filename.encode('utf-8'))+".pdf" : "PDF",
                                   "/delete/"+quote(filename.encode('utf-8')): "Delete"
                                   },
                                   filename=quote(filename.encode('utf-8')))
    else:
        if format == "json": return jsonify(
                               href="/get/" + filename,
                               title=os.path.basename(filename),
                               breadcrumbs=compileBreadcrumbs(filename),
                               mimetype=mime[0],
                               menu={
                               "/get/"+quote(filename.encode('utf-8')): "Raw",
                               "/topdf/"+quote(filename.encode('utf-8'))+".pdf" : "PDF",
                               "/delete/"+quote(filename.encode('utf-8')): "Delete"
                               },
                               filename=quote(filename.encode('utf-8')))
        else: return send_file(os.path.join(home_dir, filename), mimetype=mime[0])


def appShowHTML(filename, format):
    f = openFile(filename)
    if not f:
        abort(404)
    mime = mimetypes.guess_type(filename)
    content = f.read().decode('utf-8')
    if request.method == 'GET':
        if format == "json": return jsonify(
            content=content,
            title=os.path.basename(filename),
            breadcrumbs=compileBreadcrumbs(filename),
            mimetype=mime[0],
            menu={
                "/edit/"+quote(filename.encode('utf-8')) : "Edit",
                "/get/"+quote(filename.encode('utf-8')) : "Raw",
                "/topdf/"+quote(filename.encode('utf-8'))+".pdf" : "PDF",
                "/delete/"+quote(filename.encode('utf-8')): "Delete"
            },
            filename=quote(filename.encode('utf-8')))
        if format == "html": return render_template("show_html.html",
            content=content,
            title=os.path.basename(filename),
            breadcrumbs=compileBreadcrumbs(filename),
            mimetype=mime[0],
            menu={
                "/edit/"+quote(filename.encode('utf-8')) : "Edit",
                "/get/"+quote(filename.encode('utf-8')) : "Raw",
                "/topdf/"+quote(filename.encode('utf-8'))+".pdf" : "PDF",
                "/delete/"+quote(filename.encode('utf-8')): "Delete"
            },
            filename=quote(filename.encode('utf-8')))

def appShowMarkdown(filename, format):
    f = openFile(filename)
    if not f:
        abort(404)
    mime = mimetypes.guess_type(filename)
    content = f.read().decode('utf-8')
    content_html = markdown.markdown(content)
    menu = {
        "/edit/"+quote(filename.encode('utf-8')) : "Edit",
        "/get/"+quote(filename.encode('utf-8')) : "Raw",
        "/topdf/"+quote(filename.encode('utf-8'))+".pdf" : "PDF",
        "/delete/"+quote(filename.encode('utf-8')): "Delete"
    }
    if request.method == 'GET':
        if format == "json": return jsonify(
            content=content,
            content_html=content_html,
            title=os.path.basename(filename),
            breadcrumbs=compileBreadcrumbs(filename),
            mimetype=mime[0],
            menu=menu,
            filename=quote(filename.encode('utf-8')))
        if format == "html": return render_template("show_html.html",
            content=content_html,
            title=os.path.basename(filename),
            breadcrumbs=compileBreadcrumbs(filename),
            mimetype=mime[0],
            menu=menu,
            filename=quote(filename.encode('utf-8')))

def appShowTasks(filename, format):
    f = openFile(filename)
    if not f:
        abort(404)
    try:
        l = f.readlines()
    except:
        abort(404)
    l.sort()
    tasks = []
    mime = mimetypes.guess_type(filename)
    menu = {
        "/edit/"+quote(filename.encode('utf-8')) : "Edit",
        "/get/"+quote(filename.encode('utf-8')) : "Raw",
        "/topdf/"+quote(filename.encode('utf-8'))+".pdf" : "PDF",
        "/delete/"+quote(filename.encode('utf-8')): "Delete"
    }
    for s in l:
        if len(s) > 1:
            tasks.append( {
                "task":s.decode("utf-8"),
                "id":hashlib.md5(s).hexdigest(),
                "done": (s[:2] == "x ")
            } )
    if request.method == 'GET':
        if format == "json": return jsonify(
            tasks=tasks,
            title=os.path.basename(filename),
            breadcrumbs=compileBreadcrumbs(filename),
            mimetype=mime[0],
            menu=menu,
            filename=quote(filename.encode('utf-8')))
        if format == "html": return render_template("tasklist.html",
            tasks=tasks,
            title=os.path.basename(filename),
            breadcrumbs=compileBreadcrumbs(filename),
            mimetype=mime[0],
            menu=menu,
            filename=quote(filename.encode('utf-8')))
    if request.method == 'POST':
        if not request.form['tasks']:
            if format == "json": return jsonify(error="Please enter new tasks")
            if format == "html": return render_template("tasklist.html",
                error="Please enter new tasks",
                tasks=tasks,
                title=os.path.basename(filename),
                breadcrumbs=compileBreadcrumbs(filename),
                mimetype=mime[0],
                menu=menu,
                filename=quote(filename.encode('utf-8')))
        tasks = "\n" + request.form['tasks']
        with open(os.path.join(home_dir, filename), "a") as f:
            f.write(tasks.encode('utf-8'))
        if format == "json": return jsonify(error=False)
        else: return redirect("/" + quote(filename.encode('utf-8')))


@app.route("/tasks/<path:filename>/<id>/complete")
@app.route("/tasks/<path:filename>/<id>/complete+<format>")
def appTaskComplete(filename, id, format="html"):
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
    if format == "json": return jsonify(error=False)
    else: return redirect("/" + quote(filename.encode('utf-8')))


def appShowTimesheet(filename, format):
    f = openFile(filename)
    if not f:
        abort(404)
    try:
        l = f.readlines()
    except:
        abort(404)
    l.sort()
    log = []
    mime = mimetypes.guess_type(filename)
    menu = {
        "/edit/"+quote(filename.encode('utf-8')) : "Edit",
        "/get/"+quote(filename.encode('utf-8')) : "Raw",
        "/topdf/"+quote(filename.encode('utf-8'))+".pdf" : "PDF",
        "/delete/"+quote(filename.encode('utf-8')): "Delete"
    }
    seconds = 0
    for s in l:
        a = s.split(";")
        if len(a) >= 2:
            start = parser.parse(a[0])
            end = parser.parse(a[1])
            diff = end - start
            seconds = seconds + diff.seconds
            log.append( {
                "start" : start,
                "end" : end,
                "diff" : diff,
                "comment":a[2].decode("utf-8"),
                "id":hashlib.md5(s).hexdigest()
            } )
        print log
    if request.method == 'GET':
        if format == "json": return jsonify(
            log=log,
            seconds=seconds,
            title=os.path.basename(filename),
            breadcrumbs=compileBreadcrumbs(filename),
            mimetype=mime[0],
            menu=menu,
            filename=quote(filename.encode('utf-8')))
        if format == "html": return render_template("timesheet.html",
            log=log,
            seconds=seconds,
            title=os.path.basename(filename),
            breadcrumbs=compileBreadcrumbs(filename),
            mimetype=mime[0],
            menu=menu,
            filename=quote(filename.encode('utf-8')))
        


@app.route("/timesheet/in/<path:filename>")
def appTimesheetIn(filename):
    if "timesheet_in" in session:
        appTimesheetOut()
    session['timesheet_file'] = quote(filename.encode('utf-8'))
    session['timesheet_in'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return redirect("/" + quote(filename.encode('utf-8')))


@app.route("/timesheet/out")
def appTimesheetOut():
    filename = session['timesheet_file']
    entry = "\n" + session['timesheet_in'] + ";" + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ";"
    with open(os.path.join(home_dir, filename), "a") as f:
        f.write(entry.encode('utf-8'))
    del session['timesheet_file']
    del session['timesheet_in']
    return redirect("/" + quote(filename.encode('utf-8')))


@app.route("/get/<path:filename>")
def appGet(filename):
    filename = unicode(unquote(filename))
    f = openFile(filename)
    if not f:
        abort(404)
    return Response(f.read(), status=200, mimetype='text/plain')


@app.route("/edit/<path:filename>", methods=['GET', 'POST'])
@app.route("/edit/<path:filename>+<format>", methods=['GET', 'POST'])
def appEdit(filename, format="html"):
    filename = unicode(unquote(filename))
    f = openFile(filename)
    if not f:
        abort(404)
    if request.method == 'GET':
        if format == "json": return jsonify(
            text=f.read().decode('utf-8'),
            title=os.path.basename(filename),
            breadcrumbs=compileBreadcrumbs(filename),
            filename=quote(filename.encode('utf-8')))
        if format == "html": return render_template("edit.html",
            text=f.read().decode('utf-8'),
            title=os.path.basename(filename),
            breadcrumbs=compileBreadcrumbs(filename),
            filename=quote(filename.encode('utf-8')))
    if request.method == 'POST':
        text = request.form['text']
        with open(os.path.join(home_dir, filename), "w") as f:
            f.write(text.encode('utf-8'))
        if format == "json": return jsonify(error=False)
        else: return redirect("/" + quote(filename.encode('utf-8')))


@app.route("/topdf/<path:filename>.pdf", methods=['GET', 'POST'])
def getPDF(filename):
    html = appOpen(filename)
    url = "http://riptar.com/v1/htmlpdf/HYHglw3kBEQ2"
    post_data_dictionary = {"html":html.encode("utf-8")}
    post_data_encoded = urlencode(post_data_dictionary)
    request_object = Request(url, post_data_encoded)
    response = urlopen(request_object)
    return Response(response.read(), status=200, mimetype='application/pdf')


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
