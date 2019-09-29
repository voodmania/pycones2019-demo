CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE SEQUENCE IF NOT EXISTS aemet_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 9223372036854775807 START 1 CACHE 1;
ALTER SEQUENCE IF EXISTS aemet_id_seq RESTART WITH 1;
CREATE TABLE IF NOT EXISTS aemet(
    id Integer DEFAULT nextval('aemet_id_seq'::regclass) NOT NULL,
    codigo Character Varying(200) UNIQUE NOT NULL,
    localidad Character Varying(200) NOT NULL,
    url_xml Character Varying(200)
);
CREATE INDEX IF NOT EXISTS index_localidad ON aemet USING btree(localidad Asc NULLS Last);
