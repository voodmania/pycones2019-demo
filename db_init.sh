PGPASSWORD=postgres psql -q -h postgres -U postgres test -f db_init.sql
PGPASSWORD=postgres psql -q -h postgres -U postgres test -c "COPY aemet(codigo, localidad, url_xml) FROM STDIN WITH DELIMITER ',' csv HEADER;" < aemet.csv
