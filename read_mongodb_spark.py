import os
from dotenv import load_dotenv
from pymongo import MongoClient
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, IntegerType, ArrayType
from pyspark.sql.functions import explode, col

load_dotenv()

client = MongoClient(os.environ["MONGO_URI"])
collection = client["MovieLensDB"]["UserRatings"]

data = list(collection.find())

clean_data = [
    {
        "user_id": d["user_id"],
        "ratings": [
            {"movie_id": r["movie_id"], "rating": r["rating"], "timestamp": r["timestamp"]}
            for r in d.get("ratings", [])
        ],
    }
    for d in data
]

rating_schema = StructType([
    StructField("movie_id", IntegerType(), True),
    StructField("rating", IntegerType(), True),
    StructField("timestamp", IntegerType(), True),
])
user_schema = StructType([
    StructField("user_id", IntegerType(), True),
    StructField("ratings", ArrayType(rating_schema), True),
])

spark = SparkSession.builder.appName("PersonB-Mongo").getOrCreate()

df_mongo = spark.createDataFrame(clean_data, schema=user_schema)

df_ratings_flat = df_mongo.withColumn("r", explode(col("ratings"))).select(
    "user_id", "r.movie_id", "r.rating", "r.timestamp"
)

df_ratings_flat.show(10)
print("Flattened row count:", df_ratings_flat.count())
df_ratings_flat.printSchema()
