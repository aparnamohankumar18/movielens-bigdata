import os
import pandas as pd
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

DATA = os.path.expanduser("~/bigdata_lab/data/movielens/ml-1m")

ratings = pd.read_csv(
    f"{DATA}/ratings.dat", sep="::", engine="python",
    names=["user_id", "movie_id", "rating", "timestamp"], encoding="latin-1",
)

# group by user_id, nest each user's ratings as an array
grouped = ratings.groupby("user_id").apply(
    lambda x: x[["movie_id", "rating", "timestamp"]].to_dict("records")
).to_dict()

documents = [{"user_id": uid, "ratings": recs} for uid, recs in grouped.items()]

client = MongoClient(os.environ["MONGO_URI"])
db = client["MovieLensDB"]
collection = db["UserRatings"]

result = collection.insert_many(documents)
print(f"Inserted {len(result.inserted_ids)} user documents")
