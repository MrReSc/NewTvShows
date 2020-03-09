import feedparser
import mysql.connector
import re
from lxml import etree as ET
from apscheduler.schedulers.background import BackgroundScheduler
import os
from flask import Flask, send_from_directory, render_template, redirect
from flask_table import Table, Col
from flask_table.html import element
from flask_nav import Nav
from flask_nav.elements import *

print("Skript gestartet.")

# Interval Zeit in Minuten
minuteInt = int(os.environ["INTERVAL_MINUTEN"])
print("Intervall Zeit ist " + str(minuteInt) + " Minuten.")

# Maximale Anzahl Items im Feed
maxItemsInt = int(os.environ["MAX_ITEMS"])
print("Es werden max. " + str(maxItemsInt) + " Items im Feed behalten.")

# Url für RSS Feed der Überwacht werden soll
rssUrl = os.environ["RSS_URL"]
print("Der Url " + rssUrl + " wird überwacht.")

# Flask debug
flask_debug=os.environ["FLASK_DEBUG"]

# Eigener Feed in out Ordner kopieren wenn nicht vorhanden
if not os.path.exists("./out/serien.xml"):
    os.system("cp ./serien.xml ./out/serien.xml")

# DB Config
config = {
  "host" : os.environ["DB_HOST"],
  "port" : os.environ["DB_PORT"],
  "database" : os.environ["DB_NAME"],
  "user" : os.environ["DB_USER"],
  "passwd" : os.environ["DB_PASSWORD"]
}

# SQL queries
sqlquery = "SELECT 	e.idShow, " \
		            "t.c00 AS 'Name', " \
		            "MAX(CAST(e.c12 AS int)) AS 'Staffel', " \
                    "MAX(CAST(e.c13 AS int)) AS 'Episode' " \
            "FROM episode e " \
            "INNER JOIN tvshow t ON e.idShow=t.idShow " \
            "GROUP BY e.idShow " \
            "ORDER BY t.c00"

sqlqueryAll =   "SELECT 	idShow, c00 AS 'Name'" \
                "FROM tvshow " \
                "WHERE c00 IS NOT NULL " \
                "ORDER BY c00"

sqlqueryName = "SELECT c00 FROM tvshow WHERE c00 IS NOT NULL"

feedUrl = "./out/serien.xml"

class ItemTable(Table):
    idShow = Col('idShow')
    Name = Col('Name')
    Staffel = Col('Staffel')
    Episode = Col('Episode')

class ItemTableAll(Table):
    idShow = Col('idShow')
    Name = Col('Name')

class ExternalURLCol(Col):
    def td_format(self, content):
        return element('a', attrs=dict(href=content, target="_blank"), content="Link öffnen") 

class ItemTableFilter(Table):
    Titel = Col('Titel')
    Link = ExternalURLCol('Link')
    Datum = Col('Datum')

def check_job():  
    print("Prüfung wird ausgeführt.")
    mydb = mysql.connector.connect(** config)
    mycursor = mydb.cursor()
    mycursor.execute(sqlqueryName)

    myresult = [item[0] for item in mycursor.fetchall()]
    shows = []
    for show in myresult:
        s= str(show)
        s = s.replace(":", "")
        s = s.replace(".", "")
        s = s.replace("-", " ")
        s = s.replace("   ", "  ")
        s = s.replace("  ", " ")
        s = s.replace("'", "")
        s = s.replace("ä", "ae")
        s = s.replace("ü", "ue")
        s = s.replace("ö", "oe")
        s = s.replace("F***ing", "Fucking")

        s = re.sub(r'\(.*\)', '', s)
        s = s.lower()

        if s not in shows:
            shows.append(s)

    # Eigener RSS Feed öffnen
    parser = ET.XMLParser(remove_blank_text=True)
    tree = ET.parse(feedUrl, parser)
    channel = tree.getroot()

    # RSS feed von extern abrufen
    feed = feedparser.parse(rssUrl)

    # Eigener RSS feed abrufen
    url_e = feedUrl
    feed_e = feedparser.parse(url_e)

    # Überprufen ob neue Epdisoden vorhanden sind
    for i in feed["items"]:
        t = str(i["title"]).replace(".", " ").lower()

        # Überprüfen ob Titel schon in einem Feed vorhanden ist
        check = True
        for item_e in feed_e["items"]:
            t_e = str(item_e["title"]).replace(".", " ").lower()
            if t_e in t:
                check = False
                break

        if check:    
            for show in shows:
                if show in t:

                    # SubElement erstellen
                    item = ET.SubElement(channel, "item")
                    title = ET.SubElement(item, "title")
                    link = ET.SubElement(item, "link")
                    pubDate = ET.SubElement(item, "pubDate")
                    title.text = i["title"]
                    link.text = i["link"]
                    pubDate.text = i["published"]

                    # Zu oberst einfügen
                    channel.find(".//description").addnext(item)


    # Eigener RSS feed schreiben
    tree = ET.ElementTree(channel)
    tree.write(feedUrl, pretty_print=True, xml_declaration=True)

    # Eigener RSS feed grösse überprüfen
    parser = ET.XMLParser(remove_blank_text=True)
    tree = ET.parse(feedUrl, parser)
    channel = tree.getroot()
    leng = tree.xpath("count(//item)")
    max_leng = maxItemsInt
    count = 0

    if leng > max_leng:
        for element in channel:
            for item in element.iter("item"):
                count += 1
                if count > max_leng:
                    element.remove(item)

            tree = ET.ElementTree(channel)
            tree.write(feedUrl, pretty_print=True, xml_declaration=True)

    mycursor.close()      


check_job()

scheduler = BackgroundScheduler()
scheduler.add_job(check_job, 'interval', minutes=minuteInt)
scheduler.start()

# Start Flask
app = Flask(__name__)

# Navbar
nav = Nav(app)
nav.register_element('top', Navbar(
    View('Home', 'home'),
    View('Aktuell vorhanden', 'current'),
    View('Alle in DB', 'all'),
    View('RSS Feed', 'rss'),
    View('RSS Feed filtern', 'filterForm'),
    View('RSS Feed updaten', 'update')
))

@app.route("/")
def home():
    return redirect('/current')

@app.route("/current")
def current():
    mydb = mysql.connector.connect(** config)
    mycursor = mydb.cursor(dictionary=True)
    mycursor.execute(sqlquery)
    tabelle = ItemTable(mycursor.fetchall(), border=True)
    mycursor.close()
    return render_template("table.html", table=tabelle, header="Aktuelle auf Server vorhanden")

@app.route("/all")
def all():
    mydb = mysql.connector.connect(** config)
    mycursor = mydb.cursor(dictionary=True)
    mycursor.execute(sqlqueryAll)
    tabelle = ItemTableAll(mycursor.fetchall(), border=True)
    mycursor.close() 
    return render_template("table.html", table=tabelle, header="Alle in Datenbank vorhanden")

@app.route("/serien.xml")
def serien():
    return send_from_directory('./out', "serien.xml")

@app.route("/rss")
def rss():
    # Eigener RSS feed abrufen
    f = feedparser.parse(feedUrl)
    daten = []

    for item in f["items"]:
        element = dict(Titel=item["title"], Link=item["link"], Datum=item["published"])
        daten.append(element)

    tabelle = ItemTableFilter(daten, border=True)
    return render_template("table.html", table=tabelle, header="Eigener RSS Feed")

@app.route("/rss/update")
def update():
    check_job()
    return redirect('/rss')

@app.route("/filterForm", methods = ['POST', 'GET'])
def filterForm():
    if request.method == 'POST':
        name = request.form['nm']
        return redirect(url_for('filter',name = name))
    else:
        return render_template("filter.html", header="Eigener RSS Feed filtern")

@app.route("/filter/<name>")
def filter(name):
    # Eigener RSS feed abrufen
    f = feedparser.parse(feedUrl)
    daten = []

    for item in f["items"]:
        if name.lower() in item["title"].lower():
            element = dict(Titel=item["title"], Link=item["link"], Datum=item["published"])
            daten.append(element)

    tabelle = ItemTableFilter(daten, border=True)
    return render_template("table.html", table=tabelle, header="Eigener RSS Feed gefiltert nach '" + name + "'")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=flask_debug)