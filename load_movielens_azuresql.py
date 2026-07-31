"""Load MovieLens movies/users into Azure SQL using the credential-safe loader."""

from pathlib import Path
import pandas as pd
from azure_sql_loader import loader_from_dotenv

DATA = Path.home() / "bigdata_lab" / "data" / "movielens" / "ml-1m"
DDL = Path("ddl_movielens_schema.sql")

loader = loader_from_dotenv()
assert loader.validate_connection(), "Azure SQL connection failed — check .env"

loader.ensure_schema(DDL)

# --- movies ---
movies = pd.read_csv(
    DATA / "movies.dat", sep="::", engine="python",
    names=["movie_id", "title", "genres"], encoding="latin-1",
)
n_movies = loader.write_rows(
    "movies", ["movie_id", "title", "genres"],
    movies[["movie_id", "title", "genres"]].itertuples(index=False, name=None),
)

# --- users ---
users = pd.read_csv(
    DATA / "users.dat", sep="::", engine="python",
    names=["user_id", "gender", "age", "occupation", "zip_code"], encoding="latin-1",
)
n_users = loader.write_rows(
    "users", ["user_id", "gender", "age", "occupation", "zip_code"],
    users[["user_id", "gender", "age", "occupation", "zip_code"]].itertuples(index=False, name=None),
)

print(loader.reconcile_count("movies", n_movies))
print(loader.reconcile_count("users", n_users))
