# Solakon ONE Nulleinspeisung

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![HA Version](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue)](https://www.home-assistant.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Vollautomatische **Nulleinspeisung** für den **Solakon ONE** Wechselrichter als native Home Assistant Integration — kein Blueprint, keine Helfer-Entitäten, keine manuelle YAML-Pflege.

Die Integration regelt die Ausgangsleistung des Wechselrichters über einen **PI-Regler** so, dass der Netzbezug möglichst bei 0 W gehalten wird. Alle Parameter werden über ein **Sidebar-Panel** direkt in der HA-Oberfläche konfiguriert und persistent gespeichert.

---

## Funktionsübersicht

### Kernfunktion — Nulleinspeisung mit PI-Regler

Die Netzleistung ist die Regelgröße, die Wechselrichterausgangsleistung die Stellgröße. Der P-Anteil reagiert sofort auf Abweichungen, der I-Anteil gleicht dauerhaften Offset aus. Ein konfigurierbares Totband verhindert unnötige Stelleingriffe bei kleinen Schwankungen.

### SOC-Zonenverwaltung

Das Verhalten wird abhängig vom Batterie-Ladestand in vier Zonen eingeteilt:

| Zone | Bedingung | Verhalten |
|------|-----------|-----------|
| **Zone 0** | SOC ≥ Export-Schwelle (optional) | Überschuss-Einspeisung — Leistung über Eigenbedarf hinaus |
| **Zone 1** | SOC ≥ Zone-1-Schwelle | Aggressive Entladung — erhöhter Entladestrom |
| **Zone 2** | Zone-3-Schwelle < SOC < Zone-1-Schwelle | Normalbetrieb — batterieschonend |
| **Zone 3** | SOC ≤ Zone-3-Schwelle | Sicherheitsstopp — Entladung gesperrt |

### Optionale Module

**☀️ Überschuss-Einspeisung (Zone 0)** — Wenn PV-Erzeugung den Eigenbedarf um mehr als eine konfigurierbare Hysterese übersteigt und der SOC eine Zielschwelle erreicht hat, wird der Wechselrichter über den Nullpunkt hinaus angesteuert. Ein SOC-Hysterese-Band verhindert Flackern beim Ein- und Ausschalten.

**⚡ AC-Laden** — Steuert den Wechselrichter in den Lademodus, wenn der SOC unter ein Ziel fällt. Eigener PI-Regler mit separaten P/I-Faktoren, eigenem Offset und konfigurierbarer Leistungsobergrenze.

**💹 Tarif-Arbitrage** — Wertet einen externen Strompreis-Sensor aus und lädt bei günstigem Tarif automatisch auf, sperrt die Entladung bei mittlerem Tarif und gibt sie bei teurem Tarif wieder frei.

**🌙 Nachtabschaltung** — Unterdrückt in Zone 2 den Entladebetrieb unterhalb einer konfigurierbaren PV-Erzeugungsschwelle (Nacht/Bewölkung).

### 📊 Interner Stabilitätssensor

Die Integration berechnet intern die **Standardabweichung der Netzleistung** über ein konfigurierbares Zeitfenster (Standard: 60 s). Der Sensor wird ohne externe Helfer direkt aus dem Messwert-Stream erzeugt und gibt eine Aussage über die Netzstabilität — nützlich zur Diagnose und als Grundlage für dynamische Offset-Logik.

---

## Voraussetzungen

- Home Assistant 2024.1 oder neuer
- [HACS](https://hacs.xyz) installiert
- Solakon ONE Wechselrichter mit Modbus-Integration in HA
- Sensor für die Netzleistung (z. B. Shelly 3EM, Shelly PM)

Die folgenden Solakon-Entitäten müssen in HA vorhanden sein und werden beim Einrichten zugewiesen:

| Typ | Beschreibung |
|-----|-------------|
| `sensor` (power) | Netzleistung |
| `sensor` (power) | Tatsächliche WR-Ausgangsleistung |
| `sensor` (power) | PV-Erzeugungsleistung |
| `sensor` (battery) | Batterieladestand (SOC) |
| `sensor` | Remote-Timeout-Countdown |
| `number` | Ausgangsleistungsregler |
| `number` | Maximaler Entladestrom |
| `number` | Modus-Reset-Timer |
| `select` | Betriebsmodus |

---

## Installation

### Über HACS (empfohlen)

1. HACS öffnen → **Integrationen** → drei Punkte oben rechts → **Benutzerdefiniertes Repository hinzufügen**
2. URL eintragen: `https://github.com/D4nte85/Solakon-One-Nulleinspeisung-Blueprint-homeassistant`
3. Kategorie: **Integration** → **Hinzufügen**
4. Die Integration **Solakon ONE Nulleinspeisung** erscheint in der Liste → **Herunterladen**
5. Home Assistant neu starten

### Manuell

Repository klonen oder als ZIP herunterladen und den Ordner `custom_components/solakon_nulleinspeisung` in das Verzeichnis `config/custom_components/` der HA-Installation kopieren, dann HA neu starten.

---

## Einrichtung

Nach dem Neustart unter **Einstellungen → Geräte & Dienste → Integration hinzufügen** nach *Solakon* suchen.

Im Einrichtungsformular werden die neun Pflichtentitäten zugewiesen. Alle weiteren Parameter (PI-Regler, SOC-Zonen, optionale Module) werden **nicht** im Config-Flow konfiguriert, sondern ausschließlich über das **Sidebar-Panel**.

---

## Konfiguration im Sidebar-Panel

Nach der Einrichtung erscheint in der HA-Seitenleiste der Eintrag **Solakon ONE**. Das Panel ist in sieben Tabs gegliedert:

### 📊 Status

Zeigt in Echtzeit:
- Aktuell aktive Zone mit farblichem Banner
- Netzleistung, Solarleistung, SOC
- Netz-Standardabweichung (Stabilitätsindikator)
- PI-Integral-Wert
- Letzte Aktion und etwaige Fehlermeldungen
- Schaltfläche zum manuellen Zurücksetzen des PI-Integrals

### 🎛️ PI-Regler

| Parameter | Beschreibung | Empfehlung |
|-----------|-------------|------------|
| P-Faktor | Proportionale Verstärkung — sofortige Reaktion auf Abweichung | 0,3–0,8 |
| I-Faktor | Integrale Verstärkung — gleicht dauerhaften Offset aus | 0,05–0,15 |
| Totband (W) | Abweichungen innerhalb dieses Bereichs lösen keinen Stelleingriff aus | 0–30 |
| Wartezeit (s) | Pause zwischen Stelleingriffen — lässt MPPT-Rampen auschwingen | 10–20 |
| Stabw.-Fenster (s) | Zeitfenster für den internen Standardabweichungs-Sensor | 30–300 |

**PI-Einstellung von Grund auf:** P-Faktor auf 0,5 und I-Faktor auf 0 setzen. Wartezeit auf 15 s. Beobachten, ob der Regler schwingt oder zu träge ist, dann P schrittweise anpassen. I erst einführen, wenn P-Regelung stabil ist.

### 🔋 Zonen

Schwellen, Offsets und der Leistungs-Hard-Limit. Der **Nullpunkt-Offset** verschiebt den Zielwert des Reglers — ein negativer Wert von z. B. −20 W lässt den Regler auf −20 W Netzbezug regeln (leichter Puffer gegen versehentliche Einspeisung).

### ☀️ Überschuss, ⚡ AC Laden, 💹 Tarif, 🌙 Nacht

Jedes optionale Modul hat einen eigenen Tab mit einer Aktivierungs-Checkbox. Deaktivierte Module haben keinen Einfluss auf den Regelkreis.

Änderungen werden erst nach Klick auf **💾 Speichern** übernommen. Die Speicherleiste erscheint automatisch sobald ein Wert geändert wurde.

---

## Erzeugte Entitäten

Die Integration erzeugt automatisch folgende Entitäten unter dem Gerät **Solakon ONE**:

| Entität | Typ | Beschreibung |
|---------|-----|-------------|
| `sensor.solakon_one_aktuelle_zone` | Sensor | Aktive Zone (0–3) mit Zusatzattributen |
| `sensor.solakon_one_betriebsmodus` | Sensor | Lesbarer Modustext |
| `sensor.solakon_one_letzte_aktion` | Sensor | Letzter Logeintrag der Steuerlogik |
| `sensor.solakon_one_netz_standardabweichung` | Sensor | Netz-Stabw. in W über das konfigurierte Fenster |
| `number.solakon_one_pi_integral` | Number | Aktueller I-Anteil (schreibgeschützt, nur zur Anzeige) |
| `switch.solakon_one_entladezyklus_aktiv` | Switch | Internes Flag Entladezyklus |
| `switch.solakon_one_uberschuss_modus` | Switch | Flag Überschuss-Modus aktiv |
| `switch.solakon_one_ac_laden_aktiv` | Switch | Flag AC-Laden aktiv |
| `switch.solakon_one_tarif_laden_aktiv` | Switch | Flag Tarif-Laden aktiv |

Die Switch-Entitäten sind schreibgeschützt — sie spiegeln interne Zustände wider und können nicht manuell geschaltet werden.

---

## Fehlerbehebung

**Panel öffnet sich, zeigt aber keine Werte an**
Integration neu laden (Einstellungen → Geräte & Dienste → Solakon → drei Punkte → Neu laden). Falls das Problem bleibt, HA-Protokoll auf Fehler der Domain `solakon_nulleinspeisung` prüfen.

**Werte werden nicht gespeichert**
Im Browser-Konsolenfenster (F12) nach WebSocket-Fehlern schauen. Häufige Ursache: Integration wurde noch nicht vollständig geladen.

**Regler schwingt (Leistung pendelt stark)**
P-Faktor reduzieren oder Wartezeit erhöhen. Der Standardabweichungs-Sensor im Status-Tab zeigt, wie instabil das Netz gerade ist — bei hohem Wert (> 50 W) größeres Totband setzen.

**Zone 3 aktiv, obwohl Batterie nicht leer ist**
Zone-3-Schwelle im Zonen-Tab prüfen. Wert muss kleiner als Zone-1-Schwelle sein.

**Integration taucht nach Installation nicht auf**
Home Assistant vollständig neu starten (nicht nur neu laden). HACS-Download-Status überprüfen.

---

## Lizenz

MIT — siehe [LICENSE](LICENSE)

---

## Autor

[@D4nte85](https://github.com/D4nte85)
