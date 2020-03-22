var table = document.getElementById("rssTable");

if (table) {
    for (var i = 0 ; i < table.rows.length; i++) {
        var epis_e = parseInt(table.rows[i].cells[1].innerHTML.slice(4, 6));
        var epis_s = parseInt(table.rows[i].cells[1].innerHTML.slice(1, 3));

        var vorh_e = parseInt(table.rows[i].cells[4].innerHTML.slice(4, 6));
        var vorh_s = parseInt(table.rows[i].cells[4].innerHTML.slice(1, 3));

        // Staffel > vorhanden oder Staffel = vorhanden und Episode >
        if (epis_s > vorh_s || (epis_s == vorh_s && epis_e > vorh_e)) {
            table.rows[i].cells[0].className = "episodeColored";
            table.rows[i].cells[1].className = "episodeColored";
        }
    }
}