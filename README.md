# check.py im Container
Das Skript `check.py` ruft Daten aus einer Datenbank ab und vergleicht diese mit Daten aus einem RSS Feed. Falls neue Daten vorhanden sind, dann werden diese in einen eigenen RSS Feed geschrieben. Dieser eigene RSS Feed wird über einen Webserver lokal zur Verfügung gestellt.

## Umgebungsvariablen
| Umgebungsvariable | Beschreibung                  | Beispiel                            |
|-------------------|-------------------------------|-------------------------------------|
| DB_HOST           | IP der Datenbank              | 192.168.0.2                         |
| DB_PORT           | DB Port                       | 3307                                |
| DB_NAME           | DB Name                       | MyVideos116                         |
| DB_USER           | DB Benutzername               | ********                            |
| DB_PASSWORD       | DB Passwort                   | ********                            |
| INTERVAL_MINUTEN  | Interval für die Überprüfung  | 60                                  |
| MAX_ITEMS         | Max. Anzahl Items im RSS Feed | 200                                 |
| RSS_URL           | Zu überprüfender Feed         | https://***************ien.xml      |
| TZ                | Zeitzone                      | Europe/Zurich                       |
| FLASK_DEBUG       | Debugmode von Flask           | True                                |

## Endpoints
| Endpoint           | Beschreibung                                                |
|--------------------|-------------------------------------------------------------|
| /                  | Home                                                        |
| /current           | Übersicht über alle Shows bei denen Episoden vorhanden sind |
| /all               | Alle Shows, auch ohne Episoden                              |
| /serien.xml        | RSS Feed                                                    |
| /rss               | RSS Feed als Tabelle                                        |
| /rss/update        | RSS Feed aktualisieren. Öffnet `/rss` nach update.          |
| /filterForm        | RSS Feed Titel nach "term" filtern                          |
| /filter/"term"     | RSS Feed Titel nach "term" gefiltert                        |

## podman (Fedora)

### Build Container
```
cd new_tv_shows
podman build --rm -t newtvshows:latest "."
```

### Run Container
Wichtig ist das `:z`. Ohne hat SElinux ein `permissien dinied` Error.
Die Umgebungsvariablen müssen auch hinzugefügt werden.
```
cd new_tv_shows
podman run -v ./out:/out:z newtvshows
```
### podman-compose
```
pip3 install podman-compose
cd new_tv_shows
podman-compose up -d
```
Will man mit `podman-compose up` die Container neu starten, dann muss zuerst der `pod` gestoppt und gelöscht werden.

```
podman pod stop -a && podman pod rm -a
```
### run_debug.sh
Mit dem Skript werden alle vorhanden `pod` gestopt und gelsöcht und danach das Docker image neu gebaut. Nach dem Build wird der Container gestartet.
```
chmod +x run_debug.sh
./run_debug.sh
```

## docker

### Build Container
```
cd /volume1/docker/new_tv_shows
sudo docker build --rm -t newtvshows:latest "."
```

### docker-compose
```
cd /volume1/docker/new_tv_shows
sudo docker-compose up -d
```
