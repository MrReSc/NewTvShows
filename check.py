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
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler

# Start Flask
app = Flask(__name__)

# Debug Level
debug_level_str = os.environ["DEBUG_LEVEL"]
debug_level = logging.INFO
flask_debug = "False"
log_path = "./debug.log"

if debug_level_str.lower() == "debug":
    debug_level = logging.DEBUG
    flask_debug = "True"

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=debug_level,
    handlers=[
        # logging.FileHandler(log_path),
        logging.StreamHandler(),
        RotatingFileHandler(log_path, maxBytes=100000, backupCount=0),
    ]
)

app.logger.info("Skript gestartet.")

# Interval Zeit in Minuten
minuteInt = int(os.environ["INTERVAL_MINUTEN"])
app.logger.info("Intervall Zeit ist " + str(minuteInt) + " Minuten.")

# Maximale Anzahl Items im Feed
maxItemsInt = int(os.environ["MAX_ITEMS"])
app.logger.info("Es werden max. " + str(maxItemsInt) + " Items im Feed behalten.")

# Url für RSS Feed der Überwacht werden soll
rssUrl = os.environ["RSS_URL"]
app.logger.info("Der Url " + rssUrl + " wird überwacht.")

# Eigener Feed in out Ordner kopieren wenn nicht vorhanden
if not os.path.exists("./out/serien.xml"):
    os.system("cp ./serien.xml ./out/serien.xml")

# replace.txt in config erstellen wenn nicht vorhanden
if not os.path.exists("./config/replace.txt"):
    os.system("mkdir ./config")
    os.system("touch ./config/replace.txt")

# DB Config
config = {
  "host" : os.environ["DB_HOST"],
  "port" : os.environ["DB_PORT"],
  "database" : os.environ["DB_NAME"],
  "user" : os.environ["DB_USER"],
  "passwd" : os.environ["DB_PASSWORD"]
}

sqlquery = ("SELECT * "
            "FROM ("
                "SELECT 	e.idShow, "
    		                "t.c00 AS 'Name', "
    		                "CAST(e.c12 AS int) AS 'Staffel', "
    		                "CAST(e.c13 AS int) AS 'Episode', "
                "rank() over ( "
                "PARTITION BY t.c00 "
     		    "ORDER BY CAST(e.c12 AS int) DESC, CAST(e.c13 AS int) DESC "
                ") rn "
                "FROM episode e "
                "INNER JOIN tvshow t ON e.idShow=t.idShow "
                ") v "
            "WHERE rn = 1")

sqlqueryAll =  ("SELECT idShow, c00 AS 'Name' "
                "FROM tvshow "
                "WHERE c00 IS NOT NULL "
                "ORDER BY c00")

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
        return element('a', attrs=dict(href=content, target="_blank"), content="Seite öffnen") 

class ItemTableRSS(Table):
    Titel = Col('Titel')
    Episode = Col('Episode')
    Link = ExternalURLCol('Link')
    Datum = Col('Datum')
    Vorhanden = Col('Letzte vorhandene Episode')

def check_job():  
    print("Prüfung wird ausgeführt.")
    mydb = mysql.connector.connect(** config)
    mycursor = mydb.cursor()
    mycursor.execute(sqlqueryName)

    myresult = [item[0] for item in mycursor.fetchall()]
    shows = []
    for show in myresult:
        s = str(show)
        s = cleanName(s)
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

        # Überprüfen ob Titel aus externem RSS Feed schon im eigenen Feed vorhanden ist
        check = True
        for item_e in feed_e["items"]:
            t_e = str(item_e["title"]).replace(".", " ").lower()
            if t_e in t:
                check = False
                break

        # Titel ist nicht im eigenen Feed vorhanden                
        if check:
            # Überprüfen ob eine Show aus der DB im externen Feed vorhanden ist    
            for show in shows:
                if show in t:
                    # Wenn Show vorhadnen ist dann SubElement erstellen
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

def cleanName(name):   
    # Wenn ein File vorhanden ist und nicht leer dann werden die Begiffe ersetzt
    d = {}
    path = "./config/replace.txt"
    if os.path.exists(path) and os.path.getsize(path) > 0:
        with open(path) as f:
            d = dict([line.split("|") for line in f])

        for x, y in d.items():
            name = name.replace(x, y)

    name = re.sub(r'\(.*\)', '', name)                                      # löscht alles in Klammern und Klammern (Blafoo2017)
    name = name.replace("-", " ").replace("–", " ")                         # Bindestriche durch Leerzeichen ersetzten
    name = name.replace("ä", "ae").replace("ü", "ue").replace("ö", "oe")    # äöü ersetzten
    name = re.sub(r'[^A-Za-z0-9 ]+', '', name)                              # löscht alles was nicht Buchstabe, Leerzeichen oder Zahl ist  
    name = re.sub(r' +', ' ', name)                                         # löscht unnötige Leerzeichen
    name = name.lower()                                                     # alles lower case
    app.logger.debug(name)
    return name

def getRSStableData():
    # Diese Methode ruft alle Elemente aus dem eigenen RSS Feed ab und 
    # ergänz sie mit Infos aus der Datenbank 

    # Eigener RSS feed abrufen
    f = feedparser.parse(feedUrl)
    daten = []

    # aktuell vorhande Shows abrufen
    mydb = mysql.connector.connect(** config)
    mycursor = mydb.cursor(dictionary=True)
    mycursor.execute(sqlquery)
    shows = mycursor.fetchall()

    # Titel aus eigenem RSS Feed bereinigen
    for show in shows:
        show["Name"] = cleanName(show["Name"])

    # Jedem Element im eigenen Feed wird, falls vorhanden, die aktuelle Episode aus der DB hinzugefügt
    # Die Staffel/Episode wird aus dem Titel des Feed Elements geparsed  
    for item in f["items"]:
        for show in shows:
            rssName = str(item["title"]).replace(".", " ").lower()
            name = show["Name"]

            # Vorhandene Staffel/Epdisode auf Server
            vorhanden = "S" + str(show["Staffel"]).zfill(2) + "E" + str(show["Episode"]).zfill(2) # mit vornull wenn nicht vorhanden

            # Vorhandene Staffel/Epdisode aus Titel parsen
            match = re.search(r"(?:s)(\d{2})(?:.|)(?:e)(\d{2})", item["title"], re.I)             # regex um S01E01 oder S01.E01 zu finden
            if match:
                episode = match.group().replace(".", "")
            else:
                episode = "-"

            # Veröffentlichungsdatum formatieren
            try: 
                datetime_str = item["published"]
                datetime_object = datetime.strptime(datetime_str, "%a, %d %b %Y %H:%M:%S %z")
                datum = datetime_object.strftime("%d.%m.%Y, %H:%M:%S")
            except:
                datum = item["published"]

            if name in rssName:
                element = dict(Titel=item["title"], Episode=episode, Link=item["link"], Datum=datum, Vorhanden=vorhanden)
                break
            else:
                element = dict(Titel=item["title"], Episode=episode, Link=item["link"], Datum=datum, Vorhanden="-")
        daten.append(element)

    mycursor.close()
    return daten

# Methode beim starten einmalig aufrufen
check_job()

# Background Job starten
scheduler = BackgroundScheduler()
scheduler.add_job(check_job, 'interval', minutes=minuteInt)
scheduler.start()

# Navbar
nav = Nav(app)
nav.register_element('top', Navbar(
    View('Home', 'home'),
    View('RSS Feed', 'rss'),
    View('Aktuelle Episoden', 'current'),
    View('Alle Shows', 'all'),
    View('Log', 'log'),
))

@app.route("/")
def home():
    return redirect('/rss')

@app.route("/current")
def current():
    mydb = mysql.connector.connect(** config)
    mycursor = mydb.cursor(dictionary=True)
    mycursor.execute(sqlquery)
    tabelle = ItemTable(mycursor.fetchall(), border=True)
    mycursor.close()
    return render_template("table.html", table=tabelle, header="Aktuell auf Server vorhandene Shows")

@app.route("/all")
def all():
    mydb = mysql.connector.connect(** config)
    mycursor = mydb.cursor(dictionary=True)
    mycursor.execute(sqlqueryAll)
    tabelle = ItemTableAll(mycursor.fetchall(), border=True)
    mycursor.close() 
    return render_template("table.html", table=tabelle, header="Alle in Datenbank vorhanden Shows")

@app.route("/serien.xml")
def serien():
    return send_from_directory('./out', "serien.xml")

@app.route("/rss", methods = ['POST', 'GET'])
def rss():
    if request.method == 'POST':
        name = request.form['nm']
        return redirect(url_for('filter',name = name))
    else:
        daten = getRSStableData()
        tabelle = ItemTableRSS(daten, border=True, table_id="rssTable")
        return render_template("tableRss.html", table=tabelle, header="Eigener RSS Feed")

@app.route("/rss/update")
def update():
    check_job()
    return redirect('/rss')

@app.route("/filter/<name>")
def filter(name):
    daten = []
    f = getRSStableData()

    for item in f:
        if name.lower() in item["Titel"].lower():
            daten.append(item)

    tabelle = ItemTableRSS(daten, border=True, table_id="rssTable")
    return render_template("table.html", table=tabelle, header="Suchbegriff: '" + name + "'")

@app.route('/log')
def log():
    content = ""
    content_list = []
    with open(log_path, "r") as f:
        lines = f.readlines()
        # Log File inhalt rückwerts einlesen
        for line in reversed(lines):
            content_list.append(line)
        # Liste zu String
        content = "".join(content_list[1:])

    return render_template('log.html', log=content)    

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=flask_debug)

    