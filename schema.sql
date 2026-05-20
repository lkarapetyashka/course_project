CREATE TABLE IF NOT EXISTS topics ( -- темы 
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS cards ( -- карточки
    id INTEGER PRIMARY KEY ,
    topic_id INTEGER REFERENCES topics(id),
    card_type TEXT NOT NULL CHECK (card_type IN ('theory', 'practice')),
    question TEXT NOT NULL
    
);

CREATE TABLE IF NOT EXISTS options ( -- варианты ответов на карточки
    id INTEGER PRIMARY KEY,
    card_id INTEGER REFERENCES cards(id),
    option_text TEXT NOT NULL,
    is_correct INTEGER NOT NULL CHECK (is_correct IN (0, 1))
);

CREATE TABLE IF NOT EXISTS wrong_cards ( -- неверено решенные карточки
    id INTEGER PRIMARY KEY,
    card_id INTEGER REFERENCES cards(id) UNIQUE
);