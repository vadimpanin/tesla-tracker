CREATE TABLE cars (
    id SERIAL PRIMARY KEY,
    vin VARCHAR NOT NULL UNIQUE CHECK (vin <> '')
);

CREATE TABLE updates (
    id SERIAL PRIMARY KEY,
    carid INTEGER NOT NULL,
    firstseen TIMESTAMP NOT NULL,
    lastseen TIMESTAMP NOT NULL,
    updatehash VARCHAR NOT NULL,
    FOREIGN KEY (carid) REFERENCES cars(id)
);

CREATE TABLE updatedata (
    carid INTEGER NOT NULL,
    updatehash VARCHAR NOT NULL CHECK (updatehash <> ''),
    data JSON NOT NULL CHECK (data::text <> '{}'),
    FOREIGN KEY (carid) REFERENCES cars(id)
);

CREATE UNIQUE INDEX idx_update_data_unique ON updatedata (carid, updatehash);

ALTER TABLE updates ADD CONSTRAINT unique_carid_updatehash UNIQUE (carid, updatehash);
