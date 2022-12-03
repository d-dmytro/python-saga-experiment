CREATE TABLE sagas
(
    id uuid,
    name character varying NOT NULL,
    data text NOT NULL,
    current_step smallint NOT NULL DEFAULT(0),
    status character varying NOT NULL,
    PRIMARY KEY (id)
);
