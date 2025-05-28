CREATE TABLE profiles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50),
    email VARCHAR(100),
    bio TEXT
);

CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    title VARCHAR(100),
    content TEXT,
    profile_id INTEGER REFERENCES profiles(id)
);

insert into profiles (name, email, bio) values ('Vladimir', 'v.ivanov@somemail.com', '');
insert into documents (title, content, profile_id) values ('Report', 'Report content', 1);