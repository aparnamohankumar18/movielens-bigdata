DROP TABLE IF EXISTS dbo.movies;
DROP TABLE IF EXISTS dbo.users;

CREATE TABLE dbo.movies (
    movie_id INT PRIMARY KEY,
    title NVARCHAR(500),
    genres NVARCHAR(500)
);

CREATE TABLE dbo.users (
    user_id INT PRIMARY KEY,
    gender NVARCHAR(10),
    age INT,
    occupation INT,
    zip_code NVARCHAR(20)
);
