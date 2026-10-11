# OGC WFS 2.0.0 Service for ISRO MOSDAC SCORPIO Cyclone Tracks

This project builds an open,**OGC Web Feature Service (WFS 2.0.0 / ISO 19142)** over cyclone observation and forecast tracks from ISRO SAC's **SCORPIO** portal (`mosdac.gov.in/scorpio/`).

---

## The Gap

ISRO MOSDAC tracks North Indian Ocean cyclones (Arabian Sea & Bay of Bengal) and visualizes them on SCORPIO. However, the data is trapped behind an internal backend script  intended only for client-side browser rendering. 

MOSDAC provides **no open OGC WFS or OGC API - Features endpoints**. GIS analysts and disaster response systems (NDMA/SDMA) cannot pull these tracks directly into desktop GIS software (QGIS, ArcGIS) or automated pipelines via standard spatial queries. This project and serves them via GeoServer as an OGC WFS 2.0.0 service.

---

## Project Structure

```text
cyber-gis-mosdac-wfs/
├── data/
│   ├── mosdac_all_cyclones.geojson   # Extracted raw GeoJSON
│   ├── mosdac_cyclones.shp           # ESRI Shapefile components
│   ├── mosdac_cyclones.shx
│   ├── mosdac_cyclones.dbf
│   └── mosdac_cyclones.prj
├── scripts/
│   ├── data_extraction.py            # Crawls MOSDAC SCORPIO backend
│   └── geojsontoshp.py                  # Converts GeoJSON to Shapefile
├── web/
│   └── index.html                    # Lightweight Leaflet web viewer
├── docker-compose.yml                # GeoServer container setup
└── README.md
```
---

To run the server type the following command in terminal, ensure that docker is installed in the machine 
```shell
docker compose up
```
It can be then access at

```shell
localhost:8080 
```
on browser.
